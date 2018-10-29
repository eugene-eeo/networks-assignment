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
    invalid = None, None
    try:
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
    except socket.timeout:
        return invalid


def send_packet(s, type, data):
    try:
        length = ('{0:06d}'.format(len(data))).encode('ascii')
        header = type + b' ' + length
        packet = header + b'\n' + data
        s.sendall(packet)
        return True
    except socket.timeout:
        return False


def log(text, lock=threading.Lock(), workers={}):
    with lock:
        id = threading.current_thread().ident
        if id not in workers:
            workers[id] = 0
            workers[id] = max(workers.values()) + 1
        now = str(datetime.datetime.now())
        msg = '[{now}] [worker-{id}] {text}'.format(
            now=now,
            id=workers[id],
            text=text,
        )
        print(msg)
        with open('server.log', 'a') as fp:
            fp.write(msg + '\n')


def handle_connection(songs, sock, addr):
    t0 = time.time()
    while True:
        type, data = recv_packet(sock)
        if type is None:
            log("{addr} timed out.".format(addr=addr))
            break

        elif type == b'REQ':
            #ok = send_packet(sock, b'ACK', b'')
            #if not ok:
            #    break
            artist = data.decode()
            log("Received artist from {addr}: {artist}".format(addr=addr, artist=artist))
            songs = b'\n'.join(x.encode('ascii') for x in songs[artist])
            ok = send_packet(sock, b'RES', songs)
            if not ok:
                break

        elif type == b'BYE':
            send_packet(sock, b'END', b'')
            break

    sock.close()
    dt = time.time() - t0
    log("Connection ended with {addr} ({dt}s).".format(addr=addr, dt=dt))


def main(f):
    songs = parse(open(f))
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
            sock, addr = s.accept()
            sock.settimeout(10)
            addr = addr[0] + ':' + str(addr[1])
            log("Received connection from {addr}".format(addr=addr))
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
