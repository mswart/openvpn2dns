# -*- coding: UTF-8 -*-
import os.path
import socket

from twisted.names import dns
from twisted.names.resolve import ResolverChain
from twisted.python.failure import Failure
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


def test_extra_ns_backwards4():
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
            ('status_file', 'tests/samples/empty.ovpn-status-v1'),
            ('add_entries', 'ns')
        ],
        'ns': [
            ('@', 'NS dns-a.example.org'),
            ('@', 'NS dns-b.example.org')
        ]
    })
    c = ResolverChain(OpenVpnAuthorityHandler(cp))
    d = c.query(dns.Query('100.51.198.in-addr.arpa', dns.NS, dns.IN))
    for rr in d.result[0]:
        assert rr.name.name == '100.51.198.in-addr.arpa'
        assert rr.payload.__class__ == dns.Record_NS
    assert set(map(lambda rr: rr.payload.name.name, d.result[0])) \
        == set(('dns-a.example.org', 'dns-b.example.org'))


def test_extra_entries():
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
            ('subnet6', 'fe80::/64'),
            ('status_file', 'tests/samples/empty.ovpn-status-v1'),
            ('add_entries', 'all'),
            ('add_entries', 'all2'),
            ('add_forward_entries', 'forward'),
            ('add_backward_entries', 'backward'),
            ('add_backward4_entries', 'backward4'),
            ('add_backward6_entries', 'backward6'),
        ],
        'all':       [('all',       'A 127.0.0.1')],
        'all2':      [('all2',      'A 127.0.0.2')],
        'forward':   [('forward',   'A 127.0.0.3')],
        'backward':  [('backward',  'A 127.0.0.4')],
        'backward4': [('backward4', 'A 127.0.0.5')],
        'backward6': [('backward6', 'A 127.0.0.6')],
    })
    dd = OpenVpnAuthorityHandler(cp)
    c = ResolverChain(dd)

    def test(name, result):
        d = c.query(dns.Query(name, dns.A, dns.IN)).result

        if not result:
            assert d.__class__ is Failure
        else:
            assert type(d) is tuple
            assert len(d[0]) == 1
            assert d[0][0].type == dns.A
            assert socket.inet_ntoa(d[0][0].payload.address) == result

    # test forward:
    test('all.vpn.example.org', '127.0.0.1')
    test('all2.vpn.example.org', '127.0.0.2')
    test('forward.vpn.example.org', '127.0.0.3')
    test('backward.vpn.example.org', False)
    test('backward4.vpn.example.org', False)
    test('backward6.vpn.example.org', False)

    # test backward4:
    test('all.100.51.198.in-addr.arpa', '127.0.0.1')
    test('all2.100.51.198.in-addr.arpa', '127.0.0.2')
    test('forward.100.51.198.in-addr.arpa', False)
    test('backward.100.51.198.in-addr.arpa', '127.0.0.4')
    test('backward4.100.51.198.in-addr.arpa', '127.0.0.5')
    test('backward6.100.51.198.in-addr.arpa', False)

    # test backward6:
    test('all.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa', '127.0.0.1')
    test('all2.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa', '127.0.0.2')
    test('forward.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa', False)
    test('backward.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa', '127.0.0.4')
    test('backward4.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa', False)
    test('backward6.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa', '127.0.0.6')


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
