import xlrd
import re
from lxml import etree
import sys
from collections import defaultdict
from bunch import Bunch
from alertConstant import MAX_ALERT_ID

# helper
filename = "NONE"

def logerror(sheet, line, msg):
    sys.stdout.write("File %s: Sheet %s: Line %d: %s\n" % (filename, sheet, line + 1, msg))

def getColumnIndex(sheet):
    cidx = {}
    for col_idx in range(sheet.ncols):
        key = sval(sheet.row(0), col_idx)
        cidx[key] = col_idx
    return cidx


def sval(r, col):
    return r[col].value.encode('utf-8').strip()

def ival(r, col, base=10):
    f = r[col].value
    if type(f) == type(1.0):
        return int(r[col].value)
    else:
        s = f.encode('utf-8').strip()
        if s.startswith("0x"):
            return int(s[2:], 16)
        elif s.endswith("b"):
            return int(s[0:-1], 2)
        else: 
            return int(s, base)

def fval(r, col):
    return float(r[col].value)


def bval(r, col):
    f = r[col].value
    if type(f) == type(1.0) or type(f) == type(1):
        return bool(f)
    else:
        s = f.encode('utf-8').strip().lower()
        if s in ("yes", "y", "true", "t", "wahr", "ja", "j", "we", "si"):
            return True
        elif s in ("no", "n", "false", "f", "falsch", "nein"):
            return False
        else:
            raise Exception, "Bad truth value: %s" % s
        

class Vl(object):
    '''
    Class representing an AFDX VL
    Constructor builds a VL object from an excel row
    '''
    def __init__(self, id, row, cidx, msg, vlref=None):
        self.id      = 0
        self.bag     = 0
        self.mtu     = 0
        self.nbSubVl = 0
        self.macAdd  = 0
        self.vlName  = "Undefined"
                
        if id != None:
            self.id      = id
            self.macAdd  = "03:00:00:00:"+hex(id>>8)[2:]+":"+hex(id&0xFF)[2:]
            self.macAdd  = self.macAdd.upper()
            self.vlName  = "VL_%s_%s" % (msg.lruName, str(id))
            try:
                self.bag     = int(fval(row, cidx["BAG"])*1000)
            except:
                self.bag     = 0
            try:
                self.mtu     = ival(row, cidx["MTU"])
            except:
                self.mtu     = 0
            if vlref != None:
                if vlref.nbSubVl < msg.subVl:
                    self.nbSubVl = msg.subVl
                else:
                    self.nbSubVl = vlref.nbSubVl
            else:
                self.nbSubVl = msg.subVl
    
class AfdxMessage(object):
    '''
    Class representing an AFDX Message
    Constructor builds a message object from an excel row
    '''
    def __init__(self, name, id, row, cidx, direction):
        self.msgclass       = "AFDX"
        self.direction      = direction
        self.msgUsed        = False                             # remember if message is used by a signal
        self.msgid          = id
        self.fullname       = name
        self.msgName        = name.split('.', 1)[1]
        self.lruName        = name.split('.', 1)[0]
        try:
            self.portType       = sval(row, cidx["Type"]).upper()
        except:
            raise Exception, "Bad port type (SAMPLING or QUEUEING expected)"

        if self.portType[0:3] == "SAM":
            self.portType = "SAMPLING"
        elif self.portType[0:3] == "QUE":
            self.portType = "QUEUEING"
        else:
            raise Exception, "Bad port type (SAMPLING or QUEUEING expected)"

        try:
            self.msgLength  = ival(row, cidx["Length"])
        except:
            raise Exception, "Bad message length value"

        try:
            self.msgRxLength  = ival(row, cidx["RxLength"])
        except:
            if direction == 'input':
                raise Exception, "Bad receive length value"
            else:
                pass

        try:
            self.msgOverhead  = ival(row, cidx["Overhead"])
        except:
            raise Exception, "Bad overhead length value"


        if self.msgLength < 1 or self.msgLength > 8192:
            raise Exception, "Bad message length value: should be between 1 and 8192"
            
            
        if self.portType[0] == "Q":
            try:
                self.queueLength    = ival(row, cidx["QueueLength"])
            except:
                raise Exception, "Bad queue length value"
            if self.queueLength < 1:
                raise Exception, "Bad queue length for QUEUEING port"
        else:
            self.queueLength    = 0
                        
        try:
            self.msgRate        = ival(row, cidx["Rate"])        
        except:
            if direction == 'output' and self.queueLength > 0:
                raise Exception, "Bad Transmit Rate"
            else:
                self.msgRate        = 0

        try:
            self.msgValidityPeriod = ival(row, cidx["ValidityPeriod"])        
        except:
            if direction == 'input' and self.queueLength > 0:
                raise Exception, "Bad Receive Refresh Period"
            else:
                self.msgValidityPeriod = 0

        try:
            self.portId         = ival(row, cidx["PortID"])
        except:            
            raise Exception, "No PortID defined"

        try:
            self.portName         = sval(row, cidx["PortName"])
        except:            
            raise Exception, "No Port Name defined"

        try:
            self.EdeActive      = bval(row, cidx["EdeEnabled"])
        except:
            raise Exception, "Bad value for EdeEnabled"
        
        if self.EdeActive:
            try:
                self.EdeSource      = ival(row, cidx["EdeSourceId"])
            except:
                raise Exception, "Bad value for EDE Source ID"
        else:
            self.EdeSource = 0
            

        try:
            self.srcPortId      = ival(row, cidx["SourceUDP"])
        except:            
            raise Exception, "Bad value for Source UDP Port"

        try:
            self.dstPortId      = ival(row, cidx["DestUDP"])
        except:
            raise Exception, "Bad value for Destination UDP Port"

        try:
            self.vlId           = ival(row, cidx["Vlid"])
        except:
            raise Exception, "Bad value for VL Id"
        
        try:
            self.subVl          = ival(row, cidx["SubVl"])
        except:
            self.subVl          = None

        try:
            self.dstIp         	= sval(row, cidx["DestIP"])
        except:
            self.dstIp         	= None

        try:
            self.macSrc         = sval(row, cidx["SourceMAC"])
            self.srcIp          = sval(row, cidx["SourceIP"])
        except:
            self.macSrc         = None
            self.srcIp          = None
        

