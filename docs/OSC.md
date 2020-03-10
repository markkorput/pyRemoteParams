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


