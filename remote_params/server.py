import logging

from evento import Event

from .params import Params
from .schema import apply_schema_list, get_path, schema_list

logger = logging.getLogger(__name__)


class Remote:
    def __init__(self, serialize=False):
        class Incoming:
            def __init__(self):
                # events for remote-to-server communications
                self.valueEvent = Event()
                self.disconnectEvent = Event()
                self.confirmEvent = Event()
                self.requestSchemaEvent = Event()

        class Outgoing:
            def __init__(self):
                # events notifying about server-to-remote communications
                self.sendValueEvent = Event()
                self.sendSchemaEvent = Event()
                self.sendConnectConfirmationEvent = Event()
                self.sendDisconnectEvent = Event()

            def send_connect_confirmation(self, schema_data=None):
                """
                Use this method to send a connect confirmation
                to a connecting remote client
                """
                self.sendConnectConfirmationEvent(schema_data)

            def send_schema(self, schema_data):
                """
                Use this method to send schema data
                to a remote client
                """
                self.sendSchemaEvent(schema_data)

            def send_disconnect(self):
                logger.debug(
                    "[Remote.outgoing.send_disconnect listeners={}]".format(
                        self.sendDisconnectEvent.getSubscriberCount()
                    )
                )
                """
        Use this notify/confirm disconnect to the Remote
        """
                self.sendDisconnectEvent()

            def send_value(self, path, value):
                """
                Use this method to notify the connected client about
                a single param value change
                """
                self.sendValueEvent(path, value)

        self.serialize = serialize
        self.incoming = Incoming()
        self.outgoing = Outgoing()


def create_connection(server, remote):

    """
    Creates all the logic to connect the remote to the server and start
    receiving broadcasted data, as well as making sure date from the remote
    arrives at and gets processed by the server.

    It returns a single function which performs all disconnect operations.
    """

    logger.debug("[create_connection]")

    cleanups = []

    # register handler when receiving value from remote
    def value_handler(path, value):
        logger.debug("[Server.connect.value_handler]")
        server.handle_remote_value_change(remote, path, value)

    unsub = remote.incoming.valueEvent.add(value_handler)
    cleanups.append(unsub)

    # register handler when receiving schema request from remote
    def schema_request_handler():
        logger.debug("[Server.connect.schema_request_handler]")
        server.handle_remote_schema_request(remote)

    unsub = remote.incoming.requestSchemaEvent.add(schema_request_handler)
    cleanups.append(unsub)

    # add remote to server list
    server.connected_remotes.append(remote)

    def remove():
        if remote in server.connected_remotes:
            server.connected_remotes.remove(remote)

    cleanups.append(remove)

    # done, send confirmation to remote with schema data
    remote.outgoing.send_connect_confirmation(schema_list(server.params))

    cleanups.append(remote.outgoing.send_disconnect)

    def disconnect():
        for func in cleanups:
            func()

    return disconnect


class Server:
    def __init__(self, params, queueIncomingValuesUntilUpdate=False):
        self.params = params
        self.queueIncomingValuesUntilUpdate = queueIncomingValuesUntilUpdate
        self.connected_remotes = []

        self.connections = {}

        self.cleanups = []
        self.cleanups.append(self.params.schemaChangeEvent.add(self.broadcast_schema))
        self.cleanups.append(
            self.params.valueChangeEvent.add(self.broadcast_value_change)
        )

        self.updateFuncs = []

    def __del__(self):
        for r in self.connected_remotes:
            self.disconnect(r)

        for func in self.cleanups:
            func()

    def connect(self, remote):
        logger.debug("[Server.connect]")

        if remote in self.connections:
            logger.warning("[Server.connect] remote already connected")
            return

        # create and save new connection
        self.connections[remote] = create_connection(self, remote)

    def disconnect(self, remote):
        logger.debug("[Server.disconnect]")

        if remote not in self.connections:
            logger.warning("[Server.disconnect] could not find connection")
            return

        disconnector = self.connections[remote]
        disconnector()
        del self.connections[remote]

    def update(self):
        for f in self.updateFuncs:
            f()
        self.updateFuncs.clear()

    def broadcast_schema(self):
        logger.debug("[Server.broadcast_schema]")
        schema_data = schema_list(self.params)
        for r in self.connected_remotes:
            r.outgoing.send_schema(schema_data)

    def broadcast_value_change(self, path, value, param):
        logger.debug(
            "[Server.broadcast_value_change] to {} connected remotes".format(
                len(self.connected_remotes)
            )
        )
        serialized_value = None
        for r in self.connected_remotes:
            if param.type == "g" and r.serialize:
                if serialized_value is None:
                    serialized_value = param.get_serialized()
                r.outgoing.send_value(path, serialized_value)
            else:
                r.outgoing.send_value(path, value)

    def handle_remote_value_change(self, remote, path, value):
        def processNow():
            logger.debug("[Server.handle_remote_value_change]")
            param = get_path(self.params, path)
            if not param:
                logger.warning(
                    "[Server.handle_remote_value_change] unknown path: {}".format(path)
                )
                return
            param.set(value)

        if self.queueIncomingValuesUntilUpdate:
            self.updateFuncs.append(processNow)
            return

        processNow()

    def handle_remote_schema_request(self, remote):
        logger.debug("[Server.handle_remote_schema_request]")
        schema_data = schema_list(self.params)
        remote.outgoing.send_schema(schema_data)


def create_sync_params(remote, request_initial_schema=True):
    """
    Creates an instance of Params, which is updated with information
    received by the given remote
    """
    params = Params()

    # catch incoming schema data and apply it
    def onSchema(schema_data):
        logger.debug("[create_sync_params.onSchema] schema_data={}".format(schema_data))
        apply_schema_list(params, schema_data)

    remote.outgoing.sendSchemaEvent += onSchema

    def onValue(path, value):
        param = get_path(params, path)
        if not param:
            logging.warning(
                "[create_sync_params.onValue] got invalid path: {}".format(path)
            )
            return
        param.set(value)

    remote.outgoing.sendValueEvent += onValue

    # request schema data
    if request_initial_schema:
        remote.incoming.requestSchemaEvent()

    return params
