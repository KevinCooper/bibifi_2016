# Yacc example
import ply.yacc as yacc

# Get the token map from the lexer.  This is required.
try:
    from .langlex import tokens
    from .langlex import MyLexer
    from .ast import ProgNode, CreateCmd, CmdNode, PrimCmdBlock, PrimCmd, LocalCmd
    from .ast import ExitNode, ReturnNode, ExprNode, FieldValue, StringNode, IDNode, RecordNode
    from .ast import ChangeCmd, SetCmd, AppendCmd, SetDel, DelDel, DefaultCmd, ForEachCmd
    from .errors import ParseError
except Exception as e:
    from interpreter_scripts.langlex import tokens
    from interpreter_scripts.langlex import MyLexer
    from interpreter_scripts.ast import ProgNode, CreateCmd, CmdNode, PrimCmdBlock, PrimCmd, LocalCmd
    from interpreter_scripts.ast import ExitNode, ReturnNode, ExprNode, FieldValue, StringNode, IDNode, RecordNode
    from interpreter_scripts.ast import ChangeCmd, SetCmd, AppendCmd, SetDel, DelDel, DefaultCmd, ForEachCmd
    from interpreter_scripts.errors import ParseError
start = 'prog'

def p_prog(p):
    'prog : AS PRINCIPAL ID PASSWORD USER DO cmd END'
    # [0]   [1] [2]      [3] [4]     [5]  [6] [7] [8]
    p[0] = ProgNode(p[3], p[5], p[7])

def p_cmd(p):
    '''cmd : EXIT
           | RETURN expr
           | primcmd cmd
    '''
    if("exit" in str(p[1])):
        p[0] = ExitNode()
    elif("return" in str(p[1])):
        p[0] = ReturnNode(p[2])
    elif(issubclass(type(p[1]),PrimCmd)):
        p[0] = PrimCmdBlock(p[1], p[2])
    else:
        print(p[0], p[1], p[2])
        raise ValueError

def p_expr(p):
    '''expr : value 
            | LBRACK RBRACK
            | LBRACE fieldvals RBRACE 
    '''
    if(len(p) == 2):
        p[0] = ExprNode( p[1] )
    elif(len(p) == 3):
        p[0] = ExprNode( list() )
    elif(len(p) > 3):
        p[0] = ExprNode( p[2] )
    else:
        raise Exception
    

def p_fieldvals(p):
    ''' fieldvals : ID EQUAL value
                  | ID EQUAL value COMMA fieldvals
    '''
    if(len(p) == 4):
        p[0] = FieldValue(p[1], p[3], None)
    elif(len(p) > 4):
        p[0] = FieldValue(p[1], p[3], p[5])

def p_value(p):
    ''' value : ID
              | ID PERIOD ID
              | USER
    '''
    if(len(p) == 2 and not str(p[1]).startswith('"')):
        p[0] = IDNode(str(p[1]))
    elif(len(p) == 2 and str(p[1]).startswith('"')):
        p[0] = StringNode(str(p[1]))
    elif(len(p) == 4):
        p[0] = RecordNode(IDNode(str(p[1])), IDNode(str(p[3])))
    else:
        raise ValueError

def p_primcmd(p):
    ''' primcmd : CREATE PRINCIPAL ID USER
                | CHANGE PASSWORD ID USER
                | SET ID EQUAL expr
                | APPEND TO ID WITH expr
                | LOCAL ID EQUAL expr
                | FOREACH ID IN ID REPLACEWITH expr
                | SET DELEGATION tgt ID right ARROW ID
                | DELETE DELEGATION tgt ID right ARROW ID
                | DEFAULT DELEGATOR EQUAL ID
    '''
    if("create" in str(p[1])):
        p[0] = CreateCmd(str(p[3]), str(p[4]))
    elif("change" in str(p[1])):
        p[0] = ChangeCmd(str(p[3]), str(p[4]))
    elif("set" in str(p[1]) and "=" in str(p[3])):
        p[0] = SetCmd(str(p[2]), p[4])
    elif("append" in str(p[1])):
        p[0] = AppendCmd(str(p[3]), p[5])
    elif("local" in str(p[1])):
        p[0] = LocalCmd(str(p[2]), p[4])
    elif("foreach" in str(p[1])):
        p[0] = ForEachCmd(str(p[2]), str(p[4]), p[6])
    elif("set" in str(p[1])):
        p[0] = SetDel(str(p[3]), str(p[4]), p[5], str(p[7]))
    elif("delete" in str(p[1])):
        p[0] = DelDel(str(p[3]), str(p[4]), p[5], str(p[7]))
    elif("default" in str(p[1])):
        p[0] = DefaultCmd(str(p[4]))
    else:
        raise ValueError
    

def p_right(p):
    ''' right : READ
              | WRITE
              | APPEND
              | DELEGATE
    '''
    p[0] = str(p[1]).lower()

def p_tgt(p):
    ''' tgt : ALL
            | ID
    '''
    p[0] = str(p[1]).lower()
    
# Error rule for syntax errors
def p_error(p):
    #Error is None, which means EOF
    if not p:
        print("SYNTAX ERROR AT EOF")
    else:
        print("Syntax error in input!")
        print(p)
    raise ParseError(str(p), " found an invalid token.")

class LanguageParser(object):
    def __init__(self, lexer=None):
        if lexer is None:
            lexer = MyLexer()
        self.lexer = lexer
        self.parser = yacc.yacc(start="prog", optimize=False, debug=None, outputdir="/tmp/")

    def parse(self, code):
        self.lexer.input(code)
        result = self.parser.parse(lexer = self.lexer)
        #return ast.Module(None, result)
        return result


#my_parser = yacc.yacc()


if __name__=="__main__":
    my_parser = LanguageParser()
    # Build the parser
    with open("sample2.code", "r") as f:
        result = my_parser.parse(f.read())
        print(result)