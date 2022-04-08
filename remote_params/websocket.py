import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional, Union

from websockets import client as wsclient
from websockets import exceptions
from websockets import server as wsserver

from .params import Params
from .schema import schema_list
from .server import Remote, Server

DEFAULT_PORT = 8081

log = logging.getLogger(__name__)


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
    ):
        self.server = server if isinstance(server, Server) else Server(server)
        self.sockets: set[wsserver.WebSocketServerProtocol] = set()

        self.remote = Remote(serialize=True)
        self.setup()

    def __del__(self) -> None:
        self.destroy()

    def setup(self) -> None:
        """
        Connect private Remote instance to server
        Start websockets server coroutine in a separate thread
        """
        self.remote.outgoing.sendValueEvent += self._broadcast_value
        self.remote.outgoing.sendSchemaEvent += self._broadcast_schema
        self.server.connect(self.remote)

    def destroy(self) -> None:
        self.server.disconnect(self.remote)
        self.remote.outgoing.sendValueEvent -= self._broadcast_value
        self.remote.outgoing.sendSchemaEvent -= self._broadcast_schema

    async def connection(self, websocket: wsserver.WebSocketServerProtocol, path: str) -> None:
        """
        This method runs for every incoming websocket connection.
        It registers the websocket (add it to self.sockets)
        It awaits and processes incoming messages
        It removes the websocket from self.sockets when the connection is closed
        """
        logging.info("New websocket connection...")
        self.sockets.add(websocket)
        log.debug(f"registered websocket, {len(self.sockets)} active")

        try:
            await websocket.send("welcome to pyRemoteParams websockets")
            async for msg in websocket:
                await self._on_message(msg, websocket)
        except exceptions.ConnectionClosedError:
            log.info("Connection closed.")
        except KeyboardInterrupt:
            log.warning("KeyboardInterrupt in WebsocketServer connectionFunc")
        finally:
            self.sockets.remove(websocket)

            log.debug(f"unregistered websocket, {len(self.sockets)} left")

    async def _on_message(
        self, msg: Union[bytes, str], websocket: wsserver.WebSocketServerProtocol
    ) -> None:
        """
        onMessage is called with the connectionFunc to process
        incoming message from a specific websocket.
        """
        val = msg if isinstance(msg, str) else msg.decode("utf-8")

        if val == "stop":
            log.info("Websocket connection stopped")
            await websocket.close()
            return

        if val.startswith("GET schema.json"):
            log.info(f"Got websocket schema request ({val})")
            # immediately respond
            data = schema_list(self.server.params)
            val = f"POST schema.json?schema={json.dumps(data)}"
            log.debug(f"Websocket schema request response: ({val})")
            await websocket.send(val)
            return

        # POST <param-path>?value=<value>
        if val.startswith("POST /") and "?value=" in val:
            no_prefix = val[len("POST ") :]  # assume no query in the url
            path, val = no_prefix.split("?value=")
            log.info(f"Value received via websocket: {path} = {val}")
            self.remote.incoming.valueEvent(path, val)
            return

        log.warning(f"Received unknown websocket message: {val}")

    def _broadcast_value(self, path: str, val: Any) -> None:
        """
        This method gets called when our Remote instance gets notified by Server
        instance, about a param value-change. We'll send out the value-change
        to all connected websockets.
        """
        log.debug(f"onValueFromServer(path={path}, val={val})")
        msg = f"POST {path}?value={val}"
        asyncio.ensure_future(self._broadcast(msg))
        # asyncio.get_event_loop().run_in_executor(None, self._broadcast, msg)

    def _broadcast_schema(self, schemadata: dict[str, Any]) -> None:
        """
        This method gets called when our Remote instance gets notified by Server
        instance, about a schema change. We'll send out the schema change
        to all connected websockets.
        """
        msg = f"POST schema.json?schema={json.dumps(schemadata)}"
        asyncio.ensure_future(self._broadcast(msg))
        # asyncio.get_event_loop().run_in_executor(None, self._broadcast, msg)

    async def _broadcast(self, msg: str) -> None:
        """
        This method broadcasts the given msg to all connected websockets
        """
        log.debug(f"sendToAllConnectedSockets: {msg} websocket remote(s): {len(self.sockets)}")
        for websocket in self.sockets:
            await websocket.send(msg)

    @classmethod
    @asynccontextmanager
    async def launch(
        self, server: Union[Server, Params], host: str = "0.0.0.0", port: int = DEFAULT_PORT
    ) -> AsyncGenerator["WebsocketServer", None]:
        s = WebsocketServer(server)

        async def on_connection(websocket: wsserver.WebSocketServerProtocol, path: str) -> None:
            log.info(
                f"websocket client connected (host={websocket.host}, port={websocket.port},"
                f" path={path})"
            )
            await s.connection(websocket, path)

        async with wsserver.serve(on_connection, host, port):
            yield s


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
