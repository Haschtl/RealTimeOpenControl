# jsonsocket.py v1.5
# https://github.com/mdebbar/jsonsocket
import json
import socket
import traceback
# from Cryptodome.Cipher import DES
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

try:
    from Cryptodome.Cipher import AES
    import hashlib
except (SystemError, ImportError):
    AES = None
    logging.warning(
        'CryptodomeX or hashlib not installed! Install with "pip3 install pycryptodomex"')

HOST_WHITELIST = ['127.0.0.1', 'localhost']


class Server(object):
    """
    A JSON socket server used to communicate with a JSON socket client. All the
    data is serialized in JSON.

    Args:
        host (str): Hostname (e.g. 0.0.0.0)
        port (int): Port to bind tcp-socket (e.g. 5050)
        keyword (str or None): Set a keyword for encrypted communication. Leaf blank for unsecure connection. Note: This will not encrypt host-intern-communication. (default: None)
        reuse_port (bool): Enable/disable reuse_port (default: True)
    """

    backlog = 5
    client = None

    def __init__(self, host, port, keyword=None, reuse_port=True):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if reuse_port:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # if hasattr(socket, "TCP_KEEPIDLE") and hasattr(socket, "TCP_KEEPINTVL") and hasattr(socket, "TCP_KEEPCNT"):
        #     self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1 * 60)
        #     self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5 * 60)
        #     self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 10)
        # self.socket.setblocking(0)
        self.socket.settimeout(5.0)
        self.socket.bind((host, port))
        self.socket.listen(self.backlog)

        self.keyword = keyword

    def setKeyword(self, keyword=None):
        """
        Set a keyword to protect the tcp communication.

        Args:
            keyword (str or None): A save passcode or None to disable protection
        """
        self.keyword = keyword

    def __del__(self):
        self.close()

    def accept(self):
        """
        Accept a new client connection

        Returns:
            client
        """
        # if a client is already connected, disconnect it
        if self.client:
            self.client.close()
        self.client, self.client_addr = self.socket.accept()
        return self.client

    def send(self, data):
        """
        Send a dict to the connected client

        Args:
            data (dict): The dict you want to transmit.
        """
        if not self.client:
            raise Exception('Cannot send data, no client is connected')
        if self.client_addr[0] not in HOST_WHITELIST:
            _send(self.client, data, self.keyword)
        else:
            _send(self.client, data, "")
        return self

    def recv(self):
        """
        Receives a dict from client

        Returns:
            data (dict): The dict sent by the connected client
        """
        if not self.client:
            raise Exception('Cannot receive data, no client is connected')
        if self.client_addr[0] not in HOST_WHITELIST:
            return _recv(self.client, self.keyword)
        else:
            return _recv(self.client, "")

    def close(self):
        """
        Close the server-socket.
        Do this at the very end of your communication!

        """
        if self.client:
            self.client.close()
            self.client = None
        if self.socket:
            self.socket.close()
            self.socket = None
        self.keyword = None


