# -*- coding: UTF-8 -*-
import pytest

from config import ConfigParser, OpenVpnInstance
from config import MissingSectionError, InstanceRedifinitionError
from config import UnusedOptionWarning


@pytest.fixture
def cp():
    """ Return a new config parser instance for py.test"""
    return ConfigParser()


def test_ini_file_parsing(cp):
    assert cp.read_data('tests/samples/simple.ini') \
        == {
            'options': [
                ('a', 'value')
            ],
            'hans.b': [
                ('1.2', 'one two three four five six'),
                ('b', 'hans')
            ]
        }


def test_multiple_option_parsing(cp):
    assert cp.read_data('tests/samples/multiple.ini') \
        == {
            'options': [
                ('a', 'value')
            ],
            'hans.b': [
                ('1.2', 'one two three four five six'),
                ('1.2', 'hans')
            ]
        }


def test_space_stripping(cp):
    assert cp.read_data('tests/samples/withSpaces.ini') \
        == {
            'options': [
                ('a', 'value')
            ],
            'hans.b': [
                ('1.2', 'one two three four five six'),
                ('d', 'hans'),
                ('b', '1')
            ]
        }


def test_option_without_section(cp, recwarn):
    cp.read_data('tests/samples/withoutSection.ini')
    w = recwarn.pop(UnusedOptionWarning)
    assert 'foo = bar' in str(w.message)
    w = recwarn.pop(UnusedOptionWarning)
    assert 'bar=foo' in str(w.message)


def test_missing_options_section(cp):
    with pytest.raises(MissingSectionError):
        cp.parse_data({})


def test_useless_options_option(cp, recwarn):
    cp.parse_data({'options': [('foo', 'bar')]})
    w = recwarn.pop(UnusedOptionWarning)
    assert 'foo' in str(w.message)


def test_listen_address(cp):
    cp.parse_data({'options': (('listen', '127.0.0.1:53'), )})
    assert cp.listen_addresses == [('127.0.0.1', 53)]


def test_add_instance(cp):
    cp.data = {'vpn.example.org': [
        ('refresh', '1h'),
        ('retry', '2h'),
        ('rname', 'vpn@example.org'),
        ('notify', 'hans'),
        ('mname', 'dns.example.org'),
        ('expire', '3h'),
        ('notify', 'foo'),
        ('status_file', '/tmp/openvpn.status'),
        ('minimum', '4h'),
    ]}
    instance = cp.parse_instance('vpn.example.org')
    assert instance.name == 'vpn.example.org'
    assert instance.status_file == '/tmp/openvpn.status'
    assert instance.notify == [('hans', 53), ('foo', 53)]
    assert instance.rname == 'vpn.example.org'
    assert instance.mname == 'dns.example.org'
    assert instance.refresh == '1h'
    assert instance.retry == '2h'
    assert instance.expire == '3h'
    assert instance.minimum == '4h'


def test_useless_instance_option(cp, recwarn):
    cp.data = {'instance': [('foo', 'bar')]}
    cp.parse_instance('instance')
    w = recwarn.pop(UnusedOptionWarning)
    assert 'foo' in str(w.message)


def test_instance_redifinition(cp):
    with pytest.raises(InstanceRedifinitionError):
        cp.parse_data({
            'options': (
                ('instance', 'vpn.example.org'),
                ('instance', 'vpn.example.org')
            ),
            'vpn.example.org': [],
        })