class CanMessage(object):
    '''
    Class representing an CAN Message
    Constructor builds a message object from an excel row
    '''
    def __init__(self, name, id, row, cidx, direction):
        self.msgclass       = "CAN"
        self.direction      = direction
        self.msgUsed        = False                             # remember if message is used by a signal
        self.msgid          = id
        self.fullname       = name
        self.msgName        = name.split('.', 1)[1]
        self.lruName        = name.split('.', 1)[0]

        try:
            self.msgLength  = ival(row, cidx["Length"])
        except:
            raise Exception, "Bad message length value"
        if self.msgLength < 1 or self.msgLength > 8:
            raise Exception, "Bad CAN message length value: should be between 1 and 8"
            
        try:
            self.msgRate        = ival(row, cidx["Rate"])        
        except:
            raise Exception, "Bad value for CAN Message Rate"

        try:
            self.msgCanID       = ival(row, cidx["CanMsgID"], base=16)
        except:            
            raise Exception, "Bad value for CAN Message ID"

        try:
            self.msgPhysPort    = sval(row, cidx["PhysPort"])
        except:            
            raise Exception, "Bad value for CAN Receive Port"

VALIDITY_FRESHNESS   = 1
VALIDITY_MASK        = 2
VALIDITY_A664FSB     = 4
VALIDITY_A429SSM_DIS = 8
VALIDITY_A429SSM_BNR = 16
VALIDITY_A429SSM_BCD = 32
VALIDITY_A429SSM     = (VALIDITY_A429SSM_DIS | VALIDITY_A429SSM_BNR | VALIDITY_A429SSM_BCD)

NORMALIZE_SIGTYPES = {
    'SINT'  : 'INT',
    'SHORT' : 'INT',
    'INT'   : 'INT',
    'USHORT': 'UINT',
    'UINT'  : 'UINT',
    'CHAR'  : 'INT',
    'DIS'   : 'BOOL',
    'BOOL'  : 'BOOL',
    'ENUM'  : 'COD',
    'COD'   : 'COD',
    'OPAQUE': 'BYTES',
    'BYTES' : 'BYTES',
    'BLK'   : 'BYTES',
    'STRING': 'STRING',
    'FLOAT' : 'FLOAT',
    'BNR'   : 'BNR',
    'UBNR'  : 'UBNR',
    'BCD'   : 'BCD',
    'UBCD'  : 'UBCD',
    'ISO-5' : 'COD',
    # special purpose types, all can be treated as bitfields alias COD
    'A429OCTLBL'    : 'COD',
    'A429SDI'       : 'COD',
    'A429_SSM_BNR'  : 'COD',
    'A429_SSM_DIS'  : 'COD',
    'A429_SSM_BCD'  : 'COD',
    'A429PARITY'    : 'COD',
    'PAD'           : 'COD',
    'RESV'          : 'COD',
    'CRC'           : 'UINT',
    'A664_FSB'      : 'UINT'

}

def normalizeSigType(sigtype, sigsize):
    if sigtype in ("CHAR", "INT8", "UINT8") and sigsize != 8:
        raise Exception, "Wrong signal size for data type %s" % sigtype

    if sigtype in ("SHORT", "INT16", "UINT16") and sigsize != 16:
        raise Exception, "Wrong signal size for data type %s" % sigtype

    if sigtype in ("UINT", ) and sigsize not in (8,16,32,64):
        sigtype = "COD"
    
    normalizedType = NORMALIZE_SIGTYPES.get(sigtype)
    if normalizedType is None:
        raise Exception, "Unknown signal type %s" % sigtype
    
    return normalizedType


DATATYPES_COMPAT = {
    #Param Type  SignalType 
    'INT':       set(('INT', 'UINT', 'COD', 'FLOAT', 'BNR', 'UBNR', 'BCD', 'UBCD','BOOL',)),
    'COUNT':     set(('INT',)),
    'FLOAT':     set(('INT', 'FLOAT', 'BNR', 'UBNR', 'BCD', 'UBCD')),
    'BOOL':      set(('BOOL',)),
    'ENUM':      set(('COD',)),
    'BYTES':     set(('BYTES','STRING')),
    'CSTRING':   set(('STRING',)),
    'ASTRING':   set(('STRING',)),
}

ONEBIT_TYPES   = set(("BOOL",))
MULTIBYTE_TYPES= set(("BYTES","STRING"))
FULLBYTE_TYPES = set(("INT", "UINT", "CHAR", "FLOAT","BYTES", "STRING"))
BYTE_TYPES     = set(("INT", "UINT"))
HALFWORD_TYPES = set(("INT", "UINT"))
FULLWORD_TYPES = set(("INT", "UINT", "FLOAT"))
LONGWORD_TYPES = set(("INT", "UINT", "FLOAT"))
INTEGER_TYPES  = set(("INT", "UINT"))

        
def computeSignalAccess(msgclass, sigtype, sigsize=0, sigoffset=0, dssize=0, dspos=0):
    if msgclass == "AFDX":
        return computeSignalAccessAFDX(sigtype, sigsize, sigoffset, dssize, dspos)
    elif msgclass == "CAN":
        return computeSignalAccessCAN(sigtype, sigsize, sigoffset, dssize, dspos)
    elif msgclass == "A429":
        return computeSignalAccessA429(sigtype, sigsize, sigoffset, dssize, dspos)
    else:
        raise Exception, "Illegal Message Class %s" % msgclass



