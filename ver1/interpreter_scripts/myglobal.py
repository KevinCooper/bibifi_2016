#{"name": {"name":name, "data":data, "scope":scope, "type":type} }
#For record data
#{"name": {"name":name, "data":{"name":"string"}, "scope":scope, "type":type} }
myDataDB = None
backupDataDB = None
myUserDB = None
backupUserDB = None
def init():
    global myDataDB, backupDataDB, myUserDB, backupUserDB
    if(myDataDB is None):
        myDataDB = {}
    if(backupDataDB is None):
        backupDataDB = {}

    #{"username":"password"}
    if(myUserDB is None):
        myUserDB = {}
    if(backupUserDB is None):
        backupUserDB = {}

init()