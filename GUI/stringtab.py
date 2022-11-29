#
# String table gathers all strings (port names, parameter names)
# into stringtable appended to the binary configuration
#

class StringTable():
    def __init__(self):
        self._buffer = ""
        self._offset = 0

    def append(self, s):
        start = self._offset
        self._buffer += s + '\0'
        self._offset += len(s) + 1
        return start
    
    def buffer(self):
        return self._buffer
    
    def pad(self, padding=4):
        while self._offset % padding != 0:
            self._buffer += '\0'
            self._offset += 1
            
    def len(self):
        return len(self._buffer)
    
    def reset(self):
        self._buffer = ""
        self._offset = 0
        
stringtable = StringTable()           
