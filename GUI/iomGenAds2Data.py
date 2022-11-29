import xlrd
import re
import sys
import os
from bunch import Bunch
from Cheetah.Template import Template
import iomGenCommon
from ads2GenDeviceMapping import ads2GenDevice

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

    def newpoint(self, name="", datatype=None, datasize=1, elements=1, varlength=0, aliases=[], defaultvalue="", channelmode="SAMPLING"):
        return Bunch(name=name, datatype=datatype, datasize=datasize, elements=elements, varlength=varlength, aliases=aliases, defaultvalue=defaultvalue, channelmode=channelmode)
     
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
        
        if isinstance(param, iomGenCommon.InputSignal):
            if param.sselA429SSM(): # nested 429 label
                a429wordname = param.pubref.split('.')[-2]
                name = message.fullname + "." + param.dsName + '.' + a429wordname + '.' + param.sigName
            else:
                name = message.fullname + '.' + param.dsName + '.' + param.sigName
        elif isinstance(param, iomGenCommon.OutputSignal):
            name = message.fullname + '.' + param.dsName + '.' + param.DpName
        else:
            pdb.set_trace()

        if isinstance(param, iomGenCommon.InputSignal):
            if("RGW" not in message.lruName): #special case
                alias = param.pubref
            else:
                alias = message.lruName + '.'+ param.pubref
            aliases.append(alias)
            aliases.append(alias  + '._.' +  param.rpName)
        elif isinstance(param, iomGenCommon.OutputSignal):
            aliases.append(message.fullname + '.' + param.dsName + '.' + param.DpName)
        if param.paramName: ## only applicable with DD
            aliases.append(message.fullname + '.' + param.paramName)
           
            
        if self.devmode :                
            if (name.find("SSM") is not -1):
                name += "_"+str(param.sigDsOffset)
                print name
            if (name.find("Local_Channel_in_Control") is not -1):
                #rely on naming convention, there is probably a better for that.
                defaultvalue = "1"
            elif isinstance(param, iomGenCommon.InputSignal) and param.sselA429SSM_BNR() and (name.find("SSM") is not -1):
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
        attribs = self.newpoint(name=name, datatype="int32", datasize=4, aliases=[name], defaultvalue=defaultvalue)
        self.cvtpoints[name] = attribs
        return self.cvtname + '::' + name

    def add_a664_fsb(self, param): #assuming non FSB param
        message = param.msgRef
        name = message.fullname + "." + param.dsName + '__fsb'
        aliases = []
        aliases.append(message.fullname + "." + param.dsName + ".FSB")
        if isinstance(param, iomGenCommon.InputSignal):
            if ("RGW" not in message.lruName):
                aliases.append(param.pubref + '.__fsb__')
            else:
                aliases.append(message.lruName + "." + param.pubref + '.__fsb__')
            #aliases.append(message.fullname + "." + param.dsName + '.__fsb__' + '._at_.' + param.rpName + '.__fsb__')
        elif isinstance(param, iomGenCommon.OutputSignal):
            aliases.append(message.fullname + '.'  + param.dsName + "." + param.DpName + '.__fsb__')
        if param.paramName is not None:
            aliases.append(message.fullname + '.' + param.paramName + '.__fsb__')

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
            attribs.aliases = list(set(aliases + attribs.aliases))
            return None # caller will not create an iomap for this, it already exists


    def add_a664_a429ssm(self, param): #assuming NON-SSM param
        message = param.msgRef
        if isinstance(param, iomGenCommon.InputSignal):
            a429wordname = param.pubref.split('.')[-2]
            name = message.fullname + "." + param.dsName + '.' + a429wordname + '__ssm'
            aliases = [name.replace('__ssm', '.SSM')]
            if ("RGW" not in message.lruName):
                aliases.append(param.pubref+'.__ssm__')
                #aliases.append(".".join(param.pubref.split('.')[:-1]) + ".SSM")
            else:
                aliases.append(message.lruName + "." + param.pubref+'.__ssm__')
                aliases.append(message.lruName + "." + ".".join(param.pubref.split('.')[:-1]) + ".SSM")
            #aliases.append(name + '._at_.' + param.rpName+ '.__ssm__')
        elif isinstance(param, iomGenCommon.OutputSignal):
            a429wordname = param.DpName.split('.')[0]
            name = message.fullname + "." + param.dsName + '.' + a429wordname + '__ssm'
            aliases = [message.fullname + '.' + param.dsName + '.' + param.DpName + '.__ssm__']
            aliases.append(".".join(param.pubref.split('.')[:-1]) + ".SSM")
        if param.paramName is not None:
            aliases.append(message.fullname + '.' + param.paramName + '.__ssm__')

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
            attribs.aliases = list(set(aliases + attribs.aliases))
            return None # caller will not create an iomap for this, it already exists
        
    def add_a825_signal(self, param):
        message = param.msgRef
        
        aliases = []
        if param.paramName:
            aliases.append(message.lruName + '.' + param.paramName)

        if isinstance(param, iomGenCommon.InputSignal):
            if("RGW" not in message.lruName): #special case
                alias = param.pubref
            else:
                alias = message.lruName + '.'+ param.pubref
            name = alias
            aliases.append(alias)
            aliases.append(alias  + '._.' +  param.rpName)
        elif isinstance(param, iomGenCommon.OutputSignal):
            name = message.fullname + '.' + param.DpName
            aliases.append(message.fullname + '.' + param.DpName)
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
    def add_a825_msg(self, message):
        name = message.fullname
        alias = message.fullname
        attribs = self.newpoint(name=name, datatype="byte", elements=message.msgLength, varlength=1, aliases=[alias], channelmode="MUXFIFO")
        self.cvtpoints[name] = attribs
        return self.cvtname + '::' + name

    def add_a825_msg_control(self, message, function ):
        name = message.fullname + ".__%s__" % function
        attribs = self.newpoint(name=name, datatype="int32", datasize=4, aliases=[name])
        self.cvtpoints[name] = attribs
        return self.cvtname + '::' + name
    
    def add_a429_signal(self, param):
            message = param.msgRef
            name = message.fullname + '.' + param.sigName
            aliases = []
            if param.paramName:
                aliases.append(message.lruName + '.' + param.paramName)
        
            if isinstance(param, iomGenCommon.InputSignal):
                if("RGW" not in message.lruName): #special case
                    alias = param.pubref
                else:
                    alias = message.lruName + '.'+ param.pubref
                aliases.append(alias)
                aliases.append(alias  + '._.' +  param.rpName)
            elif isinstance(param, iomGenCommon.OutputSignal):
               
                aliases.append(message.fullname + '.' + param.sigName)
            else:
                return None

            if message.lruName.endswith('1') or message.lruName.endswith('L') and name.endswith('SDI'):
                 defaultvalue = "1"
            elif message.lruName.endswith('2') or message.lruName.endswith('R') and name.endswith('SDI'):
                 defaultvalue = "2"
            elif message.lruName.endswith('3') or message.lruName.endswith('R') and name.endswith('SDI'):
                 defaultvalue = "3"
            else:
                 defaultvalue = "0"

            if name.endswith('SSM'):
                defaultvalue = "1"


            dtype, dsize = self.ICD2ADS_DATATYPE[param.sigType]
            attribs = self.newpoint(name=name, datatype=dtype, datasize=dsize, aliases=aliases,  defaultvalue=defaultvalue)
            if param.sigType == "BYTES" or param.sigType == "STRING":
                attribs.elements = param.sigSize / 8
                attribs.varlength = 1
            self.cvtpoints[name] = attribs 
            return self.cvtname + '::' + name

    def add_a429_msg_control(self, label, function):
        name = label.fullname + ".__%s__" % function
        attribs = self.newpoint(name=name, datatype="int32", datasize=4, aliases=[name])
        self.cvtpoints[name] = attribs
        return self.cvtname + '::' + name
