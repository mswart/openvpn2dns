import os.path
import signal

from twisted.names import dns
from twisted.names.authority import FileAuthority
from twisted.names.client import Resolver
from twisted.internet import inotify
from twisted.internet import defer
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
                if '/' in address or address[-1].isalpha():
                    continue
                if client not in clients:
                    raise ValueError('Error in status file')
                clients[client] = address
        return clients


class InMemoryAuthority(FileAuthority):
    """ In memory authority class - handles the data of one zone"""
    def __init__(self, data=None):
        FileAuthority.__init__(self, data)

    def loadFile(self, data):
        if type(data) is tuple and len(data) == 2:
            self.setData(*data)

    def setData(self, soa, records):
        """ set authority data

            :param twisted.names.dns.Record_SOA soa: SOA record for this zone.
                you must add the soa to the records list yourself!!
            :param dict records: dictionary with record entries for this
                domain."""
        self.soa = soa
        self.records = records


class OpenVpnAuthorityHandler(list):
    def __init__(self, config):
        self.config = config
        # authorities for the data itself:
        self.authorities = {}
        for instance in self.config.instances:
            self.authorities[instance] = InMemoryAuthority()
            self.append(self.authorities[instance])
        # load data:
        self.loadInstances()
        # watch for file changes:
        signal.signal(signal.SIGUSR1, self.handle_signal)
        notifier = inotify.INotify()
        notifier.startReading()
        for instance in self.config.instances.values():
            notifier.watch(filepath.FilePath(instance.status_file),
                           callbacks=[self.notify])

    def loadInstances(self):
        """ (re)load data of all instances"""
        for instance in self.config.instances:
            self.loadInstance(self.config.instances[instance])

    def loadInstance(self, instance):
        clients = extract_zones_from_status_file(instance.status_file)
        self.build_zone_from_clients(instance, clients)

    def build_zone_from_clients(self, instance, clients):
        """ Basic zone generation (uses only the client list),
            additional data like SOA information must be passed
            as keyword option """
        name = '.'.join(clients.keys()[0].split('.')[1:])
        records = {}
        soa = (name, dns.Record_SOA(
            mname=instance.mname,
            rname=instance.rname,
            serial=int(os.path.getmtime(instance.status_file)),
            refresh=instance.refresh,
            retry=instance.retry,
            expire=instance.expire,
            minimum=instance.minimum,
        ))
        for name, record in instance.records + [soa]:
            records.setdefault(name, []).append(record)
        for client, address in clients.items():
            records.setdefault(client.lower(), []).append(dns.Record_A(address))
        self.authorities[instance.name].setData(soa, records)

    def handle_signal(self, a, b):
        self.loadInstances()

    def notify(self, ignored, filepath, mask):
        instance = None
        for one_instance in self.config.instances.values():
            if one_instance.status_file == filepath.path:
                instance = one_instance
                break
        if instance is None:
            print('unknown status file: {0}'.format(filepath.path))
            return
        print('{0} changed ({1}), rereading instance {2}'.format(filepath,
              ','.join(inotify.humanReadableMask(mask)), instance.name))
        self.loadInstance(instance)
        for server in instance.notify:
            r = NotifyResolver(servers=[server])
            r.sendNotify(instance.name)


class NotifyResolver(Resolver):
    def sendNotify(self, zone):
        protocol = self._connectedProtocol()

        id = protocol.pickID()

        m = dns.Message(id, opCode=dns.OP_NOTIFY)
        m.queries = [dns.Query(zone, dns.SOA, dns.IN)]

        try:
            protocol.writeMessage(m, self.servers[0])
        except:
            return defer.fail()

        resultDeferred = defer.Deferred()
        cancelCall = protocol.callLater(10, protocol._clearFailed, resultDeferred, id)
        protocol.liveMessages[id] = (resultDeferred, cancelCall)

        d = resultDeferred

        def cbQueried(result):
            protocol.transport.stopListening()
            return result
        d.addBoth(cbQueried)
        return d
