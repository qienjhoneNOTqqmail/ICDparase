import xlrd
import re
import sys
import os
from bunch import Bunch
from Cheetah.Template import Template
import iomGenCommonV2

import pdb

def excepthook(ex_cls, ex, tb):
    pdb.post_mortem(tb)
#sys.excepthook = excepthook

class CvtCollector():
    ICD2ADS_DATATYPE = {
        'INT':    ('int32',     4),
        'UINT':   ('uint32',    4),
        'FLOAT':  ('real32',    4),
        'BOOL':   ('int32',     4),
        'COD':    ('int32',     4),
        'BYTES':  ('byte',      1),
        'STRING': ('string',    1),
        'BNR':    ('real32',    4),
        'UBNR':   ('real32',    4),
        'BCD':    ('real32',    4),
        'UBCD':   ('real32',    4),
    }    


    def __init__(self, cvtname, devmode=False):
        self.cvtname      = cvtname
        self.devmode      = devmode
        self.cvtpoints    = {}

    def newpoint(self, name="", datatype=None, datasize=1, elements=1, varlength=0, aliases=[], defaultvalue=""):
        return Bunch(name=name, datatype=datatype, datasize=datasize, elements=elements, varlength=varlength, aliases=aliases, defaultvalue=defaultvalue)
    
    
    def add_a664_msg(self, message):
        name = message.fullname
        #alias = "apexport_a664_"+str(message.portId)
        alias = str(message.portName)
        if("out" in message.direction):
            alias = str(message.lruName) + "." + str(message.portName)
        attribs = self.newpoint(name=name, datatype="byte", elements=message.msgLength, aliases=[alias])
        self.cvtpoints[name] = attribs
        return self.cvtname + '::' + name
        
    def add_a664_signal(self, param):
        message = param.msgRef
        
        aliases = []
        if param.paramName:
            aliases.append(message.lruName + '.' + param.paramName)
        
        if isinstance(param, iomGenCommonV2.InputSignal):
            name = message.fullname + '.' + param.dsName + '.' + param.sigName
        elif isinstance(param, iomGenCommonV2.OutputSignal):
            name = message.fullname + '.' + param.DpName
        else:
            pdb.set_trace()
            
        if self.devmode :                
            if (name.find("SSM") is not -1):
                name += "_"+str(param.sigDsOffset)
                print name
            if (name.find("Local_Channel_in_Control") is not -1):
                #rely on naming convention, there is probably a better for that.
                defaultvalue = "1"
            elif isinstance(param, iomGenCommonV2.InputSignal) and param.sselA429SSM_BNR() and (name.find("SSM") is not -1):
                if self.cvtpoints.has_key(name) and self.cvtpoints[name]["defaultvalue"] != "":
                    defaultvalue = self.cvtpoints[name]["defaultvalue"]
                else:
                    defaultvalue = "3"
            else:
                if self.cvtpoints.has_key(name) and self.cvtpoints[name]["defaultvalue"] != "":
                    defaultvalue = self.cvtpoints[name]["defaultvalue"]
                else:
                    defaultvalue = ""
        else:
            defaultvalue = ""
        dtype, dsize = self.ICD2ADS_DATATYPE[param.sigType]
        attribs = self.newpoint(name=name, datatype=dtype, datasize=dsize, aliases=aliases, defaultvalue=defaultvalue)
        if param.sigType == "BYTES" or param.sigType == "STRING":
            attribs.elements = param.sigSize / 8
            attribs.varlength = 1
        self.cvtpoints[name] = attribs 
        return self.cvtname + '::' + name

    def add_a664_msg_control(self, message, function):
        if self.devmode:
            defaultvalue = "1"
        else:
            defaultvalue = ""
        name = message.fullname + ".__%s__" % function
        attribs = self.newpoint(name=name, datatype="int32", datasize=4, aliases=[], defaultvalue=defaultvalue)
        self.cvtpoints[name] = attribs
        return self.cvtname + '::' + name

    def add_a664_fsb(self, param):
        message = param.msgRef
        name = message.fullname + "." + param.dsName + '__fsb'
        if isinstance(param, iomGenCommonV2.InputSignal):
            aliases = [message.fullname + '.' + param.sigName + '.__fsb__']
        elif isinstance(param, iomGenCommonV2.OutputSignal):
            aliases = [message.fullname + '.' + param.DpName + '.__fsb__']
        if param.paramName is not None:
            aliases.append(message.lruName + '.' + param.paramName + '.__fsb__')

        # now create a new entry or just add the aliases to an existing one
        attribs = self.cvtpoints.get(name)
        if attribs is None:
            if self.devmode:
                defaultvalue = "3"
            else:
                defaultvalue = ""
            attribs = self.newpoint(name=name, datatype="int8", datasize=1, aliases=aliases, defaultvalue=defaultvalue)
            self.cvtpoints[name] = attribs
            return self.cvtname + '::' + name
        else:
            attribs.aliases.extend(aliases)
            return None # caller will not create an iomap for this, it already exists


    def add_a664_a429ssm(self, param):
        message = param.msgRef
        if isinstance(param, iomGenCommonV2.InputSignal):
            a429wordname = param.pubref.split('.')[-2]
            name = message.fullname + "." + param.dsName + '.' + a429wordname + '__ssm'
            aliases = [message.fullname + '.' + param.sigName + '.__ssm__']
        elif isinstance(param, iomGenCommonV2.OutputSignal):
            a429wordname = param.DpName.split('.')[0]
            name = message.fullname + "." + param.dsName + '.' + a429wordname + '__ssm'
            aliases = [message.fullname + '.' + param.DpName + '.__ssm__']
        if param.paramName is not None:
            aliases.append(message.lruName + '.' + param.paramName + '.__ssm__')

        # now create a new entry or just add the aliases to an existing one
        attribs = self.cvtpoints.get(name)
        if attribs is None:
            if self.devmode and param.sselA429SSM_BNR():
                defaultvalue = "3"
            else:
                defaultvalue = ""
            attribs = self.newpoint(name=name, datatype="int8", datasize=1, aliases=aliases, defaultvalue=defaultvalue)
            self.cvtpoints[name] = attribs
            return self.cvtname + '::' + name
        else:
            attribs.aliases.extend(aliases)
            return None # caller will not create an iomap for this, it already exists
        
    def add_a825_signal(self, param):
        message = param.msgRef
        
        aliases = []
        if param.paramName:
            aliases.append(message.lruName + '.' + param.paramName)
        
        if isinstance(param, iomGenCommonV2.InputSignal):
            name = message.fullname + '.' + param.sigName
        elif isinstance(param, iomGenCommonV2.OutputSignal):
            name = message.fullname + '.' + param.DpName
        else:
            return None

        if self.devmode:
            defaultvalue = "1"
        else:
            defaultvalue = ""
        dtype, dsize = self.ICD2ADS_DATATYPE[param.sigType]
        attribs = self.newpoint(name=name, datatype=dtype, datasize=dsize, aliases=aliases)
        if param.sigType == "BYTES" or param.sigType == "STRING":
            attribs.elements = param.sigSize / 8
            attribs.varlength = 1
        self.cvtpoints[name] = attribs 
        return self.cvtname + '::' + name

    def add_a825_msg_control(self, message, function):
        name = message.fullname + ".__%s__" % function
        attribs = self.newpoint(name=name, datatype="int32", datasize=4, aliases=[])
        self.cvtpoints[name] = attribs
        return self.cvtname + '::' + name
    
