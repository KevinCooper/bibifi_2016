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
status = []
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
    #Fails if x does not exist
    if(not temp) : raise FailError(str(node), " - setting with illegal reference to {0}".format(name))
    data = json.loads(temp[0]) #See data_format for expected output
    #Security violation if the current principal does not have read permission on x.    
    if(not has_perms(user, data, ["R"])): raise SecurityError(str(node), " - no read permission for {0}".format(name))
    #Returns the current value of variable x.
    return data.get("type", None), data.get("data", None)

def get_record_data(node, user : str, cursor : sqlite3.Cursor, parent : str, child : str):
    '''
        return: data of item matching record (x.y), given that user has correct permissions
    '''
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (parent,))
    temp = cursor.fetchone()
    #Fails if x is not a record or does not have a y field.
    if(not temp) : raise FailError(str(node), " - setting with illegal reference to {0}".format(parent))
    data = json.loads(temp[0]) #See data_format for expected output
    #Security violation if the current principal does not have read permission on x.
    if(not has_perms(user, data, ["R"])): raise SecurityError(str(node), " - no read permission for {0}".format(parent))
    data = data.get("data", None)
    #Fails if x is not a record or does not have a y field.
    if(not data): raise FailError(str(node), " - {0} has no fields.".format(parent))
    data = data.get(child, None)
    #Fails if x is not a record or does not have a y field.
    if(not data): raise FailError(str(node), " - {0} is not a field for {1}.".format(child, parent))
    #If x is a record with field y, returns the value stored in that field.
    return "string", data

def evalExpr(cursor : sqlite3.Cursor, node, user : str , expr):
    data_type = None
    data = None
    if(isinstance(expr, StringNode)): #We are assigning simple stringval
        data = expr.val
        data_type = "string"
    elif(isinstance(expr, IDNode)): #We need to reference another ID
        data_type, data = get_id_data(node, user, cursor, expr.val)
    elif(isinstance(expr, list)): #Setting item to empty list
        data = []
        data_type = "list"
    elif(isinstance(expr, RecordNode)): # x.y
        parent = expr.parent.val
        child = expr.child.val
        data_type, data = get_record_data(node, user, cursor, parent, child)
    else: # Field
        temp = expr
        data = {}
        while temp:
            #TODO: Fails if x1, …, xn are not unique.
            if(isinstance(temp.y, StringNode)):
                data[temp.x] = temp.y.val
            elif(isinstance(temp.y, IDNode)):
                data_type, data[temp.x] = get_id_data(node, user, cursor, temp.y.val)
                #field f cannot be initialized to a non-string value.
                if(data_type != "string"): raise FailError(str(node), " - unsupported type for a fieldval")
            elif(isinstance(temp.y, RecordNode)):
                parent = temp.y.parent.val
                child = temp.y.child.val
                data_type, data[temp.x] = get_record_data(node, user, cursor, parent, child)
                #field f cannot be initialized to a non-string value.
                if(data_type != "string"): raise FailError(str(node), " - unsupported type for a fieldval")
            else:
                raise FailError(str(node), " - unsupported type for a fieldval")
            temp = temp.nextNode
        #raise ValueError("Unsupported")
    return data_type, data

def primSetCmd(node : SetCmd, cursor : sqlite3.Cursor, scope : str):
    #Local:
    #    Fails if x is already defined as a local or global variable.
    #Set:
    #    Security violation if the current principal does not have write permission on x.
    global user, status
    name = node.x
    expr = node.expr.node

    new_data = {
            "name":name, 
            "perms": {"admin": ["R", "W", "A", "D"] } 
            }
    #PREP DATA
    data_type, data = evalExpr(cursor, node, user, expr)
    new_data['type'] = data_type

    new_data['data'] = data
    new_data = json.dumps(new_data)
    #print(new_data)
    #DATA UPDATE
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (name,))
    temp_data = cursor.fetchone()

    #local: Fails if x is already defined as a local or global variable.
    if(temp_data and scope == "local"): raise SecurityError(str(node), "Already defined")
    elif(temp_data):
        temp_data = json.loads(temp_data)
        #Set: Security violation if the current principal does not have write permission on x.
        if(not has_perms(user, temp_data, ["W"])): raise SecurityError(str(node), " - no Write permission for existing value {0}".format(name))
        cursor.execute("UPDATE data(name, value, scope) SET value={0} WHERE name={1}", (new_data, name))
    else:
        cursor.execute("insert into data(name, value, scope) values (?, ?, ?)", (name, new_data, scope))
    status.append({"status":"SET"})
    #cursor.execute("UPDATE users(user, password) SET password={0} WHERE user={1}", (s, p))

