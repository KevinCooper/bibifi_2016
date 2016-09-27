class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class SecurityError(Error):
    """Exception raised for a security error.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

class FailError(Error):
    """Exception raised for a security error.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

class ParseError(Error):
    """Exception raised for a security error.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

class ExitError(Error):
    """Exception raised for a security error.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """
    def __init__(self):
        pass