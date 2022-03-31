# import asyncio, asynctest, websockets, json
# from remote_params import HttpServer, Params, Server, Remote, create_sync_params, schema_list

# from remote_params.WebsocketServer import WebsocketServer

# class MockSocket:
#   def __init__(self):
#     self.close_count = 0
#     self.msgs = []

#   def close(self):
#     self.close_count += 1

#   async def send(self, msg):
#     self.msgs.append(msg)

# class TestWebsocketServer(asynctest.TestCase):
#   def setUp(self):
#     self.params = params = Params()
#     self.p1 = params.int('some_int')
#     self.p1.set(0)

#     self.wss = WebsocketServer(Server(self.params), start=False)

#   def tearDown(self):
#     self.wss.stop()

#   def test_default_port(self):
#     self.assertEqual(self.wss.port, 8081)

#   async def test_connects_only_one_remote(self):
#     self.assertEqual(len(self.wss.server.connected_remotes), 0)
#     await self.wss.start_async()
#     self.assertEqual(len(self.wss.server.connected_remotes), 1)

#     uri = f'ws://localhost:{self.wss.port}'
#     async with websockets.connect(uri) as websocket:
#       self.assertEqual(len(self.wss.server.connected_remotes), 1)

#       async with websockets.connect(uri) as websocket:
#         self.assertEqual(len(self.wss.server.connected_remotes), 1)

#       self.assertEqual(len(self.wss.server.connected_remotes), 1)

#     self.assertEqual(len(self.wss.server.connected_remotes), 1)
#     self.wss.stop()
#     self.assertEqual(len(self.wss.server.connected_remotes), 0)

#   async def test_incoming_value(self):
#     await self.wss._onMessage(f'POST /some_int?value={3}', None)
#     self.assertEqual(self.p1.value, 0) # server not started

#     await self.wss.start_async()
#     await self.wss._onMessage(f'POST /some_int?value={4}', None)
#     self.assertEqual(self.p1.value, 4) # param changed

#     await self.wss._onMessage(f'POST /wrong_int?value={5}', None)
#     self.assertEqual(self.p1.value, 4) # wrong url

#     self.wss.stop()
#     await self.wss._onMessage(f'POST /wrong_int?value={6}', None)
#     self.assertEqual(self.p1.value, 4) # server stopped

#   async def test_stop_message(self):
#     mocksock = MockSocket()
#     await self.wss._onMessage('stop', mocksock)
#     self.assertEqual(mocksock.close_count, 1)

#   async def test_responds_to_schema_request_with_schema_json(self):
#     mocksocket = MockSocket()

#     await self.wss._onMessage(f'GET schema.json', mocksocket)

#     # verify responded with schema json
#     self.assertEqual(mocksocket.msgs, [
#       f'POST schema.json?schema={json.dumps(schema_list(self.params))}'
#     ])

#   async def test_broadcasts_value_changes(self):
#     await self.wss.start_async()

#     # connect client
#     uri = f'ws://127.0.0.1:{self.wss.port}'
#     async with websockets.connect(uri) as ws:
#       # receive welcome message
#       msg = await ws.recv()
#       self.assertEqual(msg, 'welcome to pyRemoteParams websockets')

#       # change parameter value
#       self.p1.set(2)
#       # receive parameter value change
#       msg = await ws.recv()
#       self.assertEqual(msg, 'POST /some_int?value=2')

#   async def test_broadcasts_schema_change(self):
#     await self.wss.start_async()

#     # connect client
#     uri = f'ws://127.0.0.1:{self.wss.port}'
#     async with websockets.connect(uri) as ws:
#       # receive welcome message
#       msg = await ws.recv()
#       self.assertEqual(msg, 'welcome to pyRemoteParams websockets')

#       # change schema layout value
#       self.params.string('name')

#       # receive parameter value change
#       msg = await ws.recv()
#       self.assertEqual(msg, f'POST schema.json?schema={json.dumps(schema_list(self.params))}')
