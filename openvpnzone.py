import os.path
from datetime import datetime
import signal

from twisted.names import dns
from twisted.names.authority import FileAuthority

from twisted.internet import inotify
from twisted.python import filepath


def extract_status_file_path(config_path):
    """ Extracts the path to the openvpn status file from a openvpn config.

        :raises EnvironmentError: if the config does not contain a status file
            entry
        :return: the absolute path to the status file"""
    import re
    status_search = re.compile(r'^\s*status\s+(?P<value>[^#]+)(#.*)?$')

    status_file = None

    with open(config_path, 'r') as conf_file:
        for conf_line in conf_file:
            match = status_search.match(conf_line)
            if match:
                status_file = match.group('value').strip()

    if not status_file:
        raise EnvironmentError('You must specify a status entry!')

    import os
    return os.path.abspath(os.path.join(config_path, '..', status_file))


def extract_zones_from_status_file(status_path):
    """ Parses a openvpn status file and extracts the list of connected clients
        and there ip address """
    with open(status_path, 'r') as status_file:
        mode = None
        mode_changes = {
            'OpenVPN CLIENT LIST': 'clients',
            'ROUTING TABLE': 'routes',
            'GLOBAL STATS': None
        }
        clients = {}
        skip_next_lines = 0
        for status_line in status_file:
            if skip_next_lines > 0:
                skip_next_lines -= 1
                continue
            status_line = status_line.strip()
            if status_line in mode_changes:
                mode = mode_changes[status_line]
                skip_next_lines = 1
                if mode == 'clients':
                    skip_next_lines += 1
                continue
            if mode == 'clients':
                clients[status_line.split(',')[0]] = None
            if mode == 'routes':
                address, client = status_line.split(',')[0:2]
                if '/' in address:
                    continue
                if client not in clients:
                    raise ValueError('Error in status file')
                clients[client] = address
        return clients


class OpenVpnStatusAuthority(FileAuthority):
    def __init__(self, status_file,  # This nameserver's name
                 mname="ns1.example-domain.com",
                 # Mailbox of individual who handles this
                 rname="root.example-domain.com",
                 # Unique serial identifying this SOA data
                 serial=2003010601,
                 # Time interval before zone should be refreshed
                 refresh="1H",
                 # Interval before failed refresh should be retried
                 retry="1H",
                 # Upper limit on time interval before expiry
                 expire="1H",
                 # Minimum TTL
                 minimum="1H"
                 ):
        self.status_file = status_file
        self.mname = mname
        self.rname = rname
        self.refresh = refresh
        self.retry = retry
        self.expire = expire
        self.minimum = minimum
        FileAuthority.__init__(self, status_file)

        # watch for file changes:
        signal.signal(signal.SIGUSR1, self.handle_signal)
        notifier = inotify.INotify()
        notifier.startReading()
        notifier.watch(filepath.FilePath(status_file), callbacks=[self.notify])

    def loadFile(self, status_file):
        clients = extract_zones_from_status_file(status_file)
        self.build_zone_from_clients(clients, status_file)

    def build_zone_from_clients(self, clients, status_file):
        """ Basic zone generation (uses only the client list),
            additional data like SOA information must be passed
            as keyword option """
        name = '.'.join(clients.keys()[0].split('.')[1:])
        self.records = {}
        self.soa = (name, dns.Record_SOA(
            mname=self.mname,
            rname=self.rname,
            serial=int(os.path.getmtime(status_file)),
            refresh=self.refresh,
            retry=self.retry,
            expire=self.expire,
            minimum=self.minimum,
        ))
        for client, address in clients.items():
            self.records.setdefault(client.lower(), []).append(dns.Record_A(address))

    def handle_signal(self, a, b):
        self.loadFile(self.status_file)

    def notify(self, ignored, filepath, mask):
        print('{} changed ({}), rereading zone data'.format(filepath,
              ','.join(inotify.humanReadableMask(mask))))
        self.loadFile(self.status_file)
