#{"name": {"name":name, "data":data, "scope":scope, "type":type} }
#For record data
#{"name": {"name":name, "data":{"name":"string"}, "scope":scope, "type":type} }
import copy
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
        self.myUserDB = copy.deepcopy(self.backupUserDB)
        self.myDataDB = copy.deepcopy(self.backupDataDB)

    def commit(self):
        self.backupUserDB = copy.deepcopy(self.myUserDB)
        self.backupDataDB = copy.deepcopy(self.myDataDB)

    def clearLocals(self):
        for key, value in list(self.myDataDB.items()):
                if(value['scope'] == 'local'):
                    del self.myDataDB[key]