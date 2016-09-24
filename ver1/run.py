import ply.lex as lex

reserved = {
   'all' : 'IF',
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
}

# List of token names.   This is always required
tokens = (
   'NUMBER',
   'LBRACK',
   'RBRACK',
   'ARROW',
   'EQUALS',
   'USER',
   'ID',
   'COMMENT'
)

tokens = list(tokens) + list(reserved.values())

# Regular expression rules for simple tokens
t_LBRACK  = r'\['
t_RBRACK  = r'\]'
t_ARROW   = r'->'
t_EQUALS  = r'='

def t_ID(t):
    r'[A-Za-z][A-Za-z0-9_]*'
    t.type = reserved.get(t.value,'ID')
    return t

def t_USER(t):
    r'\"[A-Za-z0-9_ ,;\.?!-]*\"'
    t.type = reserved.get(t.value,'ID')
    return t

def t_COMMENT(t):
    r'[\/][\/][A-Za-z0-9_ ,;\\.?\-!]*$'
    pass
    # No return value. Token discarded
# A regular expression rule with some action code
def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)    
    return t

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

# Test it out
data = '''
as principal admin password "admin" do
   create principal alice "alices_password"
   set msg = "Hi Alice. Good luck in Build-it, Break-it, Fix-it!"
   set delegation msg admin read -> alice
   return "success"
'''

# Give the lexer some input
lexer.input(data)

# Tokenize
while True:
    tok = lexer.token()
    if not tok: 
        break      # No more input
    print(tok)