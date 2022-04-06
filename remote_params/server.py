import logging
from typing import Any, Callable, Optional

from evento import Event, decorators

from .params import ImageParam, Param, Params
from .schema import SchemaData, apply_schema_list, schema_list

log = logging.getLogger(__name__)


def valueEvent(path: str, value: Any) -> None:
    ...


def void() -> None:
    ...


class Incoming:
    def __init__(self) -> None:
        # events for remote-to-server communications
        self.valueEvent = decorators.event(valueEvent)
        self.disconnectEvent = decorators.event(void)
        self.confirmEvent = decorators.event(void)
        self.requestSchemaEvent = decorators.event(void)


def sendValueEvent(path: str, value: Any) -> None:
    ...


def sendDisconnectEvent() -> None:
    ...


class Outgoing:
    def __init__(self) -> None:
        # events notifying about server-to-remote communications
        self.sendValueEvent = decorators.event(sendValueEvent)
        self.sendSchemaEvent: Event[SchemaData] = Event()
        self.sendConnectConfirmationEvent: Event[Optional[SchemaData]] = Event()
        self.sendDisconnectEvent = decorators.event(sendDisconnectEvent)

    def send_connect_confirmation(self, schema_data: Optional[SchemaData] = None) -> None:
        """
        Use this method to send a connect confirmation
        to a connecting remote client
        """
        self.sendConnectConfirmationEvent(schema_data)

    def send_schema(self, schema_data: SchemaData) -> None:
        """
        Use this method to send schema data
        to a remote client
        """
        self.sendSchemaEvent(schema_data)

    def send_disconnect(self) -> None:
        """
        Use this notify/confirm disconnect to the Remote
        """

        log.debug(f"[Remote.outgoing.send_disconnect listeners={len(self.sendDisconnectEvent)}]")

        self.sendDisconnectEvent()

    def send_value(self, path: str, value: Any) -> None:
        """
        Use this method to notify the connected client about
        a single param value change
        """
        self.sendValueEvent(path, value)


class Remote:
    def __init__(self, serialize: bool = False) -> None:
        self.serialize = serialize
        self.incoming = Incoming()
        self.outgoing = Outgoing()


class Server:
    def __init__(self, params: Params, enqueue: bool = False) -> None:
        self.params = params
        self.enqueue = enqueue
        self.connected_remotes: list[Remote] = []

        self.connections: dict[Remote, Callable[[], None]] = {}

        self.cleanups: list[Callable[[], None]] = []
        self.cleanups.append(self.params.on_schema_change.add(self.broadcast_schema))
        self.cleanups.append(self.params.on_value_change.add(self.broadcast_value_change))

        self.updateFuncs: list[Callable[[], None]] = []

    def __del__(self) -> None:
        for r in self.connected_remotes:
            self.disconnect(r)

        for func in self.cleanups:
            func()

    def connect(self, remote: Remote) -> None:
        log.debug("[Server.connect]")

        if remote in self.connections:
            log.warning("[Server.connect] remote already connected")
            return

        # create and save new connection
        self.connections[remote] = self._creat_connection(remote)

    def disconnect(self, remote: Remote) -> None:
        log.debug("[Server.disconnect]")

        if remote not in self.connections:
            log.warning("[Server.disconnect] could not find connection")
            return

        disconnector = self.connections[remote]
        disconnector()
        del self.connections[remote]

    def update(self) -> None:
        for f in self.updateFuncs:
            f()
        self.updateFuncs.clear()

    def broadcast_schema(self) -> None:
        log.debug("[Server.broadcast_schema]")
        schema_data = schema_list(self.params)
        for r in self.connected_remotes:
            r.outgoing.send_schema(schema_data)

    def broadcast_value_change(self, path: str, value: Any, param: Param[Any]) -> None:
        log.debug(
            f"[Server.broadcast_value_change] to {len(self.connected_remotes)} connected remotes"
        )
        serialized_value = None
        for r in self.connected_remotes:
            # TODO; this is not the server's responsiiblity
            if isinstance(param, ImageParam):
                if serialized_value is None:
                    serialized_value = param.get_serialized()
                r.outgoing.send_value(path, serialized_value)
            else:
                r.outgoing.send_value(path, value)

    def handle_remote_value_change(self, remote: Remote, path: str, value: Any) -> None:
        def processNow() -> None:
            log.debug("[Server.handle_remote_value_change]")
            param = self.params.get_path(path)
            if not param:
                log.warning("[Server.handle_remote_value_change] unknown path: {}".format(path))
                return

            if isinstance(param, Param):
                param.set(value)

        if self.enqueue:
            self.updateFuncs.append(processNow)
            return

        processNow()

    def handle_remote_schema_request(self, remote: Remote) -> None:
        log.debug("[Server.handle_remote_schema_request]")
        schema_data = schema_list(self.params)
        remote.outgoing.send_schema(schema_data)

    def _creat_connection(self, remote: Remote) -> Callable[[], None]:

        """
        Connects the remote to the server and starts receiving broadcasted data,
        as well as making sure date from the remote arrives at and gets processed by self.

        It returns a single function which performs all disconnect operations.
        """

        log.debug("[_creat_connection]")

        cleanups = []

        # register handler when receiving value from remote
        def value_handler(path: str, value: Any) -> None:
            log.debug("[Server.connect.value_handler]")
            self.handle_remote_value_change(remote, path, value)

        unsub = remote.incoming.valueEvent.add(value_handler)
        cleanups.append(unsub)

        # register handler when receiving schema request from remote
        def schema_request_handler() -> None:
            log.debug("[Server.connect.schema_request_handler]")
            self.handle_remote_schema_request(remote)

        unsub = remote.incoming.requestSchemaEvent.add(schema_request_handler)
        cleanups.append(unsub)

        # add remote to server list
        self.connected_remotes.append(remote)

        def remove() -> None:
            if remote in self.connected_remotes:
                self.connected_remotes.remove(remote)

        cleanups.append(remove)

        # done, send confirmation to remote with schema data
        remote.outgoing.send_connect_confirmation(schema_list(self.params))

        cleanups.append(remote.outgoing.send_disconnect)

        def disconnect() -> None:
            for func in cleanups:
                func()

        return disconnect


def create_sync_params(remote: Remote, request_initial_schema: bool = True) -> Params:
    """
    Creates an instance of Params, which is updated with information
    received by the given remote
    """
    params = Params()

    # catch incoming schema data and apply it
    def onSchema(schema_data: SchemaData) -> None:
        log.debug("[create_sync_params.onSchema] schema_data={}".format(schema_data))
        apply_schema_list(params, schema_data)

    remote.outgoing.sendSchemaEvent += onSchema

    def onValue(path: str, value: Any) -> None:
        param = params.get_path(path)
        if not param:
            log.warning("[create_sync_params.onValue] got invalid path: {}".format(path))
            return

        if isinstance(param, Param):
            param.set(value)

    remote.outgoing.sendValueEvent += onValue

    # request schema data
    if request_initial_schema:
        remote.incoming.requestSchemaEvent()

    return params
