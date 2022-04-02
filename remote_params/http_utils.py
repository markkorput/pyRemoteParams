import logging
import os
import re
import socket
import threading
from http.client import HTTPSConnection
from http.server import CGIHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Literal, Optional
from urllib.parse import urlsplit, urlunsplit

from evento import Event

Method = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]

log = logging.getLogger(__name__)


class HttpRequest:
    def __init__(
        self,
        path: str,
        handler: "_CustomHandler",
        method: Method = "GET",
    ) -> None:
        self.path = path
        self.handler = handler
        self.method = method
        parts = urlsplit(self.path)
        # newpath = re.sub('^{}'.format(scope), '', parts.path)
        # unscopedreqpath = urlunsplit((parts.scheme, parts.netloc, newpath, parts.query, parts.fragment))
        self.query = parts.query

    def respondWithCode(self, code: int) -> None:
        self.handler.respond(code)

    def respond(self, code: int, content: bytes) -> None:
        self.handler.respond(code, content)

    def respondWithFile(self, filePath: str) -> None:
        self.handler.respondWithFile(filePath)

    def unscope(self, scope: str) -> "HttpRequest":
        if urlsplit is None or urlunsplit is None:
            return HttpRequest(self.path, self.handler, method=self.method)

        parts = urlsplit(self.path)
        newpath = re.sub("^{}".format(scope), "", parts.path)
        unscopedreqpath = urlunsplit(
            (parts.scheme, parts.netloc, newpath, parts.query, parts.fragment)
        )
        return HttpRequest(unscopedreqpath, self.handler, method=self.method)


class _CustomHandler(CGIHTTPRequestHandler, object):
    def __init__(
        self, requestCallback: Callable[[HttpRequest], None], *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.requestCallback = requestCallback
        self.hasResponded: bool = False
        self.respondedWithFile: Optional[str] = None

    def respond(
        self, code: Optional[int] = None, body: Optional[bytes] = None, headers: dict[str, Any] = {}
    ) -> None:
        self.hasResponded = True

        if code is None:
            self.send_response(404)
            self.end_headers()
            # self.wfile.close()
            return

        self.send_response(code)
        if headers:
            for key in headers:
                self.send_header(key, headers[key])

        self.end_headers()
        if body:
            self.wfile.write(body)
        # self.wfile.close()
        return

    def respondWithFile(self, filePath: str) -> None:
        self.respondedWithFile = filePath

    def process_request(self, method: Method = "GET") -> bool:
        req = HttpRequest(self.path, self, method=method)
        self.requestCallback(req)

        return self.hasResponded

    def do_HEAD(self) -> None:
        if not self.process_request(method="HEAD"):
            super().do_HEAD()

    def do_GET(self) -> None:
        if not self.process_request(method="GET"):
            super().do_GET()

    def do_POST(self) -> None:
        if not self.process_request(method="POST"):
            super().do_POST()

    def translate_path(self, path: str) -> str:
        if self.respondedWithFile:
            if os.path.isfile(self.respondedWithFile):
                return self.respondedWithFile
        return CGIHTTPRequestHandler.translate_path(self, path)


def createRequestHandler(
    requestCallback: Callable[[HttpRequest], None], verbose: bool = False
) -> type[_CustomHandler]:
    class CustomHandler(_CustomHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(requestCallback, *args, **kwargs)

    # class CustomHandler(CGIHTTPRequestHandler, object):
    #     def __init__(self, *args, **kwargs) -> None:
    #         self.hasResponded = False
    #         self.respondedWithFile = None
    #         super().__init__(*args, **kwargs)

    #     def respond(self, code=None, body=None, headers=None) -> None:
    #         self.hasResponded = True

    #         if code is None:
    #             self.send_response(404)
    #             self.end_headers()
    #             # self.wfile.close()
    #             return

    #         self.send_response(code)
    #         if headers:
    #             for key in headers:
    #                 self.send_header(key, headers[key])

    #         self.end_headers()
    #         if body:
    #             self.wfile.write(body)
    #         # self.wfile.close()
    #         return

    #     def respondWithFile(self, filePath) -> None:
    #         self.respondedWithFile = filePath

    #     def process_request(self, method="GET") -> None:
    #         req = HttpRequest(self.path, self, method=method)
    #         requestCallback(req)

    #         return self.hasResponded

    #     def do_HEAD(self) -> None:
    #         if not self.process_request(method="HEAD"):
    #             super().do_HEAD()

    #     def do_GET(self) -> None:
    #         if not self.process_request(method="GET"):
    #             super().do_GET()

    #     def do_POST(self) -> None:
    #         if not self.process_request(method="POST"):
    #             super().do_POST()

    #     def do_PUT(self) -> None:
    #         if not self.process_request(method="PUT"):
    #             super().do_PUT()

    #     def translate_path(self, path) -> str:
    #         if self.respondedWithFile:
    #             if os.path.isfile(self.respondedWithFile):
    #                 return self.respondedWithFile
    #         return CGIHTTPRequestHandler.translate_path(self, path)

    return CustomHandler


class HttpServer(threading.Thread):
    def __init__(self, port: int = 8080, start: bool = True) -> None:
        threading.Thread.__init__(self)
        self.http_server: Optional[HTTPServer] = None
        self.port = port

        self.requestEvent: Event[HttpRequest] = Event()
        self.threading_event: Optional[threading.Event] = None

        if start:
            self.startServer()

    def __del__(self) -> None:
        self.stopServer()

    def startServer(self) -> None:
        self.threading_event = threading.Event()
        self.threading_event.set()
        log.debug("[HttpServer] starting server thread")
        self.start()  # start thread

    def stopServer(self, joinThread: bool = True) -> None:
        if not self.is_alive():
            return

        if self.threading_event:
            self.threading_event.clear()

        log.debug("[HttpServer] sending GET request to stop HTTP server from blocking...")

        try:
            connection = HTTPSConnection("127.0.0.1", self.port)
            connection.request("HEAD", "/")
            connection.getresponse()
        except socket.error:
            pass

        if joinThread:
            self.join()

    def run(self) -> None:
        threading_event = self.threading_event
        assert threading_event

        log.debug("[HttpServer] starting server on port {0}".format(self.port))
        HandlerClass = createRequestHandler(self.onRequest)
        http_server = HTTPServer(("", self.port), HandlerClass)
        self.http_server = http_server

        # self.httpd.serve_forever()
        # self.httpd.server_activate()
        while threading_event.is_set():
            try:
                http_server.handle_request()
            except Exception as exc:
                print("[HttpServer] exception:")
                print(exc)

        log.debug("[HttpServer] closing server at port {0}".format(self.port))
        http_server.server_close()
        http_server = None

    def onRequest(self, req: HttpRequest) -> None:
        log.debug(
            "[HttpServer {}] request from {}".format(str(req.path), str(req.handler.client_address))
        )
        self.requestEvent(req)
