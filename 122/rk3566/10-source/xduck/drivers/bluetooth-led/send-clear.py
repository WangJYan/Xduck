"""Display the black test GIF through the shared manager."""
import asyncio
import json
from pathlib import Path
from led_rpc import show_file


async def main():
    result = await show_file(Path(__file__).with_name('clear.gif'))
    print(json.dumps(result, ensure_ascii=False))
    if not result.get('ok') or result.get('pending'):
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
