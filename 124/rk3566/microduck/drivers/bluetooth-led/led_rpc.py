"""Local IPC clients: no client ever opens a Bluetooth connection."""
import asyncio
import base64
import json
import os
import struct
import uuid
from pathlib import Path

SOCKET = '/run/xiaolong-led/control.sock'
MAX_GIF_BYTES = 256 * 1024
MAX_MESSAGE_BYTES = 400 * 1024


def validate_gif(image):
    if not 14 <= len(image) <= MAX_GIF_BYTES:
        raise ValueError('GIF size must be between 14 and 262144 bytes')
    if image[:6] not in (b'GIF87a', b'GIF89a') or image[-1:] != b';':
        raise ValueError('Incomplete GIF')
    if struct.unpack('<HH', image[6:10]) != (32, 16):
        raise ValueError('This panel requires a 32x16 GIF')


async def request(payload, timeout=125, socket=None):
    socket = socket or os.environ.get('XIAOLONG_LED_SOCKET', SOCKET)
    connect_deadline = asyncio.get_running_loop().time() + min(timeout, 10)
    while True:
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_unix_connection(socket), 2)
            break
        except (OSError, asyncio.TimeoutError):
            if asyncio.get_running_loop().time() >= connect_deadline:
                raise ConnectionError('LED manager is unavailable: ' + socket)
            await asyncio.sleep(.5)
    try:
        writer.write(json.dumps(payload, ensure_ascii=False).encode() + b'\n')
        await writer.drain()
        line = await asyncio.wait_for(reader.readline(), timeout)
        if not line:
            raise ConnectionError('LED manager restarted; inspect status or retry the request')
        return json.loads(line)
    finally:
        writer.close()
        await writer.wait_closed()


async def status(socket=None):
    return await request({'cmd': 'status'}, timeout=3, socket=socket)


async def show_bytes(image, label='image', wait=110, socket=None):
    validate_gif(image)
    return await request({'cmd': 'show', 'id': uuid.uuid4().hex,
        'label': label[:120], 'image': base64.b64encode(image).decode(),
        'wait': wait}, timeout=wait + 15, socket=socket)


async def show_file(path, wait=110, socket=None):
    path = Path(path)
    return await show_bytes(path.read_bytes(), path.name, wait, socket)