def computeSignalAccessAFDX(sigtype, sigsize=0, sigoffset=0, dssize=0, dspos=0):
    # consistency checks

    # signal must fit in dataset
    # FIXME: if sigoffset + sigsize > dssize * 8:
    #    raise Exception, "Signal does not fit into data set or message"
    
    # for AFDX dataset must be 4 byte aligned and size must be multiple of 4 byte 
    if dssize % 4 != 0 or dspos % 4 != 0:
        raise Exception, "Illegal Data Set Alignment"

    if sigtype in FULLBYTE_TYPES and sigoffset % 8 != 0:
        raise Exception, "Signal offset not aligned to byte boundary"

    if sigtype == "BYTES" and sigoffset % 32 != 0:
        raise Exception, "OPAQUE signal offset not aligned to word boundary"

    if sigtype in ONEBIT_TYPES and sigsize != 1:
        raise Exception, "Illegal signal size for type %s" % sigtype
        
    if sigtype in INTEGER_TYPES and sigsize not in (8, 16, 32, 64):
        raise Exception, "Illegal signal size for type %s" % sigtype

    if sigtype == "FLOAT" and sigsize not in (32, 64):
        raise Exception, "Illegal signal size for type %s" % sigtype
        
    
    if  (sigtype == "BYTES"):
        # Opaque: sigoffset is least significant bit of first word
        # Only works for opaque which have bitoffset multiple of 4 bytes
        sigAccess = 1
        sigByteOffset = dspos + (sigoffset / 8)
        if sigsize < 32:
            sigByteOffset += 4 - sigsize / 8
        sigBitOffset  = 0
    elif  sigtype == "STRING" or (sigtype in BYTE_TYPES  and sigsize == 8):
        # byte aligned data
        sigAccess = 1
        sigByteOffset = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in HALFWORD_TYPES and sigsize == 16:
        # 16 bit aligned data 
        sigAccess = 2
        sigByteOffset = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in  FULLWORD_TYPES and sigsize == 32:
        # 32 bit aligned data 
        sigAccess = 4
        sigByteOffset = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in LONGWORD_TYPES and sigsize == 64:
        # 64 bit aligned data 
        sigAccess = 8
        sigByteOffset = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    else: # COD, BITFIELD, BOOL, DIS, (U)BNR, (U)BCD
        # compute smallest containing access
        startbyte = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        endbyte   = dspos + (((sigoffset/32 + 1) * 4) - (sigoffset % 32) / 8 - 1)
        bytes     = endbyte - startbyte + 1
        sigAccess = {1: 4, 2: 4, 3: 4, 4: 4, 5: 8, 6: 8, 7:8, 8: 8}.get(bytes)
        while sigAccess < 8 and startbyte / sigAccess != endbyte / sigAccess:
            sigAccess *= 2

        # access byte offset should now be aligned, 
        # i.e. round down start byte to multiples of sigAccess
        sigByteOffset = (startbyte / sigAccess) * sigAccess 

        lastbyte = (sigByteOffset + sigAccess - 1)
        sigBitOffset = (lastbyte - endbyte) * 8 + sigoffset % 8

    if sigByteOffset % sigAccess != 0:
        raise Exception, "Unaligned signal access: ByteOffset=%d BitOffset=%d Access=%d" % \
            (sigByteOffset, sigBitOffset, sigAccess)
            
    return sigByteOffset, sigBitOffset, sigAccess


def computeSignalAccessCAN(sigtype, sigsize=0, sigoffset=0, dssize=0, dspos=0):
    # consistency checks
    # signal must fit in dataset
    if sigoffset + sigsize > dssize * 8:
        raise Exception, "Signal does not fit into data set or message"
    
    # dataset must fit in message
    if dssize > 8:
        raise Exception, "Illegal Data Set Size"
    
    if sigtype in FULLBYTE_TYPES and sigoffset % 8 != 0:
        raise Exception, "Signal offset not aligned to byte boundary"

    if sigtype in ONEBIT_TYPES and sigsize != 1:
        raise Exception, "Illegal signal size for type %s" % sigtype
        
    if sigtype in INTEGER_TYPES and sigsize not in (8, 16, 32, 64):
        raise Exception, "Illegal signal size for type %s" % sigtype

    if sigtype == "FLOAT" and sigsize not in (32, 64):
        raise Exception, "Illegal signal size for type %s" % sigtype
    
    if sigtype in MULTIBYTE_TYPES and sigsize % 8 != 0:
        raise Exception, "Illegal signal size for type %s" % sigtype
    
    if  sigtype in MULTIBYTE_TYPES or \
       (sigtype in BYTE_TYPES  and sigsize == 8):
        # byte aligned data
        sigAccess = 1
        sigByteOffset = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in HALFWORD_TYPES and sigsize == 16:
        # 16 bit aligned data 
        sigAccess = 2
        sigByteOffset = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in  FULLWORD_TYPES and sigsize == 32:
        # 32 bit aligned data 
        sigAccess = 4
        sigByteOffset = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in LONGWORD_TYPES and sigsize == 64:
        # 64 bit aligned data 
        sigAccess = 8
        sigByteOffset = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    else: # COD, BITFIELD, BOOL, DIS, (U)BNR, (U)BCD
        # compute smallest containing access
        startbyte = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        endbyte   = dspos + (dssize - sigoffset/8 - 1)
        bytes     = endbyte - startbyte + 1
        sigAccess = {1: 4, 2: 4, 3: 4, 4: 4, 5: 8, 6: 8, 7:8, 8: 8}.get(bytes)

        if sigAccess is None:
            raise Exception, "Illegal signal size for type %s" % sigtype

        while sigAccess < 8 and startbyte / sigAccess != endbyte / sigAccess:
            sigAccess *= 2

        # access byte offset should now be aligned, 
        # i.e. round down start byte to multiples of sigAccess
        sigByteOffset = (startbyte / sigAccess) * sigAccess 

        lastbyte = (sigByteOffset + sigAccess - 1)
        sigBitOffset = (lastbyte - endbyte) * 8 + sigoffset % 8

    if sigByteOffset % sigAccess != 0:
        raise Exception, "Unaligned signal access: ByteOffset=%d BitOffset=%d Access=%d" % \
            (sigByteOffset, sigBitOffset, sigAccess)
            
    return sigByteOffset, sigBitOffset, sigAccess

    
