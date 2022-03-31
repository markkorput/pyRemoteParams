from remote_params import http, server
from remote_params.params import Params

if __name__ == "__main__":
    import logging
    import time
    from optparse import OptionParser

    logger = logging.getLogger(__name__)

    def parse_args():
        parser = OptionParser()
        parser.add_option("-p", "--port", dest="port", default=4445, type="int")
        parser.add_option("--host", dest="host", default="127.0.0.1")
        parser.add_option(
            "-s", "--show", dest="show", action="store_true", default=False
        )

        parser.add_option(
            "-v", "--verbose", dest="verbose", action="store_true", default=False
        )
        parser.add_option(
            "--verbosity", dest="verbosity", action="store_true", default="info"
        )

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

    opts, args = parse_args()

    params = Params()
    params.string("name")
    params.float("score")
    params.int("level")
    params.bool("highest-score")

    http_server = http.HttpServer(server.Server(params))
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Received Ctrl+C... initiating exit")

    http_server.stop()
