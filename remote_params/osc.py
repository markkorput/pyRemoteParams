import json
import logging
import threading
from typing import Any, Callable, Optional, Union

from pythonosc import dispatcher, osc_server, udp_client

from .params import Params
from .schema import SchemaData, schema_list
from .server import Remote, Server

log = logging.getLogger(__name__)


class Client:
    """
    This Client class performs all server-to-client OSC communications.
    The id given to the constructor specifies where all communications
    should be addressed to and should have the following format:
      '<host>:<port>'

      ie.

      '127.0.0.1:8082'

      or

      'localhost:6000'
    """

    def __init__(self, id: str, prefix: str = "/params") -> None:
        """
        Parameters
        ----------
        id : str
          address for outgoing messages in the following format: "<host>:<port>"
          ie. "127.0.0.1:8001" or "devlaptop.local:8081"

        prefix : str
          prefix to apply to all outgoing OSC message addresses
        """
        parts = id.split(":")

        if len(parts) < 2 or not str(parts[1]).isdigit():
            log.warning("[Connection.__init__] invalid response details: {}".format(id))
            self.isValid = False
        else:
            self.host = parts[0]
            self.port = int(parts[1])
            self.isValid = True

        self.client = udp_client.SimpleUDPClient(self.host, self.port)
        self.connect_confirm_addr = prefix + "/connect/confirm"
        self.disconnect_addr = prefix + "/disconnect"
        self.schema_addr = prefix + "/schema"
        self.value_addr = prefix + "/value"

    def sendValue(self, path: str, value: Any) -> None:
        self.send(self.value_addr, path, value)

    def sendSchema(self, data: SchemaData) -> None:
        if self.isValid:
            self.send(self.schema_addr, json.dumps(data))

    def sendConnectConfirmation(self, data: SchemaData) -> None:
        if self.isValid:
            self.send(self.connect_confirm_addr, json.dumps(data))

    def sendDisconnect(self) -> None:
        self.send(self.disconnect_addr)

    def send(self, addr: str, *args: Any) -> None:
        self.send_message(self.client, addr, *args)

    @staticmethod
    def send_message(
        to: Union[tuple[str, int], udp_client.SimpleUDPClient],
        addr: str,
        *args: Any,
        client: Optional[udp_client.SimpleUDPClient] = None,
    ) -> None:
        client = (
            to
            if isinstance(to, udp_client.SimpleUDPClient)
            else udp_client.SimpleUDPClient(to[0], to[1])
        )
        client.send_message(addr, args)


class Connection:
    """
    The Connection class responds to all server-to-client
    instructions from the Server and translates them into OSC actions
    """

    def __init__(self, server: Server, id: str, connect: bool = True):
        log.debug("[Connection.__init__] id: {}".format(id))
        self.server = server
        self.client = Client(id)
        self.isActive = self.client.isValid and connect

        r = Remote()
        r.outgoing.sendConnectConfirmationEvent += self.onConnectConfimToRemote
        r.outgoing.sendValueEvent += self.onValueToRemote
        r.outgoing.sendSchemaEvent += self.onSchemaToRemote
        r.outgoing.sendDisconnectEvent += self.onDisconnectToRemote
        self.remote = r

        if self.isActive:
            self.server.connect(self.remote)

    def __del__(self) -> None:
        self.disconnect()

    def disconnect(self) -> None:
        self.isActive = False

        if self.remote and self.server:
            self.server.disconnect(self.remote)

    def onValueToRemote(self, path: str, value: Any) -> None:
        if not self.isActive:
            return
        self.client.sendValue(path, value)

    def onSchemaToRemote(self, schema_data: SchemaData) -> None:
        if not self.isActive:
            return
        self.client.sendSchema(schema_data)

    def onConnectConfimToRemote(self, schema_data: SchemaData) -> None:
        if not self.isActive:
            return
        self.client.sendConnectConfirmation(schema_data)

    def onDisconnectToRemote(self) -> None:
        log.debug("[Connection.onDisconnectToRemote isActive={}]".format(self.isActive))
        if not self.isActive:
            return
        self.disconnect()
        self.client.sendDisconnect()


