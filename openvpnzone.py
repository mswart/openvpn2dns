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


def build_zone_from_clients(clients, name, **zone_opts):
    """ Basic zone generation (uses only the client list),
        additional data like SOA information must be passed
        as keyword option """
    from twisted.names import dns
    name = name or '.'.join(clients.keys()[0].split('.')[1:])
    zone = []
    zone.append((name, dns.Record_SOA(**zone_opts)))
    for client, address in clients.items():
        zone.append((client, dns.Record_A(address)))
    return zone


status_file = extract_status_file_path('server.conf')

zone = []

clients = extract_zones_from_status_file(status_file)

zone = build_zone_from_clients(clients, name=None,
                               # This nameserver's name
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
                               )
