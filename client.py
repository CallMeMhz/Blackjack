import sys
from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread
from utils import pack_msg, unpack_msg, RECV_BUFFER

def prompt():
    sys.stdout.write('$opt$ ')
    sys.stdout.flush()

def send_input():
    while True:
        cmd = sys.stdin.readline().split()
        if len(cmd) == 2:
            msg = (cmd[0], cmd[1])
        else:
            msg = cmd[0]
        _msg = pack_msg(msg)
        sock.sendall(_msg)

sock = socket(AF_INET, SOCK_STREAM)
sock.connect(('localhost', 25000))

t = Thread(target=send_input)
t.start()

while True:
    _msg = sock.recv(RECV_BUFFER)
    if not _msg:
        break

    # print('###', unpack_msg(_msg))

    head, data = unpack_msg(_msg)
    if head == 'table':
        print('table:', data)
    elif head == 'new':
        print('Game start!')
    elif head == 'bet':
        bet = 0
        while bet <= 0:
            bet = int(input('Bet: '))
        sock.sendall(('bet', bet))
    else:
        if data:
            print(head, data)
        else:
            print(head)

    # prompt()

sock.close()
