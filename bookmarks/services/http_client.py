"""
HTTP client for fetching user-supplied URLs.

All outbound requests that target URLs provided by users (bookmark URLs,
preview images found in page metadata, ...) must go through this module. It
protects against server-side request forgery (SSRF) by refusing to connect to
addresses that are not publicly routable, such as loopback, private network,
link-local (cloud metadata) and carrier-grade NAT addresses.

The check runs when urllib3 opens the socket for a connection, which has a few
useful properties compared to validating URLs up front:

- The hostname is resolved exactly once, and the socket is opened to one of
  the addresses that were checked. This closes the DNS rebinding gap where a
  hostname resolves to a public address during validation and to a private
  address when connecting.
- Redirects are covered automatically, since every redirect hop opens a new
  connection.
- TLS verification and the Host header keep working, because the URL itself
  is never rewritten.

Which addresses are considered public is decided by the IANA special-purpose
address registries, as implemented by the ``ipaddress`` module in the standard
library. This requires Python 3.13 or newer, which correctly classifies
IPv4-mapped IPv6 addresses.

The guard can be relaxed through the ``LD_ALLOWED_INTERNAL_HOSTS`` setting, see
the options documentation for details.

Limitations:

- If an HTTP proxy is configured through environment variables, requests
  bypass the guarded connection classes and connect to the proxy instead,
  which circumvents the protection.
- Subprocesses, such as single-file for HTML snapshots, use their own network
  stack and are not covered.
"""

import functools
import ipaddress
import logging
import socket
import sys
from dataclasses import dataclass, field

import requests  # noqa: TID251 - this module wraps requests with SSRF protection
from django.conf import settings
from requests.adapters import HTTPAdapter  # noqa: TID251
from urllib3 import connection as urllib3_connection
from urllib3 import exceptions as urllib3_exceptions
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.util import connection as urllib3_util_connection

logger = logging.getLogger(__name__)

# Re-exported so that callers do not need to import requests themselves
RequestException = requests.RequestException

SETTING_NAME = "LD_ALLOWED_INTERNAL_HOSTS"
ALLOW_ALL = "*"

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

# IPv6 ranges that the ipaddress module classifies as global, but that embed
# an IPv4 address or are only meaningful on a local network. Treat them as
# internal, like other projects do.
_NON_PUBLIC_IPV6_NETWORKS = [
    # NAT64 well-known prefix, a NAT64 gateway on the local network would
    # connect to the embedded IPv4 address
    ipaddress.ip_network("64:ff9b::/96"),
    # Deprecated IPv4-compatible addresses, e.g. ::127.0.0.1
    ipaddress.ip_network("::/96"),
    # Deprecated site-local addresses, predecessor of unique local addresses
    ipaddress.ip_network("fec0::/10"),
]


class BlockedAddressError(requests.ConnectionError):
    """
    Raised when a request targets a host that resolves to an address that is
    not publicly routable and is not allowed through the allowlist.
    """

    def __init__(self, host: str, address: IPAddress):
        self.host = host
        self.address = address
        super().__init__(
            f"Refusing to connect to {host}, which resolves to the non-public address {address}. "
            f"Use the {SETTING_NAME} option to allow requests to this host."
        )


class _BlockedAddress(Exception):
    """
    Internal exception raised while opening a connection. This intentionally
    does not extend OSError, so that neither the error handling in _new_conn
    nor urllib3's retry logic catch and wrap it. It is converted to
    BlockedAddressError at the module boundary.
    """

    def __init__(self, host: str, address: IPAddress):
        self.host = host
        self.address = address
        super().__init__(host, address)


def is_public_address(address: IPAddress) -> bool:
    """
    Returns whether an IP address is publicly routable, meaning it is not
    reserved for loopback, private networks, link-local, carrier-grade NAT,
    multicast, or other special purposes.
    """
    # is_global and is_multicast classify IPv4-mapped IPv6 addresses by their
    # embedded IPv4 address since Python 3.13
    if address.is_multicast:
        return False
    if any(address in network for network in _NON_PUBLIC_IPV6_NETWORKS):
        return False
    return address.is_global


@dataclass
class Allowlist:
    allow_all: bool = False
    hostnames: list[str] = field(default_factory=list)
    networks: list[IPNetwork] = field(default_factory=list)

    @staticmethod
    def parse(value: str | None) -> "Allowlist":
        allowlist = Allowlist()
        entries = [entry.strip().lower() for entry in (value or "").split(",")]
        for entry in entries:
            if not entry:
                continue
            if entry == ALLOW_ALL:
                allowlist.allow_all = True
                continue
            # IPv6 literals may be written with brackets, as in URLs
            entry = entry.removeprefix("[").removesuffix("]")
            try:
                allowlist.networks.append(ipaddress.ip_network(entry, strict=False))
                continue
            except ValueError:
                pass
            if "/" in entry:
                logger.warning(
                    f"Ignoring invalid network range in {SETTING_NAME}: {entry}"
                )
                continue
            allowlist.hostnames.append(entry)
        return allowlist

    def matches_host(self, host: str) -> bool:
        host = host.lower().rstrip(".")
        for hostname in self.hostnames:
            if hostname.startswith("."):
                # .example.com matches example.com and any subdomain
                if host == hostname[1:] or host.endswith(hostname):
                    return True
            elif host == hostname:
                return True
        return False

    def matches_address(self, address: IPAddress) -> bool:
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        return any(address in network for network in self.networks)


