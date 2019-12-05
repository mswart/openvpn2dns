OpenVPN 2 DNS
=============

[![Build Status](https://travis-ci.org/mswart/openvpn2dns.png?branch=master)](https://travis-ci.org/mswart/openvpn2dns)

A pure python DNS server serving the content of OpenVPN status files. It parses
the status files of the OpenVPN server to extract the connected clients and
their IP addresses. From theses data OpenVPN2DNS creates DNS zones and serves
them as DNS server (using Python's twisted module).

Afterwards all connected VPN clients have valid DNS entries.

The server supports zone transfers (``AXFR``) and zone update notifies and can therefore used as master DNS server.


Installation
------------

### Debian/Ubuntu

I provide a PPA at [ppa:malte.swart/openvpn2dns][ppa] for various Ubuntu Releases. The packages should also work for Debian.

[ppa]: https://launchpad.net/~malte.swart/+archive/ubuntu/openvpn2dns "Startpage of that PPA at launchpad"


### PyPI

`openvpn2dns` is listed on [PyPI][pypi-openvpn2dns]. With a python package manager like `pip` or `easy_install` you should be able to install openvpn2dns and all its dependencies except twisted. Twisted can also be installed via `pip`. But `openvpn2dns` only requires the `names` module from `twisted`, and you are not require to install the whole `twisted` module. On errors see the following manual section for openvpn2dns's requirements and who to get them.

[pypi-openvpn2dns]: https://pypi.python.org/pypi/openvpn2dns "openvpn2dns Application in the Python Package Index"


### Manual

`openvpn2dns` depends on:

- Python >= 3.6
- [``Twisted`` python module][twisted] - versions >= 17.1 working
- [``IPy`` python module][ipy] - at least versions >= 0.73 working

[twisted]: https://pypi.python.org/pypi/Twisted/ "Twisted Module in the Python Package Index"
[ipy]: https://pypi.python.org/pypi/IPy/ "IPy Module in the Python Package Index"

On most system all dependencies are available via the package manager - look for package names like ``python``/``python3``, ``python3-twisted`` and ``python3-ipy``. The twisted packages contains multiple submodules but openvpn2dns requires only the ``core`` part and the ``names`` submodule. You do not need to install the whole suite.

Currently `openvpn2dns` is only available via source (but I administrative thinking about building Debian/Ubuntu packages), e.g.:

```
git clone git://github.com/mswart/openvpn2dns.git
```

If python is installed the needed Python modules can also be installed via the Python Package Index and package manager like ``pip``(or ``easy_install``), e.g.:

```
pip install -r requirements.txt
# or
pip install twisted IPy
```



Configuration
-------------

openvpn2dns uses a INI-style file configuration but handles and supports multiple option with the same name per section.


### ``options`` section - general option

- **listen**: Specify on which address and port the DNS server should listen. You must specify the a port (DNS default port is 53). This option can be specify multiple times.
- **instance**: Define one OpenVPN instance (one status file that should be served). The value is the name for the zone and the section that contains options above this instance.
- **daemon**: Whether detach and run as daemon
- **drop-privileges**: Whether drop privileges after opened sockets. User and group information needed (via option or config)
- **user**: User id or name to use when dropping privileges after opened sockets (see drop-privileges option)
- **group**: Group id or name to use when dropping privileges after opened sockets (see drop-privileges option)
- **log**: Log destination (file name, ``-`` for stdout or ``syslog`` for syslog)
- **pidfile**: Name of the pidfile, recommended for daemon mode
- **reactor**: twisted reactor type for twisted


### instance section

This section is used to set up the zone and e.g. ``SOA`` entry for the zone. The section and all its options must be specified.

- **rname**: A <domain-name> which specifies the mailbox of the person responsible for this zone.
- **mname**: The <domain-name> of the name server that was the original or primary source of data for this zone.
- **refresh**: A 32 bit time interval in seconds before the zone should be refreshed. String suffixes like ``h``, ``d`` are supported.
- **retry**: A 32 bit time interval that should elapse before a failed refresh should be retried. String suffixes like ``h``, ``d`` are supported.
- **expire**: A 32 bit time value that specifies the upper limit on the time interval that can elapse before the zone is no longer authoritative. String suffixes like ``h``, ``d`` are supported.
- **minimum**: The unsigned 32 bit minimum TTL field that should be exported with any RR from this zone. String suffixes like ``h``, ``d`` are supported.

The following options define needed information about the OpenVPN server:

- **status_file**: The path to the OpenVPN status file.
- **subnet4**: ipv4 subnet of the OpenVPN server. If set openvpn2dns serves also reverse lookups.
- **subnet6**: ipv6 subnet of the OpenVPN server. If set openvpn2dns serves also reverse lookups.

They can be specify directly or extracted from the OpenVPN server configuration:

- **server_config**: The path to the OpenVPN configuration file.
  The values for **status_file**, **subnet4** and **subnet6** are extracted.

The following options are optional:

- **notify**: A DNS name or IP address for other DNS server which working as slaves and should be notified via the DNS notify extension above zone updates. This option can be specify multiple times.
- **add_entries**: name of one entry section thats records should be added to the zone of this instance.
- **add_forward_entries**: name of one entry section thats records should be added to the forward zone of this instance.
- **add_backward_entries**: name of one entry section thats records should be added to the backward zone (IPv4 and IPv6) of this instance.
- **add_backward4_entries**: name of one entry section thats records should be added to the backward zone (only IPv4) of this instance.
- **add_backward6_entries**: name of one entry section thats records should be added to the backward zone (only IPv6) of this instance.
- **suffix**: zone suffix that should be appended to all certificate common names - needed if the common names are no full-qualified domain names. The shortcut ``@`` references the zone name.


### entry section - additional (static) DNS entries

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

Launch openvpn2dns with ``openvpn2dns`` and pass the file name of your configuration file:

```
python3 openvpn2dns <configuration file like openvpn2dns.ini>
```

The most options setting can be specified by command line options. To get a complete list and help run:

```
python3 openvpn2dns --help
```


Production Usage
----------------

``openvpn2dns`` is stable and usable for production service.

To handle a higher query count run openvpn2dns as hidden master DNS server and use optimized DNS server to handle the query load. ``openvpn2dns`` supports zone transfers and the ``notify`` option pushes chances fast to slave servers.

The server is written python and security holes are therefore unlikely. But to be sure it is recommended to specify a ``user`` and ``group`` and set ``drop-privileges`` to ``true``: the process drops all privileges after opened the network sockets.

**Warning:** ``openvpn2dns`` does no access control. All clients can query every data from the DNS zone or transfer the entire zone. Adjust the firewall to block unwanted connections.

The ``scripts`` directory contains a ``upstart`` and a ``init.d`` script. You can copy them. You may want to replace the launch and configuration path inside the scripts.

**Info:** The ``init.d`` passes ``--daemon=yes`` and ``--pidfile=/var/run/openvpn2dns.pid`` via command line arguments. Values for these options inside the configuration file have no effect.


Contributing
------------

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Add specs for your feature
4. Implement your feature
5. Commit your changes (`git commit -am 'Add some feature'`)
6. Push to the branch (`git push origin my-new-feature`)
7. Create new Pull Request


License
-------

MIT License

Copyright (c) 2013-2019 Malte Swart. MIT license, see LICENSE for more details.
