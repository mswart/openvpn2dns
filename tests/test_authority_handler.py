# -*- coding: UTF-8 -*-
import os.path
import socket

from twisted.names import dns
from twisted.names.resolve import ResolverChain
from IPy import IP

from config import ConfigParser
from openvpnzone import OpenVpnAuthorityHandler


def test_soa():
    cp = ConfigParser()
    cp.parse_data({
        'options': [
            ('instance', 'vpn.example.org'),
        ],
        'vpn.example.org': [
            ('mname', 'dns.example.org'),
            ('rname', 'dns.example.org'),
            ('refresh', '1h'),
            ('retry', '2h'),
            ('expire', '3h'),
            ('minimum', '4h'),
            ('status_file', 'tests/samples/empty.ovpn-status-v1')
        ]
    })
    c = ResolverChain(OpenVpnAuthorityHandler(cp))
    d = c.query(dns.Query('vpn.example.org', dns.SOA, dns.IN))
    rr = d.result[0][0]
    assert rr.name.name == 'vpn.example.org'
    payload = rr.payload
    assert payload.__class__ == dns.Record_SOA
    assert payload.mname.name == 'dns.example.org'
    assert payload.rname.name == 'dns.example.org'
    assert payload.serial == int(os.path.getmtime(
        'tests/samples/empty.ovpn-status-v1'))
    assert payload.refresh == 3600
    assert payload.retry == 2*3600
    assert payload.expire == 3*3600
    assert payload.minimum == 4*3600


def test_a():
    cp = ConfigParser()
    cp.parse_data({
        'options': [
            ('instance', 'vpn.example.org'),
        ],
        'vpn.example.org': [
            ('mname', 'dns.example.org'),
            ('rname', 'dns.example.org'),
            ('refresh', '1h'),
            ('retry', '2h'),
            ('expire', '3h'),
            ('minimum', '4h'),
            ('status_file', 'tests/samples/one.ovpn-status-v1')
        ]
    })
    c = ResolverChain(OpenVpnAuthorityHandler(cp))
    d = c.query(dns.Query('one.vpn.example.org', dns.A, dns.IN))
    rr = d.result[0][0]
    assert rr.name.name == 'one.vpn.example.org'
    payload = rr.payload
    assert payload.__class__ == dns.Record_A
    assert payload.address == socket.inet_aton('198.51.100.8')


def test_aaaa():
    cp = ConfigParser()
    cp.parse_data({
        'options': [
            ('instance', 'vpn.example.org'),
        ],
        'vpn.example.org': [
            ('mname', 'dns.example.org'),
            ('rname', 'dns.example.org'),
            ('refresh', '1h'),
            ('retry', '2h'),
            ('expire', '3h'),
            ('minimum', '4h'),
            ('status_file', 'tests/samples/ipv6.ovpn-status-v1')
        ]
    })
    c = ResolverChain(OpenVpnAuthorityHandler(cp))
    d = c.query(dns.Query('one.vpn.example.org', dns.AAAA, dns.IN))
    rr = d.result[0][0]
    assert rr.name.name == 'one.vpn.example.org'
    payload = rr.payload
    assert payload.__class__ == dns.Record_AAAA
    assert IP(socket.inet_ntop(socket.AF_INET6, payload.address)) \
        == IP('fddc:abcd:1234::1008')


def test_ptr():
    cp = ConfigParser()
    cp.parse_data({
        'options': [
            ('instance', 'vpn.example.org'),
        ],
        'vpn.example.org': [
            ('mname', 'dns.example.org'),
            ('rname', 'dns.example.org'),
            ('refresh', '1h'),
            ('retry', '2h'),
            ('expire', '3h'),
            ('minimum', '4h'),
            ('subnet4', '198.51.100.0/24'),
            ('status_file', 'tests/samples/one.ovpn-status-v1')
        ]
    })
    c = ResolverChain(OpenVpnAuthorityHandler(cp))
    reverse = '8.100.51.198.in-addr.arpa'
    d = c.query(dns.Query(reverse, dns.PTR, dns.IN))
    rr = d.result[0][0]
    assert rr.name.name == reverse
    payload = rr.payload
    assert payload.__class__ == dns.Record_PTR
    assert payload.name.name == 'one.vpn.example.org'


