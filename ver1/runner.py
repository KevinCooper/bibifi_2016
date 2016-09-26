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

def do_stuff(s : socket.socket, db_con : sqlite3.Connection ,  network : nx.DiGraph):
    #TODO: Seperate the reading of socket data from the running of a program
    #TODO: Between running each program, flush every data item where scope="local"     

    with open("sample2.code", "r") as f:
        print(run_program(db_con, f.read(), network))

def handler():
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

    signal.signal(signal.SIGTERM, handler)

    password, port = get_inputs()

    network = nx.DiGraph()

    db_con = setup_db(password, network)

    s = socket.socket()
    
    try:
        s.bind(("127.0.0.1", port))
        do_stuff(s, db_con, network)
    except socket.error as e:
        if e.errno == 98:
            sys.exit(63)
        else:
            print("Error")
            sys.exit(0)
    #except Exception as e:
    #    print(e)