#./server PORT [PASSWORD]"
import signal
import socket
import sys
import os
import re
import sqlite3
import interpreter_scripts
from interpreter_scripts.parser import LanguageParser
from interpreter_scripts.interpreter import run_program
from interpreter_scripts.errors import *
import networkx as nx
import time
import glob

def recv_until_prog_end(s: socket.socket):
    buffer = ""
    data = ""
    while True:
        data += s.recv(1024).decode('ascii')
        if not data:
            break
        buffer += data
        if("***" in buffer):
            break

    return buffer



def handle_progs(s : socket.socket, db_con : sqlite3.Connection ,  network : nx.DiGraph):
    ending = False
    while not ending:
        conn, addr = s.accept()
        print("Conn from:" + str(addr))
        data = recv_until_prog_end(conn)
        #print(repr(data))

        start = time.time()

        network, status, ending = run_program(db_con, data, network)

        end = time.time()

        if(status and status[-1].get('status') == "FAILED" or status[-1].get('status') == "DENIED"):
            db_con.rollback()
        else:
            cursor = db_con.cursor()
            #Delete local data from DB
            cursor.execute("DELETE FROM data WHERE scope=?", ("local",))
            db_con.commit()

            #Delete local from permissions network
            for node in network.nodes(data=True):
                if(node[1].get("scope", "global") == "local"):
                    network.remove_node(node)

        status = [str(item) for item in status ]
        #print("\n\n")
        #print(str(status)+"\n"+str(end-start))
        print("Time:" + str(end-start))
        conn.sendall(("\n".join(status)).encode('ascii'))
        conn.close()

            
            

def handler():
    signal.signal(signal.SIGINT, original_sigint)
    print('You pressed Ctrl+C!')
    sys.exit(0)

def get_inputs():
    if(len(sys.argv) <= 1):
        sys.exit(255)
    elif(len(sys.argv) == 2):
        port = sys.argv[1]
        password = "admin"
    elif(len(sys.argv) == 3):
        port = sys.argv[1]
        password = sys.argv[2]
    else:
        sys.exit(255)

    if(len(password) > 4096 or len(port) > 4096):
        sys.exit(255)
    if(not port.isdigit() or int(port) < 1024 or int(port) > 65535 ):
        sys.exit(255)
    if(not re.match(r'^[A-Za-z0-9_ ,;\.?!-]*$', password)):
        sys.exit(255)
    
    return password, int(port) 

def setup_db(password: str, network : nx.DiGraph ):
    con = sqlite3.connect(':memory:')
    cursor = con.cursor()
    cursor.execute("create table data(name TEXT, value TEXT, scope, TEXT)")
    cursor.execute("create table users(user TEXT, password TEXT)")
    cursor.execute("insert into users(user, password) values (?, ?)", ("admin", password))
    #Anyone is given a password that can not ever be input.  Admin can change this later if they choose to.
    cursor.execute("insert into users(user, password) values (?, ?)", ("anyone", "@"))
    con.commit()
    network.add_node("admin")
    network.add_node("anyone")
    return con


if __name__=="__main__":

    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGTERM, handler)

    password, port = get_inputs()

    network = nx.DiGraph()

    db_con = setup_db(password, network)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   
    try:
        s.bind(("", port))
        s.listen(1)
        handle_progs(s, db_con, network)
    except socket.error as e:
        if e.errno == 98:
            sys.exit(63)
        else:
            print("Error")
            raise(e)
            sys.exit(0)
    except KeyboardInterrupt:
        handler()
    #except Exception as e:
    #    print(e)