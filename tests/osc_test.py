import json
import time
from typing import Any

from pytest_mock import MockerFixture

from remote_params import Params, osc, schema
from remote_params.server import Server


def _create_server(**kwargs: Any) -> osc.OscServer:
    params = Params()
    params.string("name")
    server = Server(params)
    return osc.OscServer(server, **kwargs)


class TestOsc:
    def test_osc_server_choreography(self, mocker: MockerFixture) -> None:
        #
        # setup
        #

        params = Params()
        params.string("name")

        sendmock = mocker.patch.object(osc.Client, "send")

        # create osc server
        osc_server = osc.OscServer(params, start=False)

        #
        # Client connects
        #

        # create fake incoming connect message
        osc_server.receive("/params/connect", "127.0.0.1:8081")
        # verify a connect confirmation was sent
        sendmock.assert_called_with(
            "/params/connect/confirm", json.dumps(schema.schema_list(params))
        )

        #
        # Client sends new value
        #
        assert params.get("name").get() == ""
        # send_log.clear()
        osc_server.receive("/params/value", "/name", "Fab")
        # verify value got applied into our local params
        assert params.get("name").get() == "Fab"
        assert len(sendmock.call_args_list) == 2
        sendmock.assert_called_with("/params/value", "/name", "Fab")

        #
        # Client sends invalid new value
        #
        osc_server.receive("/params/value", "/foo", "bar")
        assert len(sendmock.call_args_list) == 2

        #
        # Schema change broadcasted to client
        #
        params.int("age")
        assert len(sendmock.call_args_list) == 3
        sendmock.assert_called_with("/params/schema", json.dumps(schema.schema_list(params)))

        #
        # Client requests schema
        #
        osc_server.receive("/params/schema", "192.168.1.2:8080")
        assert len(sendmock.call_args_list) == 4
        sendmock.assert_called_with("/params/schema", json.dumps(schema.schema_list(params)))

        #
        # Client disconnected by server
        #
        for r in osc_server.server.connected_remotes:
            r.outgoing.send_disconnect()

        assert len(sendmock.call_args_list) == 5
        sendmock.assert_called_with("/params/disconnect")

        osc_server.stop()


class TestClient:
    def test_sendSchema(self) -> None:
        client = osc.Client("localhost:8124")
        client.sendSchema('{"foo": "bar"}')


class TestServer:
    def test_receive_schema_request(self, mocker: MockerFixture) -> None:
        sendmock = mocker.patch.object(osc.Client, "send")

        osc_server = _create_server()

        # send schema request
        osc.Client.send_message(
            ("127.0.0.1", osc_server.port),
            osc_server.schema_addr,
            f"127.0.0.1:{osc_server.port+1}",
        )

        # allow some time to process request
        deadline = time.time() + 0.2
        while not len(sendmock.call_args_list) and time.time() < deadline:
            time.sleep(0.01)

        osc_server.stop()

        sendmock.assert_called_once_with(
            osc_server.schema_addr,
            json.dumps(schema.schema_list(osc_server.server.params)),
        )
