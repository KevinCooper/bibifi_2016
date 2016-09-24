# Yacc example

import ply.yacc as yacc

# Get the token map from the lexer.  This is required.
from langlex import tokens
from langlex import MyLexer
start = 'prog'

def p_prog(p):
    'prog : AS PRINCIPAL ID PASSWORD USER DO cmd END'
    pass

def p_cmd(p):
    '''cmd : EXIT
           | RETURN expr
           | primcmd cmd
    '''
    pass

def p_expr(p):
    '''expr : value 
            | LBRACK RBRACK
            | LBRACE fieldvals RBRACE 
    '''
    pass

def p_fieldvals(p):
    ''' fieldvals : ID EQUAL value
                  | ID EQUAL value COMMA fieldvals
    '''
    pass

def p_value(p):
    ''' value : ID
              | ID PERIOD ID
              | USER
    '''
    pass

def p_primcmd(p):
    ''' primcmd : CREATE PRINCIPAL ID USER
                | CHANGE PASSWORD ID USER
                | SET ID EQUAL expr
                | APPEND TO ID WITH expr
                | LOCAL ID EQUAL expr
                | FOREACH ID IN ID REPLACEWITH expr
                | SET DELEGATION ID ID right ARROW ID
                | DELETE DELEGATION ID ID right ARROW ID
                | DEFAULT DELEGATOR EQUAL ID
    '''
    pass

def p_right(p):
    ''' right : READ
              | WRITE
              | APPEND
              | DELEGATE
    '''
    pass
    
# Error rule for syntax errors
def p_error(p):
    #Error is None, which means EOF
    if not p:
        print("SYNTAX ERROR AT EOF")
    else:
        print("Syntax error in input!")
        print(p)

class LanguageParser(object):
    def __init__(self, lexer=None):
        if lexer is None:
            lexer = MyLexer()
        self.lexer = lexer
        self.parser = yacc.yacc(start="prog")

    def parse(self, code):
        self.lexer.input(code)
        result = self.parser.parse(lexer = self.lexer)
        #return ast.Module(None, result)
        return result


#my_parser = yacc.yacc()


if __name__=="__main__":
    my_parser = LanguageParser()
    # Build the parser
    with open("sample.code", "r") as f:
        result = my_parser.parse(f.read())
        print(result)