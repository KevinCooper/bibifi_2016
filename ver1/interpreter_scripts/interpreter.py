import socket
import sys
import re
import sqlite3
from .parser import LanguageParser
from .errors import *
from .ast import *
import pickle
import json
import networkx as nx
import time

user = ""
status = []
network = None

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

def has_perms(name: str, user: str, reqs : list) -> bool:
    #x admin ['read']
    global network
    '''
        We need to run this for each requirements, because a user may be able to read X from delegations
        down one path, but has to user another path.  Since we are making a copy of the network, maybe
        we could just remove items from each set aren't what we need, then if the edge has an empty set
        then delete it.  That would only require one pass maybe
    '''

    #ADMIN IS GOD
    if(user == "admin"): return True

    for req in reqs:
        G = network.copy()
        del_req = set(["delegate:"+req+":"+name])
        for edge in G.edges(data=True):
            #('admin', 'x', {'write', 'read', 'append', 'delegate'})
            #If edge to item and not access
            if(edge[1] == name and not set(edge[2]).issuperset(set([req]))):
                G.remove_edge(*edge[:2])
                continue
            #Edge isn't to our desired item, need delegate access
            #Can't have delegated access from user -> item
            elif(edge[1] != name and not set(edge[2]).issuperset(del_req)):
                G.remove_edge(*edge[:2])
                continue
        
        if(not nx.has_path(G, user, name)):
            return False    
    return True
    

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
    if(not has_perms(name, user, ["read"])): raise SecurityError(str(node), " - no read permission for {0}".format(name))
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
    if(not has_perms(data['name'], user, ["read"])): raise SecurityError(str(node), " - no read permission for {0}".format(parent))
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
    elif(isinstance(expr, FieldValue)): # Field
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
        data_type = "record"

    return data_type, data

def primSetCmd(node : SetCmd, cursor : sqlite3.Cursor, scope : str):
    #Local:
    #    Fails if x is already defined as a local or global variable.
    #Set:
    #    Security violation if the current principal does not have write permission on x.
    global user, status, network
    name = node.x
    expr = node.expr.node

    new_data = {
            "name":name, 
            }
    #PREP DATA
    data_type, data = evalExpr(cursor, node, user, expr)
    new_data['type'] = data_type

    new_data['data'] = data
    new_data = json.dumps(new_data)
    #DATA UPDATE
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (name,))
    temp_data = cursor.fetchone()

    #local: Fails if x is already defined as a local or global variable.
    if(temp_data and scope == "local"): raise SecurityError(str(node), "Already defined")
    elif(temp_data):
        temp_data = json.loads(temp_data[0])
        #Set: Security violation if the current principal does not have write permission on x.
        if(not has_perms(name, user, ["write"])): raise SecurityError(str(node), " - no Write permission for existing value {0}".format(name))
        cursor.execute("UPDATE data SET value=? WHERE name=?",(new_data, name))
    else:
        cursor.execute("insert into data(name, value, scope) values (?, ?, ?)", (name, new_data, scope))
        network.add_node(name, scope=scope)
        #If x is created by this command, and the current principal is not admin, then the current principal is delegated read, write, append, and delegate rights from the admin on x 
        if(user != "admin"):
            network[user]["admin"] = set(["delegate:read:"+name, "delegate:write:"+name, "delegate:append:"+name, "delegate:delegate:"+name])
        network["admin"][name] = set(["read", "write", "append", "delegate"])
    

    status.append({"status":"SET"})


    

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
    
    global user, network
    new_user = node.p
    s = node.s.replace('"', "")

    #Security violation if the current principal is not admin.
    if(user != "admin"): raise SecurityError("{0}".format(user), " is not the administrator")

    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (new_user,))
    temp = cursor.fetchone()

    #Fails if p already exists as a principal.
    if(temp): raise FailError("{0}".format(user), " already exists")

    cursor.execute("insert into users(user, password) values (?, ?)", (new_user, s))
    network.add_node(new_user)

    #Delegate 'all' from p to q
    #all then q delegates <right> to p for all variables on which q (currently) has delegate permission.
    delegator = network.node["@default"]['value']
    to_add = set()
    for edge in network.edges([delegator], data=True):
        items = [x for x in set(edge[2]) if "delegate:" in x]
        to_add.union(items)
    network.add_edge(new_user, delegator, to_add)

    status.append({"status":"CREATE_PRINCIPAL"})

def returnBlock(node : ReturnNode, cursor : sqlite3.Cursor):
    global user, status
    data_type, data = evalExpr(cursor, node, user, node.expr.node)
    status.append({"status":"RETURNING", "output":data})
    return None

def exitBlock(node : ExitNode):
    global status
    status.append({"status":"EXITING"})
    raise ExitError()