def create_osc_listener(
    port: int = 8000, callback: Optional[Callable[..., None]] = None
) -> tuple[osc_server.ThreadingOSCUDPServer, Callable[[], None]]:
    """
    Create a threaded OSC server that listens for incoming UDP messages
    """
    log.debug("[create_osc_listener port={}]".format(port))

    def handler(addr: str, *args: Any) -> None:
        log.debug(f"[create_osc_listener.handler] addr={addr} args={args}")
        if callback:
            callback(addr, *args)

    disp = dispatcher.Dispatcher()
    disp.set_default_handler(handler)
    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", port), disp)

    print(f"Starting OSC listener on port {port}")
    thread = threading.Thread(target=server.serve_forever)

    def disconnect() -> None:
        server.shutdown()
        thread.join()

    thread.start()
    return server, disconnect


class OscServer:
    def __init__(
        self,
        subject: Union[Server, Params],
        port: int = 8000,
        prefix: str = "/params",
        start: bool = True,
    ) -> None:
        self.server = subject if isinstance(subject, Server) else Server(subject)
        self.remote = Remote()
        self.server.connect(self.remote)

        self.port = port
        self.connections: list[Connection] = []

        self.prefix = prefix
        self.connect_addr = self.prefix + "/connect"
        self.disconnect_addr = self.prefix + "/disconnect"
        self.value_addr = self.prefix + "/value"
        self.schema_addr = self.prefix + "/schema"

        self._disconnect: Optional[Callable[[], None]] = None
        if start:
            self.start()

    def __del__(self) -> None:
        self.server.disconnect(self.remote)
        self.stop()

    def start(self) -> None:
        _, disconnect = create_osc_listener(port=self.port, callback=self.receive)
        self._disconnect = disconnect

    def stop(self) -> None:
        # this triggers cleanup in destructor of the Connection instances
        for c in self.connections:
            c.disconnect()
        self.connections.clear()

        if self._disconnect:
            self._disconnect()
            self._disconnect = None

    def receive(self, addr: str, *args: Any) -> None:
        log.debug("[OscServer.receive] addr={} args={}".format(addr, args))

        # Param value?
        if addr == self.value_addr:
            if len(args) == 2:
                path, value = args
                self.on_value(path, value)
            else:
                log.warning(
                    "[OscServer.receive] received value message ({}) with invalid"
                    " number ({}) of arguments: {}. Expecting two arguments (path and"
                    " value)".format(addr, len(args), args)
                )
            return

        # Param value (with param ID in OSC address)
        if addr.startswith(self.value_addr):
            if len(args) == 1:
                length = len(self.value_addr)
                path = addr[length:]
                value = args[0]
                self.on_value(path, value)
            else:
                log.warning(
                    f"[OscServer.receive] received value message ({addr}) with invalid"
                    f" number ({len(args)}) of arguments: {args}. Expecting one"
                    " arguments (value)"
                )
            return

        # Connect request?
        if addr == self.connect_addr:
            if len(args) == 1:
                self.on_connect(args[0])
            else:
                log.warning("[OscServer.receive] got connect message without host/port info")
            return

        # Schema request?
        if addr == self.schema_addr and len(args) == 1:
            self.on_schema_request(args[0])

    def on_connect(self, response_info: str) -> None:
        connection = Connection(self.server, response_info)
        if connection.isActive:
            self.connections.append(connection)

    def on_value(self, path: str, value: Any) -> None:
        log.debug(f"[OscServer.onValueReceived path={path} value={value}]")
        # pass it on to the server through our remote instance
        self.remote.incoming.valueEvent(path, value)

    def on_schema_request(self, responseInfo: str) -> None:
        Client(responseInfo).sendSchema(schema_list(self.server.params))


if __name__ == "__main__":
    import time

    from .params import Params
    from .server import Server

    logging.basicConfig(level=logging.DEBUG)

    # Create params
    params = Params()
    params.string("name").on_change += print

    # Create Server and Osc server
    oscserver = OscServer(params)

    try:
        print("Waiting for incoming messages")

        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("[timer] KeyboardInterrupt, stopping.")

    oscserver.stop()
