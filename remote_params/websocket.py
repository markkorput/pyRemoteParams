import asyncio
import json
import logging
import math
import threading
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional, Union

from websockets import client as wsclient
from websockets import exceptions
from websockets import server as wsserver

from .params import Params
from .schema import schema_list
from .server import Remote, Server

DEFAULT_PORT = 8081

logger = logging.getLogger(__name__)


class WebsocketServer:
    """
    Connect a private Remote instance on a given params.Server instance
    Accepts new websocket connections.
    Broadcasts any value and schema change notifications from the server
    to all connected client at that moment.
    Forwards any value change from a connected client to the server.
    Respond to schema requests from a connected client with the schema
    schema information for the server's params.
    """

    def __init__(
        self,
        server: Union[Server, Params],
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
        start: bool = True,
    ):
        self.server = server if isinstance(server, Server) else Server(server)
        self.host = host
        self.port = port
        self.thread: Optional[threading.Thread] = None
        self.sockets: set[wsserver.WebSocketServerProtocol] = set()

        self.remote = Remote(serialize=True)
        self.remote.outgoing.sendValueEvent += self._onValueFromServer
        self.remote.outgoing.sendSchemaEvent += self._onSchemaFromServer

        self._ws_server: Optional[wsserver.WebSocketServer] = None

        if start:
            self.start()

    def __del__(self) -> None:
        self.stop()
        self.remote.outgoing.sendValueEvent -= self._onValueFromServer
        self.remote.outgoing.sendSchemaEvent -= self._onSchemaFromServer

    def start(self) -> None:
        """
        Connect private Remote instance to server
        Start websockets server coroutine in a separate thread
        """
        self.server.connect(self.remote)

        async_action = wsserver.serve(self._connectionFunc, self.host, self.port)

        eventloop = asyncio.get_event_loop()

        def func() -> None:
            eventloop.run_until_complete(async_action)
            eventloop.run_forever()

        self.thread = threading.Thread(target=func)
        self.thread.start()

    async def start_async(self) -> wsserver.WebSocketServer:
        """
        Connect private Remote instance to server
        Start websockets server coroutine.

        Returns
        -------
        websocket WebsocketServer instance
        """
        self.server.connect(self.remote)
        self._ws_server = await wsserver.serve(self._connectionFunc, self.host, self.port)
        return self._ws_server

    def stop(self, joinThread: bool = True) -> None:
        """

        Disconnect private remote instance form server.
        Closes start WebsocketServer is any.
        Wait for spawned thread to end if any and if `joinThread` is True.

        Parameter
        ---------
        joinThread: boolean
          When True, will wait for started thread to finish
        """
        self.server.disconnect(self.remote)

        if self._ws_server:
            self._ws_server.close()
            self._ws_server = None

        if not self.thread:
            return

        if joinThread:
            print("joining thread")
            self.thread.join()
        self.thread = None
        logger.debug("WebsocketServer thread stopped")

    async def _connectionFunc(self, websocket: wsserver.WebSocketServerProtocol, path: str) -> None:
        """
        This method runs for every incoming websocket connection.
        It registers the websocket (add it to self.sockets)
        It awaits and processes incoming messages
        It removes the websocket from self.sockets when the connection is closed
        """
        logging.info("New websocket connection...")
        self.sockets.add(websocket)
        logger.debug(f"registered websocket, {len(self.sockets)} active")

        try:
            await websocket.send("welcome to pyRemoteParams websockets")
            async for msg in websocket:
                await self._onMessage(msg, websocket)
        except exceptions.ConnectionClosedError:
            logger.info("Connection closed.")
        except KeyboardInterrupt:
            logger.warning("KeyboardInterrupt in WebsocketServer connectionFunc")
        finally:
            self.sockets.remove(websocket)

            logger.debug(f"unregistered websocket, {len(self.sockets)} left")

    async def _onMessage(
        self, msg: Union[bytes, str], websocket: wsserver.WebSocketServerProtocol
    ) -> None:
        """
        onMessage is called with the connectionFunc to process
        incoming message from a specific websocket.
        """
        val = msg if isinstance(msg, str) else msg.decode("utf-8")

        if val == "stop":
            logger.info("Websocket connection stopped")
            websocket.close()
            return

        if val.startswith("GET schema.json"):
            logger.info(f"Got websocket schema request ({val})")
            # immediately respond
            data = schema_list(self.server.params)
            val = f"POST schema.json?schema={json.dumps(data)}"
            logger.debug(f"Websocket schema request response: ({val})")
            await websocket.send(val)
            return

        # POST <param-path>?value=<value>
        if val.startswith("POST /") and "?value=" in val:
            no_prefix = val[len("POST ") :]  # assume no query in the url
            path, val = no_prefix.split("?value=")
            logger.info(f"Value received via websocket: {path} = {val}")
            self.remote.incoming.valueEvent(path, val)
            return

        logger.warning(f"Received unknown websocket message: {val}")

    def _onValueFromServer(self, path: str, val: Any) -> None:
        """
        This method gets called when our Remote instance gets notified by Server
        instance, about a param value-change. We'll send out the value-change
        to all connected websockets.
        """
        logger.debug(f"onValueFromServer(path={path}, val={val})")
        msg = f"POST {path}?value={val}"
        asyncio.ensure_future(self._sendToAllConnectedSockets(msg))

    def _onSchemaFromServer(self, schemadata: dict[str, Any]) -> None:
        """
        This method gets called when our Remote instance gets notified by Server
        instance, about a schema change. We'll send out the schema change
        to all connected websockets.
        """
        msg = f"POST schema.json?schema={json.dumps(schemadata)}"
        asyncio.ensure_future(self._sendToAllConnectedSockets(msg))

    async def _sendToAllConnectedSockets(self, msg: str) -> None:
        """
        This method broadcasts the given msg to all connected websockets
        """
        logger.debug(f"sendToAllConnectedSockets: {msg} websocket remote(s): {len(self.sockets)}")
        for websocket in self.sockets:
            await websocket.send(msg)


