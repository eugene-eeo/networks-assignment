import sys
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
        # first char of entry is always not a space
        if not line or line[0] == ' ':
            continue
        # sometimes we get entries like
        # 1 - Really Long Song Name ......
        #                   Artist Name  1994
        if len(line) < 69:
            line = line.rstrip() + next(f)

        line = line.strip()
        # sometimes we have
        # n - Really Long Name......-Artist   Year
        match = re.match(r'^\d+ {0,1}- {0,1}(.+?) +\d+$', line)
        if match and '  ' not in match.group(1).strip():
            song, artists = match.group(1).split('-')
        else:
            match = re.match(r'^\d+ {0,1}- {0,1}(.+?) {2,}(.+?) +\d+$', line)
            if match is None:
                continue
            song, artists = match.groups()

        song = song.strip()
        for artist in artists.strip().split('/'):
            songs[artist].append(song)

    return songs


# PROTOCOL
# --------
#
# message    = header(10) + "\n" + data
# header(10) = type(3) + " " + length(6) (base 10 with 0-padding)
# type = "REQ"  => request songs
#      | "ACK"  => ack request
#      | "RES"  => response songs
#      | "BYE"  => request end
#      | "END"  => ack end


def recv_packet(s):
    invalid = (None, None)
    header = s.recv(10)
    if not header:
        return invalid

    type, length = header.split(b" ")
    length = int(length)
    data = s.recv(length + 1)
    if len(data) != length + 1:
        return invalid

    # remember to drop newline
    return type, data[1:]


def send_packet(s, type, data):
    length = ('{0:06d}'.format(len(data))).encode('ascii')
    header = type + b' ' + length
    packet = header + b'\n' + data
    s.sendall(packet)


def log(text, lock=threading.Lock(), ids={}):
    now = str(datetime.datetime.now())
    with lock:
        id = threading.current_thread().ident
        if id not in ids:
            ids[id] = 0
            ids[id] = max(ids.values()) + 1
        msg = '[{now}] [worker-{id}] {text}'.format(
            now=now,
            id=ids[id],
            text=text,
        )
        print(msg)
        with open('server.log', 'a') as fp:
            fp.write(msg + '\n')


def handle_connection(songs, sock, addr):
    start_time = time.time()
    try:
        while True:
            type, data = recv_packet(sock)
            if type is None:
                break

            elif type == b'REQ':
                send_packet(sock, b'ACK', b'')
                artist = data.decode()
                log("Received artist from {addr}: {artist}".format(addr=addr, artist=artist))
                song_list = [] if artist not in songs else songs[artist]
                song_text = b'\n'.join(song.encode('ascii') for song in song_list)
                send_packet(sock, b'RES', song_text)

            elif type == b'BYE':
                send_packet(sock, b'END', b'')
                break

    except socket.error:
        log("error when communicating with {addr}.".format(addr=addr))

    finally:
        sock.close()
        total_time = time.time() - start_time
        log("Connection ended with {} ({}s).".format(addr, total_time))


def serve(songs):
    port = 8081
    t = ThreadPoolExecutor(max_workers=4)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('localhost', port))
    except OSError:
        print("ERROR: Unable to bind to port")
        exit(1)
    s.listen(4)
    log("Server started, listening at port {port}".format(port=port))
    try:
        while True:
            sock, (host, port) = s.accept()
            sock.settimeout(10)
            addr = '{host}:{port}'.format(host=host, port=port)
            log("Received connection from {addr}".format(addr=addr))
            t.submit(handle_connection, songs, sock, addr)
    finally:
        # needs to be before t.shutdown because t.shutdown will
        # not return if there are still any active connections
        s.shutdown(socket.SHUT_RDWR)
        t.shutdown(wait=True)
        s.close()


if __name__ == '__main__':
    serve(parse(open(sys.argv[1])))
