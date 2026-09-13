import datetime
import ipaddress
import os
import socket
import ssl
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import SimpleTestCase, override_settings

from bookmarks.services import http_client
from bookmarks.services.http_client import Allowlist, BlockedAddressError


class SelfSignedCertificate:
    """
    Generates a self-signed certificate for localhost / 127.0.0.1 into a
    temporary directory, for testing TLS connections to the local test server.
    """

    def __init__(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cert_path = os.path.join(self.temp_dir.name, "localhost.crt")
        self.key_path = os.path.join(self.temp_dir.name, "localhost.key")

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "localhost")])
        now = datetime.datetime.now(datetime.UTC)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=5))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    ]
                ),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        with open(self.cert_path, "wb") as file:
            file.write(cert.public_bytes(serialization.Encoding.PEM))
        with open(self.key_path, "wb") as file:
            file.write(
                key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                )
            )

    def cleanup(self):
        self.temp_dir.cleanup()


class LocalServer:
    """
    Minimal HTTP server bound to loopback, used to verify the guard against
    real connections instead of mocks. Records the path of every request that
    reached it.
    """

    def __init__(self, certificate: SelfSignedCertificate | None = None):
        self.requests = []
        self.scheme = "https" if certificate else "http"
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                server.requests.append(self.path)
                if self.path.startswith("/redirect-relative"):
                    self.send_response(302)
                    self.send_header("Location", "/target")
                    self.end_headers()
                    return
                if self.path.startswith("/redirect-to/"):
                    self.send_response(302)
                    self.send_header("Location", self.path[len("/redirect-to/") :])
                    self.end_headers()
                    return
                body = b"<html><head><title>Test Server</title></head></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_HEAD(self):
                server.requests.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.end_headers()

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        if certificate:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certificate.cert_path, certificate.key_path)
            self.server.socket = context.wrap_socket(
                self.server.socket, server_side=True
            )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def url(self, host, path="/"):
        return f"{self.scheme}://{host}:{self.port}{path}"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def addrinfo(*addresses, port=80):
    """Builds a socket.getaddrinfo result for the given IPv4 addresses."""
    return [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))
        for address in addresses
    ]


def resolve(hostname, *addresses):
    """
    Patches socket.getaddrinfo so that hostname resolves to the given addresses,
    while all other lookups use the real resolver. Returns the mock, whose
    calls can be inspected to check which names were looked up.
    """
    real_getaddrinfo = socket.getaddrinfo

    def fake_getaddrinfo(host, port, *args, **kwargs):
        if host == hostname:
            return addrinfo(*addresses, port=port)
        return real_getaddrinfo(host, port, *args, **kwargs)

    return mock.patch("socket.getaddrinfo", side_effect=fake_getaddrinfo)


class LocalServerTestCase(SimpleTestCase):
    """
    Base class for tests that make real requests to a local test server.
    Subclasses set `certificate` to run the server with TLS.
    """

    certificate: SelfSignedCertificate | None = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.server = LocalServer(certificate=cls.certificate)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        super().tearDownClass()

    def setUp(self):
        self.server.requests.clear()
        # Pick up settings overridden per test
        http_client.get_allowlist.cache_clear()
        self.addCleanup(http_client.get_allowlist.cache_clear)