class Client(object):
    """
    A JSON socket client used to communicate with a JSON socket server. All the
    data is serialized in JSON. How to use it:

    Args:
        keyword (str or None): Set a keyword for encrypted communication. Leaf blank for unsecure connection. (default: None)
    """

    socket = None
    keyword = None
    host = None

    def setKeyword(self, keyword=None):
        """
        Set a keyword to protect the tcp communication.

        Args:
            keyword (str or None): A save passcode or None to disable protection
        """
        self.keyword = keyword

    def __del__(self):
        self.close()

    def connect(self, host, port, keyword=None, reuse_port=True):
        """
        Establish a connection to a host (server)

        Args:
            host (str): Hostname (e.g. 0.0.0.0)
            port (int): Port to bind tcp-socket (e.g. 5050)
            keyword (str or None): Set a keyword for encrypted communication. Leaf blank for unsecure connection. (default: None)
            reuse_port (bool): Enable/disable reuse_port (default: True)
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if reuse_port:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        # self.socket.setblocking(0)
        self.socket.settimeout(5.0)
        self.socket.connect((host, port))
        self.keyword = keyword
        self.host = host
        return self

    def send(self, data):
        """
        Send a dict to the connected server

        Args:
            data (dict): The dict you want to transmit.
        """
        if not self.socket:
            raise Exception('You have to connect first before sending data')

        if self.host not in HOST_WHITELIST:
            _send(self.socket, data, self.keyword)
        else:
            _send(self.socket, data, "")
        return self

    def recv(self):
        """
        Receives a dict from server

        Returns:
            data (dict): The dict sent by the connected server
        """
        if not self.socket:
            raise Exception('You have to connect first before receiving data')
        if self.host not in HOST_WHITELIST:
            return _recv(self.socket, self.keyword)
        else:
            return _recv(self.socket, "")

    def recv_and_close(self):
        """
        Receives a dict from server and closes connection.

        Returns:
            data (dict): The dict sent by the connected server
        """
        data = self.recv()
        self.close()
        return data

    def close(self):
        """
        Close the client-socket.
        Do this at the end of every single communication!

        """
        if self.socket:
            self.socket.close()
            self.socket = None
        self.host = None

# helper functions ##


def _send(socket, data, key=None):
    try:
        serialized = json.dumps(data)
        # serialized=pickle.dumps(list(data))
    except (TypeError, ValueError):
        logging.debug(traceback.format_exc())
        print(traceback.format_exc())
        raise Exception('You can only send JSON-serializable data')
    # send the length of the serialized data first
    nonce = b''
    tag = b''
    if key is not None and key != '' and type(key) == str and AES is not None:
        # des = DES.new(key.encode(), DES.MODE_ECB)
        # padded_text = pad(serialized)
        # serialized = des.encrypt(padded_text.encode('utf-8'))
        # while len(key)<16:
        #     key=key+key
        hash_object = hashlib.sha256(key.encode('utf-8'))
        cipher = AES.new(hash_object.digest(), AES.MODE_EAX)
        padded_text = pad(serialized)
        serialized, tag = cipher.encrypt_and_digest(padded_text.encode('utf-8'))
        nonce = cipher.nonce
    else:
        serialized = serialized.encode()
    b = '%d,%d,%d\n' % (len(serialized), len(tag), len(nonce))
    socket.send(b.encode())
    # send the serialized data
    socket.sendall(tag+nonce+serialized)


def _recv(socket, key=None):
    # read the length of the data, letter by letter until we reach EOL
    length_str = ''
    try:
        char = socket.recv(1).decode()
        while char != '\n':
            length_str += char
            char = socket.recv(1).decode()
    except Exception:
        # socket.close()
        print(traceback.format_exc())
        return False
    lens = length_str.split(',')
    total = 0
    tagTotal = 0
    nonceTotal = 0
    for packet_l in range(len(lens)):
        if packet_l == 0:
            total = int(lens[packet_l])
        elif packet_l == 1:
            tagTotal = int(lens[packet_l])
        elif packet_l == 2:
            nonceTotal = int(lens[packet_l])

    # use a memoryview to receive the data chunk by chunk efficiently
    if tagTotal > 0:
        tagView = memoryview(bytearray(tagTotal))
        next_offset = 0
        while tagTotal - next_offset > 0:
            recv_size = socket.recv_into(tagView[next_offset:], tagTotal - next_offset)
            next_offset += recv_size
        tagView = tagView.tobytes()
    else:
        tagView = b''
    if nonceTotal > 0:
        nonceView = memoryview(bytearray(nonceTotal))
        next_offset = 0
        while nonceTotal - next_offset > 0:
            recv_size = socket.recv_into(nonceView[next_offset:], nonceTotal - next_offset)
            next_offset += recv_size
        nonceView = nonceView.tobytes()
    else:
        nonceView = b''
    view = memoryview(bytearray(total))
    next_offset = 0
    while total - next_offset > 0:
        recv_size = socket.recv_into(view[next_offset:], total - next_offset)
        next_offset += recv_size
    view = view.tobytes()
    if key is not None and key != '' and type(key) == str:
        if len(tagView) != 0 and len(nonceView) != 0 and AES is not None:
            try:
                # des = DES.new(key.encode(), DES.MODE_ECB)
                # decrypted = des.decrypt(view.tobytes())
                hash_object = hashlib.sha256(key.encode('utf-8'))
                cipher = AES.new(hash_object.digest(), AES.MODE_EAX, nonceView)
                decrypted = cipher.decrypt_and_verify(view, tagView)
                deserialized = json.loads(decrypted.decode('utf-8'))
                return deserialized
            except Exception:
                tb = traceback.format_exc()
                logging.debug(tb)
                print('tb')
                logging.error("SOCKET PASSWORD ERROR, The provided password is wrong!")
                return None
        else:
            logging.error("SOCKET PASSWORD ERROR, No password provided!\nCannot receive data")
            return None
    else:
        if len(tagView) == 0 and len(nonceView) == 0:
            try:
                deserialized = json.loads(view.decode('utf-8'))
                return deserialized
            except (TypeError, ValueError):
                tb = traceback.format_exc()
                logging.debug(tb)
                logging.error("JSON SOCKET ERROR, Data received was not in JSON format")
                logging.error("Maybe the RTOC-Server is password-protected")
                return {}
        else:
            logging.error("SOCKET ERROR, No password protection found!\nUnknown error")
            return None

    # try:
    #     deserialized = json.loads(view.tobytes())
    #     return deserialized
    # except (TypeError, ValueError):
    #         # raise Exception('Data received was not in JSON format')
    #     try:
    #         deserialized = json.loads(view.tobytes().decode('utf-8'))
    #         return deserialized
    #     except (TypeError, ValueError):
    #         tb = traceback.format_exc()
    #         logging.error("JSON SOCKET ERROR, Data received was not in JSON format")
    #         logging.debug(tb)
    #         return {}


def pad(text, padding=16):
    while len(text) % padding != 0:
        text += ' '
    return text
