import datetime
import time
import socket
from contextlib import contextmanager
from server import recv_packet, send_packet


HOST = 'localhost'
PORT = 8081


@contextmanager
def error_handler(operation, intent, sock):
    exc = None
    msg = None
    try:
        yield
    except ValueError as exc:
        msg, = exc.args
    except socket.error as exc:
        _, msg = exc.args
    if msg is not None:
        print("Error: " + msg)
        with open('client.log', 'a') as fp:
            fp.write('[{time}] {operation}: ({intent}) {msg}\n'.format(
                time=datetime.datetime.now(),
                operation=operation,
                intent=intent,
                msg=msg,
                ))
        sock.close()
        exit(1)


def try_send(sock, intent, packet):
    type, data = packet
    with error_handler("send", intent, sock):
        send_packet(sock, type, data)


def try_recv(sock, intent):
    with error_handler("recv", intent, sock):
        start_time = time.time()
        type, data = recv_packet(sock)
        if type is None:
            raise ValueError("Invalid packet! Maybe the server has closed the connection.")
        with open('client.log', 'a') as fp:
            fp.write('[{}] Server response ({}): length={}, delay={}s.\n'.format(
                    datetime.datetime.now(),
                    intent,
                    11 + len(data),
                    time.time() - start_time,
                ))
        return type, data


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((HOST, PORT))
    except ConnectionRefusedError as e:
        _, message = e.args
        print(message)
        exit(1)

    print("Waiting for connection...")
    try_send(s, 'client ping', (b'PIN', b''))
    try_recv(s, 'server pong')
    print("Connected to server.")
    # get artist
    while True:
        artist = input('Artist Name: ').strip()
        if artist:
            break

    # send request and make sure that server receives request
    try_send(s, 'song request', (b'REQ', artist.encode('ascii')))
    try_recv(s, 'server ack query')
    print('Server received query')

    # then fetch songs
    _, data = try_recv(s, 'fetch songs')
    songs = data.decode('ascii')
    print('Songs:')
    if songs:
        for i, song in enumerate(songs.split('\n')):
            print('  [' + str(i) + '] ' + song)
    else:
        print('<No results>')

    input('Press enter to quit.')
    try_send(s, 'goodbye message', (b'BYE', b''))
    try_recv(s, 'server ack for goodbye')
    s.close()
    print('Connection closed by server.')


if __name__ == '__main__':
    main()
