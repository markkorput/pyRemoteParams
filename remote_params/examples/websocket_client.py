import asyncio
import logging
import time
from optparse import OptionParser
from typing import Any

from remote_params.websocket import DEFAULT_PORT, WebsocketClient

log = logging.getLogger(__name__)


def parse_args() -> tuple[Any, Any]:
    parser = OptionParser()
    parser.add_option("-p", "--port", default=DEFAULT_PORT, type="int")
    parser.add_option("--host", default="0.0.0.0")
    parser.add_option("--param", default="/score")

    # parser.add_option("--no-async", action="store_true")
    parser.add_option("-v", "--verbose", action="store_true", default=False)
    parser.add_option("--verbosity", action="store_true", default="info")

    opts, args = parser.parse_args()
    lvl = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }["debug" if opts.verbose else str(opts.verbosity).lower()]
    logging.basicConfig(level=lvl)
    return opts, args


async def main(host: str, port: int) -> None:
    log.info(f"Starting websocket client on port: {port}")

    async with WebsocketClient.connect(host, port) as client:
        try:
            while True:
                await asyncio.sleep(0.5)
                await client.send_value(opts.param, time.time())

        except KeyboardInterrupt:
            print("Received Ctrl+C... initiating exit")

        print("Stopping...")


if __name__ == "__main__":
    opts, args = parse_args()

    asyncio.run(main(opts.host, opts.port))
