# -*- coding: UTF-8 -*-
from twisted.names import dns
import pytest

from openvpnzone import InMemoryAuthority


def make_soa(serial):
    return dns.Record_SOA(
        mname='dns.example.org',
        rname='admin.example.org',
        serial=int(serial),
        refresh='1h',
        retry='2h',
        expire='3h',
        minimum='4h'
    )


@pytest.fixture
def a():
    a = InMemoryAuthority()
    soa = make_soa(1)
    records = {'vpn.example.org': [dns.Record_A('127.0.0.1')]}
    a.setData(soa, records)
    a.old_records = records
    return a


def test_no_default_data():
    a = InMemoryAuthority()
    assert a.soa is None
    assert a.records is None


def test_set_data():
    a = InMemoryAuthority()
    soa = object()
    records = [object(), object()]
    assert a.setData(soa, records) is True
    assert a.soa is soa
    assert a.records == records


def test_update_on_new_names(a):
    soa2 = make_soa(2)
    new_records = {
        'vpn.example.org': [dns.Record_A('127.0.0.1')],
        'example.org': [dns.Record_A('127.0.0.8')],
    }
    assert a.setData(soa2, new_records) is True
    assert a.soa.serial is 2
    assert a.records is new_records


def test_update_on_removed_names(a):
    soa2 = make_soa(2)
    new_records = {}
    assert a.setData(soa2, new_records) is True
    assert a.soa.serial is 2
    assert a.records is new_records


def test_update_on_add_record(a):
    soa2 = make_soa(2)
    new_records = {'vpn.example.org': [
        dns.Record_A('127.0.0.1'),
        dns.Record_AAAA('::1'),
    ]}
    assert a.setData(soa2, new_records) is True
    assert a.soa.serial is 2
    assert a.records is new_records


def test_update_on_changed_record(a):
    soa2 = make_soa(2)
    new_records = {'vpn.example.org': [
        dns.Record_A('127.0.0.8'),
    ]}
    assert a.setData(soa2, new_records) is True
    assert a.soa.serial is 2
    assert a.records is new_records


def test_update_on_removed_record(a):
    soa2 = make_soa(2)
    new_records = {'vpn.example.org': []}
    assert a.setData(soa2, new_records) is True
    assert a.soa.serial is 2
    assert a.records is new_records


def test_ignore_update_with_same_data(a):
    soa2 = make_soa(2)
    new_records = {'vpn.example.org': [dns.Record_A('127.0.0.1')]}
    assert a.setData(soa2, new_records) is False
    assert a.soa.serial is 1
    assert a.records is a.old_records


def test_ignore_update_with_same_data_but_different_soa_serial(a):
    soa = make_soa(2)
    soa2 = make_soa(3)
    old_records = {'vpn.example.org': [soa]}
    new_records = {'vpn.example.org': [soa2]}
    a.setData(soa, old_records)
    assert a.setData(soa2, new_records) is False
    assert a.soa is soa
    assert a.records is old_records
