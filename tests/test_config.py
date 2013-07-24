# -*- coding: UTF-8 -*-
from pytest import fixture

from config import ConfigParser


@fixture
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
