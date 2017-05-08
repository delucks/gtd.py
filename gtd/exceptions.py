class GTDException(Exception):
    '''single parameter indicates exit code for the interpreter, because
    this exception typically results in a return of control to the terminal'''
    def __init__(self, errno):
        self.errno = errno
