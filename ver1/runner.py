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

def do_stuff(s : socket.socket, db_con : sqlite3.Connection ,  password : str):
    #TODO: Seperate the reading of socket data from the running of a program
    

    with open("sample_whitespace.code", "r") as f:
        run_program(db_con, f.read())

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

def setup_db(password: str):
    con = sqlite3.connect(':memory:')
    cursor = con.cursor()
    cursor.execute("create table data(name, value)")
    cursor.execute("create table users(user, password)")
    cursor.execute("insert into users(user, password) values (?, ?)", ("admin", password))
    #Anyone is given a password that can not ever be input.  Admin can change this later if they choose to.
    cursor.execute("insert into users(user, password) values (?, ?)", ("anyone", "@"))
    con.commit()
    #cursor = con.cursor()
    #cursor.execute("select * from users")
    #print(cursor.fetchone())
    return con


if __name__=="__main__":

    signal.signal(signal.SIGTERM, handler)

    password, port = get_inputs()

    db_con = setup_db(password)

    s = socket.socket()
    
    try:
        s.bind(("127.0.0.1", port))
        do_stuff(s, db_con, password)
    except socket.error as e:
        if e.errno == 98:
            sys.exit(63)
        else:
            print("Error")
            sys.exit(0)