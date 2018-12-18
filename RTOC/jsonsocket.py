# file:jsonsocket.py
# https://github.com/mdebbar/jsonsocket
import json
import socket
import traceback
# from Cryptodome.Cipher import DES
from Cryptodome.Cipher import AES
import hashlib

class Server(object):
    """
    A JSON socket server used to communicate with a JSON socket client. All the
    data is serialized in JSON. How to use it:

    server = Server(host, port)
    while True:
      server.accept()
      data = server.recv()
      # shortcut: data = server.accept().recv()
      server.send({'status': 'ok'})
    """

    backlog = 5
    client = None

    def __init__(self, host, port, keyword = None):
        self.socket = socket.socket()
        #self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(0)
        self.socket.settimeout(5.0)
        self.socket.bind((host, port))
        self.socket.listen(self.backlog)

        self.keyword = keyword

    def setKeyword(self, keyword = None):
        self.keyword = keyword

    def __del__(self):
        self.close()

    def accept(self):
        # if a client is already connected, disconnect it
        if self.client:
            self.client.close()
        self.client, self.client_addr = self.socket.accept()
        return self

    def send(self, data):
        if not self.client:
            raise Exception('Cannot send data, no client is connected')
        _send(self.client, data, self.keyword)
        return self

    def recv(self):
        if not self.client:
            raise Exception('Cannot receive data, no client is connected')
        return _recv(self.client, self.keyword)

    def close(self):
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

    data = {
      'name': 'Patrick Jane',
      'age': 45,
      'children': ['Susie', 'Mike', 'Philip']
    }
    client = Client()
    client.connect(host, port)
    client.send(data)
    response = client.recv()
    # or in one line:
    response = Client().connect(host, port).send(data).recv()
    """

    socket = None
    keyword = None

    def setKeyword(self, keyword = None):
        self.keyword = keyword

    def __del__(self):
        self.close()

    def connect(self, host, port, keyword = None):
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(0)
        self.socket.settimeout(5.0)
        self.socket.connect((host, port))
        self.keyword = keyword
        return self

    def send(self, data):
        if not self.socket:
            raise Exception('You have to connect first before sending data')
        _send(self.socket, data, self.keyword)
        return self

    def recv(self):
        if not self.socket:
            raise Exception('You have to connect first before receiving data')
        return _recv(self.socket, self.keyword)

    def recv_and_close(self):
        data = self.recv()
        self.close()
        return data

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

# helper functions ##


def _send(socket, data, key = None):
    try:
        serialized = json.dumps(data)
        # serialized=pickle.dumps(list(data))
    except (TypeError, ValueError):
        raise Exception('You can only send JSON-serializable data')
    # send the length of the serialized data first
    nonce = b''
    tag = b''
    if key != None and key != '' and type(key) == str:
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


def _recv(socket, key = None):
    # read the length of the data, letter by letter until we reach EOL
    length_str = ''
    char = socket.recv(1).decode()
    while char != '\n':
        length_str += char
        char = socket.recv(1).decode()
    lens = length_str.split(',')
    total = 0
    tagTotal = 0
    nonceTotal = 0
    for l in range(len(lens)):
        if l == 0:
            total = int(lens[l])
        elif l == 1:
            tagTotal = int(lens[l])
        elif l == 2:
            nonceTotal = int(lens[l])

    # use a memoryview to receive the data chunk by chunk efficiently
    if tagTotal>0:
        tagView = memoryview(bytearray(tagTotal))
        next_offset = 0
        while tagTotal - next_offset > 0:
            recv_size = socket.recv_into(tagView[next_offset:], tagTotal - next_offset)
            next_offset += recv_size
        tagView = tagView.tobytes()
    else:
        tagView = b''
    if nonceTotal>0:
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
    if key != None and key != '' and type(key) == str:
        if len(tagView)!=0 and len(nonceView)!=0:
            try:
                # des = DES.new(key.encode(), DES.MODE_ECB)
                # decrypted = des.decrypt(view.tobytes())
                hash_object = hashlib.sha256(key.encode('utf-8'))
                cipher = AES.new(hash_object.digest(), AES.MODE_EAX, nonceView)
                decrypted = cipher.decrypt_and_verify(view, tagView)
                deserialized = json.loads(decrypted.decode('utf-8'))
                return deserialized
            except:
                tb = traceback.format_exc()
                print("SOCKET PASSWORD ERROR, The provided password is wrong!")
                print(tb)
                return None
        else:
            print("SOCKET PASSWORD ERROR, No password provided!\nCannot receive data")
            return None
    else:
        if len(tagView)==0 and len(nonceView)==0:
            try:
                deserialized = json.loads(view.decode('utf-8'))
                return deserialized
            except (TypeError, ValueError):
                tb = traceback.format_exc()
                print("JSON SOCKET ERROR, Data received was not in JSON format")
                print("Maybe the RTOC-Server is password-protected")
                print(tb)
                return {}
        else:
            print("SOCKET PASSWORD ERROR, No password provided!\nCannot receive data")
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
    #         print("JSON SOCKET ERROR, Data received was not in JSON format")
    #         print(tb)
    #         return {}

def pad(text, padding = 16):
    while len(text) % padding != 0:
        text += ' '
    return text