class IsPublicAddressTestCase(SimpleTestCase):
    def assertBlocked(self, *addresses):
        for address in addresses:
            self.assertFalse(
                http_client.is_public_address(ipaddress.ip_address(address)),
                f"{address} should not be public",
            )

    def assertPublic(self, *addresses):
        for address in addresses:
            self.assertTrue(
                http_client.is_public_address(ipaddress.ip_address(address)),
                f"{address} should be public",
            )

    def test_blocks_loopback(self):
        self.assertBlocked("127.0.0.1", "127.255.255.254", "::1")

    def test_blocks_unspecified(self):
        self.assertBlocked("0.0.0.0", "::")

    def test_blocks_link_local(self):
        self.assertBlocked("169.254.169.254", "169.254.1.1", "fe80::1")

    def test_blocks_private_networks(self):
        self.assertBlocked(
            "10.0.0.1", "172.16.0.1", "172.31.255.255", "192.168.1.1", "fd12:3456::1"
        )

    def test_blocks_carrier_grade_nat(self):
        self.assertBlocked("100.64.0.1", "100.127.255.255")

    def test_blocks_ipv4_embedded_in_ipv6(self):
        self.assertBlocked(
            # IPv4-mapped
            "::ffff:127.0.0.1",
            "::ffff:10.0.0.1",
            "::ffff:169.254.169.254",
            # 6to4, Teredo
            "2002:7f00:1::",
            "2001:0::7f00:1",
            # NAT64
            "64:ff9b::7f00:1",
            "64:ff9b:1::7f00:1",
            # IPv4-compatible
            "::127.0.0.1",
            "::a9fe:a9fe",
        )

    def test_blocks_site_local(self):
        self.assertBlocked("fec0::1", "feff::1")

    def test_blocks_multicast(self):
        self.assertBlocked("224.0.0.1", "ff02::1")

    def test_allows_public_addresses(self):
        self.assertPublic(
            "8.8.8.8",
            "93.184.216.34",
            "2606:4700::1111",
            "2a00:1450:4001:80b::200e",
            "::ffff:8.8.8.8",
        )


class AllowlistTestCase(SimpleTestCase):
    def test_parse_empty(self):
        for value in [None, "", " ", ","]:
            allowlist = Allowlist.parse(value)
            self.assertFalse(allowlist.allow_all)
            self.assertEqual([], allowlist.hostnames)
            self.assertEqual([], allowlist.networks)

    def test_parse_allow_all(self):
        self.assertTrue(Allowlist.parse("*").allow_all)
        self.assertTrue(Allowlist.parse("nas.local, *").allow_all)
        self.assertFalse(Allowlist.parse("nas.local").allow_all)

    def test_parse_entries(self):
        allowlist = Allowlist.parse(
            " NAS.local , .home.arpa,192.168.1.20, 10.0.0.0/8 ,[::1],fd00::/8"
        )
        self.assertEqual(["nas.local", ".home.arpa"], allowlist.hostnames)
        self.assertEqual(
            [
                ipaddress.ip_network("192.168.1.20/32"),
                ipaddress.ip_network("10.0.0.0/8"),
                ipaddress.ip_network("::1/128"),
                ipaddress.ip_network("fd00::/8"),
            ],
            allowlist.networks,
        )

    def test_parse_ignores_invalid_network(self):
        with self.assertLogs("bookmarks.services.http_client", level="WARNING"):
            allowlist = Allowlist.parse("10.0.0.0/33,nas.local")
        self.assertEqual(["nas.local"], allowlist.hostnames)
        self.assertEqual([], allowlist.networks)

    def test_matches_host(self):
        allowlist = Allowlist.parse("nas.local,.home.arpa")
        self.assertTrue(allowlist.matches_host("nas.local"))
        self.assertTrue(allowlist.matches_host("NAS.LOCAL"))
        self.assertTrue(allowlist.matches_host("nas.local."))
        self.assertTrue(allowlist.matches_host("home.arpa"))
        self.assertTrue(allowlist.matches_host("printer.home.arpa"))
        self.assertFalse(allowlist.matches_host("nas.local.evil.com"))
        self.assertFalse(allowlist.matches_host("mynas.local"))
        self.assertFalse(allowlist.matches_host("nothome.arpa"))
        self.assertFalse(allowlist.matches_host("127.0.0.1"))

    def test_matches_address(self):
        allowlist = Allowlist.parse("192.168.1.20,10.0.0.0/8")
        self.assertTrue(allowlist.matches_address(ipaddress.ip_address("192.168.1.20")))
        self.assertTrue(allowlist.matches_address(ipaddress.ip_address("10.1.2.3")))
        self.assertTrue(
            allowlist.matches_address(ipaddress.ip_address("::ffff:10.1.2.3"))
        )
        self.assertFalse(
            allowlist.matches_address(ipaddress.ip_address("192.168.1.21"))
        )
        self.assertFalse(allowlist.matches_address(ipaddress.ip_address("127.0.0.1")))


