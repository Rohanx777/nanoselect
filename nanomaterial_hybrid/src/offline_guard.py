"""Process-local verification guard. Not a firewall or a production feature."""
import ipaddress
import socket
import sys


class OfflineNetworkBlocked(RuntimeError):
    pass


def allowed_host(host,allow_machine_name=False):
    if host is None:
        return True
    if isinstance(host,bytes):
        host=host.decode("ascii",errors="replace")
    name=str(host).strip().casefold()
    if name=="localhost" or (allow_machine_name and name==socket.gethostname().casefold()):
        return True
    try:
        return ipaddress.ip_address(name.split("%",1)[0]).is_loopback
    except ValueError:
        return False


def install():
    if getattr(sys,"_nanomaterial_offline_guard",False):
        return
    def audit(event,args):
        if event in {"socket.connect","socket.sendto"}:
            address=args[-1]
            if isinstance(address,tuple) and not allowed_host(address[0]):
                raise OfflineNetworkBlocked("External socket access blocked during demo verification")
        if event in {"socket.getaddrinfo","socket.gethostbyname","socket.gethostbyaddr"}:
            if args and not allowed_host(args[0],allow_machine_name=True):
                raise OfflineNetworkBlocked("External name lookup blocked during demo verification")
    sys.addaudithook(audit)
    sys._nanomaterial_offline_guard=True