class InputSignal(object):
    def __init__(self, row, cidx, msgref, ddmap, paramxref, noparams=False, rowidx=0):
        # when called with noparam=True, we ignore DD-RP and DD offset map
        # such a model can not be used for generation of IOM configuration
        # but can be used to generate system level test system configuration
        self.rowidx = rowidx
        
        if noparams:
            paramname    = None
            datatype     = None
            datasize     = None
            paramtype    = None
            paramoffset  = None
            statusoffset = None
        else:
            paramname = sval(row,cidx["Parameter"])
            datatype  = sval(row,cidx["DataType"])
            datasize  = ival(row,cidx["DataSize"])

            if ddmap is None:
                # not available, this model cannot be used for generation of 
                # IO Manager config
                paramtype    = None
                paramoffset  = None
                statusoffset = None
            else:
                if paramname in ddmap:
                    paramtype   = ddmap[paramname].type
                    paramoffset = ddmap[paramname].offset
                    paramelem   = ddmap[paramname].elements

                    statusoffset = None
                    for suffix in ('_Status', '_status', '_STATUS', 'Status'):
                        if paramname + suffix in ddmap:
                            statusoffset = ddmap[paramname + suffix].offset
                            break
                    if statusoffset is None:
                        raise Exception, "Missing Status Variable for Variable %s (expected _Status, _status, Status or _STATUS)" % paramname
                else:
                    paramtype   = datatype
                    paramoffset = -1
                    paramelem   = -1
                    statusoffset = -1
            
                if not ((datatype == paramtype) or  \
                        (datatype == "COUNT" and paramtype == "INT") or \
                        (datatype == "BYTES" and paramtype == "CHAR")):
                    raise Exception, "Incompatible data types: Model Parameter: %s,  ICD Map: %s" % \
                        (ddmap[paramname].type, datatype)
                        
                if (datatype == "BYTES" and datasize != paramelem * 8):
                    raise Exception, "Incompatible data size for %s: Model: %d,  IOLIST: %d" % \
                        (paramname, paramelem, datasize)
                    
        
        self.msgRef           = msgref           
        self.paramXref        = paramxref
        self.paramName        = paramname
        self.paramDatatype    = datatype
        self.paramDatasize    = datasize
        self.paramOffset      = paramoffset
        self.paramOffsetStatus= statusoffset
        self.pubref           = sval(row, cidx["Pubref"])
        self.dsName           = sval(row, cidx["DataSet"])
        self.dsDsOffset       = ival(row, cidx["DSOffset"])
        self.dsDsSize         = ival(row, cidx["DSSize"])
        self.sigName          = sval(row, cidx["Signal"])
        self.sigDsOffset      = ival(row, cidx["SigOffset"])
        self.sigSize          = ival(row, cidx["SigSize"])
        self.sigType          = normalizeSigType(sval(row, cidx["SigType"]), self.sigSize)

        if self.sigType in ("BNR","UBNR","BCD"):
            self.sigLsbValue  = fval(row, cidx["LsbValue"])
        else:
            self.sigLsbValue  = 1
          
        try:
            self.alertId     = ival(row, cidx["AlertID"])
        except:
            self.alertId     = None
            
        if self.alertId is not None:
            if self.alertId > MAX_ALERT_ID:
                raise Exception, "Bad alert ID: Expect integer value in the range 1-2000"
            self.sigDsOffset   = (30+((int)((self.alertId-1)/16))*32) - (((self.alertId-1)%16) *2 )        # bit offset within DataSet
            self.sigSize       = 2;
            self.sigType       = "COD";

        self.sigByteOffset, self.sigBitOffset, self.sigAccess = computeSignalAccess(
                  self.msgRef.msgclass, self.sigType, 
                  sigsize   = self.sigSize,
                  sigoffset = self.sigDsOffset,
                  dssize    = self.dsDsSize,
                  dspos     = self.dsDsOffset, 
        )

        sselstr     = sval(row, cidx["SSEL"])
        ssel        = [p.strip().upper() for p in sselstr.split(',')]
        
        self.sourceSelect = 0
        for p in ssel:
            if p == "FRESH":
                self.sourceSelect |= VALIDITY_FRESHNESS
            elif p == "MASK":
                self.sourceSelect |= VALIDITY_MASK
            elif p == "FSB":
                self.sourceSelect |= VALIDITY_A664FSB
            elif p == "SSM_BNR":
                if self.sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                    raise Exception, "Illegal source selection method: %s" % sselstr
                self.sourceSelect |= VALIDITY_A429SSM_BNR
            elif p == "SSM_DIS":
                if self.sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                    raise Exception, "Illegal source selection method: %s" % sselstr
                self.sourceSelect |= VALIDITY_A429SSM_DIS
            elif p == "SSM_BCD":
                if self.sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                    raise Exception, "Illegal source selection method: %s" % sselstr
                self.sourceSelect |= VALIDITY_A429SSM_BCD
            elif p != '':
                raise Exception, "Illegal source selection method: %s" % sselstr
        
        if self.sourceSelect & VALIDITY_A664FSB:
            self.dsFsbOffset      = ival(row, cidx["FsbOffset"])
        else:
            self.dsFsbOffset      = None
            
            
        if self.sourceSelect & VALIDITY_MASK:
            # fetch and validate parameters
            self.maskValidParam = sval(row, cidx["MaskValidParam"])
            self.maskValidValue = ival(row, cidx["MaskValidValue"])
        else:
            self.maskValidParam = None
            self.maskValidValue = None

        if not noparams:
            if self.paramDatatype not in DATATYPES_COMPAT:
                raise Exception, "Illegal parameter data type: %s" % self.paramDatatype

            if self.sigType not in DATATYPES_COMPAT[self.paramDatatype]:
                raise Exception, "Illegal or incompatible signal data type: %s - %s" % (self.paramDatatype, self.sigType)
            if self.paramDatatype != "BYTES":
                if self.paramDatasize != 32:
                    raise Exception, "Illegal parameter data size: %d" % self.paramDatasize
                if self.sigSize > 32:
                    raise Exception, "Illegal signal size: Only 32 bit values are supported"
            else:
                if (self.paramDatasize & 0x7): # not multiple of bytes
                    raise Exception, "Illegal parameter data size: %d" % self.paramDatasize
                if self.paramDatasize != self.sigSize:
                    raise Exception, "Incompatible data size for BYTES signal %s: Parameter: %d,  Signal: %d" % \
                            (self.paramName, self.paramDatasize, self.sigSize)
            
    def sselFreshness(self):
        return self.sourceSelect & VALIDITY_FRESHNESS

    def sselMaskValue(self):
        return self.sourceSelect & VALIDITY_MASK
    
    def sselMaskParams(self):
        '''
        return a bunch with msgid, offset, mask and value for constructing the condition
        '''
        # find parameter definition refered to by mask field
        sigs = self.paramXref.get(self.maskValidParam)
        if not sigs:
            logerror("Input Signals", self.rowidx, 
                     "Parameter referred to by MaskValidParam not found: %s" % self.maskValidParam)
            return None

        if len(sigs) > 1:
            logerror("Input Signals", self.rowidx, 
                     "Parameter referred to by MaskValidParam not unique: %s" % self.maskValidParam)
            return None

        sig = sigs[0]
        res = Bunch(
            msgid  = sig.msgRef.msgid,
            offset = sig.sigByteOffset,
            mask   = ((1 << sig.sigSize) - 1) << sig.sigBitOffset,
            value  = self.maskValidValue << sig.sigBitOffset
        )    
        return res
        

    def sselA664Fsb(self):
        return self.sourceSelect & VALIDITY_A664FSB

    def sselA429SSM(self):
        return self.sourceSelect & VALIDITY_A429SSM

    def sselA429SSM_BNR(self):
        return self.sourceSelect & VALIDITY_A429SSM_BNR
            
    def sselA429SSM_DIS(self):
        return self.sourceSelect & VALIDITY_A429SSM_DIS
            
    def sselA429SSM_BCD(self):
        return self.sourceSelect & VALIDITY_A429SSM_BCD
            
            
