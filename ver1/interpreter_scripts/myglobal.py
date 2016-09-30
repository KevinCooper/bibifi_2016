#{"name": {"name":name, "data":data, "scope":scope, "type":type} }
#For record data
#{"name": {"name":name, "data":{"name":"string"}, "scope":scope, "type":type} }
import copy
import pickle
class DB:
    def __init__(self):
        self.myDataDB = {}
        self.backupDataDB = {}
        self.myUserDB = {}
        self.backupUserDB = {}

    def getUser(self, name):
        return self.myUserDB.get(name, None)

    def setUser(self, name, data):
        self.myUserDB[name] = data

    def getData(self, name):
        return self.myDataDB.get(name, None)

    def setData(self, name, data):
        self.myDataDB[name] = data

    def popData(self, name):
        self.myDataDB.pop(name)

    def revert(self):
        self.myUserDB = pickle.loads(self.backupUserDB)
        self.myDataDB = pickle.loads(self.backupDataDB)

    def commit(self):
        self.backupUserDB = pickle.dumps(self.myUserDB)
        self.backupDataDB = pickle.dumps(self.myDataDB)

    def clearLocals(self):
        for key, value in list(self.myDataDB.items()):
                if(value['scope'] == 'local'):
                    del self.myDataDB[key]