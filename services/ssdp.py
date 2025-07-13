import random
import socket
import struct
from time import sleep

import logManager

logging = logManager.logger.get_logger(__name__)

def ssdpSearch(ip: str, port: int, mac: str, api: str) -> None:
    """
    Perform SSDP search and respond to M-SEARCH requests.

    Args:
        ip (str): The IP address of the device.
        port (int): The port number of the device.
        mac (str): The MAC address of the device.
        api (str): The API version of the device.
    """
    SSDP_ADDR = '239.255.255.250'
    SSDP_PORT = 1900
    multicast_group_c = SSDP_ADDR
    multicast_group_s = (SSDP_ADDR, SSDP_PORT)
    # Bind to the local address instead of the multicast address
    server_address = ('0.0.0.0', SSDP_PORT)
    Response_message = 'HTTP/1.1 200 OK\r\nHOST: 239.255.255.250:1900\r\nEXT:\r\nCACHE-CONTROL: max-age=100\r\nLOCATION: http://' + ip + ':' + str(port) + '/description.xml\r\nSERVER: Hue/1.0 UPnP/1.0 IpBridge/' + api + '\r\nhue-bridgeid: ' + (mac[:6] + 'FFFE' + mac[6:]).upper() + '\r\n'
    custom_response_message = {0: {"st": "upnp:rootdevice", "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac + "::upnp:rootdevice"}, 1: {"st": "uuid:2f402f80-da50-11e1-9b23-" + mac, "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac}, 2: {"st": "urn:schemas-upnp-org:device:basic:1", "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac}}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(server_address)

    group = socket.inet_aton(multicast_group_c)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    logging.info("starting ssdp...")

    try:
        while True:
            data, address = sock.recvfrom(1024)
            data = data.decode('utf-8')
            if data[0:19] == 'M-SEARCH * HTTP/1.1':
                if data.find("ssdp:discover") != -1:
                    sleep(random.randrange(1, 10) / 10)
                    logging.debug("Sending M-Search response to " + address[0])
                    for x in range(3):
                        sock.sendto(bytes(Response_message + "ST: " + custom_response_message[x]["st"] + "\r\nUSN: " + custom_response_message[x]["usn"] + "\r\n\r\n", "utf8"), address)
            sleep(0.2)
    except Exception as e:
        logging.error("ssdp error: " + str(type(e).__name__) + " " + str(e))


def ssdpBroadcast(ip: str, port: int, mac: str, api: str) -> None:
    """
    Broadcast SSDP NOTIFY messages.

    Args:
        ip (str): The IP address of the device.
        port (int): The port number of the device.
        mac (str): The MAC address of the device.
        api (str): The API version of the device.
    """
    logging.info("start ssdp broadcast")
    SSDP_ADDR = '239.255.255.250'
    SSDP_PORT = 1900
    MSEARCH_Interval = 2
    multicast_group_s = (SSDP_ADDR, SSDP_PORT)
    message = 'NOTIFY * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nCACHE-CONTROL: max-age=100\r\nLOCATION: http://' + ip + ':' + str(port) + '/description.xml\r\nSERVER: Linux/3.14.0 UPnP/1.0 IpBridge/' + api + '\r\nNTS: ssdp:alive\r\nhue-bridgeid: ' + (mac[:6] + 'FFFE' + mac[6:]).upper() + '\r\n'
    custom_message = {0: {"nt": "upnp:rootdevice", "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac + "::upnp:rootdevice"}, 1: {"nt": "uuid:2f402f80-da50-11e1-9b23-" + mac, "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac}, 2: {"nt": "urn:schemas-upnp-org:device:basic:1", "usn": "uuid:2f402f80-da50-11e1-9b23-" + mac}}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(MSEARCH_Interval + 0.5)
    ttl = struct.pack('b', 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    while True:
        for x in range(3):
            try:
                sock.sendto(bytes(message + "NT: " + custom_message[x]["nt"] + "\r\nUSN: " + custom_message[x]["usn"] + "\r\n\r\n", "utf8"), multicast_group_s)
                sock.sendto(bytes(message + "NT: " + custom_message[x]["nt"] + "\r\nUSN: " + custom_message[x]["usn"] + "\r\n\r\n", "utf8"), multicast_group_s)
            except TimeoutError:
                logging.warning("Timeout occurred, retrying...")
                continue
        sleep(60)
