import logging, json, time, cv2

from optparse import OptionParser
import asyncio, websockets, threading

from remote_params import Params, Server, Remote, schema_list, WebsocketServer

logger = logging.getLogger(__name__)

class App:
  def __init__(self, host, port):
    self.host = host
    self.port = port
    
    self.imageParam = None
    self.cap = None

  async def main(self):
    # Params
    params = Params()
    self.imageParam = params.image('image')
    fps = params.float('fps', min=0.0, max=100.0)
    snap = params.void('snap')

    fps.set(0.2)
    snap.ontrigger(self.update)

    logger.info(f'Starting websocket server on port: {self.port}')
    wss = WebsocketServer(Server(params), host=self.host, port=self.port, start=False)
    await wss.start_async()

    logger.info(f'Starting webcam')
    self.cap = cv2.VideoCapture(0)

    nextTime = time.time()
    try:
      while True:
        t = time.time()
        hz = fps.val()

        if t >= nextTime and hz > 0.00001:
          self.update()
          nextTime = t + 1.0 / hz

        await asyncio.sleep(0.05)

        key = cv2.waitKey(10) & 0xFF

        if key == 27 or key == ord('q'): # escape or Q
          break

    except KeyboardInterrupt:
      print("Received Ctrl+C... initiating exit")

    print('Stopping...')
    wss.stop()

  def update(self):
    ret, frame = self.cap.read()
    if not ret:
      return
    print('setting new image...')
    frame = cv2.resize(frame, (300,200), interpolation=cv2.INTER_AREA)
    cv2.imshow('cam', frame)
    self.imageParam.set(frame)

def parse_args():
  parser = OptionParser()
  parser.add_option('-p', '--port', default=8081, type='int')
  parser.add_option('--host', default='0.0.0.0')

  parser.add_option('-v', '--verbose', action='store_true', default=False)
  parser.add_option('--verbosity', action='store_true', default='info')

  opts, args = parser.parse_args()
  lvl = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning':logging.WARNING, 'error':logging.ERROR, 'critical':logging.CRITICAL}['debug' if opts.verbose else str(opts.verbosity).lower()]
  logging.basicConfig(level=lvl)
  return opts, args

if __name__ == '__main__':
  opts, args = parse_args()
  app = App(opts.host, opts.port)

  asyncio.run(app.main())
