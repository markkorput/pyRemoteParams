import logging
import os.path

from .http_utils import HttpRequest
from .http_utils import HttpServer as UtilHttpServer
from .server import Remote, Server

logger = logging.getLogger(__name__)


class HttpServer:
    def __init__(self, server: Server, port: int = 8080, startServer: bool = True) -> None:
        self.server = server
        self.remote = Remote()

        # register our remote instance through which we'll
        # inform the server about incoming information
        if self.server and self.remote:
            self.server.connect(self.remote)

        self.httpServer = UtilHttpServer(port=port, start=False)
        self.httpServer.requestEvent += self._on_http_request

        self.uiHtmlFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__), "ui.html"))

        if startServer:
            self.start()

    def __del__(self) -> None:
        if self.server and self.remote:
            self.server.disconnect(self.remote)

    def start(self) -> None:
        logger.info("Starting HTTP server on port: {}".format(self.httpServer.port))
        self.httpServer.startServer()

    def stop(self) -> None:
        self.httpServer.stopServer()

    def _on_http_request(self, req: HttpRequest) -> None:
        # logger.info('HTTP req: {}'.format(req))
        # logger.info('HTTP req path: {}'.format(req.path))

        if req.path == "/":
            logger.debug("Responding with ui file: {}".format(self.uiHtmlFilePath))
            req.respondWithFile(self.uiHtmlFilePath)
            # req.respond(200, b'TODO: respond with html file')
            return

        if req.path == "/params/value":
            # TODO
            req.respond(404, b"TODO: responding to HTTP requests not yet implemented")

        req.respond(404, b"WIP")
