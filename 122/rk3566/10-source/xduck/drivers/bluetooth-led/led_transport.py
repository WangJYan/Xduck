"""Exclusive LEDCanvas BLE transport. Only led_manager may instantiate this."""
import asyncio
import contextlib
import logging
import struct
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from dbus_fast import BusType, Message, MessageType
from dbus_fast.aio import MessageBus

ADDRESS = '1C:DB:B8:AB:5C:34'
DEVICE_PATH = '/org/bluez/hci0/dev_1C_DB_B8_AB_5C_34'
COMMAND = '0000c821-0000-1000-8000-00805f9b34fb'
DATA = '0000c822-0000-1000-8000-00805f9b34fb'
NOTIFY = '0000c823-0000-1000-8000-00805f9b34fb'


def crc16(data):
    value = 0xffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ 0xa001 if value & 1 else value >> 1
    return struct.pack('>H', value)


def crc32c(data):
    value = 0xffffffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ 0x82f63b78 if value & 1 else value >> 1
    return value ^ 0xffffffff


class Transport:
    def __init__(self, on_disconnect=None, on_phase=None):
        self.client = None
        self.bus = None
        self.notifications = asyncio.Queue(maxsize=128)
        self.disconnected = asyncio.Event()
        self.disconnected.set()
        self.closing = False
        self.on_disconnect = on_disconnect or (lambda: None)
        self.on_phase = on_phase or (lambda phase: None)

    @property
    def connected(self):
        return bool(self.client and self.client.is_connected and not self.disconnected.is_set())

    def link_lost(self, client):
        if client is not self.client:
            return
        self.disconnected.set()
        if not self.closing:
            logging.warning('BLE_LINK_LOST target=%s', ADDRESS)
            self.on_disconnect()

    def notified(self, _, data):
        if self.notifications.full():
            self.notifications.get_nowait()
        self.notifications.put_nowait(bytes(data))

    async def properties(self):
        try:
            if self.bus is None:
                self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            reply = await asyncio.wait_for(self.bus.call(Message(
                destination='org.bluez', path=DEVICE_PATH,
                interface='org.freedesktop.DBus.Properties', member='GetAll',
                signature='s', body=['org.bluez.Device1'])), 3)
            if reply.message_type == MessageType.ERROR:
                return None
            return {key: value.value for key, value in reply.body[0].items()}
        except Exception:
            if self.bus:
                with contextlib.suppress(Exception):
                    self.bus.disconnect()
            self.bus = None
            raise

    async def attach(self, device, timeout):
        self.disconnected.clear()
        self.client = BleakClient(device, timeout=timeout, disconnected_callback=self.link_lost)
        await self.client.connect()
        await self.client.start_notify(NOTIFY, self.notified)
        # Bleak 0.22 / BlueZ needs this to obtain the negotiated MTU.
        await self.client._backend._acquire_mtu()
        if not self.connected:
            raise ConnectionError('Disconnected during service discovery')
        logging.info('BLE_CONNECTED target=%s mtu=%d', ADDRESS, self.client.mtu_size)

    async def connect(self):
        if self.connected:
            return
        # A cached device can reconnect directly, without repeatedly scanning.
        self.on_phase('cached-connect')
        props = await self.properties()
        if props and str(props.get('Address', '')).upper() == ADDRESS:
            logging.info('BLE_REUSE_KNOWN_DEVICE path=%s', DEVICE_PATH)
            device = BLEDevice(ADDRESS, props.get('Name'),
                               {'path': DEVICE_PATH, 'props': props}, props.get('RSSI', -127))
            try:
                await self.attach(device, 25)
                return
            except Exception as error:
                logging.warning('BLE_CACHED_CONNECT_FAILED %s: %s', type(error).__name__, error)
                await self.close()
        self.on_phase('scanning')
        found = asyncio.get_running_loop().create_future()

        def detected(device, advertisement):
            if device.address.upper() == ADDRESS and not found.done():
                found.set_result(device)

        logging.info('BLE_SCAN_START target=%s timeout=30s', ADDRESS)
        async with BleakScanner(detected, bluez={'filters': {'DuplicateData': True}}):
            await asyncio.sleep(1)
            if not found.done():
                # Work around this controller's duplicate cache for this scan only.
                for enabled in ('00', '01'):
                    process = await asyncio.create_subprocess_exec(
                        'hcitool', '-i', 'hci0', 'cmd', '0x08', '0x0042', enabled,
                        '00', '00', '00', '00', '00',
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    output, error = await asyncio.wait_for(process.communicate(), 4)
                    if process.returncode or output.decode().split()[-4:] != ['01', '42', '20', '00']:
                        raise RuntimeError('Scan recovery failed: ' + (output + error).decode())
            device = await asyncio.wait_for(found, 30)
        logging.info('BLE_SCAN_FOUND target=%s', ADDRESS)
        self.on_phase('connecting')
        await self.attach(device, 60)

    async def health(self):
        if not self.connected:
            raise ConnectionError('BLE link is disconnected')
        props = await self.properties()
        if not props or not props.get('Connected'):
            raise ConnectionError('BlueZ reports the lamp disconnected')

    async def close(self):
        client = self.client
        self.closing = True
        try:
            if client:
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(client.disconnect(), 4)
        finally:
            if self.client is client:
                self.client = None
            self.disconnected.set()
            self.closing = False

    async def shutdown(self):
        await self.close()
        if self.bus:
            with contextlib.suppress(Exception):
                self.bus.disconnect()
            self.bus = None

    async def ack(self, predicate, timeout=8):
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            received = asyncio.create_task(self.notifications.get())
            lost = asyncio.create_task(self.disconnected.wait())
            try:
                done, _ = await asyncio.wait([received, lost],
                    timeout=max(.01, deadline - asyncio.get_running_loop().time()),
                    return_when=asyncio.FIRST_COMPLETED)
                if lost in done:
                    raise ConnectionError('BLE disconnected while waiting for acknowledgement')
                if received not in done:
                    raise TimeoutError('LED acknowledgement timeout')
                data = received.result()
                if predicate(data):
                    return data
            finally:
                for task in (received, lost):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(received, lost, return_exceptions=True)

    async def write(self, data, channel=COMMAND):
        if not self.connected:
            raise ConnectionError('BLE disconnected before write')
        await asyncio.wait_for(self.client.write_gatt_char(channel, data + crc16(data), response=True), 10)

    async def show(self, image):
        while not self.notifications.empty():
            self.notifications.get_nowait()
        await self.write(b'\x08\x02\x05\x00' + struct.pack('>I', crc32c(image)))
        reply = await self.ack(lambda d: len(d) >= 4 and d[:2] == b'\x08\x02')
        if reply[3] == 3:
            return {'cached': True, 'frames': 0, 'ack': reply.hex()}
        if reply[3] != 1:
            raise RuntimeError('Image rejected: ' + reply.hex())
        budget = min(512, self.client.mtu_size - 3) - 13
        size = 7 if budget <= 20 else budget
        frame_count = 0
        for index, offset in enumerate(range(0, len(image), size)):
            chunk = image[offset:offset + size]
            frame = b'\x01\x08\x02' + struct.pack('>IHH', len(image), index, len(chunk)) + chunk
            await asyncio.sleep(.08)
            await self.write(frame, DATA)
            reply = await self.ack(lambda d: len(d) >= 6 and d[:2] == b'\x01\x01'
                                   and int.from_bytes(d[2:4], 'big') == index)
            if reply[5] != 1:
                raise RuntimeError('Frame rejected: ' + reply.hex())
            frame_count += 1
        end = b'\x01\x02\x01\x01'
        await self.write(end + crc16(end))
        reply = await self.ack(lambda d: len(d) >= 4 and d[:3] == b'\x01\x02\x01')
        if reply[3] != 1:
            raise RuntimeError('GIF checksum rejected: ' + reply.hex())
        return {'cached': False, 'frames': frame_count, 'ack': reply.hex()}
