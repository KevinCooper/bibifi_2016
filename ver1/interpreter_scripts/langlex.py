import ply.lex as lex

reserved = {
   'all' : 'ALL',
   'append' : 'APPEND',
   'as' : 'AS',
   'change' : 'CHANGE',
   'create' : 'CREATE',
   'default' : 'DEFAULT',
   'delegate' : 'DELEGATE',
   'delegation' : 'DELEGATION',
   'delegator' : 'DELEGATOR',
   'delete' : 'DELETE',
   'do' : 'DO',
   'exit' : 'EXIT',
   'foreach' : 'FOREACH',
   'in' : 'IN',
   'local' : 'LOCAL',
   'password' : 'PASSWORD',
   'principal' : 'PRINCIPAL',
   'read' : 'READ',
   'replacewith' : 'REPLACEWITH',
   'return' : 'RETURN',
   'set' : 'SET',
   'to' : 'TO',
   'write' : 'WRITE',
   'with'  : 'WITH',
}

# List of token names.   This is always required
tokens = (
   'LBRACK',
   'RBRACK',
   'ARROW',
   'EQUAL',
   'USER',
   'ID',
   'COMMENT',
   'LBRACE',
   'RBRACE',
   'COMMA',
   'PERIOD',
   'END'
)

tokens = list(tokens) + list(reserved.values())

# Regular expression rules for simple tokens
t_LBRACK  = r'\['
t_RBRACK  = r'\]'
t_LBRACE  = r'{'
t_RBRACE  = r'}'
t_ARROW   = r'->'
t_EQUAL   = r'='
t_COMMA   = r','
t_PERIOD  = r'\.'
t_END     = r'\*\*\*'

def t_ID(t):
    r'[A-Za-z][A-Za-z0-9_]*'
    t.type = reserved.get(t.value,'ID')
    return t

def t_USER(t):
    r'\"[A-Za-z0-9_ ,;\.?!-]*\"'
    t.type = reserved.get(t.value,'USER')
    return t

def t_COMMENT(t):
    r'//[A-Za-z0-9_ ,;\\.?\-!]*'
    #TODO: Ensure matches all comment cases
    pass
    # No return value. Token discarded

# Define a rule so we can track line numbers
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# A string containing ignored characters (spaces and tabs)
t_ignore  = ' \t'

# Error handling rule
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

# Build the lexer
lexer = lex.lex()

class MyLexer(object):
    def __init__(self, debug=0, optimize=1, lextab='lextab', reflags=0, outputdir="/tmp/"):
        self.lexer = lex.lex(debug=debug, optimize=optimize, lextab=lextab, reflags=reflags, outputdir=outputdir)
        self.token_stream = None
    def input(self, s):
        self.lexer.paren_count = 0
        self.lexer.input(s)
        self.token_stream = self.lexer
    def token(self):
        try:
            return self.token_stream.next()
        except StopIteration:
            return None


if __name__=='__main__':
    # Test it out
    data = '''
    as principal admin password "admin" do
    create principal alice "alices_password"
    set msg = "Hi Alice. Good luck in Build-it, Break-it, Fix-it!"
    set delegation msg admin read -> alice
    return "success"
    ***
    '''


    # Give the lexer some input
    lexer.input(data)

    # Tokenize
    while True:
        tok = lexer.token()
        if not tok: 
            break      # No more input
        print(tok)