import sys
import socket
import random
import time
from server import recv_packet, send_packet

port = int(sys.argv[1])

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', port))
send_packet(s, b'REQ', sys.argv[2].encode('ascii'))
print(recv_packet(s))
time.sleep(2 * random.random())
send_packet(s, b'BYE', b'')
s.close()
