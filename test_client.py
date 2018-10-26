import sys
import socket
import random
import time
from server import get_next_packet, write_packet

port = int(sys.argv[1])

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', port))
write_packet(s, b'REQ', sys.argv[2].encode('ascii'))
print(get_next_packet(s))
time.sleep(2 * random.random())
write_packet(s, b'BYE', b'')
s.close()
