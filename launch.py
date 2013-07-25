#!/usr/bin/env python2
import os
import argparse

from twisted.application import internet, service
from twisted.names import dns
from twisted.names import server
from twisted.scripts._twistd_unix import UnixApplicationRunner

from openvpnzone import OpenVpnAuthorityHandler
from config import ConfigParser, ConfigurationError


class OpenVpn2DnsApplication(UnixApplicationRunner):
    def __init__(self, config, twisted_config):
        UnixApplicationRunner.__init__(self, twisted_config)
        self.service_config = config

    def createOrGetApplication(self):
        return service.Application('OpenVPN2DNS')

    def createOpenvpn2DnsService(self):
        zones = OpenVpnAuthorityHandler(self.service_config)

        m = service.MultiService()
        for listen in self.service_config.listen_addresses:
            f = server.DNSServerFactory(zones, None, None, 2)
            p = dns.DNSDatagramProtocol(f)
            f.noisy = 0
            for (klass, arg) in [(internet.TCPServer, f), (internet.UDPServer, p)]:
                s = klass(listen[1], arg, interface=listen[0])
                s.setServiceParent(m)
        m.setServiceParent(self.application)

    def postApplication(self):
        self.createOpenvpn2DnsService()
        UnixApplicationRunner.postApplication(self)


def file_path(value):
    if not os.path.isfile(value):
        raise argparse.ArgumentTypeError('Could not found config file {0}'
                                         .format(value))
    return value


parser = argparse.ArgumentParser(description='A pure python DNS server serving'
                                 ' the content of OpenVPN status files')
parser.add_argument('configfile', type=file_path,
                    help='file path to configuration file')

args = parser.parse_args()


class DefaultDict(dict):
    def __getitem__(self, name):
        return self.get(name, None)

# emulate twisted configuration:
twisted_config = DefaultDict()
twisted_config['nodaemon'] = True
twisted_config['no_save'] = True
twisted_config['originalname'] = 'openvpn2dns'
twisted_config['rundir'] = '.'

# parse configuration file:
try:
    config = ConfigParser(args.configfile)
except ConfigurationError as e:
    parser.error(e)

# run appliation:
OpenVpn2DnsApplication(config, twisted_config).run()
