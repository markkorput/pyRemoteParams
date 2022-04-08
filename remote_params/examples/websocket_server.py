import asyncio
import logging
import math
import time
from optparse import OptionParser
from typing import Any

from remote_params.params import Params
from remote_params.websocket import WebsocketServer

log = logging.getLogger(__name__)


def parse_args() -> tuple[Any, Any]:
    parser = OptionParser()
    parser.add_option("-p", "--port", default=8081, type="int")
    parser.add_option("--host", default="0.0.0.0")

    parser.add_option("--no-async", action="store_true")
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


def create_params() -> Params:
    params = Params()
    params.string("name").set("Jane Doe")

    params.float("score")
    params.float("range", min=0.0, max=100.0)
    params.int("level")
    params.bool("highest-score")

    params.void("stop")
    params.float("sine", min=0.0, max=1.0)

    gr = Params()
    gr.string("name").set("John Doe")
    gr.float("score")
    gr.float("range", min=0.0, max=100.0)
    gr.int("level")
    gr.bool("highest-score")

    params.group("partner", gr)
    return params


async def main(host: str, port: int) -> None:
    log.info(f"Starting websocket server on port: {port}")
    # Create some vars to test with
    params = create_params()
    sineparam = params.get_param("sine")
    assert sineparam

    async with WebsocketServer.launch(params, host, port):
        try:
            while True:
                await asyncio.sleep(0.5)
                sineparam.set(math.sin(time.time()))

        except KeyboardInterrupt:
            print("Received Ctrl+C... initiating exit")

        print("Stopping...")


# def main_sync(host: str, port: int) -> None:
#     log.info(f"Starting websocket server on port: {port}")
#     # Create some vars to test with
#     params = create_params()

#     wss = WebsocketServer(params, host=host, port=port)

#     try:
#         while True:
#             time.sleep(0.5)
#     except KeyboardInterrupt:
#         print("Received Ctrl+C... initiating exit")

#     print("Stopping...")
#     wss.stop()


if __name__ == "__main__":
    opts, args = parse_args()

    # if opts.no_async:
    #     main_sync(opts.host, opts.port)
    # else:
    asyncio.run(main(opts.host, opts.port))
