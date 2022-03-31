import logging
import os.path

from remote_params import (
    Params,
    Remote,  # , create_sync_params, schema_list
    Server,
    schema_list,
)

from .http_utils import HttpServer as UtilHttpServer

logger = logging.getLogger(__name__)


class HttpServer:
    def __init__(self, server, port=8080, startServer=True):
        self.server = server
        self.remote = Remote()

        # register our remote instance through which we'll
        # inform the server about incoming information
        if self.server and self.remote:
            self.server.connect(self.remote)

        self.httpServer = UtilHttpServer(port=port, start=False)
        self.httpServer.requestEvent += self.onHttpRequest

        self.uiHtmlFilePath = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "ui.html")
        )

        if startServer:
            self.start()

    def __del__(self):
        if self.server and self.remote:
            self.server.disconnect(self.remote)

    def start(self):
        logger.info("Starting HTTP server on port: {}".format(self.httpServer.port))
        self.httpServer.startServer()

    def stop(self):
        self.httpServer.stopServer()

    def onHttpRequest(self, req):
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
