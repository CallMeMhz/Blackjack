from pickle import dumps, loads

RECV_BUFFER = 10240

def pack_msg(obj):
    data = dumps(obj)
    return data

def unpack_msg(data):
    msg = loads(data)
    if isinstance(msg, tuple):
        return msg[0], msg[1]
    else:
        return msg, None

def send_msg(client_sock, msg):
    _msg = pack_msg(msg)
    client_sock.sendall(_msg)
