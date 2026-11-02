"""
Local egress proxy for HTML snapshots.

Headless Chromium, spawned by single-file, has its own network stack, so
the guard in http_client.py does not cover snapshot fetches: a page that
passes the pre-check can redirect Chromium to a non-public address, or
reference one as a subresource, and the response lands in the snapshot.
Running Chromium behind this proxy closes that gap: every request the
browser makes — page, redirect hop, subresource — is validated against
the same SSRF policy before connecting, and the connection goes to an
address that was checked, never back to the hostname.

The proxy binds 127.0.0.1 on an ephemeral port and only lives for one
snapshot. It opens direct sockets and never consults environment proxy
variables, so the proxy-env bypass documented in http_client.py does not
apply to this path.
"""

import logging
import select
import socket
import threading
from contextlib import contextmanager
from urllib.parse import urlsplit

from bookmarks.services import http_client

logger = logging.getLogger(__name__)

_SOCKET_TIMEOUT = 60

# Headers that must not be forwarded: hop-by-hop headers, plus anything
# that would let the client steer the proxy itself.
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-connection",
    "proxy-authorization",
    "te",
    "trailer",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class _BufReader:
    """Buffered reader over a socket, so bytes read ahead are never lost."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buf = bytearray()

    def _fill(self):
        data = self.sock.recv(65536)
        if not data:
            raise EOFError("connection closed")
        self.buf += data

    def readline(self, limit: int = 65536) -> bytes:
        while True:
            idx = self.buf.find(b"\n")
            if idx >= 0:
                line = bytes(self.buf[: idx + 1])
                del self.buf[: idx + 1]
                return line
            if len(self.buf) >= limit:
                line = bytes(self.buf)
                self.buf.clear()
                return line
            self._fill()

    def read_exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            self._fill()
        data = bytes(self.buf[:n])
        del self.buf[:n]
        return data

    def read_chunked(self):
        """Yield de-chunked body bytes from a chunked transfer encoding."""
        while True:
            size_line = self.readline().split(b";", 1)[0].strip()
            size = int(size_line, 16)
            if size == 0:
                # Trailers run until a blank line
                while True:
                    line = self.readline()
                    if line in (b"\r\n", b"\n", b""):
                        break
                return
            yield self.read_exact(size)
            self.read_exact(2)  # CRLF after each chunk


def _read_headers(reader: _BufReader) -> list[tuple[str, str]]:
    headers = []
    while True:
        line = reader.readline()
        if line in (b"\r\n", b"\n", b""):
            return headers
        name, _, value = line.decode("iso-8859-1").partition(":")
        headers.append((name.strip().lower(), value.strip()))


def _header(headers: list[tuple[str, str]], name: str) -> str | None:
    for key, value in headers:
        if key == name:
            return value
    return None


def _split_host_port(target: str, default_port: int) -> tuple[str, int] | None:
    try:
        if target.startswith("["):
            host, _, rest = target[1:].partition("]")
            port = int(rest.lstrip(":") or default_port)
            return host, port
        if ":" in target:
            host, _, port = target.rpartition(":")
            return host, int(port)
        return target, default_port
    except ValueError:
        return None


def _connect_checked(host: str, port: int) -> socket.socket | None:
    """
    Connect to a policy-checked address, or return None when blocked.
    Raises OSError when every checked address refuses the connection.
    """
    try:
        resolved = http_client.resolve_allowed_addresses(host, port)
    except http_client._BlockedAddress as error:
        logger.warning(f"Blocked proxied request to {host}: {error}")
        return None
    if resolved is None:
        # Allowlisted host: no address check needed
        sock = socket.create_connection((host, port), timeout=_SOCKET_TIMEOUT)
        return sock
    last_error = None
    for family, _, _, _, sockaddr in resolved:
        try:
            sock = socket.socket(family, socket.SOCK_STREAM)
            sock.settimeout(_SOCKET_TIMEOUT)
            sock.connect((sockaddr[0], port))
            return sock
        except OSError as error:
            last_error = error
    if last_error is not None:
        raise last_error
    raise OSError(f"getaddrinfo returned an empty list for {host}")


def _send_simple(sock: socket.socket, status: int, reason: str):
    body = f"{status} {reason}\n".encode()
    sock.sendall(
        f"HTTP/1.1 {status} {reason}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n\r\n".encode()
        + body
    )


def _handle_connect(conn: socket.socket, reader: _BufReader, target: str):
    split = _split_host_port(target, 443)
    if split is None:
        _send_simple(conn, 400, "Bad Request")
        return
    host, port = split
    try:
        target_sock = _connect_checked(host, port)
    except OSError:
        _send_simple(conn, 502, "Bad Gateway")
        return
    if target_sock is None:
        _send_simple(conn, 403, "Forbidden")
        return
    try:
        conn.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        # Bytes the buffered reader already pulled in belong to the tunnel
        if reader.buf:
            target_sock.sendall(bytes(reader.buf))
            reader.buf.clear()
        # Relay raw bytes both ways until either side closes
        while True:
            ready, _, _ = select.select([conn, target_sock], [], [], 60)
            if not ready:
                break
            if conn in ready:
                data = conn.recv(65536)
                if not data:
                    break
                target_sock.sendall(data)
            if target_sock in ready:
                data = target_sock.recv(65536)
                if not data:
                    break
                conn.sendall(data)
    except OSError:
        pass
    finally:
        target_sock.close()


def _forward_request_body(
    reader: _BufReader, target_sock: socket.socket, headers: list[tuple[str, str]]
):
    content_length = _header(headers, "content-length")
    transfer_encoding = _header(headers, "transfer-encoding") or ""
    if "chunked" in transfer_encoding.lower():
        # Forward chunked framing verbatim
        while True:
            size_line = reader.readline()
            target_sock.sendall(size_line)
            size = int(size_line.split(b";", 1)[0].strip(), 16)
            if size == 0:
                while True:
                    line = reader.readline()
                    target_sock.sendall(line)
                    if line in (b"\r\n", b"\n", b""):
                        break
                return
            target_sock.sendall(reader.read_exact(size + 2))
    elif content_length is not None:
        target_sock.sendall(reader.read_exact(int(content_length)))


def _handle_http(
    conn: socket.socket,
    reader: _BufReader,
    method: str,
    target: str,
    headers: list[tuple[str, str]],
):
    split = urlsplit(target)
    if split.scheme != "http" or not split.hostname:
        _send_simple(conn, 400, "Bad Request")
        return
    host = split.hostname
    port = split.port or 80
    try:
        target_sock = _connect_checked(host, port)
    except OSError:
        _send_simple(conn, 502, "Bad Gateway")
        return
    if target_sock is None:
        _send_simple(conn, 403, "Forbidden")
        return
    try:
        path = split.path or "/"
        if split.query:
            path += "?" + split.query
        lines = [f"{method} {path} HTTP/1.1"]
        host_header = host if port == 80 else f"{host}:{port}"
        lines.append(f"Host: {host_header}")
        for name, value in headers:
            if name in _HOP_BY_HOP or name == "host":
                continue
            if (
                name == "content-length"
                and "chunked" in (_header(headers, "transfer-encoding") or "").lower()
            ):
                continue
            lines.append(f"{name}: {value}")
        lines.append("Connection: close")
        target_sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1"))
        if _header(headers, "expect") == "100-continue":
            conn.sendall(b"HTTP/1.1 100 Continue\r\n\r\n")
        _forward_request_body(reader, target_sock, headers)

        target_reader = _BufReader(target_sock)
        status_line = target_reader.readline()
        response_headers = _read_headers(target_reader)
        out = [status_line.decode("iso-8859-1").rstrip("\r\n")]
        for name, value in response_headers:
            if name in _HOP_BY_HOP or name in ("content-length",):
                continue
            out.append(f"{name}: {value}")
        out.append("Connection: close")
        conn.sendall(("\r\n".join(out) + "\r\n\r\n").encode("iso-8859-1"))

        status_code = int(status_line.split()[1])
        if method.upper() == "HEAD" or status_code in (204, 304) or status_code < 200:
            return
        transfer_encoding = _header(response_headers, "transfer-encoding") or ""
        content_length = _header(response_headers, "content-length")
        if "chunked" in transfer_encoding.lower():
            for chunk in target_reader.read_chunked():
                conn.sendall(chunk)
        elif content_length is not None:
            remaining = int(content_length)
            while remaining > 0:
                data = target_reader.read_exact(min(remaining, 65536))
                conn.sendall(data)
                remaining -= len(data)
        else:
            # Close-delimited body: relay until the origin closes
            while True:
                try:
                    if target_reader.buf:
                        data = bytes(target_reader.buf)
                        target_reader.buf.clear()
                    else:
                        data = target_reader.sock.recv(65536)
                except OSError:
                    break
                if not data:
                    break
                conn.sendall(data)
    except (OSError, EOFError, ValueError):
        pass
    finally:
        target_sock.close()


def _handle_client(conn: socket.socket):
    conn.settimeout(_SOCKET_TIMEOUT)
    reader = _BufReader(conn)
    try:
        while True:
            try:
                request_line = reader.readline()
            except EOFError:
                break
            if not request_line.strip():
                continue
            parts = request_line.decode("iso-8859-1").strip().split()
            if len(parts) != 3:
                _send_simple(conn, 400, "Bad Request")
                break
            method, target, _version = parts
            headers = _read_headers(reader)
            if method.upper() == "CONNECT":
                _handle_connect(conn, reader, target)
                break
            _handle_http(conn, reader, method, target, headers)
            # Every plain response says Connection: close
            break
    except (OSError, EOFError, ValueError):
        pass
    finally:
        conn.close()


@contextmanager
def egress_proxy():
    """Run the egress proxy on 127.0.0.1 for one snapshot; yields its port."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(64)
    listener.settimeout(0.5)
    stop = threading.Event()

    def serve():
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=_handle_client, args=(conn,), daemon=True).start()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        stop.set()
        listener.close()
        thread.join(timeout=2)
