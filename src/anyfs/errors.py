class NotAFileException(Exception):
    pass

def raise_enoent(self, path):
    raise FileNotFoundError(path, None)

def raise_eacces(self, path):
    raise PermissionError(f"Permission denied: '{path}'")

def raise_eexist(self, path):
    raise FileExistsError(f"File exists: '{path}'")

def raise_eisdir(self, path):
    raise IsADirectoryError(f"Is a directory: '{path}'")

def raise_enotdir(self, path):
    raise NotADirectoryError(f"Not a directory: '{path}'")

def raise_enotfile(self, path):
    raise NotAFileException(f"Not a file: '{path}'")

def raise_ewouldblock(self):
    raise BlockingIOError("Operation would block")

def raise_echild(self):
    raise ChildProcessError("No child processes")

def raise_econnaborted(self):
    raise ConnectionAbortedError("Connection aborted")

def raise_econnrefused(self, address):
    raise ConnectionRefusedError(f"Connection refused: '{address}'")

def raise_econnreset(self):
    raise ConnectionResetError("Connection reset by peer")

def raise_eintr(self):
    raise InterruptedError("Interrupted function call")

def raise_epipe(self):
    raise BrokenPipeError("Broken pipe")

def raise_etimedout(self):
    raise TimeoutError("Operation timed out")

def raise_enotsup(self, path, operation):
    raise NotImplementedError(f"Operation '{operation}' not supported: '{path}'")
