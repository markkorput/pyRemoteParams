# pyRemoteParams
<!-- [![Build Status](https://travis-ci.org/markkorput/pyevento.svg)](https://travis-ci.org/markkorput/pyevento) -->


Python remote_params package lets you add (remote) GUI controlable parameters to your pyhton application.

## Install

```shell
pip install remote_params
```

## Run tests
```shell
python setup.py test
```

## Usage

```python
person1 = Params()
person1.string('name')

person2 = Params()
person2.string('name')

room = Params()
room.group(person1)
room.group(person2)

params_osc_server = create_osc_server(room, port=8082)
# or
params_websocket_server = WebsocketServer(Server(room), port=8083)
```
