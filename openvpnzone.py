import os.path
import signal
import collections

from twisted.names import dns
from twisted.names.authority import FileAuthority
from twisted.names.client import Resolver
from twisted.internet import inotify
from twisted.internet import defer
from twisted.python import filepath
from IPy import IP


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
                clients[status_line.split(',')[0]] = []
            if mode == 'routes':
                address, client = status_line.split(',')[0:2]
                if '/' in address:  # subnet
                    continue
                try:
                    address = IP(address)
                except ValueError:  # cached route ...
                    continue
                if address.len() > 1:  # subnet
                    continue
                if client not in clients:
                    raise ValueError('Error in status file')
                clients[client].append(address)
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
        if soa == self.soa or self.changed(soa, records) is False:
            if type(soa) is tuple:
                print('skip unchanged update for zone {0}'.format(soa[0]))
            return False
        self.soa = soa
        self.records = records
        return True

    def changed(self, soa, records):
        """ Checks whether the new record list differs from the old one"""
        if self.records is None:  # previously set data
            return True
        if len(self.records) != len(records):
            return True
        for name in self.records:
            if name not in records:
                return True
            if len(self.records[name]) != len(records[name]):
                return True
            for record in self.records[name]:
                for new_record in records[name]:
                    if new_record == record:
                        break
                    if new_record.__class__ is dns.Record_SOA and \
                            record.__class__ is dns.Record_SOA and \
                            new_record.mname == record.mname and \
                            new_record.rname == record.rname and \
                            new_record.refresh == record.refresh and \
                            new_record.retry == record.retry and \
                            new_record.expire == record.expire and \
                            new_record.minimum == record.minimum:
                        break
                else:
                    return True
        return False


AuthorityTuple = collections.namedtuple('AuthorityTuple', ('forward',
                                        'backward4', 'backward6'))


class OpenVpnAuthorityHandler(list):
    def __init__(self, config):
        self.config = config
        self.send_notify = False
        # authorities for the data itself:
        self.authorities = {}
        for instance in self.config.instances:
            self.authorities[instance] = AuthorityTuple(
                forward=InMemoryAuthority(),
                backward4=InMemoryAuthority(),
                backward6=InMemoryAuthority()
            )
            self.append(self.authorities[instance].forward)
            if self.config.instances[instance].subnet4:
                self.append(self.authorities[instance].backward4)
            if self.config.instances[instance].subnet6:
                self.append(self.authorities[instance].backward6)
        # load data:
        self.loadInstances()
        # watch for file changes:
        signal.signal(signal.SIGUSR1, self.handle_signal)
        notifier = inotify.INotify()
        notifier.startReading()
        for instance in self.config.instances.values():
            notifier.watch(filepath.FilePath(instance.status_file),
                           callbacks=[self.status_file_changed])
        print('Serving {0} zones: {1}'.format(len(self),
              ', '.join(map(lambda z: z.soa[0], self))))

    def loadInstances(self):
        """ (re)load data of all instances"""
        for instance in self.config.instances:
            self.loadInstance(self.config.instances[instance])

    def loadInstance(self, instance):
        clients = extract_zones_from_status_file(instance.status_file)
        self.build_zone_from_clients(instance, clients)

    @staticmethod
    def create_record_base(zone_name, soa, initial_data):
        if zone_name is None:
            return {}
        records = {}
        records.setdefault(zone_name, []).append(soa)
        for name, record in initial_data:
            if name == '@':
                name = zone_name
            elif not name.endswith('.'):
                name = name + '.' + zone_name
            records.setdefault(name, []).append(record)
        return records

    def build_zone_from_clients(self, instance, clients):
        """ Basic zone generation (uses only the client list),
            additional data like SOA information must be passed
            as keyword option """
        soa = dns.Record_SOA(
            mname=instance.mname,
            rname=instance.rname,
            serial=int(os.path.getmtime(instance.status_file)),
            refresh=instance.refresh,
            retry=instance.retry,
            expire=instance.expire,
            minimum=instance.minimum,
        )
        forward_records = self.create_record_base(instance.name, soa,
                                                  instance.forward_records)
        backward4_records = self.create_record_base(instance.subnet4, soa,
                                                    instance.backward4_records)
        backward6_records = self.create_record_base(instance.subnet6, soa,
                                                    instance.backward6_records)
        for client, addresses in clients.items():
            if instance.suffix is not None:
                if instance.suffix == '@':
                    client += '.' + instance.name
                else:
                    client += '.' + instance.suffix
            client = client.lower()
            for address in addresses:
                reverse = IP(address).reverseName()[:-1]
                if address.version() == 4:
                    forward_records.setdefault(client, []) \
                        .append(dns.Record_A(str(address)))
                    backward4_records.setdefault(reverse, []) \
                        .append(dns.Record_PTR(client))
                elif address.version() == 6:
                    forward_records.setdefault(client, []) \
                        .append(dns.Record_AAAA(str(address)))
                    backward6_records.setdefault(reverse, []) \
                        .append(dns.Record_PTR(client))
        # push data to authorities:
        authority = self.authorities[instance.name]
        if authority.forward.setData((instance.name, soa), forward_records):
            self.notify(instance, instance.name)
        if instance.subnet4:
            if authority.backward4.setData((instance.subnet4, soa), backward4_records):
                self.notify(instance, instance.subnet4)
        if instance.subnet6:
            if authority.backward6.setData((instance.subnet6, soa), backward6_records):
                self.notify(instance, instance.subnet6)

    def handle_signal(self, a, b):
        self.loadInstances()

    def status_file_changed(self, ignored, filepath, mask):
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

    def notify(self, instance, name):
        if self.send_notify is not True:
            return
        for server in instance.notify:
            print('Notify {0} new data for zone {1}'.format(server[0], name))
            r = NotifyResolver(servers=[server])
            r.sendNotify(name)

    def start_notify(self):
        self.send_notify = True
        for instance in self.config.instances.values():
            self.notify(instance, instance.name)
            if instance.subnet4:
                self.notify(instance, instance.subnet4)
            if instance.subnet6:
                self.notify(instance, instance.subnet6)


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
