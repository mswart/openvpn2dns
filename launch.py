from twisted.application import internet, service
from twisted.names import dns
from twisted.names import server
from openvpnzone import OpenVpnStatusAuthority
from config import ConfigParser


def createOpenvpn2DnsService():
    config = ConfigParser('openvpn2dns.cfg')
    zones = [OpenVpnStatusAuthority(config)]

    m = service.MultiService()
    for listen in config.listen:
        f = server.DNSServerFactory(zones, None, None, 100)
        p = dns.DNSDatagramProtocol(f)
        f.noisy = 0
        for (klass, arg) in [(internet.TCPServer, f), (internet.UDPServer, p)]:
            s = klass(listen[1], arg, interface=listen[0])
            s.setServiceParent(m)
    return m

application = service.Application("OpenVPN2DNS")

createOpenvpn2DnsService().setServiceParent(application)