class OutputSignal(object):
    def __init__(self, row, cidx, msgref, ddmap, paramxref, noparams=False):

            if noparams:
                paramname   = None
                datatype    = None
                datasize    = None
                paramtype   = None
                paramoffset = None
                statusoffset= None
            else:
                paramname = sval(row,cidx["Parameter"])
                datatype  = sval(row,cidx["DataType"])
                datasize  = ival(row,cidx["DataSize"])
            
                if ddmap is None:
                    paramtype = None
                    paramoffset = None
                    statusoffset = None
                else:
                    if paramname in ddmap:
                        paramtype   = ddmap[paramname].type
                        paramoffset = ddmap[paramname].offset
                        paramelem   = ddmap[paramname].elements
                        statusoffset = None
                        for suffix in ('_Status', '_status', '_STATUS'):
                            if paramname + suffix in ddmap:
                                statusoffset = ddmap[paramname + suffix].offset
                                break
                        if statusoffset is None:
                           raise Exception, "Missing Status Variable for Variable %s (expected _Status, _status or _STATUS)" % paramname
                    else:
                        paramtype   = datatype
                        paramoffset = -1
                        paramelem   = -1
                        statusoffset = -1
                    
                    if not ((datatype == paramtype) or  \
                            (datatype == "BYTES" and paramtype == "CHAR")):
                        raise Exception, "Incompatible data types: Model Parameter: %s,  ICD Map: %s" % \
                            (ddmap[paramname].type, datatype)
                    
                    if (datatype == "BYTES" and datasize != paramelem * 8):
                        raise Exception, "Incompatible data size for %s: Model: %d,  IOLIST: %d" % \
                            (paramname, paramelem, datasize)
            
            self.msgRef           = msgref           
            self.paramXref        = paramxref
            self.paramName        = paramname
            self.paramDatatype    = datatype
            self.paramDatasize    = datasize
            self.paramOffset      = paramoffset
            self.paramOffsetStatus= statusoffset
            try:
                self.constValue       = ival(row, cidx["ConstantVal"])
            except:
                self.constValue       = None

            self.dsName           = sval(row, cidx["DataSet"])
            self.dsDsOffset       = ival(row, cidx["DSOffset"])
            self.dsDsSize         = ival(row, cidx["DSSize"])
            self.DpName           = sval(row, cidx["DpName"])
            self.sigDsOffset      = ival(row, cidx["SigOffset"])
            self.sigSize          = ival(row, cidx["SigSize"])
            self.sigType          = normalizeSigType(sval(row, cidx["SigType"]), self.sigSize)
            if self.sigType == "BNR":
                self.sigLsbValue  = fval(row, cidx["LsbValue"])
            else:
                self.sigLsbValue  = 1
                
            self.sigByteOffset, self.sigBitOffset, self.sigAccess = computeSignalAccess(
                      msgclass  = self.msgRef.msgclass,
                      sigtype   = self.sigType, 
                      sigsize   = self.sigSize,
                      sigoffset = self.sigDsOffset,
                      dspos     = self.dsDsOffset, 
                      dssize    = self.dsDsSize,
            )

            validstr    = sval(row, cidx["Validity"])
            validlst    = [p.strip().upper() for p in validstr.split(',')]
            
            self.validity = 0
            for p in validlst:
                if p == "FSB":
                    self.validity |= VALIDITY_A664FSB
                elif p == "SSM_BNR":
                    if self.validity & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal validity method: %s" % sselstr
                    self.validity |= VALIDITY_A429SSM_BNR
                elif p == "SSM_DIS":
                    if self.validity & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal validity method: %s" % sselstr
                    self.validity |= VALIDITY_A429SSM_DIS
                elif p == "SSM_BCD":
                    if self.validity & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal validity method: %s" % sselstr
                    self.validity |= VALIDITY_A429SSM_BCD
                elif p != '':
                    raise Exception, "Illegal validity method: %s" % sselstr
                
            if self.validity & VALIDITY_A664FSB:
                self.dsFsbOffset      = ival(row, cidx["FsbOffset"])
            else:
                self.dsFsbOffset      = None

            if not noparams:
                if not DATATYPES_COMPAT.has_key(self.paramDatatype):
                    raise Exception, "Illegal parameter data type: %s" % self.paramDatatype
                if self.sigType not in DATATYPES_COMPAT[self.paramDatatype]:
                    raise Exception, "Illegal or incompatible signal data type: %s - %s" % (self.paramDatatype, self.sigType)
                if self.paramDatatype != "BYTES":
                    if self.paramDatasize != 32:
                        raise Exception, "Illegal parameter data size: %d" % self.paramDatasize
                    if self.sigSize > 32:
                        raise Exception, "Illegal signal size: Only 32 bit values are supported"
                else:
                    if (self.paramDatasize & 0x7): # not multiple of bytes
                        raise Exception, "Illegal parameter data size: %d" % self.paramDatasize
                    if self.paramDatasize != self.sigSize:
                        raise Exception, "Illegal signal size: Not equal to parameter size"
            
    def sselA664Fsb(self):
        return self.validity & VALIDITY_A664FSB

    def sselA429SSM(self):
        return self.validity & VALIDITY_A429SSM
                
