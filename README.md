OpenVPN 2 DNS
=============

[![Build Status](https://travis-ci.org/mswart/openvpn2dns.png?branch=master)](https://travis-ci.org/mswart/openvpn2dns)

A pure python DNS server serving the content of OpenVPN status files. It parses
the status files of the OpenVPN server to extract the connected clients and
their IP addresses. From theses data OpenVPN2DNS creates DNS zones and serving
they as DNS server (using Python's twisted module).

Afterwards all connected VPN clients have valid DNS entries.


Installation
------------

Install the following dependencies e.g. with your package management system:

- Python 2.7.x (Python 3.x support missing because of leaking twisted support)
- the twisted Python module (I tested twisted 11.1)

Clone this repository to get the openvpn2dns source code:

```
git clone git://github.com/mswart/openvpn2dns.git
```


Configuration
-------------

openvpn2dns uses a INI-style file configuration but handles and supports multiple option with the same name per section.


### ``options`` section - general option

- **listen**: Specify on which address and port the DNS server should listen. You must specify the a port (DNS default port is 53). This option can be specify multiple times.
- **instance**: Define one OpenVPN instance (one status file that should be served). The value is the name for the zone and the section that contains options above this instance.


### instance section

This section is used to set up the zone and e.g. ``SOA`` entry for the zone. The section and all its options must be specified.

- **status_file**: The path to the OpenVPN status file.
- **rname**: A <domain-name> which specifies the mailbox of the person responsible for this zone.
- **mname**: The <domain-name> of the name server that was the original or primary source of data for this zone.
- **refresh**: A 32 bit time interval in seconds before the zone should be refreshed. String suffixes like ``h``, ``d`` are supported.
- **retry**: A 32 bit time interval that should elapse before a failed refresh should be retried. String suffixes like ``h``, ``d`` are supported.
- **expire**: A 32 bit time value that specifies the upper limit on the time interval that can elapse before the zone is no longer authoritative. String suffixes like ``h``, ``d`` are supported.
- **minimum**: The unsigned 32 bit minimum TTL field that should be exported with any RR from this zone. String suffixes like ``h``, ``d`` are supported.

The following options are optional:

- **notify**: A DNS name or IP address for other DNS server which working as slaves and should be notified via the DNS notify extension above zone updates. This option can be specify multiple times.
- **add_entries**: name of one entry section thats records should be added to the zone of this instance.


### entry section - additional (fixed) DNS entries

This section contains entries that should be added to the dynamic entries from the status file. This should be administrative entries like name servers (NS) or entries for the VPN server.

The option name is the record name. If the name does not end with a dot, the zone name is appended. The ``@`` means the zone name itself.

All common types like ``A``, ``AAAA``, ``MX``, ``NS`` are supported.


### Example

```ini
[options]
# run settings:
listen = 192.0.2.1:53
listen = 198.51.100.1:53
# instances
instances = vpn.example.org
[vpn.example.org]
# data source:
status_file = /etc/openvpn/openvpn-status.log
# notify slaves:
notify = dns.example.org
notify = dns-backup.example.com
# zone SOA options:
rname = dns@example.org
mname = vpn.example.org
refresh = 1h
retry = 5m
expire = 2h
minimum = 5m
# additional zone entries:
add_entries = nameservers
add_entries = vpn-server
[nameservers]
@ = NS dns.example.org
@ = NS dns-backup.example.com
[vpn-server]
@ = A 203.0.113.1
```


Starting
--------

Uses the twisted ``twistd`` executable to launch openvpn2dns:

```
twistd -y launch.py
```

At the moment the configuration file name is hard-coded to ``openvpn2dns.cfg`` #1.

``twistd`` as additional option to specify to user id or the log destination. Use ``twistd --help`` for all option.

I recommend running openvpn2dns as nobody and therefore launch it with:

```
twistd -y launch.py -u 65534 -g 65534
```


Limitations
-----------

openvpn2dns has some known limitations:

- Hard coded configuration file name #1
- Only one status file supported (in progress) #2
- Support IPv6 address for OpenVPN clients #3
- Missing reverse DNs zone #4

I recommend using openvpn2dns only as hidden DNS server and explicit DNS servers (like bind ...) for the clients. openvpn2dns supports zone transfers and notify.


Contributing
------------

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
4. Add specs for your feature
5. Implement your feature
6. Commit your changes (`git commit -am 'Add some feature'`)
7. Push to the branch (`git push origin my-new-feature`)
8. Create new Pull Request


License
-------

MIT License

Copyright (c) 2013 Malte Swart. MIT license, see LICENSE for more details.
