import socket
from server import recv_packet, send_packet


HOST = 'localhost'
PORT = 8081


def try_send(*args):
    if not send_packet(*args):
        print("Timeout: Server unavailable")
        exit(1)


def try_recv(*args):
    type, data = recv_packet(*args)
    if type is None:
        print("Timeout: Server unavailable")
        exit(1)
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
    _, data = try_recv(s)
    songs = data.decode('ascii')
    print('Songs:')
    if songs:
        for i, song in enumerate(songs.split('\n')):
            print('  [' + str(i) + '] ' + song)
    else:
        print('<No results>')

    input('Quit? (Enter)')
    try_send(s, b'BYE', b'')
    s.close()


if __name__ == '__main__':
    main()
