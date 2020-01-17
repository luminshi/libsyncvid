import json
import socket

# Lumin: I was lazy to write a duplex connection nor a tcp connection.
#           the following code is 'borrowed' from:
#               https://github.com/mdebbar/jsonsocket
#           with minor changes so it can work in python3
#           Blame the original author instead of me, :)

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

    def __init__(self, host, port):
        self.socket = socket.socket()
        self.socket.bind((host, port))
        self.socket.listen(self.backlog)

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
        _send(self.client, data)
        return self

    def recv(self):
        if not self.client:
            raise Exception('Cannot receive data, no client is connected')
        return _recv(self.client)

    def close(self):
        if self.client:
            self.client.close()
            self.client = None
        if self.socket:
            self.socket.close()
            self.socket = None


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

    def __del__(self):
        self.close()

    def connect(self, host, port):
        self.socket = socket.socket()
        self.socket.connect((host, port))
        return self

    def send(self, data):
        if not self.socket:
            raise Exception('You have to connect first before sending data')
        _send(self.socket, data)
        return self

    def recv(self):
        if not self.socket:
            raise Exception('You have to connect first before receiving data')
        return _recv(self.socket)

    def recv_and_close(self):
        data = self.recv()
        self.close()
        return data

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None


## helper functions ##

def _send(socket, data):
    try:
        serialized = json.dumps(data)
    except ValueError:
        raise Exception('You can only send JSON-serializable data')
    # send the length of the serialized data first

    msg_len = '%d\n' % len(serialized)
    socket.send(msg_len.encode())
    # send the serialized data
    socket.sendall(serialized.encode())


def _recv(socket):
    # read the length of the data, letter by letter until we reach EOL
    length_str = ''
    char = socket.recv(1).decode()
    while char != '\n':
        length_str += char
        char = socket.recv(1).decode()
    total = int(length_str)
    # use a memoryview to receive the data chunk by chunk efficiently
    view = memoryview(bytearray(total))
    next_offset = 0
    while total - next_offset > 0:
        recv_size = socket.recv_into(view[next_offset:], total - next_offset)
        next_offset += recv_size
    try:
        deserialized = json.loads(view.tobytes())
    except ValueError:
        raise Exception('Data received was not in JSON format')
    print("deserialized: {}".format(deserialized))
    return deserialized
