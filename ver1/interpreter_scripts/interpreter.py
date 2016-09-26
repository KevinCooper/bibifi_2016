import socket
import sys
import re
import sqlite3
from .parser import LanguageParser
from .errors import *
from .ast import *
import pickle
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

def has_perms(user: str, data : dict , req : list) -> bool:
    perms = data.get("perms", None)
    perms = perms.get(user, None)
    if(not perms): return False #user does not exist in permission list
    return set(req).issubset(set(perms))

def get_id_data(node, user : str , cursor : sqlite3.Cursor , name : str):
    '''
        return: data_format of item matching name, given that user has correct permissions
    '''
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (name,))
    temp = cursor.fetchone()
    if(not temp) : raise FailError(str(node), " - setting with illegal reference to {0}".format(name))
    data = json.loads(temp[0]) #See data_format for expected output
    if(not has_perms(user, data, ["R"])): raise SecurityError(str(node), " - no read permission for {0}".format(name))
    return data.get("data", None)

def get_record_data(node, user : str, cursor : sqlite3.Cursor, parent : str, child : str):
    '''
        return: data of item matching record (x.y), given that user has correct permissions
    '''
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (parent,))
    temp = cursor.fetchone()
    if(not temp) : raise FailError(str(node), " - setting with illegal reference to {0}".format(parent))
    data = json.loads(temp[0]) #See data_format for expected output
    if(not has_perms(user, data, ["R"])): raise SecurityError(str(node), " - no read permission for {0}".format(parent))
    data = data.get("subdata", None)
    if(not data): raise FailError(str(node), " - {0} has no fields.".format(parent))
    data = data.get(child, None)
    if(not data): raise FailError(str(node), " - {0} is not a field for {1}.".format(child, parent))
    return data

def primSetCmd(node : SetCmd, cursor : sqlite3.Cursor, scope : str):
    global user
    name = node.x
    expr = node.expr.node


    #PREP DATA
    new_data = {
            "name":name, 
            "perms": {"admin": ["R", "W", "A", "D"] } 
            }

    data = None
    if(isinstance(expr, StringNode)): #We are assigning simple stringval
        data = expr.val
    elif(isinstance(expr, IDNode)): #We need to reference another ID
        data = get_id_data(node, user, cursor, expr.val)
    elif(isinstance(expr, list)): #Setting item to empty list
        data = []
    elif(isinstance(expr, RecordNode)): # x.y
        parent = expr.parent.val
        child = expr.child.val
        data = get_record_data(node, user, cursor, parent, child)
    else: # Field
        temp = expr
        data = {}
        while temp:
            if(isinstance(temp.y, StringNode)):
                data[temp.x] = temp.y.val
            elif(isinstance(temp.y, IDNode)):
                data[temp.x] = get_id_data(node, user, cursor, temp.y.val)
            elif(isinstance(temp.y, RecordNode)):
                parent = temp.y.parent.val
                child = temp.y.child.val
                data[temp.x] = get_record_data(node, user, cursor, parent, child)
            else:
                raise FailError(str(node), " - unsupported type for a fieldval")
            temp = temp.nextNode
        #raise ValueError("Unsupported")

    new_data['data'] = data
    new_data = json.dumps(new_data)
    #print(new_data)
    #DATA UPDATE
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (name,))
    temp_data = cursor.fetchone()

    if(temp_data):
        temp_data = json.loads(temp_data)
        if(not has_perms(user, temp_data, ["R", "W"])): raise SecurityError(str(node), " - no read/write permission for existing value {0}".format(name))
        cursor.execute("UPDATE data(name, value, scope) SET value={0} WHERE name={1}", (new_data, name))
    else:
        cursor.execute("insert into data(name, value, scope) values (?, ?, ?)", (name, new_data, scope))

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

    if(type(primcmd) == SetCmd): #TODO: OUTPUT
        primSetCmd(primcmd, cursor, "global")
    elif(type(primcmd) == LocalCmd): #TODO: OUTPUT
        primSetCmd(primcmd, cursor, "local")
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
