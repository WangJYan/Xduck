"""Compatibility adapter for the voice app; BLE belongs to led_manager only."""
from pathlib import Path
from led_rpc import show_file, status
from led_transport import ADDRESS, COMMAND, DATA, NOTIFY, crc16, crc32c


class DisplayPending(RuntimeError):
    pass


class Panel:
    async def connect(self):
        return await status()

    async def smile(self):
        reply = await show_file(Path(__file__).with_name('smile.gif'))
        if not reply.get('ok'):
            raise RuntimeError(reply.get('error', 'Display request failed'))
        if reply.get('pending'):
            raise DisplayPending('Accepted by LED manager; automatic reconnection is pending')
        return reply

    async def close(self):
        # A caller exiting must never disconnect the shared hardware link.
        return None
