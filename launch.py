from twisted.application import internet, service
from twisted.names import dns
from twisted.names import server
from openvpnzone import OpenVpnStatusAuthority, extract_status_file_path


def createOpenvpn2DnsService():
    zones = [OpenVpnStatusAuthority(extract_status_file_path('server.conf'))]

    f = server.DNSServerFactory(zones, None, None, 100)
    p = dns.DNSDatagramProtocol(f)
    f.noisy = 0

    m = service.MultiService()
    for (klass, arg) in [(internet.TCPServer, f), (internet.UDPServer, p)]:
        s = klass(53535, arg)
        s.setServiceParent(m)
    return m

application = service.Application("OpenVPN2DNS")

createOpenvpn2DnsService().setServiceParent(application)
