"""One BLE owner, serialized display requests, automatic reconnect and replay."""
import argparse
import asyncio
import base64
import contextlib
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import signal
import tempfile
import time
import uuid
from led_rpc import MAX_MESSAGE_BYTES, validate_gif
from led_transport import ADDRESS, Transport


def utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def atomic_write(path, data):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


class LedManager:
    def __init__(self, socket, state_dir, initial=None, transport_factory=Transport, retry_scale=1):
        self.socket = Path(socket)
        self.state_dir = Path(state_dir)
        self.assets = self.state_dir / 'assets'
        self.assets.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / 'display.json'
        self.desired = None
        self.confirmed = None
        self.generation = 0
        self.confirmed_version = -1
        try:
            stored = json.loads(self.state_file.read_text())
            self.desired = stored.get('desired')
            self.confirmed = stored.get('confirmed')
            self.generation = int(stored.get('generation', 0))
            if self.desired:
                self.asset_bytes(self.desired)
        except FileNotFoundError:
            pass
        except Exception:
            logging.exception('DISPLAY_STATE_INVALID; using initial asset')
            self.desired = self.confirmed = None
        if self.desired is None and initial:
            self.desired = self.stage(Path(initial).read_bytes(), Path(initial).name)
            self.generation += 1
        self.instance = uuid.uuid4().hex[:12]
        self.phase = 'starting'
        self.connection_id = 0
        self.connect_attempts = 0
        self.link_losses = 0
        self.confirmations = 0
        self.last_error = None
        self.connected_at = None
        self.disconnected_at = None
        self.active = None
        self.jobs = asyncio.Queue(maxsize=16)
        self.futures = set()
        self.handlers = set()
        self.stop = asyncio.Event()
        self.wake = asyncio.Event()
        self.retry_scale = retry_scale
        self.transport = transport_factory(self.link_lost, self.set_phase)
        self.owner_lock = None
        self.server = None

    def stage(self, image, label):
        validate_gif(image)
        digest = hashlib.sha256(image).hexdigest()
        path = self.assets / (digest + '.gif')
        if not path.exists():
            atomic_write(path, image)
        return {'sha256': digest, 'label': str(label)[:120], 'bytes': len(image)}

    def asset_bytes(self, asset):
        digest = asset['sha256']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid asset digest')
        image = (self.assets / (digest + '.gif')).read_bytes()
        validate_gif(image)
        if hashlib.sha256(image).hexdigest() != digest:
            raise ValueError('Stored GIF checksum mismatch')
        return image

    def persist(self):
        atomic_write(self.state_file, json.dumps({'version': 1,
            'generation': self.generation, 'desired': self.desired,
            'confirmed': self.confirmed}, ensure_ascii=False).encode())

    def set_phase(self, phase):
        self.phase = phase

    def link_lost(self):
        self.link_losses += 1
        self.disconnected_at = utc()
        self.phase = 'disconnected'
        logging.warning('LINK_DOWN instance=%s connection=%d losses=%d',
                        self.instance, self.connection_id, self.link_losses)

    def status(self):
        return {'ok': True, 'instance': self.instance, 'pid': os.getpid(),
            'target': ADDRESS, 'phase': self.phase,
            'connected': self.transport.connected, 'connection_id': self.connection_id,
            'connect_attempts': self.connect_attempts, 'link_losses': self.link_losses,
            'connected_at': self.connected_at, 'disconnected_at': self.disconnected_at,
            'last_error': self.last_error, 'desired': self.desired,
            'confirmed': self.confirmed, 'confirmations': self.confirmations,
            'pending_jobs': self.jobs.qsize(),
            'active_request': self.active['id'] if self.active else None}

    async def handle(self, reader, writer):
        task = asyncio.current_task()
        self.handlers.add(task)
        try:
            line = await asyncio.wait_for(reader.readline(), 5)
            if not line or len(line) > MAX_MESSAGE_BYTES:
                raise ValueError('Invalid request size')
            data = json.loads(line)
            if data.get('cmd') == 'status':
                result = self.status()
            elif data.get('cmd') == 'show':
                if self.jobs.full() or self.stop.is_set():
                    raise RuntimeError('Display queue is full or stopping')
                image = base64.b64decode(data['image'], validate=True)
                asset = self.stage(image, data.get('label', 'image'))
                self.generation += 1
                self.desired = asset
                self.persist()  # Accepted intent survives a daemon restart.
                future = asyncio.get_running_loop().create_future()
                self.futures.add(future)
                future.add_done_callback(self.futures.discard)
                job = {'asset': asset, 'future': future, 'version': self.generation,
                       'id': str(data.get('id', uuid.uuid4().hex))[:80], 'failures': 0}
                self.jobs.put_nowait(job)
                self.wake.set()
                logging.info('DISPLAY_ACCEPTED id=%s asset=%s generation=%d',
                             job['id'], asset['label'], self.generation)
                wait = max(.01, min(120, float(data.get('wait', 110))))
                try:
                    result = await asyncio.wait_for(asyncio.shield(future), wait)
                except asyncio.TimeoutError:
                    result = {'ok': True, 'pending': True, 'id': job['id'],
                              'message': 'Accepted; will send automatically after reconnection',
                              'status': self.status()}
            else:
                raise ValueError('Unknown command')
        except asyncio.CancelledError:
            raise
        except Exception as error:
            result = {'ok': False, 'error': type(error).__name__ + ': ' + str(error)}
        finally:
            try:
                if not task.cancelled() and 'result' in locals():
                    writer.write(json.dumps(result, ensure_ascii=False).encode() + b'\n')
                    await writer.drain()
            except (OSError, ConnectionError, asyncio.CancelledError):
                pass
            writer.close()
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await writer.wait_closed()
            self.handlers.discard(task)

    async def backoff(self, streak):
        delay = (min(30, 2 ** min(streak, 5)) + random.uniform(0, .25)) * self.retry_scale
        self.phase = 'reconnecting'
        logging.info('RECONNECT_WAIT seconds=%.2f', delay)
        try:
            await asyncio.wait_for(self.wake.wait(), delay)
        except asyncio.TimeoutError:
            pass
        self.wake.clear()

    def error(self, error):
        self.last_error = {'time': utc(), 'type': type(error).__name__, 'message': str(error)}
        logging.warning('BLE_OPERATION_FAILED %s: %s', type(error).__name__, error)

    async def actor(self):
        streak = 0
        replay = True
        job = None
        while True:
            if not self.transport.connected:
                self.connect_attempts += 1
                logging.info('CONNECT_ATTEMPT number=%d', self.connect_attempts)
                try:
                    await self.transport.connect()
                    self.connection_id += 1
                    self.connected_at = utc()
                    self.phase = 'connected'
                    self.last_error = None
                    streak = 0
                    replay = True
                    logging.info('LINK_UP instance=%s connection=%d', self.instance, self.connection_id)
                except Exception as error:
                    self.error(error)
                    await self.transport.close()
                    streak += 1
                    await self.backoff(streak)
                    continue
            if job is None:
                if not self.jobs.empty():
                    job = self.jobs.get_nowait()
                elif replay and self.desired:
                    job = {'asset': self.desired, 'version': self.generation,
                           'id': 'restore-' + str(self.connection_id), 'future': None, 'failures': 0}
                else:
                    incoming = asyncio.create_task(self.jobs.get())
                    lost = asyncio.create_task(self.transport.disconnected.wait())
                    try:
                        done, _ = await asyncio.wait([incoming, lost], timeout=5,
                                                    return_when=asyncio.FIRST_COMPLETED)
                        if incoming in done:
                            job = incoming.result()
                        elif lost not in done:
                            await self.transport.health()
                    except Exception as error:
                        self.error(error)
                        await self.transport.close()
                    finally:
                        for task in (incoming, lost):
                            if not task.done():
                                task.cancel()
                        await asyncio.gather(incoming, lost, return_exceptions=True)
                        if job is None and incoming.done() and not incoming.cancelled() and incoming.exception() is None:
                            job = incoming.result()
                    if job is None:
                        continue
            self.active = job
            if not self.transport.connected:
                continue
            self.phase = 'sending'
            try:
                receipt = await self.transport.show(self.asset_bytes(job['asset']))
            except Exception as error:
                self.error(error)
                job['failures'] += 1
                await self.transport.close()
                if job['failures'] >= 3:
                    if job['future'] and not job['future'].done():
                        job['future'].set_result({'ok': False, 'error': str(error), 'id': job['id']})
                    if job['version'] == self.generation:
                        self.desired = self.confirmed['asset'] if self.confirmed else None
                        self.persist()
                    logging.error('DISPLAY_FAILED id=%s after=3-transfer-attempts', job['id'])
                    job = self.active = None
                streak += 1
                await self.backoff(streak)
                continue
            self.confirmations += 1
            self.confirmed = {'asset': job['asset'], 'time': utc(),
                              'connection_id': self.connection_id, 'receipt': receipt}
            self.confirmed_version = job['version']
            self.persist()
            result = {'ok': True, 'pending': False, 'id': job['id'],
                      'instance': self.instance, 'connection_id': self.connection_id,
                      'asset': job['asset'], 'receipt': receipt}
            logging.info('DISPLAY_CONFIRMED id=%s connection=%d asset=%s frames=%s cached=%s',
                         job['id'], self.connection_id, job['asset']['label'],
                         receipt.get('frames'), receipt.get('cached'))
            if job['future'] and not job['future'].done():
                job['future'].set_result(result)
            job = self.active = None
            replay = False
            self.phase = 'connected'
            streak = 0

    async def run(self):
        self.socket.parent.mkdir(parents=True, exist_ok=True)
        self.owner_lock = open(self.socket.parent / 'owner.lock', 'a')
        try:
            fcntl.flock(self.owner_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.owner_lock.close()
            self.owner_lock = None
            raise
        self.owner_lock.seek(0)
        self.owner_lock.truncate()
        self.owner_lock.write(str(os.getpid()))
        self.owner_lock.flush()
        with contextlib.suppress(FileNotFoundError):
            self.socket.unlink()
        self.persist()
        self.server = await asyncio.start_unix_server(self.handle, path=str(self.socket),
                                                     limit=MAX_MESSAGE_BYTES + 1)
        os.chmod(self.socket, 0o660)
        logging.info('LED_MANAGER_READY instance=%s socket=%s', self.instance, self.socket)
        actor = asyncio.create_task(self.actor())
        stopped = asyncio.create_task(self.stop.wait())
        try:
            done, _ = await asyncio.wait([actor, stopped], return_when=asyncio.FIRST_COMPLETED)
            if actor in done:
                await actor
        finally:
            self.phase = 'stopping'
            self.server.close()
            await self.server.wait_closed()
            for task in (actor, stopped):
                task.cancel()
            await asyncio.gather(actor, stopped, return_exceptions=True)
            for future in list(self.futures):
                if not future.done():
                    future.set_result({'ok': False, 'error': 'LED manager is stopping'})
            for handler in list(self.handlers):
                handler.cancel()
            await asyncio.gather(*list(self.handlers), return_exceptions=True)
            await self.transport.shutdown()
            with contextlib.suppress(FileNotFoundError):
                self.socket.unlink()
            self.owner_lock.close()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket', default='/run/xiaolong-led/control.sock')
    parser.add_argument('--state-dir', default='/var/lib/xiaolong-led')
    parser.add_argument('--initial-gif')
    args = parser.parse_args()
    manager = LedManager(args.socket, args.state_dir, args.initial_gif)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, manager.stop.set)
    await manager.run()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    asyncio.run(main())