def genAds2ConfigsAFDX(inMap, outMap, outdir, outfn, mode="stim", device=None, msgonly=False, devmode=False, split=False):
    templateDir = os.path.dirname(__file__)
    
    lrus = set()
    if(split):
        for msg in outMap.afdx.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
        for msg in inMap.afdx.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
    else:
        lrus.add(None)

    while len(lrus) > 0:
        lruName = lrus.pop()

        if(lruName is not None):
            outfn_ = "_".join([lruName, outfn])
        else:
            outfn_ =outfn

        if mode == 'stim':
            outputModel = Bunch(afdx=inMap.afdx)
            inputModel  = Bunch(afdx=outMap.afdx)
        else:
            inputModel = Bunch(afdx=inMap.afdx)
            outputModel  = Bunch(afdx=outMap.afdx)
        
        cvts = CvtCollector(outfn_,devmode)
        if(device is not None):
            genCfg = ads2GenDevice(None, device, None)
            genCfg.setIcdMap([inputModel, outputModel])
            device_ = genCfg.getAdsDevice(lruName+".afdx")
        else:
            device_ = "AFDX-1"
        # generate IO Maps
        tmpl = Template(file= os.path.join(templateDir, "ads2genAFDX.tpl"), 
                    searchList=[{ 
                        "lruName"     : lruName,
                        "outputModel" : outputModel,
                        "inputModel"  : inputModel,
                        "cvts"        : cvts,
                        "device": device_, 'mode': mode, 'msgonly': msgonly, 'devmode': devmode }])
    
        fn = os.path.join(outdir, '%s.iom' % (outfn_))
        open(fn, "w").write(tmpl.respond())
            
        # generate CVTs with points collected by the collector during generating IOM
        model = Bunch(cvtpoints=cvts.cvtpoints.values())
        tmpl = Template(file=os.path.join(templateDir, "ads2genCVT.tpl"), 
                        searchList=[{ "model": model}])
    
        fn = os.path.join(outdir, '%s.cvt' % (outfn_))
        open(fn, "w").write(tmpl.respond())

