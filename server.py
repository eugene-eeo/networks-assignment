import re
import time
import socket
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict


def parse(f):
    songs = defaultdict(list)
    for line in f:
        if not line or line[0] == ' ':
            continue
        if len(line) < 69:
            line = line.rstrip() + next(f)
        line = line.strip()
        match = re.match(r'^\d+ {0,1}- {0,1}(.+?) {2,}(.+?) +\d+$', line)
        if match is not None:
            song, artists = match.groups()
            song = song.strip()
            artists = artists.strip().split('/')
            for artist in artists:
                songs[artist].append(song)
    return songs


# message    = header + "\n" + data
# header(10) = type(3) + " " + length(6) (base 10 with padding)
# type = "REQ"
#      | "RES"
#      | "BYE"


def get_next_packet(s):
    header = s.recv(10)

    type, length = header.split(b" ")
    length = int(length)
    data = s.recv(length + 1)[1:]  # (need to add newline)

    assert type in {b"REQ", b"RES", b"BYE"}
    assert len(data) == length
    return type, data


def write_packet(s, type, data):
    header = type + b' ' + ('{0:06d}'.format(len(data))).encode('ascii')
    packet = header + b'\n' + data
    s.sendall(packet)


def log(text, lock=threading.Lock()):
    with lock:
        id = threading.current_thread().ident
        now = str(datetime.datetime.now())
        with open('server.log', 'a') as fp:
            fp.write(f'[{now}] [worker-{id}] {text}\n')


def handle_connection(songs, sock, addr):
    t0 = time.time()
    while True:
        type, data = get_next_packet(sock)
        if type == b'REQ':
            artist = data.decode()
            log(f"Received artist from {addr}: {artist}")
            songs = b'\n'.join(x.encode('ascii') for x in songs[artist])
            write_packet(sock, b'RES', songs)
            continue

        if type == b'BYE':
            dt = time.time() - t0
            sock.close()
            log(f"Connection ended with {addr} ({dt}s).")
            break


def main(f):
    songs = parse(open(f))
    port = 8081
    t = ThreadPoolExecutor(max_workers=4)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('localhost', port))
    except OSError:
        print("ERROR: Unable to bind to port")
        return
    s.listen()
    log(f"Server started, listening at port {port}")
    try:
        while True:
            sock, addr = s.accept()
            log(f"Received connection from {addr}")
            t.submit(handle_connection, songs, sock, addr)
    finally:
        # needs to be before t.shutdown because t.shutdown will
        # not return if there are still any active connections
        s.shutdown(socket.SHUT_RDWR)
        t.shutdown(wait=True)
        s.close()


if __name__ == '__main__':
    import sys
    main(sys.argv[1])
