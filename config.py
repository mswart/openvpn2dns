from __future__ import print_function

import warnings

from twisted.names import dns


class ConfigurationError(Exception):
    pass


class MissingSectionError(ConfigurationError):
    pass


class InstanceRedifinitionError(ConfigurationError):
    pass


class ConfigurationWarning(UserWarning):
    pass


class UnusedOptionWarning(ConfigurationWarning):
    pass


class OptionRedifinitionWarning(ConfigurationWarning):
    pass


SOA = ['rname', 'mname', 'refresh', 'retry', 'expire', 'minimum']


class OpenVpnInstance(object):
    def __init__(self, name):
        self.name = name
        self.status_file = None
        self.notify = []
        self.rname = None
        self.mname = None
        self.refresh = None
        self.retry = None
        self.expire = None
        self.minimum = None
        self.records = []


class ConfigParser(object):
    """ Parser and data storage for configuration information.
        The file format uses the INI syntax but with multiple use of option
        names per section therefore the config module is not usable.

        :param str filename: file path to configuration file"""
    def __init__(self, filename=None):
        self.listen_addresses = []
        self.instances = {}
        if filename:
            self.read_file(filename)

    @staticmethod
    def read_data(filename):
        """ Reads the given file name. It assumes that the file has a INI file
            syntax. The parser returns the data without comments and fill
            characters. It supports multiple option with the same name per
            section but not multiple sections with the same name.

            :param str filename: path to INI file
            :return: a dictionary - the key is the section name value, the
                option is a array of (option name, option value) tuples"""
        sections = {}
        with open(filename) as f:
            section = None
            options = None
            for line in f:
                # ignore comments:
                if line.startswith('#'):
                    continue
                line = line.strip()
                if not line:
                    continue
                # handle section header:
                if line.startswith('[') and line.endswith(']'):
                    if section:  # save old section data
                        sections[section] = options
                    section = line[1:-1]
                    options = []
                    continue
                if section is None:
                    warnings.warn('Option without sections: {}'.format(line),
                                  UnusedOptionWarning, stacklevel=2)
                    continue
                option, value = line.split('=', 1)
                options.append((option.strip(), value.strip()))
            if section:  # save old section data
                sections[section] = options
        return sections

    def read_file(self, file_name):
        """ Read and parse the configuration file"""
        self.parse_data(self.read_data(file_name))

    def parse_data(self, data):
        """ Parse configuration data

            :param dict data: data extracted from :meth:`read_data`
            :raises ConfigurationError: missing information"""
        # store data for other methods:
        self.data = data
        # handle main options:
        if 'options' not in data:
            raise MissingSectionError('Missing options section')
        for option, value in data['options']:
            if option == 'listen':
                self.add_listen_address(value)
            elif option == 'instance':
                self.parse_instance(value)
            else:
                warnings.warn('Unknown option {} in options section'
                              .format(option), UnusedOptionWarning,
                              stacklevel=2)

    def add_listen_address(self, listen):
        """ Add a listen information

            :param str listen: listen information (name, ip, port)"""
        address, port = listen.split(':', 1)
        self.listen_addresses.append((address, int(port)))

    def parse_instance(self, name):
        """ register one openvpn status instance

            :param str name: name for this instance (used as zone name)"""
        if name in self.instances:
            raise InstanceRedifinitionError('Instance {} already defined'
                                            .format(name))
        instance = OpenVpnInstance(name)
        if name not in self.data:
            raise MissingSectionError('section for instance {}'.format(name))
        for option, value in self.data[name]:
            # status file:
            if option == 'status_file':
                instance.status_file = value
            # slave name server notifies:
            elif option == 'notify':
                instance.notify.append((value, 53))
            # SOA entries:
            elif option in SOA:
                if option == 'rname':
                    value = value.replace('@', '.', 1)
                if getattr(instance, option) is not None:
                    warnings.warn('Overwrite SOA value {}'.format(option),
                                  OptionRedifinitionWarning, stacklevel=2)
                setattr(instance, option, value)
            # additional entries:
            elif option == 'add_entries':
                if value not in self.data:
                    raise MissingSectionError('Referencing unknown section {}'
                                              .format(value))
                instance.records += self.parse_entry_section(self.data[value],
                                                             name=name)
            else:
                warnings.warn('Unknown option {} in section {}'.format(option,
                              name), UnusedOptionWarning, stacklevel=2)
        self.instances[name] = instance
        return instance

    @staticmethod
    def parse_entry_section(options, name=None):
        records = []
        for entry, value in options:
            if entry == '@':
                entry = ''
            if not entry.endswith('.'):
                entry = entry + name
            parts = value.split(' ')
            record = getattr(dns, 'Record_%s' % parts[0], None)
            if not record:
                raise NotImplementedError("Record type %r not supported" % type)
            records.append((entry, record(*parts[1:])))
        return records
