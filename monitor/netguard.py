# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""Outgoing requests that cannot be turned against the local network (SSRF).

An outgoing notification goes to an address that comes from the configuration. Unless `notify.allow_private_targets` is true, a destination is refused when its host is, or RESOLVES to,
a loopback, private (RFC 1918, fc00::/7), link-local (169.254.0.0/16 with the cloud metadata address 169.254.169.254, fe80::/10), shared (100.64.0.0/10), multicast, unspecified or
reserved address. The check is made on the address the connection really uses (the name is resolved once and the socket is opened to that address), so a name that changes its answer
between the check and the connection (DNS rebinding) and every redirect (each hop is a new connection) go through the same rule.
"""
import http.client
import ipaddress
import socket
import ssl
import urllib.error
import urllib.request

SHARED = ipaddress.ip_network("100.64.0.0/10")


class Refused(OSError):
    """The destination is a private address and `notify.allow_private_targets` is off."""


def blocked_ip(value):
    """True for an address that must not be reached from a public-facing notifier. Accepts text or an ipaddress object; IPv4-mapped IPv6 addresses are judged as their IPv4 address."""
    try:
        ip = ipaddress.ip_address(str(value).strip("[]").split("%")[0])
    except ValueError:
        return True
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if ip.version == 6 and ip.sixtofour is not None and blocked_ip(ip.sixtofour):
        return True
    return bool(ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved or (ip.version == 4 and ip in SHARED))


def resolve(host, port=443, resolver=None):
    """The distinct IP addresses of `host` (an address literal is returned as it is). Raises OSError when nothing resolves."""
    try:
        return [str(ipaddress.ip_address(host.strip("[]")))]
    except ValueError:
        pass
    found = []
    for item in (resolver or socket.getaddrinfo)(host, port, type=socket.SOCK_STREAM):
        address = item[4][0]
        if address not in found:
            found.append(address)
    if not found:
        raise OSError("unresolved")
    return found


def check_host(host, port=443, allow_private=False, resolver=None):
    """The address to connect to, or raises Refused. Every address the name resolves to must be allowed (a name that mixes a public and a private answer is refused)."""
    addresses = resolve(host, port, resolver)
    if not allow_private and any(blocked_ip(a) for a in addresses):
        raise Refused("private_target")
    return addresses[0]


def _connect(connection, allow_private, resolver):
    ip = check_host(connection.host, connection.port, allow_private, resolver)
    return socket.create_connection((ip, connection.port), connection.timeout, connection.source_address)


def _handlers(allow_private, resolver):
    class Plain(http.client.HTTPConnection):
        def connect(self):
            self.sock = _connect(self, allow_private, resolver)

    class Secure(http.client.HTTPSConnection):
        def connect(self):
            sock = _connect(self, allow_private, resolver)
            self.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)      # the certificate is checked against the NAME, the socket goes to the checked address

    class HttpHandler(urllib.request.HTTPHandler):
        def http_open(self, req):
            return self.do_open(Plain, req)

    class HttpsHandler(urllib.request.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(Secure, req)
    return [HttpHandler(), HttpsHandler()]


def open_url(request, timeout=8, allow_private=False, resolver=None):
    """urllib's urlopen with the rule above on every connection (the first one and every redirect). A refused destination raises Refused (an OSError)."""
    return urllib.request.build_opener(*_handlers(allow_private, resolver)).open(request, timeout=timeout)


def opener_for(allow_private=False, resolver=None):
    """A function with the shape of urlopen(request, timeout=...) that applies the rule."""
    return lambda request, timeout=8: open_url(request, timeout, allow_private, resolver)


def reason_of(error):
    """Short stable reason for a failed send: private_target when the rule refused it, else failed."""
    cause = error.reason if isinstance(error, urllib.error.URLError) else error
    return "private_target" if isinstance(cause, Refused) else "failed"
