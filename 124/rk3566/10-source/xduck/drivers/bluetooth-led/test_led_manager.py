"""Connection ownership / reconnect tests; no real Bluetooth operations."""
import asyncio
import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from led_manager import LedManager
from led_rpc import request, show_bytes, status

FIXTURES = Path(os.environ.get('XDUCK_LED_FIXTURES',
    str(Path(__file__).parent)))


class FakeTransport:
    def __init__(self, on_disconnect, on_phase):
        self.connected = False
        self.disconnected = asyncio.Event()
        self.disconnected.set()
        self.callback = on_disconnect
        self.blocked = False
        self.sessions = 0
        self.uploads = []
        self.active_uploads = 0
        self.max_uploads = 0

    async def connect(self):
        if self.blocked:
            raise ConnectionError('simulated unavailable lamp')
        self.sessions += 1
        self.connected = True
        self.disconnected.clear()

    async def health(self):
        if not self.connected:
            raise ConnectionError('simulated lost link')

    async def show(self, data):
        self.active_uploads += 1
        self.max_uploads = max(self.max_uploads, self.active_uploads)
        try:
            await asyncio.sleep(.015)
            if not self.connected:
                raise ConnectionError('lost during transfer')
            self.uploads.append(hashlib.sha256(data).hexdigest())
            return {'frames': 1, 'cached': False, 'ack': '010201010802'}
        finally:
            self.active_uploads -= 1

    def drop(self):
        self.connected = False
        self.disconnected.set()
        self.callback()

    async def close(self):
        self.connected = False
        self.disconnected.set()

    async def shutdown(self):
        await self.close()


class ManagerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='xiaolong-led-test-')
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.a = (FIXTURES / 'smile.gif').read_bytes()
        self.b = (FIXTURES / 'eyes/02-red-hunter-32x16.gif').read_bytes()
        self.manager = self.task = None
        await self.start()
        self.addAsyncCleanup(self.halt)
        await self.until(lambda: self.manager.confirmations >= 1)

    async def until(self, predicate):
        deadline = asyncio.get_running_loop().time() + 3
        while not predicate():
            if self.task and self.task.done():
                await self.task
                raise AssertionError('manager stopped early')
            if asyncio.get_running_loop().time() >= deadline:
                self.fail('condition timed out')
            await asyncio.sleep(.005)

    async def start(self, blocked=False):
        self.manager = LedManager(self.root / 'run/control.sock', self.root / 'state',
                                  FIXTURES / 'smile.gif', FakeTransport, retry_scale=.002)
        self.manager.transport.blocked = blocked
        self.task = asyncio.create_task(self.manager.run())
        await self.until(lambda: self.manager.socket.exists())

    async def halt(self):
        if self.manager and self.task and not self.task.done():
            self.manager.stop.set()
            await asyncio.wait_for(self.task, 2)

    @property
    def socket(self):
        return str(self.manager.socket)

    async def test_concurrent_callers_share_one_connection_and_serialize(self):
        images = [self.b, self.a, self.b]
        replies = await asyncio.gather(*[
            show_bytes(image, label=str(i), wait=1, socket=self.socket)
            for i, image in enumerate(images)])
        for image, reply in zip(images, replies):
            self.assertTrue(reply['ok'])
            self.assertFalse(reply['pending'])
            self.assertEqual(reply['connection_id'], 1)
            self.assertEqual(reply['asset']['sha256'], hashlib.sha256(image).hexdigest())
        self.assertEqual(self.manager.transport.sessions, 1)
        self.assertEqual(self.manager.transport.max_uploads, 1)

    async def test_drop_reconnects_and_replays_without_another_request(self):
        await show_bytes(self.b, wait=1, socket=self.socket)
        previous = self.manager.confirmations
        self.manager.transport.drop()
        await self.until(lambda: self.manager.connection_id == 2
                         and self.manager.confirmations > previous)
        self.assertEqual(self.manager.link_losses, 1)
        self.assertEqual(self.manager.transport.uploads[-1], hashlib.sha256(self.b).hexdigest())

    async def test_accepted_offline_intent_survives_process_restart(self):
        await self.halt()
        await self.start(blocked=True)
        reply = await show_bytes(self.b, wait=.02, socket=self.socket)
        self.assertTrue(reply['pending'])
        stored = json.loads(self.manager.state_file.read_text())
        self.assertEqual(stored['desired']['sha256'], hashlib.sha256(self.b).hexdigest())
        await self.halt()
        await self.start()
        await self.until(lambda: self.manager.confirmations >= 1)
        self.assertEqual(self.manager.transport.uploads[0], hashlib.sha256(self.b).hexdigest())

    async def test_second_owner_is_rejected_without_touching_existing_socket(self):
        other = LedManager(self.manager.socket, self.manager.state_dir,
                           FIXTURES / 'smile.gif', FakeTransport)
        with self.assertRaises(BlockingIOError):
            await other.run()
        reply = await status(socket=self.socket)
        self.assertEqual(reply['instance'], self.manager.instance)
        self.assertEqual(self.manager.transport.sessions, 1)
        self.assertEqual(other.transport.sessions, 0)

    async def test_invalid_image_does_not_change_selected_display(self):
        before = self.manager.desired.copy()
        reply = await request({'cmd': 'show', 'image': base64.b64encode(b'invalid').decode()},
                              socket=self.socket)
        self.assertFalse(reply['ok'])
        self.assertEqual(self.manager.desired, before)
        self.assertEqual(self.manager.jobs.qsize(), 0)


if __name__ == '__main__':
    unittest.main()