class MapReader(object):
    def __init__(self, fname, dd=None, msgonly=False, noparams=False, direction='input'):
        
        global filename
        filename = fname
        
        self.errorCount = 0
        workbook       = xlrd.open_workbook(filename)
        #idSheet       = workbook.sheet_by_name("Identification")
        self.identification = Bunch(application="", revision="", icd="")
        #self.readIdent(self.idSheet, self.identification)

        if direction == 'input':
            try:
                ipSignalSheet  = workbook.sheet_by_name("InputSignals")
                ipAfdxMsgSheet = workbook.sheet_by_name('InputAfdxMessages')
                ipCanMsgSheet  = workbook.sheet_by_name('InputCanMessages')
            except Exception, msg:
                raise Exception, "File %s open failed!: %s" % (filename, str(msg))
    
    
            self.afdx   = self.readAfdxMessages(ipAfdxMsgSheet, direction)
            self.can    = self.readCanMessages(ipCanMsgSheet, direction)
    
            self.afdx.datasets  = dict()
            self.can.datasets   = defaultdict(list)
            self.paramXref      = defaultdict(list)
    
            if not msgonly:
                self.readInputSignals(dd, ipSignalSheet, noparams)
        else:
            try:
                opSignalSheet  = workbook.sheet_by_name("OutputSignals")
                opAfdxMsgSheet = workbook.sheet_by_name('OutputAfdxMessages')
                opCanMsgSheet  = workbook.sheet_by_name('OutputCanMessages')
            except Exception, msg:
                raise Exception, "File %s open failed!: %s" % (filename, str(msg))
    
            self.afdx  = self.readAfdxMessages(opAfdxMsgSheet, direction)
            self.can   = self.readCanMessages(opCanMsgSheet, direction)
            
            self.afdx.datasets = dict()
            self.can.datasets  = defaultdict(list)
            self.paramXref     = defaultdict(list)
            if not msgonly:
                self.readOutputSignals(dd, opSignalSheet, noparams)

    def logerr(self, sheet, line, msg):
        logerror(sheet, line, msg)
        self.errorCount += 1
    
    def readIdent(self, sheet, idobj):
        for row_idx in range(1, sheet.nrows):
            row = sheet.row(row_idx)
            if sval(row, 0) == "Application":
                idobj.application = sval(row, 1)
            if sval(row, 0) == "Revision":
                idobj.revision = sval(row, 1)
            if sval(row, 0) == "ICD":
                idobj.icd = sval(row, 1)

    def readAfdxMessages(self, sheet, direction):
        cidx = getColumnIndex(sheet)

        messages    = dict()
        vls         = dict()
        messageKeys = list()
        msgidx      = 0

        for row_idx in range(1, sheet.nrows):
            row = sheet.row(row_idx)
            if sval(row, 0).startswith("#"):
                continue

            msgidx += 1
            lru = sval(row, cidx["Lru"])
            message = sval(row, cidx["Message"])
            msgname = lru + '.' + message
            try:
                messages[msgname] = AfdxMessage(msgname, msgidx, row, cidx, direction)
            except Exception, msg:
                self.logerr("Afdx %s messages" % direction, row_idx, str(msg) + ' - message skipped')
                continue

            messageKeys.append(msgname)
            #check and update the VL if necessary:
            vlId = messages[msgname].vlId
            vls[vlId] = Vl(vlId, row, cidx, messages[msgname], vls.get(vlId))

        return Bunch(messages=messages, vls=vls, messageKeys=messageKeys)

    def readCanMessages(self, sheet, direction):

        cidx = getColumnIndex(sheet)
        messages    = dict()
        messageKeys = []
        msgidx      = 0

        for row_idx in range(1, sheet.nrows):
            row = sheet.row(row_idx)
            if sval(row, 0).startswith("#"):
                continue

            msgidx += 1
            lru = sval(row, cidx["Lru"])
            message = sval(row, cidx["Message"])
            msgname = lru + '.' + message
            try:
                messages[msgname] = CanMessage(msgname, msgidx, row, cidx, direction)
            except Exception, msg:
                self.logerr("CAN %s messages" % direction, row_idx, str(msg) + ' - message skipped')
                continue

            messageKeys.append(msgname)

        return Bunch(messages=messages, messageKeys=messageKeys)


    def readInputSignals(self, ddmap, sheet, noparams):
        cidx = getColumnIndex(sheet)

        for row_idx in range(1, sheet.nrows):
            row = sheet.row(row_idx)
            if sval(row, 0).startswith('#'):
                continue

            # identify message the signal belongs too
            lru = sval(row, cidx["Lru"])
            msgName = lru + '.' + sval(row, cidx["Message"])
            message = self.afdx.messages.get(msgName)
            if message is None:
                message = self.can.messages.get(msgName)
                if message is None:
                    self.logerr("Input Signals", row_idx, "Message %s not found in input message sheets" % msgName)
                    continue
            
            try:
                sig = InputSignal(row, cidx, message, ddmap, self.paramXref, noparams, rowidx=row_idx)
                self.paramXref[sig.paramName].append(sig)
            except Exception, excmsg:
                self.logerr("Input Signals", row_idx, str(excmsg))
                continue
            message.msgUsed = True
            
            if sig.paramOffset != -1 or noparams:
                if message.msgclass == 'AFDX':
                    # if we have an embedded 429 word, we have to consider the signals of the word
                    # as separate source selection group (i.e. they are something like a sub-dataset)
                    # We achieve this by adding the offset of the containing 429 word to the ds key.
                    # The ultimate complication is when we have an additional mask validity flag.
                    # Then the mask/value validity parameters become yet an other criteria for separating data sets
                    
                    if sig.sourceSelect & VALIDITY_A429SSM:
                        sselgroupSSM = (sig.sigDsOffset / 32) * 32
                    else:
                        sselgroupSSM = 0
                    
                    if (sig.sourceSelect & VALIDITY_MASK):
                        sselgroupMask = (sig.maskValidParam, sig.maskValidValue)
                    else:
                        sselgroupMask = ()


                    # dskey = (sig.sourceSelect, message.msgName, sig.dsName, sselgroupSSM,  sselgroupMask)
                    dskey = sig.paramName

                    if not self.afdx.datasets.has_key(dskey):
                        self.afdx.datasets[dskey] = dict()
                    dso = self.afdx.datasets[dskey]
                    if not sig.paramName in dso:
                        dso[sig.paramName] = []
                    dso[sig.paramName].append(sig)
                elif message.msgclass == 'CAN':
                    dskey = message.msgid
                    self.can.datasets[dskey].append(sig)

    def readOutputSignals(self, ddmap, sheet, noparams):
        cidx = getColumnIndex(sheet)
        for row_idx in range(1, sheet.nrows):
            row = sheet.row(row_idx)
            if sval(row, 0).startswith('#'):
                continue

            # identify message the signal belongs too
            lru = sval(row, cidx["Lru"])
            msgName = lru + '.' + sval(row, cidx["Message"])
            message = self.afdx.messages.get(msgName)
            if message is None:
                message = self.can.messages.get(msgName)
                if message is None:
                    self.logerr("Output Signals", row_idx, "Message %s not found in output message sheets" % msgName)
                    continue
            try:
                sig = OutputSignal(row, cidx, message, ddmap, self.paramXref, noparams)
                self.paramXref[sig.paramName].append(sig)
            except Exception, excmsg:
                self.logerr("Output Signals", row_idx, str(excmsg))
                continue
            message.msgUsed = True
            
            if sig.paramOffset != -1 or noparams:
                if message.msgclass == 'AFDX':
                    dskey = (message.msgName, sig.dsName)
                    if not dskey in self.afdx.datasets:
                        self.afdx.datasets[dskey] = []
                    self.afdx.datasets[dskey].append(sig)
                elif message.msgclass == 'CAN':
                    dskey = message.msgid
                    self.can.datasets[dskey].append(sig)
                    
