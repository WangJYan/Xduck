"""Submit display jobs to the persistent manager; never opens Bluetooth."""
import argparse
import asyncio
import json
from led_rpc import show_file, status


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('gif', nargs='?')
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--wait', type=float, default=110)
    args = parser.parse_args()
    if args.status:
        result = await status()
    else:
        if not args.gif:
            parser.error('provide a GIF or --status')
        result = await show_file(args.gif, wait=args.wait)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get('ok'):
        raise SystemExit(1)
    if result.get('pending'):
        raise SystemExit(75)


if __name__ == '__main__':
    asyncio.run(main())
