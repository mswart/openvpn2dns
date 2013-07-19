from twisted.names import dns


class ConfigParser(object):
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

    def read_file(self, file_name):
        with open(file_name) as f:
            section = None
            for line in f:
                # ignore comments:
                if line.startswith('#'):
                    continue
                line = line.strip()
                # handle section header:
                if line.startswith('[') and line.endswith(']'):
                    section = line[1:-1]
                    if section not in ['options', 'SOA', 'entries']:
                        print('Warning: unknown section {}'.format(section))
                    continue
                option, value = line.split('=', 1)
                option = option.strip()
                value = value.strip()
                if section == 'entries':
                    self.parse_entry(option, value)
                elif section in ['options', 'SOA']:
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