# --------------------- TEST CODE ----------------------------------                    
                    
def testComputeSignalAccess():
    tc = (
          #,msgclass, sigtype  , sigsize, sigoffset,   dssize,  dspos  Expected Result
         (1, ("AFDX",   "INT"  ,   16,         32,          8,      0), ( 6,  0, 2)),
         (2, ('AFDX',   'COD'  ,   16,          8,          8,      0), ( 0,  8, 4)),
         (3, ('CAN' ,   'COD'  ,   16,         40,          8,      0), ( 0,  8, 4)),
         (4, ('CAN' ,   'COD'  ,   16,         40,          5,      0), "Exception"),
         (5, ('CAN' ,   'INT'  ,   17,          8,          4,      0), "Exception"),
         (6, ('CAN' ,   'INT'  ,   16,          8,          8,      0), "Exception"),
         (7, ('CAN' ,   'INT'  ,   16,          8,          5,      0), ( 2,  0, 2)),
         (8, ('CAN' ,   'INT'  ,   16,          8,          3,      0), ( 0,  0, 2)),
         (9, ('CAN' ,   'BOOL' ,    2,          8,          3,      0), "Exception"),
         (10,('CAN' ,   'INT'  ,   33,          8,          4,      0), "Exception"),
         (11,('CAN' ,   'INT'  ,   33,          8,          16,     0), "Exception"),
         (12,('CAN' ,   'INT'  ,   33,          8,           8,     0), "Exception"),
         (13,('CAN' ,   'INT'  ,   64,          8,           8,     0), "Exception"),
         (14,('CAN' ,   'INT'  ,   64,          0,           8,     0), ( 0,  0, 8)),
         (15,('CAN' ,   'BOOL' ,    1,          8,           3,     0), ( 0, 16, 4)),
         (16,("AFDX",   "INT"  ,    8,         39,           8,     0), "Exception"),
         (17,("AFDX",   "INT"  ,    8,         40,           8,     0), ( 6,  0, 1)),
         (18,("AFDX",   "INT"  ,   16,         40,           8,     0), "Exception"),
         (19,("AFDX",   "INT"  ,   16,         48,           8,     0), ( 4,  0, 2)),
         (20,("AFDX",   "INT"  ,   16,         56,           8,     0), "Exception"),
         (21,("AFDX",   "INT"  ,   16,          0,           8,     0), ( 2,  0, 2)),
         (22,("AFDX",   "INT"  ,   16,         16,           8,     0), ( 0,  0, 2)),
         (23,("AFDX",   "INT"  ,   24,         16,           8,     0), "Exception"),
         (24,("AFDX",   "INT"  ,   32,         16,           8,     0), "Exception"),
         (25,("AFDX",   "INT"  ,   32,          0,           8,     0), ( 0,  0, 4)),
         (26,("AFDX",   "INT"  ,   32,         32,           8,     0), ( 4,  0, 4)),
         (27,("AFDX",   "COD"  ,    5,         36,           8,     0), ( 4,  4, 4)),
         (28,("AFDX",   "COD"  ,    5,         44,           8,     0), ( 4, 12, 4)),
         (29,("AFDX",   "COD"  ,    5,         50,           8,     0), ( 4, 18, 4)),
         (30,("AFDX",   "COD"  ,    5,         62,           8,     0), ( 0, 30, 8)),
         (31,("AFDX",   "COD"  ,    5,          1,           8,     0), ( 0,  1, 4)),
         (32,("AFDX",   "FLOAT",   16,          0,           4,     0), "Exception"),
         (33,("AFDX",   "FLOAT",   32,         48,           8,     0), "Exception"),
         (34,("AFDX",   "FLOAT",   32,         32,           8,     0), ( 4,  0, 4)),
         (35,("AFDX",   "INT"  ,   24,         32,           8,     0), "Exception"),
         (36,("AFDX",   "BYTES",   24,         32,           8,     0), ( 5,  0, 1)),
         (37,("AFDX",   "COD"  ,    7,        424,         148,     8), (60,  8, 4)),
         (38,("AFDX",   "COD"  ,    7,        431,         148,     8), (60, 15, 4)),
         (39,("AFDX",   "BYTES", 4000,          0,        1020,     8), ( 8,  0, 1)),
         (40,("AFDX",   "INT"  ,    8,         48,          28,     8), (13,  0, 1)),
         (41,("AFDX",   "INT"  ,   16,         32,          28,     8), (14,  0, 2)),
         (42,("AFDX",   "INT"  ,   64,        160,          28,     8), (24,  0, 8)),
         (43,("AFDX",   "COD"  ,   35,         96,          16,     8), (16,  0, 8)),
         (44,("AFDX",   "COD"  ,   19,         32,          12,     8), (12,  0, 4)),
         (45,("AFDX",   "COD"  ,    3,          9,           8,     8), ( 8,  9, 4)),
         (46,("AFDX",   "FLOAT",   64,         32,          16,     8), ( 8,  0, 8)),
         (47,("AFDX",   "FLOAT",   64,         96,          16,     8), (16,  0, 8)),
         (48,("AFDX",   "INT"  ,    8,         24,           8,     8), ( 8,  0, 1)),
         (49,("AFDX",   "INT"  ,    8,         16,           8,     8), ( 9,  0, 1)),
         (50,("AFDX",   "INT"  ,    8,          8,           8,     8), (10,  0, 1)),
         (51,("AFDX",   "INT"  ,    8,          0,           8,     8), (11,  0, 1)),
         (52,("AFDX",   "INT"  ,    8,         32,           8,     8), (15,  0, 1)),
         (53,("AFDX",   "INT"  ,   16,          0,           4,     8), (10,  0, 2)),
         (54,("AFDX",   "INT"  ,   16,          0,           4,    12), (14,  0, 2)),
         (55,("AFDX",   "INT"  ,   16,          0,           4,    16), (18,  0, 2)),
         (56,("AFDX",   "INT"  ,   16,          0,           4,    20), (22,  0, 2)),
         (57,("AFDX",   "INT"  ,   16,          0,           4,    28), (30,  0, 2)), 
         (58,("AFDX",   "INT"  ,   32,          0,          12,     8), ( 8,  0, 4)),
         (59,("AFDX",   "FLOAT",   32,         32,          12,     8), (12,  0, 4)),
         (60,("AFDX",   "FLOAT",   32,         64,          12,     8), (16,  0, 4)),
         (61,("AFDX",   "INT"  ,   32,          0,          12,    20), (20,  0, 4)),
         (62,("AFDX",   "FLOAT",   32,         32,          12,    20), (24,  0, 4)),
         (63,("AFDX",   "FLOAT",   32,         32,          12,    20), (24,  0, 4)),
         (64,("AFDX",   "COD"  ,    3,         12,           8,     8), ( 8, 12, 4)),
         (65,("AFDX",   "COD"  ,    3,          9,           8,     8), ( 8,  9, 4)),
         (66,("AFDX",   "COD"  ,    3,          6,           8,     8), ( 8,  6, 4)),
         (67,("AFDX",   "COD"  ,    3,          3,           8,     8), ( 8,  3, 4)),
         (68,("AFDX",   "COD"  ,    3,          0,           8,     8), ( 8,  0, 4)),
         (69,("AFDX",   "COD"  ,   19,          0,          12,     8), ( 8,  0, 4)),
         (70,("AFDX",   "COD"  ,   19,         32,          12,     8), (12,  0, 4)),
         (71,("AFDX",   "COD"  ,   19,         64,          12,     8), (16,  0, 4)),
         (72,("AFDX",   "COD"  ,   19,          0,          12,    20), (20,  0, 4)),
         (73,("AFDX",   "COD"  ,   19,         64,          12,    20), (28,  0, 4)),
         (74,("AFDX",   "COD"  ,   35,         32,          16,     8), ( 8,  0, 8)),
         (75,("AFDX",   "COD"  ,   35,         96,          16,     8), (16,  0, 8)),
         (76,("AFDX",   "COD"  ,    3,          0,          28,     8), ( 8,  0, 4)),
         (77,("AFDX",   "BNR"  ,   16,         16,          28,     8), ( 8, 16, 4)),
         (78,("AFDX",   "BNR"  ,   16,         32,          28,     8), (12,  0, 4)),
         (79,("AFDX",   "BNR"  ,    8,         48,          28,     8), (12, 16, 4)),
         (80,("AFDX",   "BNR"  ,    8,         56,          28,     8), (12, 24, 4)),
         (81,("AFDX",   "COD"  ,    6,         64,          28,     8), (16,  0, 4)),
         (82,("AFDX",   "COD"  ,    8,         72,          28,     8), (16,  8, 4)),
         (83,("AFDX",   "COD"  ,   64,        160,          28,     8), (24,  0, 8)),
         (84,("AFDX",   "COD"  ,   18,        192,          28,     8), (32,  0, 4)),
         (85,("AFDX",   "BYTES"  , 64,        0,            28,     8), (8,  0, 1)),
         (86,("AFDX",   "BYTES"  , 24,        0,            28,     8), (9,  0, 1)),
         (87,("AFDX",   "BYTES"  , 24,        8,            28,     8), "Exception"),
    )

    okcount = 0
    failedcount = 0

    for x in tc:
        try:
            res = computeSignalAccess(*x[1])
            if cmp(x[2], res) != 0:
                print "Error: TC ", x[0], ": Expected: ", x[2], "Got: ", res 
                failedcount += 1
            else:
                okcount += 1
        except Exception, e:
            if x[2] != "Exception":
                print "Error: TC ", x[0], ": Expected: ", x[2], "Got: ", str(e)
                failedcount += 1
            else:
                okcount += 1
    print "OK: %d, FAILED: %d" % (okcount, failedcount)

if __name__ == "__main__":
    testComputeSignalAccess()
    