def genAds2ConfigsCAN(inMap, outMap, outdir, outfn, mode="stim", device=None, msgonly=False, devmode=False, split=False):
    templateDir = os.path.dirname(__file__)

    lrus = set()
    if(split):
        for msg in outMap.can.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
        for msg in inMap.can.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
    else:
        lrus.add(None)

    while len(lrus) > 0:
        lruName = lrus.pop()

        if(lruName is not None):
            outfn_ = "_".join([lruName, outfn])
        else:
            outfn_ =outfn

        cvts = CvtCollector(outfn_, devmode)
    
        # generate IO Maps
        if mode == 'stim':
                outputModel = Bunch(can=inMap.can)
                inputModel  = Bunch(can=outMap.can)
        else:
                inputModel = Bunch(can=inMap.can)
                outputModel  = Bunch(can=outMap.can)

        if(device is not None):
            genCfg = ads2GenDevice(None, device, None)
            genCfg.setIcdMap([inputModel, outputModel])
            device_ = genCfg
        else:
            device_ = "CAN-1-1"
            
        tmpl = Template(file= os.path.join(templateDir, "ads2genCAN.tpl"), 
                    searchList=[{
                        "lruName"     : lruName, 
                        "outputModel" : outputModel,
                        "inputModel"  : inputModel,
                        "cvts"        : cvts,
                        "device": device_, 'mode': mode, 
                        'msgonly': msgonly }])

        fn = os.path.join(outdir,'%s.iom' % (outfn_))
        open(fn, "w").write(tmpl.respond())
        
        # generate CVTs with points collected by the collector during generating IOM
        model = Bunch(cvtpoints=cvts.cvtpoints.values())
        tmpl = Template(file=os.path.join(templateDir, "ads2genCVT.tpl"), 
                        searchList=[{ "model": model}])

        fn = os.path.join(outdir, outfn_ + '.cvt')
        open(fn, "w").write(tmpl.respond())

def genAds2ConfigsA429(inMap, outMap, outdir, outfn, mode="stim", device=None, msgonly=False, devmode=False, split=False):
    templateDir = os.path.dirname(__file__)

    lrus = set()
    if(split):
        for msg in outMap.a429.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
        for msg in inMap.a429.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
    else:
        lrus.add(None)


    while len(lrus) > 0:
        lruName = lrus.pop()

        if(lruName is not None):
            outfn_ = "_".join([lruName, outfn])
        else:
            outfn_ =outfn

        if not split:
            cvts = CvtCollector(outfn_,devmode)
        else:
            cvts = CvtCollector(outfn_,devmode)

        # generate IO Maps
        if mode == 'stim':
            outputModel = Bunch(a429=inMap.a429)
            inputModel  = Bunch(a429=outMap.a429)
        else:
            inputModel = Bunch(a429=inMap.a429)
            outputModel  = Bunch(a429=outMap.a429)

        if(device is not None):
            genCfg = ads2GenDevice(None, device, None)
            genCfg.setIcdMap([inputModel, outputModel])
            device_ = genCfg
        else:
            device_ = "A429-1"
            
        tmpl = Template(file= os.path.join(templateDir, "ads2genA429.tpl"), 
                    searchList=[{
                        "lruName"     : lruName, 
                        "outputModel" : outputModel,
                        "inputModel"  : inputModel,
                        "cvts"        : cvts,
                        "device": device_, 'mode': mode, 'msgonly': msgonly }])

        fn = os.path.join(outdir, '%s.iom' % (outfn_))
        open(fn, "w").write(tmpl.respond())
        
        # generate CVTs with points collected by the collector during generating IOM
        model = Bunch(cvtpoints=cvts.cvtpoints.values())
        tmpl = Template(file=os.path.join(templateDir, "ads2genCVT.tpl"), 
                        searchList=[{ "model": model}])

        fn = os.path.join(outdir, '%s.cvt' % (outfn_))
        open(fn, "w").write(tmpl.respond())