class GuardedRequestsTestCase(LocalServerTestCase):
    def assertBlockedRequest(self, url, expected_address=None):
        self.server.requests.clear()
        with (
            self.assertLogs("bookmarks.services.http_client", level="WARNING") as logs,
            self.assertRaises(BlockedAddressError) as context,
        ):
            http_client.get(url, timeout=5)
        self.assertEqual([], self.server.requests, "server should not be reached")
        error = context.exception
        if expected_address:
            self.assertEqual(ipaddress.ip_address(expected_address), error.address)
        self.assertIn(http_client.SETTING_NAME, str(error))
        self.assertIn(url, logs.output[0])
        return error

    def test_blocks_loopback_by_default(self):
        self.assertBlockedRequest(self.server.url("127.0.0.1"), "127.0.0.1")
        self.assertBlockedRequest(self.server.url("localhost"))
        self.assertBlockedRequest(self.server.url("[::1]"), "::1")

    def test_blocks_alternative_loopback_notations(self):
        self.assertBlockedRequest(self.server.url("127.1"), "127.0.0.1")
        self.assertBlockedRequest(self.server.url("0x7f000001"), "127.0.0.1")
        self.assertBlockedRequest(self.server.url("2130706433"), "127.0.0.1")
        self.assertBlockedRequest(self.server.url("0.0.0.0"), "0.0.0.0")
        self.assertBlockedRequest(self.server.url("[::]"), "::")
        self.assertBlockedRequest(
            self.server.url("[::ffff:127.0.0.1]"), "::ffff:127.0.0.1"
        )

    def test_blocks_hostname_resolving_to_private_address(self):
        with resolve("public.example.com", "10.0.0.5"):
            error = self.assertBlockedRequest("http://public.example.com/")
        self.assertEqual("public.example.com", error.host)
        self.assertEqual(ipaddress.ip_address("10.0.0.5"), error.address)

    def test_blocks_hostname_resolving_to_mixed_addresses(self):
        # If any resolved address is non-public, block the request, since the
        # client might connect to either address
        with resolve("public.example.com", "93.184.216.34", "127.0.0.1"):
            self.assertBlockedRequest("http://public.example.com/", "127.0.0.1")

    def test_error_is_a_requests_exception(self):
        with self.assertRaises(requests.ConnectionError):
            http_client.get(self.server.url("127.0.0.1"), timeout=5)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="*")
    def test_allow_all(self):
        response = http_client.get(self.server.url("127.0.0.1"), timeout=5)
        self.assertEqual(200, response.status_code)
        self.assertEqual(["/"], self.server.requests)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="localhost")
    def test_allowlisted_hostname(self):
        response = http_client.get(self.server.url("localhost"), timeout=5)
        self.assertEqual(200, response.status_code)
        self.assertIn("Test Server", response.text)

        # allowing a hostname does not allow the address it resolves to
        self.assertBlockedRequest(self.server.url("127.0.0.1"), "127.0.0.1")

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="127.0.0.1")
    def test_allowlisted_address(self):
        response = http_client.get(self.server.url("127.0.0.1"), timeout=5)
        self.assertEqual(200, response.status_code)

        self.assertBlockedRequest(self.server.url("127.0.0.2"), "127.0.0.2")

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="127.0.0.0/8")
    def test_allowlisted_network(self):
        response = http_client.get(self.server.url("127.0.0.1"), timeout=5)
        self.assertEqual(200, response.status_code)

        self.assertBlockedRequest(self.server.url("[::1]"), "::1")

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="127.0.0.0/8")
    def test_allowlisted_network_matches_ipv4_mapped_address(self):
        response = http_client.get(self.server.url("[::ffff:127.0.0.1]"), timeout=5)
        self.assertEqual(200, response.status_code)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="localhost")
    def test_follows_relative_redirects(self):
        response = http_client.get(
            self.server.url("localhost", "/redirect-relative"), timeout=5
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, len(response.history))
        self.assertEqual(["/redirect-relative", "/target"], self.server.requests)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="localhost")
    def test_blocks_redirect_to_non_public_address(self):
        # The initial request is allowed, the redirect target is not
        target = self.server.url("127.0.0.1", "/secret")
        url = self.server.url("localhost", "/redirect-to/" + target)
        with self.assertRaises(BlockedAddressError) as context:
            http_client.get(url, timeout=5)
        self.assertEqual(ipaddress.ip_address("127.0.0.1"), context.exception.address)
        self.assertEqual(["/redirect-to/" + target], self.server.requests)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="127.0.0.0/8")
    def test_connects_to_resolved_address(self):
        # The name is resolved once by the guard, and the connection is made to
        # the resolved address. A second lookup would fail, since the name does
        # not exist.
        with resolve("does-not-exist.invalid", "127.0.0.1") as spy:
            response = http_client.get(
                self.server.url("does-not-exist.invalid"), timeout=5
            )

        self.assertEqual(200, response.status_code)
        # The hostname is looked up exactly once, any further lookups are for
        # the resolved IP literal, which does not involve DNS
        lookups = [call.args[0] for call in spy.call_args_list]
        self.assertEqual(1, lookups.count("does-not-exist.invalid"))
        for host in lookups:
            if host != "does-not-exist.invalid":
                ipaddress.ip_address(host)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="localhost")
    def test_streaming_response(self):
        with http_client.get(self.server.url("localhost"), stream=True, timeout=5) as r:
            content = b"".join(r.iter_content(chunk_size=8))
        self.assertIn(b"Test Server", content)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="localhost")
    def test_head_request(self):
        response = http_client.head(self.server.url("localhost"), timeout=5)
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/pdf", response.headers["Content-Type"])

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="10.0.0.0/33,localhost")
    def test_logs_invalid_allowlist_entry_once(self):
        with self.assertLogs("bookmarks.services.http_client", level="WARNING") as logs:
            http_client.get(self.server.url("localhost"), timeout=5)
            http_client.get(self.server.url("localhost"), timeout=5)

        self.assertEqual(1, len(logs.output))
        self.assertIn("10.0.0.0/33", logs.output[0])

    def test_unresolvable_host(self):
        with self.assertRaises(requests.ConnectionError):
            http_client.get("http://does-not-exist.invalid/", timeout=5)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="localhost")
    def test_connection_refused(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            unused_port = s.getsockname()[1]
        with self.assertRaises(requests.ConnectionError):
            http_client.get(f"http://localhost:{unused_port}/", timeout=5)


class GuardedHttpsRequestsTestCase(LocalServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.certificate = SelfSignedCertificate()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.certificate.cleanup()

    def test_blocks_by_default(self):
        with self.assertRaises(BlockedAddressError):
            http_client.get(self.server.url("localhost"), timeout=5)
        self.assertEqual([], self.server.requests)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="localhost")
    def test_certificate_verification_is_preserved(self):
        # The test server uses a self-signed certificate, so verification must
        # fail by default...
        with self.assertRaises(requests.exceptions.SSLError):
            http_client.get(self.server.url("localhost"), timeout=5)

        # ...and succeed when trusting the certificate
        response = http_client.get(
            self.server.url("localhost"),
            timeout=5,
            verify=self.certificate.cert_path,
        )
        self.assertEqual(200, response.status_code)

    @override_settings(LD_ALLOWED_INTERNAL_HOSTS="127.0.0.0/8")
    def test_certificate_is_verified_against_hostname_when_pinning_address(self):
        # The guard connects to the resolved IP, but TLS must still verify the
        # certificate against the hostname from the URL. The certificate is
        # issued for localhost, not for this name.
        with (
            resolve("does-not-exist.invalid", "127.0.0.1"),
            self.assertRaises(requests.exceptions.SSLError),
        ):
            http_client.get(
                self.server.url("does-not-exist.invalid"),
                timeout=5,
                verify=self.certificate.cert_path,
            )
