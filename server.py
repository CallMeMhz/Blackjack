'''
    An Online Casino Server
'''

import sys
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, SOL_SOCKET, socket
from table import Table


def echo_server(addr):
    '''Socket Listener Thread'''
    listen_sock = socket(AF_INET, SOCK_STREAM)
    listen_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    listen_sock.bind(addr)
    listen_sock.listen(20)
    while True:
        client_sock, client_addr = listen_sock.accept()
        table._threadpool.submit(table.client_handler, client_sock)
    listen_sock.close()


if __name__ == '__main__':
    table = Table()
    echo_server(('', 25000))