def genAds2ConfigsAFDXbyLRU(inMap, outMap, outdir, outfn, mode="stim", device='AFDX-1', msgonly=False, devmode=False):
    templateDir = os.path.dirname(__file__)
    
    lrus = set()
    for msg in outMap.afdx.messages.values():
        if msg.lruName not in lrus:
            lrus.add(msg.lruName)
    for msg in inMap.afdx.messages.values():
        if msg.lruName not in lrus:
            lrus.add(msg.lruName)

    while len(lrus) > 0:
        lruName = lrus.pop()
        if mode == 'stim':
            outputModel = Bunch(afdx=inMap.afdx)
            inputModel  = Bunch(afdx=outMap.afdx)
        else:
            inputModel = Bunch(afdx=inMap.afdx)
            outputModel  = Bunch(afdx=outMap.afdx)
        
        cvts = CvtCollector(outfn,devmode)
    
        # generate IO Maps
        tmpl = Template(file= os.path.join(templateDir, "ads2genAFDX.tpl"), 
                    searchList=[{ 
                        "lruName"     : lruName,
                        "outputModel" : outputModel,
                        "inputModel"  : inputModel,
                        "cvts"        : cvts,
                        "device": device, 'mode': mode, 'msgonly': msgonly, 'devmode': devmode }])
    
        fn = os.path.join(outdir, '%s-%s.iom' % (outfn, lruName))
        open(fn, "w").write(tmpl.respond())
            
        # generate CVTs with points collected by the collector during generating IOM
        model = Bunch(cvtpoints=cvts.cvtpoints.values())
        tmpl = Template(file=os.path.join(templateDir, "ads2genCVT.tpl"), 
                        searchList=[{ "model": model}])
    
        fn = os.path.join(outdir, '%s-%s.cvt' % (outfn, lruName))
        open(fn, "w").write(tmpl.respond())

