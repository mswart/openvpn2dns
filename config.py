from __future__ import print_function

import os.path
import warnings
import pwd
import grp

from twisted.names import dns
from IPy import IP


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


def extract_status_file_path(config_path):
    """ Extracts the path to the openvpn status file from a openvpn config.

        :raises EnvironmentError: if the config does not contain a status file
            entry
        :return: the absolute path to the status file"""
    import re
    status_search = re.compile(r'^\s*(?P<option>(status|server|server-ipv6))\s+(?P<value>[^#]+)(#.*)?$')

    status_file = None
    subnet4 = None
    subnet6 = None

    with open(config_path, 'r') as conf_file:
        for conf_line in conf_file:
            match = status_search.match(conf_line)
            if not match:
                continue
            if match.group('option') == 'status':
                status_file = os.path.abspath(os.path.join(config_path, '..',
                                              match.group('value').strip()))
            elif match.group('option') == 'server':
                subnet4 = match.group('value').strip()
            elif match.group('option') == 'server-ipv6':
                subnet6 = match.group('value').strip()

    if not status_file:
        raise EnvironmentError('You must specify a status entry!')

    return (status_file, subnet4, subnet6)


class SetSingleValueMixin:
    def set_single_option(self, name, value, convert=None):
        old_value = getattr(self, name, object())
        if old_value is not None:
            warnings.warn('Overwrite old {0} option value ({1})'
                          .format(name, old_value), OptionRedifinitionWarning,
                          stacklevel=2)
        if convert is not None:
            try:
                value = convert(value)
            except Exception as e:
                raise ConfigurationError(e.message)
        setattr(self, name, value)


class OpenVpnInstance(object, SetSingleValueMixin):
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
        self.forward_records = []
        self.backward4_records = []
        self.backward6_records = []
        self.suffix = None
        self.subnet4 = None
        self.subnet6 = None


class ConfigParser(object, SetSingleValueMixin):
    """ Parser and data storage for configuration information.
        The file format uses the INI syntax but with multiple use of option
        names per section therefore the config module is not usable.

        :param str filename: file path to configuration file"""
    def __init__(self, filename=None):
        self.listen_addresses = []
        self.daemon = None
        self.drop = None
        self.user = None
        self.group = None
        self.log = None
        self.pidfile = None
        self.reactor = None
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
                    warnings.warn('Option without sections: {0}'.format(line),
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

    @staticmethod
    def parse_boolean(value):
        if value.lower() in ['true', 't', 'yes', 'y', '1']:
            return True
        if value.lower() in ['false', 'f', 'no', 'n', '0']:
            return False
        raise ValueError('Could not parse boolean value')

    @staticmethod
    def parse_filename(value):
        if not os.path.isfile(value):
            raise ValueError('Could not found config file {0}'.format(value))
        return value

    @staticmethod
    def parse_userid(value):
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return pwd.getpwnam(value)[2]
        except KeyError:
            raise ValueError('Unknown user name or id: {0}'.format(value))

    @staticmethod
    def parse_groupid(value):
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return grp.getgrnam(value)[2]
        except KeyError:
            raise ValueError('Unknown group name or id: {0}'.format(value))

    @staticmethod
    def parse_net(value):
        return IP(value.replace(' ', '/')).reverseName()[:-1]

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
            elif option == 'reactor':
                self.set_single_option('reactor', value)
            elif option == 'log':
                self.set_single_option('log', value)
            elif option == 'daemon':
                self.set_single_option('daemon', value, self.parse_boolean)
            elif option == 'drop-privileges':
                self.set_single_option('drop', value, self.parse_boolean)
            elif option == 'user':
                self.set_single_option('user', value, self.parse_userid)
            elif option == 'group':
                self.set_single_option('group', value, self.parse_groupid)
            elif option == 'pidfile':
                self.set_single_option('pidfile', value, self.parse_boolean)
            else:
                warnings.warn('Unknown option {0} in options section'
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
            raise InstanceRedifinitionError('Instance {0} already defined'
                                            .format(name))
        instance = OpenVpnInstance(name)
        if name not in self.data:
            raise MissingSectionError('section for instance {0}'.format(name))
        for option, value in self.data[name]:
            # openvpn server information:
            if option == 'server_config':
                status, subnet4, subnet6 = extract_status_file_path(value)
                instance.set_single_option('status_file', status)
                if subnet4:
                    instance.set_single_option('subnet4', subnet4, self.parse_net)
                if subnet6:
                    instance.set_single_option('subnet6', subnet6, self.parse_net)
            elif option == 'status_file':
                instance.set_single_option('status_file', os.path.abspath(value))
            elif option == 'subnet4':
                instance.set_single_option('subnet4', value, self.parse_net)
            elif option == 'subnet6':
                instance.set_single_option('subnet6', value, self.parse_net)
            # slave name server notifies:
            elif option == 'notify':
                instance.notify.append((value, 53))
            elif option == 'suffix':
                instance.suffix = value
            # SOA entries:
            elif option in ('rname', 'mname', 'refresh', 'retry', 'expire',
                            'minimum'):
                if option == 'rname':
                    value = value.replace('@', '.', 1)
                if getattr(instance, option) is not None:
                    warnings.warn('Overwrite SOA value {0}'.format(option),
                                  OptionRedifinitionWarning, stacklevel=2)
                setattr(instance, option, value)
            # additional entries:
            elif option in ['add_entries',
                            'add_forward_entries', 'add_backward_entries',
                            'add_backward4_entries', 'add_backward6_entries']:
                if value not in self.data:
                    raise MissingSectionError('Referencing unknown section {0}'
                                              .format(value))
                records = self.parse_entry_section(self.data[value])
                type = option[4:-8]
                if type in ('', 'forward'):
                    instance.forward_records += records
                if type in ('', 'backward', 'backward4'):
                    instance.backward4_records += records
                if type in ('', 'backward', 'backward6'):
                    instance.backward6_records += records
            else:
                warnings.warn('Unknown option {0} in section {1}'.format(option,
                              name), UnusedOptionWarning, stacklevel=2)
        self.instances[name] = instance
        return instance

    @staticmethod
    def parse_entry_section(options, name=None):
        records = []
        for entry, value in options:
            parts = value.split(' ')
            record = getattr(dns, 'Record_%s' % parts[0], None)
            if not record:
                raise NotImplementedError("Record type %r not supported" % type)
            records.append((entry, record(*parts[1:])))
        return records
