import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests
from django.test import SimpleTestCase, override_settings

from bookmarks.services import http_client, ssrf_proxy


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _send(self, status, body, headers=None):
        data = body.encode()
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/redirect-to-blocked":
            self._send(
                302,
                "",
                {"Location": f"http://127.0.0.2:{self.server.blocked_port}/secret"},
            )
        elif self.path == "/chunked":
            self.send_response(200)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for chunk in (b"hello ", b"world"):
                self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
            self.wfile.write(b"0\r\n\r\n")
        elif self.path == "/secret":
            self._send(200, "secret-body")
        else:
            self._send(200, "public-body")


class _Server:
    def __init__(self, host):
        self.httpd = ThreadingHTTPServer((host, 0), _Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@override_settings(LD_ALLOWED_INTERNAL_HOSTS="127.0.0.1/32")
class SsrfProxyTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.public_server = _Server("127.0.0.1")
        cls.blocked_server = _Server("127.0.0.2")
        # The redirect target needs the blocked server's port
        cls.public_server.httpd.blocked_port = cls.blocked_server.port

    @classmethod
    def tearDownClass(cls):
        cls.public_server.stop()
        cls.blocked_server.stop()
        super().tearDownClass()

    def setUp(self):
        http_client.get_allowlist.cache_clear()
        self.addCleanup(http_client.get_allowlist.cache_clear)
        self._proxy_ctx = ssrf_proxy.egress_proxy()
        self.proxy_port = self._proxy_ctx.__enter__()
        self.addCleanup(self._proxy_ctx.__exit__, None, None, None)

    def proxies(self):
        proxy_url = f"http://127.0.0.1:{self.proxy_port}"
        return {"http": proxy_url, "https": proxy_url}

    def test_allows_allowlisted_host(self):
        response = requests.get(
            f"http://127.0.0.1:{self.public_server.port}/",
            proxies=self.proxies(),
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "public-body")

    def test_blocks_non_allowlisted_loopback(self):
        response = requests.get(
            f"http://127.0.0.2:{self.blocked_server.port}/secret",
            proxies=self.proxies(),
            timeout=10,
        )
        self.assertEqual(response.status_code, 403)

    def test_blocks_redirect_to_blocked_host(self):
        response = requests.get(
            f"http://127.0.0.1:{self.public_server.port}/redirect-to-blocked",
            proxies=self.proxies(),
            timeout=10,
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("secret-body", response.text)

    def test_chunked_response_relayed(self):
        response = requests.get(
            f"http://127.0.0.1:{self.public_server.port}/chunked",
            proxies=self.proxies(),
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "hello world")

    def test_connect_tunnel_allows_allowlisted_host(self):
        sock = socket.create_connection(("127.0.0.1", self.proxy_port), timeout=10)
        try:
            sock.sendall(
                f"CONNECT 127.0.0.1:{self.public_server.port} HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{self.public_server.port}\r\n\r\n".encode()
            )
            status_line = sock.makefile("rb").readline().decode()
            self.assertIn("200", status_line)
        finally:
            sock.close()

    def test_connect_tunnel_blocks_non_allowlisted_host(self):
        sock = socket.create_connection(("127.0.0.1", self.proxy_port), timeout=10)
        try:
            sock.sendall(
                f"CONNECT 127.0.0.2:{self.blocked_server.port} HTTP/1.1\r\n"
                f"Host: 127.0.0.2:{self.blocked_server.port}\r\n\r\n".encode()
            )
            status_line = sock.makefile("rb").readline().decode()
            self.assertIn("403", status_line)
        finally:
            sock.close()
