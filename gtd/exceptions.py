class GTDException(Exception):
    def __init__(self, errno):
        self.errno = errno