def primAppendCmd(node : ReturnNode, cursor : sqlite3.Cursor):
    global user
    name = node.x
    expr = node.expr.node
    data_type, data = evalExpr(cursor, node, user, expr)
    #Fails if x is not defined or is not a list (see below).
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (name,))
    temp_data = cursor.fetchone()

    #local: Fails if x is not already defined as a local or global variable.
    if(not temp_data):
        raise FailError(str(node), " {0} is not defined".format(name))
    elif(temp_data):
        temp_data = json.loads(temp_data[0])
        #Fails if x is not a list.
        if(temp_data['type'] != 'list'): raise FailError(str(node), " {0} is not a list".format(name))
        #Security violation if the current principal does not have either write or append permission on x.
        if(not has_perms(name, user, ["write", "append"])): raise SecurityError(str(node), " - no write/append permission for existing value {0}".format(name))
        if(data_type != "list"):
            temp_data['data'].extend([data])
        else:
            temp_data['data'].extend(data)
        new_data = json.dumps(temp_data)
        cursor.execute("UPDATE data SET value=? WHERE name=?",(new_data, name))
    status.append({"status":"APPEND"})

def primSetDel(node: SetDel, cursor : sqlite3.Cursor):
    #set delegation <tgt> q <right> -> p
    #                tgt  src right  -> dst
    global user, status, network
    target = node.tgt
    src_user = node.src_id
    right = node.right
    dst_user = node.dst_id
    
    #Fails if either p or q does not exist.
    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (src_user,))
    temp_data = cursor.fetchone()
    if(not temp_data): raise FailError(str(node), " giving user does not exist")
    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (dst_user,))
    temp_data = cursor.fetchone()
    if(not temp_data): raise FailError(str(node), " receiving user does not exist")
    #set delegation x p <right> -> q requires that, if x is a "normal" variable, the current principal be either admin or p.
    #If the latter, p must have delegate permission on x.
    if(user != "admin" and user != src_user): raise SecurityError(str(node), " cannot give another users rights away")

    if(not network.has_edge(dst_user, src_user)):
        network.add_edge(dst_user, src_user, set())
    
    if(right == "all"):
        to_add = set()
        #Get all the rights the delegator has
        for edge in network.edges([src_user], data=True):
            items = [x for x in set(edge[2]) if "delegate:" in x]
            to_add.union(items)
        #Get all the rights the delegatee has
        tempSet = set(network[dst_user][src_user])
        #Combine and assign to delegatee, s + t
        network[dst_user][src_user] = tempSet.union(to_add)
    else:
        if(not has_perms(target, src_user, ["delegate"])): raise SecurityError(str(node), " - no write/append permission for existing value {0}".format(name))
        tempSet = set(network[dst_user][src_user])
        network[dst_user][src_user] = tempSet.union(set(["delegate:"+right+":"+target]))

    status.append({"status":"SET_DELEGATION"})
    

def primDelDel(node: DelDel, cursor : sqlite3.Cursor):
    #delete delegation <tgt> q <right> -> p 
    #                  tgt  src right  -> dst
    global user, status
    target = node.tgt
    src_user = node.src_id
    right = node.right
    dst_user = node.dst_id

    #Fails if either p or q does not exist.
    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (src_user,))
    temp_data = cursor.fetchone()
    if(not temp_data): raise FailError(str(node), " giving user does not exist")
    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (dst_user,))
    temp_data = cursor.fetchone()
    if(not temp_data): raise FailError(str(node), " receiving user does not exist")
    #set delegation x p <right> -> q requires that, if x is a "normal" variable, the current principal be either admin or p.
    #If the latter, p must have delegate permission on x.
    if(user != "admin" and user != src_user and user != dst_user): raise SecurityError(str(node), " cannot delete another users rights")


    if(not network.has_edge(dst_user, src_user)):
        pass #Does exist anyways!
    elif(right == "all"):
        to_remove = set()
        #Get all the rights the delegator has
        for edge in network.edges([src_user], data=True):
            items = [x for x in set(edge[2]) if "delegate:" in x]
            to_remove.union(items)
        #Get all the rights the delegatee has
        tempSet = set(network[dst_user][src_user])
        #Subtract and assign to delegatee, s - t
        network[dst_user][src_user] = tempSet.difference(to_add)
    else:
        if(not has_perms(target, src_user, ["delegate"])): raise SecurityError(str(node), " - no delegate permission for existing value {0}".format(name))
        tempSet = set(network[dst_user][src_user])
        network[dst_user][src_user] = tempSet.difference(set(["delegate:"+right+":"+target]))

    status.append({"status":"DELETE_DELEGATION"})