def genAds2ConfigsAFDX(inMap, outMap, outdir, outfn, mode="stim", device='AFDX-1', msgonly=False, devmode=False):
    templateDir = os.path.dirname(__file__)
    cvts = CvtCollector(outfn,devmode)
    
    # generate IO Maps
    if mode == 'stim':
            outputModel = Bunch(afdx=inMap.afdx)
            inputModel  = Bunch(afdx=outMap.afdx)
    else:
            inputModel = Bunch(afdx=inMap.afdx)
            outputModel  = Bunch(afdx=outMap.afdx)
    
    tmpl = Template(file= os.path.join(templateDir, "ads2genAFDX.tpl"), 
                searchList=[{ 
                    "lruName"     : None,
                    "outputModel" : outputModel,
                    "inputModel"  : inputModel,
                    "cvts"        : cvts,
                    "device": device, 'mode': mode, 'msgonly': msgonly, 'devmode':devmode}])

    fn = os.path.join(outdir, outfn + '.iom')
    open(fn, "w").write(tmpl.respond())
        
    # generate CVTs with points collected by the collector during generating IOM
    model = Bunch(cvtpoints=cvts.cvtpoints.values())
    tmpl = Template(file=os.path.join(templateDir, "ads2genCVT.tpl"), 
                    searchList=[{ "model": model}])

    fn = os.path.join(outdir, outfn + '.cvt')
    open(fn, "w").write(tmpl.respond())

def genAds2ConfigsCAN(inMap, outMap, outdir, outfn, mode="stim", device='CAN-1-1', msgonly=False, devmode=False):
    templateDir = os.path.dirname(__file__)
    cvts = CvtCollector(outfn,devmode)
    
    # generate IO Maps
    if mode == 'stim':
            outputModel = Bunch(can=inMap.can)
            inputModel  = Bunch(can=outMap.can)
    else:
            inputModel = Bunch(can=inMap.can)
            outputModel  = Bunch(can=outMap.can)
            
    tmpl = Template(file= os.path.join(templateDir, "ads2genCAN.tpl"), 
                searchList=[{ 
                    "outputModel" : outputModel,
                    "inputModel"  : inputModel,
                    "cvts"        : cvts,
                    "device": device, 'mode': mode, 'msgonly': msgonly }])

    fn = os.path.join(outdir, outfn + '-%s.iom' % device)
    open(fn, "w").write(tmpl.respond())
        
    # generate CVTs with points collected by the collector during generating IOM
    model = Bunch(cvtpoints=cvts.cvtpoints.values())
    tmpl = Template(file=os.path.join(templateDir, "ads2genCVT.tpl"), 
                    searchList=[{ "model": model}])

    fn = os.path.join(outdir, outfn + '.cvt')
    open(fn, "w").write(tmpl.respond())

def usage():
    sys.stderr.write("Usage: iomGenAds2Data inputfile outputdir outfile (sim|stim) (raw|params|signals) (SDIB|SSDL|MDVS|SWTESTS)")
    
def main(args):
    if len(args) < 6:
        usage()
        return -1

    inputfile  = args[0]        # input excel ICD (After joindd)
    outdir     = args[1]        # prefix of output file - .cvt, .iom, etc. will be appended
    outfile    = args[2]        # prefix of output file - .cvt, .iom, etc. will be appended
    simmode    = args[3]        # sim / stim 
    msgmode    = args[4]        # raw / params / signals
    target     = args[5]        #
    if len(args) > 6:           # compatibility with old makefiles
        splitiom   = args[6]    #
    else:
        splitiom   = "False"

    simmode = simmode.lower()
    if simmode not in ("sim", "stim"):
        usage()
        return -1
    
    msgmode = msgmode.lower()
    if msgmode not in ("raw", "signals", "params"):
        usage()
        return -1
        
    if msgmode == "raw":
        msgonly  = True
        noparams = True
    elif msgmode == "signals":
        msgonly  = False
        noparams = True
    else:
        msgonly  = False
        noparams = False

    if target == "SWTESTS":
        devmode = True
    else:
        devmode = False
        
    # read Excel File 
    inputMappings  = iomGenCommonV2.MapReader(inputfile, dd=None, msgonly=msgonly, noparams=True, direction='input')
    outputMappings = iomGenCommonV2.MapReader(inputfile, dd=None, msgonly=msgonly, noparams=True, direction='output')
    
    # Generate Test System (SDIB) configuration (CVT and IOM)
    if splitiom is not "True":
        genAds2ConfigsAFDX(inputMappings, outputMappings, outdir, '%s-afdx' % outfile, mode=simmode, device="AFDX-1", msgonly=msgonly, devmode=devmode )    
    else:
        genAds2ConfigsAFDXbyLRU(inputMappings, outputMappings, outdir, '%s-afdx' % outfile, mode=simmode, device="AFDX-1", msgonly=msgonly, devmode=devmode)
    genAds2ConfigsCAN(inputMappings, outputMappings, outdir, '%s-can' % outfile, mode=simmode, device="can-1-1", msgonly=msgonly)
    genAds2ConfigsCAN(inputMappings, outputMappings, outdir, '%s-can' % outfile, mode=simmode, device="can-1-2", msgonly=msgonly)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
