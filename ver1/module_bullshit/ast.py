import re

class Node:
    def execute(self):
        raise NotImplementedError
    def __repr__(self):
        return self.__str__()

class ProgNode(Node):
    def __init__(self, user: str, password: str, CmdNode: Node):
        super()
        self.user = user
        self.password = password
        self.cmd = CmdNode

    def __str__(self):
        return "<ProgNode> User: {0}. Pass: {1}. \n{2}".format(self.user, self.password, str(self.cmd))

    def execute(self) -> bool:
        #Setup DB Connection
        #TODO: DB HERE

        if(self.cmd.execute()):
            pass #TODO: append json success string
        else:
            pass #TODO: append json failure string
        
class CmdNode(Node):
    def __init__(self):
        super()


class ExitNode(CmdNode):
    
    def __init__(self):
        super()

    def __str__(self):
        return "\t<CmdNode> EXIT."


class FieldValue(Node):
    def __init__(self, x, y, nextNode):
        super()
        self.x = x
        self.y = y
        self.nextNode = nextNode

    def __str__(self):
        if(self.nextNode is None):
            return "{0} = {1}".format(self.x, self.y)
        else:
            return "{0} = {1}, {2}".format(self.x, self.y, str(self.nextNode))

    def execute(self):
        pass


class ExprNode(Node):
    def __init__(self, temp):
        super()
        if(isinstance(temp, str)):
            self.temp = temp
        elif(isinstance(temp, list)):
            self.temp = temp
        elif(isinstance(temp, FieldValue)):
            self.temp = temp #TODO: Maybe create a dict() here?

    def __str__(self):
        return str(self.temp)


class ReturnNode(CmdNode):
    def __init__(self, expr: ExprNode):
        super()
        self.expr = expr

    def __str__(self):
        return "\t<CmdNode> RETURN: {0}".format(str(self.expr))
    
    def execute(self):
        return self.expr.execute()
    
class PrimCmd(Node):
    def __init__(self, ):
        super()

    def __str__(self):
        return "\t<PrimCmd>"


class PrimCmdBlock(Node):
    def __init__(self, primcmd : PrimCmd, cmd : CmdNode):
        super()
        self.primcmd = primcmd
        self.cmd = cmd

    def __str__(self):
        return "{0} \n{1}".format(str(self.primcmd), str(self.cmd))

    def execute(self):
        self.primcmd.execute()
        self.cmd.execute()