def primChangeCmd(node : CreateCmd, cursor : sqlite3.Cursor):
    ''' create principal p s  #s surrounded by double quotes
    Failure conditions:
        Fails if p already exists as a principal.
        Security violation if the current principal is not admin.
    Successful status code: 
        CREATE_PRINCIPAL
    '''
    global user, status
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
    status.append({"status":"CHANGE_PASSWORD"})

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
    status.append({"status":"CREATE_PRINCIPAL"})

def returnBlock(node : ReturnNode, cursor : sqlite3.Cursor):
    global user, status
    data_type, data = evalExpr(cursor, node, user, node.expr.node)
    status.append({"status":"RETURNING", "output":data})
    return None

def exitBlock(node : ExitNode):
    global status
    status.append({"status":"EXITING"})
    return None


def primAppendCmd(node : ReturnNode, cursor : sqlite3.Cursor):
    global user
    name = node.x
    expr = node.expr.node

    data_type, data = evalExpr(cursor, node, user, expr)

    #Fails if x is not defined or is not a list.
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (name,))
    temp_data = cursor.fetchone()

    #local: Fails if x is not already defined as a local or global variable.
    if(not temp_data):
        raise FailError(str(node), " {0} is not defined".format(name))
    elif(temp_data):
        temp_data = json.loads(temp_data)
        #Fails if x is not a list.
        if(temp_data['type'] != 'list'): raise FailError(str(node), " {0} is not a list".format(name))
        #Security violation if the current principal does not have either write or append permission on x.
        if(not has_perms(user, temp_data, ["W", "A"])): raise SecurityError(str(node), " - no write/append permission for existing value {0}".format(name))
        temp_data['data'].append(data)
        new_data = json.dumps(temp_data)
        cursor.execute("UPDATE data(name, value, scope) SET value={0} WHERE name={1}", (new_data, name))

def primSetDel(node: SetDel, cursor : sqlite3.Cursor):
    global user, status
    target = node.tgt
    src_user = node.src_id
    right = node.right
    dst_user = node.dst_id

    #set delegation x p <right> -> q requires that, if x is a "normal" variable, the current principal be either admin or p.
    #If the latter, p must have delegate permission on x.
    if(user != "admin" and user != src_user and target != "all"): raise FailError(str(node), " cannot give another users rights away")
    #Do we need to check src user, since we can't be running as him if he doesn't exist?
    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (src_user,))
    temp_data = cursor.fetchone()
    if(not temp_data): raise FailError(str(node), " giving user does not exist")
    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (dst_user,))
    temp_data = cursor.fetchone()
    if(not temp_data): raise FailError(str(node), " receiving user does not exist")


    status.append({"status":"SET_DELEGATION"})
    

def primDelDel(node: SetDel, cursor : sqlite3.Cursor):
    global user, status
    target = node.tgt
    src_user = node.src_id
    right = node.right
    dst_user = node.dst_id

    status.append({"status":"DELETE_DELEGATION"})

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
    elif(type(primcmd) == AppendCmd): #TODO: OUTPUT
        primAppendCmd(primcmd, cursor)
    elif(type(primcmd) == SetDel):
        primSetDel(primcmd, cursor)
    elif(type(primcmd) == DelDel):
        primDetDel(primcmd, cursor)
    return cmd


def run_program(db_con : sqlite3.Connection , program: str):
    my_parser = LanguageParser()
    result = my_parser.parse(program)
    #print("\n\nAST:")
    #print(result)
    cursor = db_con.cursor()

    node = result
    #print(node)
    #print("\n\nRunning Interpreter!")
    while node is not None:
        #print(repr(node))
        if (type(node) == ProgNode):
            node = progNode(node, cursor)
        elif (type(node) == PrimCmdBlock):
            node = primCmdBlockNode(node, cursor)
        elif (type(node) == ReturnNode):
            node = returnBlock(node, cursor)
        elif (type(node) == ExitNode):
            node = exitBlock(node)
    
    return status