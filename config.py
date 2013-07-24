from twisted.names import dns


class ConfigParser(object):
    """ Parser and data storage for configuration information.
        The file format uses the INI syntax but with multiple use of option
        names per section therefore the config module is not usable.

        :param str filename: file path to configuration file"""
    def __init__(self, filename=None):
        self.status_file = None
        self.listen = []
        self.notify = []
        self.name = None
        self.zone_admin = None
        self.master_name = None
        self.refresh = None
        self.retry = None
        self.expire = None
        self.minimum = None
        self.records = []
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
                    raise ValueError('Options without sections')
                option, value = line.split('=', 1)
                options.append((option.strip(), value.strip()))
            if section:  # save old section data
                sections[section] = options
        return sections

    def read_file(self, file_name):
        data = self.read_data(file_name)
        for section in ('options', 'SOA', 'entries'):
            for option, value in data[section]:
                if section == 'entries':
                    self.parse_entry(option, value)
                else:
                    method = getattr(self, section + '__' + option, None)
                    if method is None:
                        print('Warning: unknown option {} in section {}'.format(
                            option, section))
                    else:
                        method(value)

    def options__status_file(self, file_name):
        self.status_file = file_name

    def options__listen(self, listen):
        address, port = listen.split(':', 1)
        self.listen.append((address, int(port)))

    def options__notify(self, host):
        self.notify.append((host, 53))

    def options__name(self, name):
        self.name = name

    def SOA__zone_admin(self, admin):
        self.zone_admin = admin.replace('@', '.')

    def SOA__master_name(self, name):
        self.master_name = name

    def SOA__refresh(self, refresh):
        self.refresh = refresh

    def SOA__retry(self, retry):
        self.retry = retry

    def SOA__expire(self, expire):
        self.expire = expire

    def SOA__minimum(self, minimum):
        self.minimum = minimum

    def parse_entry(self, entry, value):
        if entry == '@':
            entry = ''
        if not entry.endswith('.'):
            entry = entry + self.name
        parts = value.split(' ')
        record = getattr(dns, 'Record_%s' % parts[0], None)
        if not record:
            raise NotImplementedError("Record type %r not supported" % type)
        self.records.append((entry, record(*parts[1:])))
