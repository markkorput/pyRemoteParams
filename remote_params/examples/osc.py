import time

from remote_params import Params
from remote_params.osc import OscServer

params = Params()
params.string("name")
params.float("value")


try:
    osc_server = OscServer(params)
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    pass
except Exception:
    pass

osc_server.stop()
