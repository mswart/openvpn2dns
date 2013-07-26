# -*- coding: UTF-8 -*-
from openvpnzone import extract_zones_from_status_file

from IPy import IP


def test_empty_server():
    assert extract_zones_from_status_file('tests/samples/empty.ovpn-status-v1') \
        == {}


def test_one_client_on_server():
    assert extract_zones_from_status_file('tests/samples/one.ovpn-status-v1') \
        == {'one.vpn.example.org': [IP('198.51.100.8')]}


def test_multiple_client_on_server():
    assert extract_zones_from_status_file('tests/samples/multiple.ovpn-status-v1') \
        == {
            'one.vpn.example.org': [IP('198.51.100.8')],
            'two.vpn.example.org': [IP('198.51.100.12')],
            'three.vpn.example.org': [IP('198.51.100.16')]
        }


def test_subnet_for_client():
    assert extract_zones_from_status_file('tests/samples/subnet.ovpn-status-v1') \
        == {'one.vpn.example.org': [IP('198.51.100.8')]}


def test_cached_route():
    assert extract_zones_from_status_file('tests/samples/cached-route.ovpn-status-v1') \
        == {'one.vpn.example.org': [IP('198.51.100.8')]}