def test_extra_ns():
    cp = ConfigParser()
    cp.parse_data({
        'options': [
            ('instance', 'vpn.example.org'),
        ],
        'vpn.example.org': [
            ('mname', 'dns.example.org'),
            ('rname', 'dns.example.org'),
            ('refresh', '1h'),
            ('retry', '2h'),
            ('expire', '3h'),
            ('minimum', '4h'),
            ('status_file', 'tests/samples/empty.ovpn-status-v1'),
            ('add_entries', 'ns')
        ],
        'ns': [
            ('@', 'NS dns-a.example.org'),
            ('@', 'NS dns-b.example.org')
        ]
    })
    c = ResolverChain(OpenVpnAuthorityHandler(cp))
    d = c.query(dns.Query('vpn.example.org', dns.NS, dns.IN))
    for rr in d.result[0]:
        assert rr.name.name == 'vpn.example.org'
        assert rr.payload.__class__ == dns.Record_NS
    assert set(map(lambda rr: rr.payload.name.name, d.result[0])) \
        == set(('dns-a.example.org', 'dns-b.example.org'))


def test_suffix():
    cp = ConfigParser()
    cp.parse_data({
        'options': [
            ('instance', 'vpn.example.org'),
        ],
        'vpn.example.org': [
            ('mname', 'dns.example.org'),
            ('rname', 'dns.example.org'),
            ('refresh', '1h'),
            ('retry', '2h'),
            ('expire', '3h'),
            ('minimum', '4h'),
            ('suffix', 'clients.vpn.example.org'),
            ('status_file', 'tests/samples/no-fqdn.ovpn-status-v1'),
        ]
    })
    c = ResolverChain(OpenVpnAuthorityHandler(cp))
    # query one:
    d = c.query(dns.Query('one.clients.vpn.example.org', dns.A, dns.IN))
    rr = d.result[0][0]
    assert rr.name.name == 'one.clients.vpn.example.org'
    assert rr.payload.__class__ == dns.Record_A
    assert rr.payload.address == socket.inet_aton('198.51.100.8')
    # query two:
    d = c.query(dns.Query('one.two.clients.vpn.example.org', dns.A, dns.IN))
    rr = d.result[0][0]
    assert rr.name.name == 'one.two.clients.vpn.example.org'
    assert rr.payload.__class__ == dns.Record_A
    assert rr.payload.address == socket.inet_aton('198.51.100.12')


def test_suffix_at():
    cp = ConfigParser()
    cp.parse_data({
        'options': [
            ('instance', 'vpn.example.org'),
        ],
        'vpn.example.org': [
            ('mname', 'dns.example.org'),
            ('rname', 'dns.example.org'),
            ('refresh', '1h'),
            ('retry', '2h'),
            ('expire', '3h'),
            ('minimum', '4h'),
            ('suffix', '@'),
            ('status_file', 'tests/samples/no-fqdn.ovpn-status-v1'),
        ]
    })
    c = ResolverChain(OpenVpnAuthorityHandler(cp))
    # query one:
    d = c.query(dns.Query('one.vpn.example.org', dns.A, dns.IN))
    rr = d.result[0][0]
    assert rr.name.name == 'one.vpn.example.org'
    assert rr.payload.__class__ == dns.Record_A
    assert rr.payload.address == socket.inet_aton('198.51.100.8')
    # query two:
    d = c.query(dns.Query('one.two.vpn.example.org', dns.A, dns.IN))
    rr = d.result[0][0]
    assert rr.name.name == 'one.two.vpn.example.org'
    assert rr.payload.__class__ == dns.Record_A
    assert rr.payload.address == socket.inet_aton('198.51.100.12')
