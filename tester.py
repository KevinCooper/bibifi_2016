import socket
import glob
import sys
import time


if __name__=="__main__":
    dir = sys.argv[1]
    for item in glob.glob(dir + "*.code"):
        with open(item, 'r') as f:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 1024))
            s.sendall(f.read().encode('ascii'))
            print("GOT:")
            print(s.recv(100000).decode('ascii'))
            print("")