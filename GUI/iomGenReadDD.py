import sys
from lxml import etree

class Parameter():
    def __init__(self, xp, baseoffset=0):
        self.name      = xp.attrib["name"]
        self.key       = self.name.split('.', 1)[-1]
        self.type      = xp.attrib["type"].strip().upper()
        self.offset    = int(xp.attrib["offset"]) + baseoffset
        self.elements  = int(xp.attrib["elements"])
        self.size      = int(xp.attrib["size"])
            
        if self.type == "REAL":
            self.type = "FLOAT"
        if not self.type in ("FLOAT", "INT", "BOOL", "ENUM", "CHAR", "COUNT"):
            raise Exception, "Unsupported type in DD: %s (%s)" % (self.type, self.name)
        if (self.elements > 1 and self.type != "CHAR"):
            raise Exception, "Unsupported type in DD: array of %s (%s)" % (self.type, self.name)

            
def ddread(filenames):

    params = {}
    
    for filename in filenames:
        xmltree = etree.parse(open(filename, "r"))
        paramlist = xmltree.getroot()

        s = paramlist.attrib.get("offset")
        if s:
            baseoffset = int(s)
        else:
            baseoffset = 0
            
        for xmlparam in paramlist.iterfind("parameter"):
            try:
                param = Parameter(xmlparam, baseoffset=baseoffset)
            except Exception, msg:
                logerr(filename, msg)
                continue
        
            if param.key in params:
                logerr(filename, "Duplicate parameter in DDMap: %s" % param.key)
            else:
                params[param.key] = param
        
            # also add the parameter under its full name, some DD-RP maps use full name
            if param.name != param.key:
                if param.name in params:
                    logerr(filename, "Duplicate parameter in DDMap: %s" % param.name)
                else:
                    params[param.name] = param
                    
    return params
    
def logerr(filename, msg):
    sys.stdout.write("File %s: %s\n" % (filename, msg))