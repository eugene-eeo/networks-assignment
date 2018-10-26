import datetime
import time
import socket
from server import recv_packet, send_packet


HOST = 'localhost'
PORT = 8081


def try_send(sock, type, data):
    if not send_packet(sock, type, data):
        print("Timeout: Server unavailable")
        exit(1)


def try_recv(sock, reason):
    t0 = time.time()
    with open('client.log', 'a') as fp:
        type, data = recv_packet(sock)
        t1 = time.time()
        if type is None:
            fp.write('[{0}] Timeout during {1}: server unavailable.\n'.format(datetime.datetime.now(), reason))
            print("Timeout: Server unavailable")
            exit(1)
        fp.write('[{0}] Server response ({1}): length={2}, time={3}s.\n'.format(
            datetime.datetime.now(),
            reason,
            len(type) + 1 + len(data),
            t1 - t0,
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

    # get artist
    artist = ''
    while not artist:
        artist = input('Artist Name: ').strip()

    # send request
    try_send(s, b'REQ', artist.encode('ascii'))
    #_, _ = try_recv(s)
    #print('Server received query')
    _, data = try_recv(s, 'fetch songs')
    songs = data.decode('ascii')
    print('Songs:')
    if songs:
        for i, song in enumerate(songs.split('\n')):
            print('  [' + str(i) + '] ' + song)
    else:
        print('<No results>')

    input('Quit? (Enter)')
    try_send(s, b'BYE', b'')
    try_recv(s, 'close connection')
    s.close()
    print('Connection closed by server.')


if __name__ == '__main__':
    main()