def primSetDef(node : DefaultCmd, cursor):
    global user, status, network

    name = node.x

    #Fails if p does not exist.
    cursor.execute("SELECT * FROM users WHERE user = ? LIMIT 1", (name,))
    temp_data = cursor.fetchone()
    if(not temp_data): raise FailError(str(node), " user does not exist")

    #Security violation if the current principal is not admin.
    if(user != "admin"): raise SecurityError(str(node), " user must be admin")

    network.node["@default"]['value'] = name

    status.append({"status":"DEFAULT_DELEGATOR"})

def primForEach(node : ForEachCmd, cursor):
    #foreach y in x replacewith <expr>
    global user, status, network
    item = node.y
    name = node.x
    expr = node.expr.node

    #Fails if x is not defined
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (name,))
    temp_data = cursor.fetchone()
    if(not temp_data): raise FailError(str(node), " {0} is not defined".format(name))

    #Fails if x is not a list.
    temp_data = json.loads(temp_data[0])
    if(temp_data['type'] != 'list'): raise FailError(str(node), " {0} is not a list".format(name))

    #Fails if y is already defined as a local or global variable.
    cursor.execute("SELECT value FROM data WHERE name = ? LIMIT 1", (item,))
    temp = cursor.fetchone()
    if(temp): raise FailError(str(node), " {0} is already defined".format(item))

    #Security violation if the current principal does not have read/write permission on x.
    if(not has_perms(name, user, ["read", "write"])): raise SecurityError(str(node), " - no read/write permission for {0}".format(name))


    #To do this properly would require a clusterfuck of code
    #Aka, instantiating the rec variable from item in list, getting possible
    #subfields, then rebuilding a new list and returning that.  Just check for
    #The possible data types, an ID, String, Subfield.  We can cheat on the subfield
    #Since it has to be an attribute of records in our array (not any possible globa dict)
    
    #Data is a list of whatever
    data = list(temp_data['data'])

    for index, element in enumerate(data):
        #Instantiate y
        #TODO: what other types are there? List?
        to_insert = { 'name' : item, 'data' : element, 'type' : 'string'}
        cursor.execute("insert into data(name, value, scope) values (?, ?, ?)", (item, json.dumps(to_insert), "local"))
        network.add_node(item, scope="local")
        if(user != "admin"):
            network[user]["admin"] = set(["delegate:read:"+item, "delegate:write:"+item, "delegate:append:"+item, "delegate:delegate:"+item])
        network["admin"][item] = set(["read", "write", "append", "delegate"])

        
        _, temp = evalExpr(cursor, node, user, expr)
        data[index] = temp

        #remove Node
        network.remove_node(item)
        #remove Instantiation
        cursor.execute("DELETE FROM data WHERE name=?", (item,))

    #DATA UPDATE
    temp_data['data'] = data
    temp_data = json.dumps(temp_data)
    cursor.execute("UPDATE data SET value=? WHERE name=?",(temp_data, name))


    status.append({"status":"FOREACH"})


def primCmdBlockNode(node : PrimCmdBlock, cursor : sqlite3.Cursor) :
    primcmd = node.primcmd
    cmd = node.cmd

    if(type(primcmd) == SetCmd): 
        primSetCmd(primcmd, cursor, "global")
    elif(type(primcmd) == LocalCmd): 
        primSetCmd(primcmd, cursor, "local")
    elif(type(primcmd) == CreateCmd): 
        primCreateCmd(primcmd, cursor)
    elif(type(primcmd) == ChangeCmd): 
        primChangeCmd(primcmd, cursor)
    elif(type(primcmd) == AppendCmd): 
        primAppendCmd(primcmd, cursor)
    elif(type(primcmd) == SetDel):
        primSetDel(primcmd, cursor)
    elif(type(primcmd) == DelDel):
        primDetDel(primcmd, cursor)
    elif(type(primcmd) == DefaultCmd):
        primSetDef(primcmd, cursor)
    elif(type(primcmd) == ForEachCmd):
        primForEach(primcmd, cursor)
    return cmd


def run_program(db_con : sqlite3.Connection , program: str, in_network : nx.DiGraph ):
    global network, status
    status = []
    network = in_network
    backup = network.copy()
    ending = False
    try:
        my_parser = LanguageParser()
        result = my_parser.parse(program)

        cursor = db_con.cursor()
        node = result
        while node is not None:
            if (type(node) == ProgNode):
                node = progNode(node, cursor)
            elif (type(node) == PrimCmdBlock):
                node = primCmdBlockNode(node, cursor)
            elif (type(node) == ReturnNode):
                node = returnBlock(node, cursor)
            elif (type(node) == ExitNode):
                node = exitBlock(node)
    except FailError as e:
        network = backup
        status.append({"status":"FAILED"})
        print(e)
    except SecurityError as e:
        network = backup
        status.append({"status":"DENIED"})
        print(e)
    except ParseError as e:
        status = [{"status":"FAILED"}]
        print(e)
    except ExitError as e:
        ending = True
    
    return network, status, ending