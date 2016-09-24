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
        return "<ProgNode> User: {0}. Pass: {1}. CmdNode: \n{2}".format(self.user, self.password, str(self.cmd))

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

class ExprNode(Node):
    def __init__(self):
        super()
    def __str__(self):
        return ""

class ReturnNode(CmdNode):
    def __init__(self, expr: ExprNode):
        super()
        self.expr = expr
    def __str__(self):
        return "\t<CmdNode> RETURN: {0}".format(str(self.expr))
    
    def execute(self):
        return self.expr.execute()
    

class PrimCmd(Node):
    def __init__(self):
        super()
    def __str__(self):
        return "\t<PrimCmd>"