class WebsocketClient:
    def __init__(self, client: wsclient.WebSocketClientProtocol) -> None:
        self.client: Optional[wsclient.WebSocketClientProtocol] = client

    def __del__(self) -> None:
        self.disconnect()

    async def disconnect(self) -> None:
        if self.client:
            await self.client.close()
            self.client = None

    async def send_value(self, path: str, value: Any) -> None:
        await self._send(f"POST {path}?value={str(value)}")

    async def _send(self, message: str) -> None:
        assert self.client
        await self.client.send(message)

    @classmethod
    @asynccontextmanager
    async def connect(
        cls, host: str = "127.0.0.1", port: int = DEFAULT_PORT
    ) -> AsyncGenerator["WebsocketClient", None]:
        async with wsclient.connect(f"ws://{host}:{port}") as client:
            yield cls(client)


if __name__ == "__main__":
    from remote_params.params import Params

    """
  Example: serve bunch of params
  """
    import time
    from optparse import OptionParser

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

    async def main(host: str, port: int) -> None:
        logger.info(f"Starting websocket server on port: {port}")
        # Create some vars to test with
        params = Params()
        params.string("name").set("John Doe")
        sineparam = params.float("sine")
        params.float("range", min=0.0, max=100.0)
        params.int("level")
        params.bool("highest-score")
        params.void("stop")

        gr = Params()
        gr.string("name").set("Jane Doe")
        gr.float("score")
        gr.float("range", min=0.0, max=100.0)
        gr.int("level")
        gr.bool("highest-score")

        params.group("parner", gr)

        wss = WebsocketServer(Server(params), host=host, port=port, start=False)
        await wss.start_async()

        try:
            while True:
                await asyncio.sleep(0.5)
                sineparam.set(math.sin(time.time()))

        except KeyboardInterrupt:
            print("Received Ctrl+C... initiating exit")

        print("Stopping...")
        wss.stop()

    def main_sync(host: str, port: int) -> None:
        logger.info(f"Starting websocket server on port: {port}")
        # Create some vars to test with
        params = Params()
        params.string("name").set("John Doe")
        params.float("score")
        params.float("range", min=0.0, max=100.0)
        params.int("level")
        params.bool("highest-score")
        params.void("stop")

        gr = Params()
        gr.string("name").set("Jane Doe")
        gr.float("score")
        gr.float("range", min=0.0, max=100.0)
        gr.int("level")
        gr.bool("highest-score")

        params.group("parner", gr)

        wss = WebsocketServer(Server(params), host=host, port=port)

        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Received Ctrl+C... initiating exit")

        print("Stopping...")
        wss.stop()

    opts, args = parse_args()

    if opts.no_async:
        main_sync(opts.host, opts.port)
    else:
        asyncio.run(main(opts.host, opts.port))
