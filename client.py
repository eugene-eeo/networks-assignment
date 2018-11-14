import datetime
import time
import socket
from server import recv_packet, send_packet


HOST = 'localhost'
PORT = 8081


def try_send(sock, type, data):
    try:
        send_packet(sock, type, data)
    except socket.error:
        print("Timeout: Server unavailable")
        with open('client.log', 'a') as fp:
            fp.write('[{0}] Timeout during {1}: server unavailable.\n'.format(datetime.datetime.now(), type))
        sock.close()
        exit(1)


def try_recv(sock, reason):
    with open('client.log', 'a') as fp:
        try:
            start_time = time.time()
            type, data = recv_packet(sock)
            if type is None:
                raise socket.error
            fp.write('[{0}] Server response ({1}): length={2}, time={3}s.\n'.format(
                datetime.datetime.now(),
                reason,
                len(type) + 1 + len(data),
                time.time() - start_time,
                ))
            return type, data
        except socket.error:
            fp.write('[{0}] Timeout during {1}: server unavailable.\n'.format(datetime.datetime.now(), reason))
            print("Timeout: Server unavailable")
            sock.close()
            exit(1)


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

    # make sure that server receives request
    try_recv(s, 'ack query')
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
    try_send(s, b'BYE', b'')
    try_recv(s, 'close connection')
    s.close()
    print('Connection closed by server.')


if __name__ == '__main__':
    main()
