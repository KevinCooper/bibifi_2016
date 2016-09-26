import socket
import sys
import re
import sqlite3
from .parser import LanguageParser
from .errors import *
from .ast import *
import json

user = ""
local_data = {

}
prog_data = {

}
def progNode(node : ProgNode, cursor : sqlite3.Cursor) :
    global user
    user = node.user
    password = node.password.replace('"', '')

    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (user,))

    temp = cursor.fetchone()
    if(not temp):
        #Fails if principal p does not exist.
        raise FailError("{0}".format(user), " does not exist")
    elif(temp and (temp[1] != password)):
        #Security violation if the password s is not p’s password.
        raise SecurityError("Incorrect password for user:{0}".format(user), "Correct: {0}, Given:{1}".format(temp[1], password))
    
    #Otherwise, the server terminates the connection after running <cmd> under the authority of principal p.
    return node.cmd

def primSetCmd(node : SetCmd, cursor : sqlite3.Cursor):
    global user
    permissions = ["R", "W", "A", "D"]
    name = node.x
    expr = str(node.expr)
    print(name, expr)
    mytype = ""


    if(expr.startswith('"')):
        mytype = "string"
        data = expr
    elif(expr.startswith('{')):
        mytype = "dict"
    else:
        mytype = "list"
        data = []

    toStore = {
            "data": data,
            "type": mytype,
            "names": {
                "admin": [ "R", "W", "A", "D" ],
                     },
            }

    cursor.execute("SELECT * FROM data WHERE name = ? LIMIT 1", (name,))
    temp = cursor.fetchone()

    if(temp):
        pass
    else:
        pass

    #cursor.execute("UPDATE users(user, password) SET password={0} WHERE user={1}", (s, p))

def primChangeCmd(node : CreateCmd, cursor : sqlite3.Cursor):
    ''' create principal p s  #s surrounded by double quotes
    Failure conditions:
        Fails if p already exists as a principal.
        Security violation if the current principal is not admin.
    Successful status code: 
        CREATE_PRINCIPAL
    '''
    global user
    p = node.p
    s = node.s.replace('"', "")

    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (p,))
    temp = cursor.fetchone()

    if(not temp): #Fails if p already exists as a principal.
        raise FailError("{0}".format(user), " does not exist")

    if(user != "admin" and user != p): #Security violation if the current principal is not admin.
        raise SecurityError("{0}".format(user), " does not have permissions to change this password.")

    #TODO: Check vulnerability
    cursor.execute("UPDATE users(user, password) SET password={0} WHERE user={1}", (s, p))

def primCreateCmd(node : CreateCmd, cursor : sqlite3.Cursor):
    ''' create principal p s  #s surrounded by double quotes
    Failure conditions:
        Fails if p already exists as a principal.
        Security violation if the current principal is not admin.
    Successful status code: 
        CREATE_PRINCIPAL
    '''
    global user
    p = node.p
    s = node.s.replace('"', "")

    if(user != "admin"): #Security violation if the current principal is not admin.
        raise SecurityError("{0}".format(user), " is not the administrator")

    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (p,))
    temp = cursor.fetchone()

    if(temp): #Fails if p already exists as a principal.
        raise FailError("{0}".format(user), " already exists")

    cursor.execute("insert into users(user, password) values (?, ?)", (p, s))

def returnBlock(node : ReturnNode):
    return None

def exitBlock(node : ExitNode):
    return None

def primCmdBlockNode(node : PrimCmdBlock, cursor : sqlite3.Cursor) :
    primcmd = node.primcmd
    cmd = node.cmd

    if(type(primcmd) == SetCmd): #TODO: all
        primSetCmd(primcmd, cursor)
    elif(type(primcmd) == CreateCmd): #TODO: OUTPUT
        primCreateCmd(primcmd, cursor)
    elif(type(primcmd) == ChangeCmd): #TODO: OUTPUT
        primChangeCmd(primcmd, cursor)
    return cmd


def run_program(db_con : sqlite3.Connection , program: str):
    my_parser = LanguageParser()
    result = my_parser.parse(program)
    print("\n\nAST:")
    print(result)
    cursor = db_con.cursor()

    node = result
    print("\n\nRunning Interpreter!")
    while node is not None:
        print(repr(node))
        if (type(node) == ProgNode):
            node = progNode(node, cursor)
        elif (type(node) == PrimCmdBlock):
            node = primCmdBlockNode(node, cursor)
        elif (type(node) == ReturnNode):
            node = returnBlock(node)
        elif (type(node) == ExitNode):
            node = exitBlock(node)