@functools.cache
def get_allowlist() -> Allowlist:
    # Parsed once on first use, so that warnings about invalid entries are
    # only logged once. Tests call get_allowlist.cache_clear() to pick up
    # changed settings.
    return Allowlist.parse(getattr(settings, SETTING_NAME, ""))


def _parse_resolved_address(sockaddr: tuple) -> IPAddress:
    # Strip IPv6 scope id, e.g. fe80::1%eth0
    return ipaddress.ip_address(sockaddr[0].split("%", 1)[0])


def create_guarded_connection(
    address: tuple[str, int],
    timeout=urllib3_util_connection._DEFAULT_TIMEOUT,
    source_address: tuple[str, int] | None = None,
    socket_options=None,
) -> socket.socket:
    """
    Drop-in replacement for urllib3's create_connection that only connects to
    addresses that are allowed by the SSRF policy.
    """
    host, port = address
    allowlist = get_allowlist()

    if allowlist.allow_all or allowlist.matches_host(host):
        return urllib3_util_connection.create_connection(
            address, timeout, source_address, socket_options
        )

    # Resolve the host exactly once. Connections are then made to the
    # resolved addresses, never to the hostname again.
    resolved = socket.getaddrinfo(
        host, port, urllib3_util_connection.allowed_gai_family(), socket.SOCK_STREAM
    )
    for _, _, _, _, sockaddr in resolved:
        resolved_address = _parse_resolved_address(sockaddr)
        if not allowlist.matches_address(resolved_address) and not is_public_address(
            resolved_address
        ):
            raise _BlockedAddress(host, resolved_address)

    # Passing IP literals to urllib3's create_connection does not trigger any
    # DNS lookup, but reuses its socket setup logic
    last_error = None
    for _, _, _, _, sockaddr in resolved:
        try:
            return urllib3_util_connection.create_connection(
                (sockaddr[0], port), timeout, source_address, socket_options
            )
        except OSError as error:
            last_error = error

    if last_error is not None:
        raise last_error
    raise OSError(f"getaddrinfo returned an empty list for {host}")


class _GuardedConnectionMixin:
    # Overrides urllib3.connection.HTTPConnection._new_conn to use the guarded
    # connection function. Error handling mirrors the original implementation.
    def _new_conn(self) -> socket.socket:
        try:
            sock = create_guarded_connection(
                (self._dns_host, self.port),
                self.timeout,
                source_address=self.source_address,
                socket_options=self.socket_options,
            )
        except socket.gaierror as e:
            raise urllib3_exceptions.NameResolutionError(self.host, self, e) from e
        except TimeoutError as e:
            raise urllib3_exceptions.ConnectTimeoutError(
                self,
                f"Connection to {self.host} timed out. (connect timeout={self.timeout})",
            ) from e
        except OSError as e:
            raise urllib3_exceptions.NewConnectionError(
                self, f"Failed to establish a new connection: {e}"
            ) from e

        sys.audit("http.client.connect", self, self.host, self.port)

        return sock


class GuardedHTTPConnection(_GuardedConnectionMixin, urllib3_connection.HTTPConnection):
    pass


class GuardedHTTPSConnection(
    _GuardedConnectionMixin, urllib3_connection.HTTPSConnection
):
    pass


class GuardedHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = GuardedHTTPConnection


class GuardedHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = GuardedHTTPSConnection


class GuardedHTTPAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        super().init_poolmanager(connections, maxsize, block, **pool_kwargs)
        # Instance attribute, does not affect other pool managers
        self.poolmanager.pool_classes_by_scheme = {
            "http": GuardedHTTPConnectionPool,
            "https": GuardedHTTPSConnectionPool,
        }


def request(method: str, url: str, **kwargs) -> requests.Response:
    # Use a new session per request, as background tasks run in multiple
    # threads and sessions are not guaranteed to be thread-safe
    session = requests.Session()
    adapter = GuardedHTTPAdapter()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    try:
        return session.request(method, url, **kwargs)
    except _BlockedAddress as error:
        blocked_error = BlockedAddressError(error.host, error.address)
        logger.warning(f"Blocked request to {url}: {blocked_error}")
        raise blocked_error from None
    finally:
        # Closing the session does not close the response, streaming responses
        # keep their own connection open until they are consumed or closed
        session.close()


def get(url: str, **kwargs) -> requests.Response:
    return request("GET", url, **kwargs)


def head(url: str, **kwargs) -> requests.Response:
    return request("HEAD", url, **kwargs)
