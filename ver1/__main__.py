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
import json

def recv_until_prog_end(s: socket.socket):
    buffer = ""
    data = ""
    while True:
        data += s.recv(1024*1024).decode('ascii')
        if not data:
            break
        buffer += data
        if("***" in buffer):
            break

    return buffer



def handle_progs(s : socket.socket, db_con : sqlite3.Connection ,  network : nx.DiGraph):
    ending = False
    prev = None
    while not ending:
        conn, addr = s.accept()

        start = time.time()

        data = recv_until_prog_end(conn)
        with open("log.txt", "w") as f: f.write(data)
        #if(prev != data):
        network, status, ending, side_effects = run_program(db_con, data, network)
        #    prev = data

        

        if(status and status[-1].get('status') == "FAILED" or status[-1].get('status') == "DENIED"):
            db_con.rollback()
        #TODO: Careful about this optimization
        elif(side_effects):
            cursor = db_con.cursor()
            #Delete local data from DB
            cursor.execute("DELETE FROM data WHERE scope=?", ("local",))
            db_con.commit()

            #Delete local from permissions network
            for node in network.nodes(data=True):
                #node[0] = nodeName, node[1]= dict of node data
                if(node[1].get("scope", "global") == "local"):
                    network.remove_node(node[0])

        send_status = json.dumps(status)
        conn.sendall(send_status.encode('ascii'))
        conn.close()
        end = time.time()
        print("time:" + str(end-start))
            
            

def handler():
    signal.signal(signal.SIGINT, original_sigint)
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
    network.add_node("@default", value="anyone")
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