def genAds2ComponentCheckLru(inMsgs, outMsgs, Lru):
     for msg in inMsgs:
        if Lru in msg.lruName:
            return True
     for msg in outMsgs:
        if Lru in msg.lruName:
            return True
     return False

def genAds2Component(inMap, outMap, outdir, outfns, split=False):
     lrus = set()
     if(split):
        for msg in outMap.a429.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
        for msg in inMap.a429.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
        for msg in outMap.can.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
        for msg in inMap.can.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
        for msg in outMap.afdx.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
        for msg in inMap.afdx.messages.values():
            if msg.lruName not in lrus:
                lrus.add(msg.lruName)
     else:
        lrus.add(None)

     while len(lrus) > 0:
        lruName = lrus.pop()

        if(lruName is not None):
            outfn_ = lruName
        else:
            outfn_ = outfns
        
        cmp='''
        VERSION_CONTROL {FILE_NAME = "Id:$";REVISION = "$Revision: $";AUTHOR = "$Author: foo $"; DATE = "$Date:$";}
        CVTS {CVTLIST = {'''
        if genAds2ComponentCheckLru(outMap.afdx.messages.values(), inMap.afdx.messages.values(), outfn_) or (split==False):
            cmp += '''{CVT = "%s_afdx";}'''%(outfn_)
        if genAds2ComponentCheckLru(outMap.can.messages.values(), inMap.can.messages.values(), outfn_) or (split==False):
            cmp += '''{ CVT = "%s_can"; }'''%(outfn_)
        if genAds2ComponentCheckLru(outMap.a429.messages.values(), inMap.a429.messages.values(), outfn_) or (split==False):
            cmp += '''{ CVT = "%s_a429";}'''%(outfn_)
        cmp+= ''' }}'''
        cmp +='''IFREAL {LOADLIST = "";UNLOADLIST = "";IOMAPLIST = {'''
        if genAds2ComponentCheckLru(outMap.afdx.messages.values(), inMap.afdx.messages.values(), outfn_) or (split==False):
            cmp +='''{IOMAP = "%s_afdx";}'''%(outfn_)
        if genAds2ComponentCheckLru(outMap.can.messages.values(), inMap.can.messages.values(), outfn_) or (split==False):
            cmp +='''{ IOMAP = "%s_can"; }'''%(outfn_)
        if genAds2ComponentCheckLru(outMap.a429.messages.values(), inMap.a429.messages.values(), outfn_) or (split==False):
            cmp +='''{ IOMAP = "%s_a429";}'''%(outfn_)
        cmp+= ''' }}'''	
        cmp +='''IFSIM {LOADLIST = "";UNLOADLIST = "";SIMULATIONS = {}}'''
        fn = os.path.join(outdir, 'IO_%s.cmp' % (outfn_))
        open(fn, "w").write(cmp)

def usage():
    sys.stderr.write("Usage: iomGenAds2Data inputfile outputdir outfile (sim|stim) (raw|params|signals) (SDIB|SSDL|MDVS|SWTESTS) (True|False)")
    
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
    if len(args) > 6:
        splitiom   = bool(args[6] == 'True') # Split configuration files according  LRU name
    else:
        splitiom   = False
    if len(args) > 7:
        devicemap   = args[7]
    else:
        devicemap   = None 

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
    
    if target == "SSDL":
        devmode = False
        
    # read Excel File 
    inputMappings  = iomGenCommon.MapReader(inputfile, dd=None, msgonly=msgonly, noparams=True, direction='input', ignoreSrc=True)
    outputMappings = iomGenCommon.MapReader(inputfile, dd=None, msgonly=msgonly, noparams=True, direction='output', ignoreSrc=True)
    
    # Generate Test System configuration (CVT and IOM)
    outfile_ ='';
    if(bool(outfile)):
        outfile_ = '%s_afdx'%(outfile)
    else:
        outfile_ = 'afdx'
    genAds2ConfigsAFDX(inputMappings, outputMappings, outdir, outfile_ , mode=simmode, device=devicemap, msgonly=msgonly, devmode=devmode, split=splitiom)
    outfile_ ='';
    if(bool(outfile)):
        outfile_ = '%s_can'%(outfile)
    else:
        outfile_ = 'can'
    genAds2ConfigsCAN(inputMappings, outputMappings, outdir, outfile_, mode=simmode, device=devicemap, msgonly=msgonly, split=splitiom)
    outfile_ ='';
    if(bool(outfile)):
        outfile_ = '%s_a429'%(outfile)
    else:
        outfile_ = 'a429'
    genAds2ConfigsA429(inputMappings, outputMappings, outdir, outfile_, mode=simmode, device=devicemap, msgonly=msgonly, split=splitiom)

    genAds2Component(inputMappings, outputMappings, outdir, outfile, splitiom)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
