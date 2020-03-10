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
```

## OscServer Choreography

 - server broadcasts at interval its host/port/protocol-version information
 - client who picks up the broadcast, sends a /connect with its own ip/port data
 - server responds with confirmation and schema data, from now on, until connection is broken the server sends all changes (value changes or schema changes) to the client

```
# server broadcasts its availability
[server -> broadcast] /params/server '{server-info:json}'

# client requests info
[client -> server] /params/schema <client-port-for-response> [<custom-address-to-respond-with>]
[server -> client] /params/schema '{json}'

# client connects
[client -> server] /params/connect <client-port-for-response> [<addr_prefix>]
[server -> client] [<addr_prefix>]/params/connect/confirmation '{json-schema}'

# client sends new values
[client -> server] /params/value '/id/of/param' <value>
[server -> client] [<addr_prefix>]/params/value '/id/of/param' <value>
[client -> server] [<addr_prefix>]/params/confirm

# server announces schema change
[server -> client] [<addr_prefix>]/params/schema '{json}'
[client -> server] [<addr_prefix>]/params/confirm
```


