import logging, os.path
from .http_utils import HttpServer as UtilHttpServer
from remote_params import Params, Server, Remote #, create_sync_params, schema_list

logger = logging.getLogger(__name__)

class HttpServer:
  def __init__(self, server, startServer=True):
    self.server = server
    self.remote = Remote()

    # register our remote instance through which we'll
    # inform the server about incoming information
    if self.server and self.remote:
      self.server.connect(self.remote)

    self.httpServer = UtilHttpServer(start=False)
    self.httpServer.requestEvent += self.onHttpRequest
    
    self.uiHtmlFilePath = os.path.abspath(os.path.join(os.path.dirname(__file__),'ui.html'))

    if startServer:
      self.start()

  def __del__(self):
    if self.server and self.remote:
      self.server.disconnect(self.remote)

  def start(self):
    self.httpServer.startServer()

  def stop(self):
    self.httpServer.stopServer()

  def onHttpRequest(self, req):
    logger.info('HTTP req: {}'.format(req))
    
    logger.info('HTTP req path: {}'.format(req.path))

    if req.path == '/':
      logger.info('Responding with ui file: {}'.format(self.uiHtmlFilePath))
      req.respondWithFile(self.uiHtmlFilePath)
      # req.respond(200, b'TODO: respond with html file')

      return
    req.respond(404, b'WIP')
