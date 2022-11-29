import sys
from collections import defaultdict
from bunch import Bunch
from alertConstant import MAX_ALERT_ID

from imtExcelRW import readExcelFile
from iomGenSigtypes import computeSignalAccess, normalizeSigType, compatParamSignal 

# helper
filename = "NONE"

def logerror(sheet, objid, msg):
    sys.stdout.write("File %s: Sheet %s: Id %s: %s\n" % (filename, sheet, objid, msg))

def getColumnIndex(sheet):
    cidx = {}
    for col_idx in range(sheet.ncols):
        key = sval(sheet.row(0), col_idx)
        cidx[key] = col_idx
    return cidx


def sval(strToEval):
    return strToEval.encode('utf-8').strip()

def ival(intToEval, base=10):
    f = intToEval
    if type(f) == type(1.0) or type(f) == type(long(1)):
        return int(intToEval)
    elif type(f) == type(1):
        return intToEval
    else:
        s = f.encode('utf-8').strip().lower()
        if s in ["n/a","tbd","none"]:
            return None
        elif s.startswith("0x"):
            return int(s[2:], 16)
        elif s.endswith("b"):
            return int(s[0:-1], 2)
        else: 
            return int(s, base)

def fval(floatToEval):
    if type(floatToEval) == type(u"") or type(floatToEval) == type(""):
        s = floatToEval.encode('utf-8').strip().lower()
        if s in ["n/a","tbd","none"]:
            return None
    return float(floatToEval)
        


def bval(boolToEval):
    f = boolToEval
    if type(f) == type(1.0) or type(f) == type(1):
        return bool(f)
    elif type(f) == type(True):
        return f
    else:
        s = f.encode('utf-8').strip().lower()
        if s in ["n/a","tbd","none"]:
            return None
        elif s in ("yes", "y", "true", "t", "wahr", "ja", "j", "we", "si"):
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
    def __init__(self, vlid, refData, msg, vlref=None):
        self.id      = 0
        self.bag     = 0
        self.mtu     = 0
        self.nbSubVl = 0
        self.macAdd  = 0
        self.vlName  = "Undefined"
                
        if vlid != None:
            self.id      = vlid
            self.macAdd  = "03:00:00:00:"+hex(vlid>>8)[2:]+":"+hex(vlid&0xFF)[2:]
            self.macAdd  = self.macAdd.upper()
            self.vlName  = "VL_%s_%s" % (msg.lruName, str(vlid))
            self.lru  = "%s" % (msg.lruName)
            try:
                self.bag     = int(fval(refData.BAG)*1000)
            except:
                self.bag     = 0
            try:
                self.mtu     = ival(refData.MTU)
            except:
                self.mtu     = 0

            if vlref != None:
                self.nbSubVl = max(vlref.nbSubVl, msg.subVl)
            else:
                self.nbSubVl = msg.subVl
    
class AfdxMessage(object):
    '''
    Class representing an AFDX Message
    Constructor builds a message object from an excel row
    '''
    def __init__(self, msgid, afdxMsg, direction, apprate=0):
        self.msgclass       = "AFDX"
        self.direction      = direction
        self.msgUsed        = False                             # remember if message is used by a signal
        self.msgid          = msgid
        self.msgName        = sval(afdxMsg.Message)
        self.lruName        = sval(afdxMsg.TxLru)
        self.portName       = sval(afdxMsg.TxPort)
        self.fullname       = ".".join((self.lruName, self.msgName))
        self.schedRate      = 0
        self.schedOffset    = 0
        
        #Note: Not sure the evaluation functions are still needed with the use of readExcelFile function.
        
        try:
            self.portType       = sval(afdxMsg.PortType).upper()
        except:
            raise Exception, "Bad port type (SAMPLING or QUEUEING expected)"

        try:
            self.protocolType   = sval(afdxMsg.ProtocolType).upper()
        except:
            raise Exception, "Bad protocol type"
            
        if self.portType[0:3] == "SAM":
            self.portType = "SAMPLING"
        elif self.portType[0:3] == "QUE":
            self.portType = "QUEUEING"
        else:
            raise Exception, "Bad port type (SAMPLING or QUEUEING expected)"

        try:
            self.msgLength  = ival(afdxMsg.A664MsgMaxLength)
        except:
            raise Exception, "Bad message length value"

        try:
            self.msgRxLength  = ival(afdxMsg.A653MsgLength)
        except:
            if direction == 'input':
                raise Exception, "Bad receive length value"
            else:
                pass

        if self.msgLength < 1 or self.msgLength > 8192:
            raise Exception, "Bad message length value: should be between 1 and 8192"
            
            
        if self.portType[0] == "Q":
            try:
                self.queueLength    = ival(afdxMsg.PortQueueLength)
            except:
                raise Exception, "Bad queue length value"
            if self.queueLength < 1:
                raise Exception, "Bad queue length for QUEUEING port"
        else:
            self.queueLength    = 0
                        
        try:        
            self.msgTxInterval = ival(afdxMsg.TxInterval)
        except:
            if direction == 'output' and self.queueLength > 0:
                raise Exception, "Bad Transmit Tx Interval"
            else:
                self.msgTxInterval = 0

        try:
            self.msgTxRefreshPeriod = ival(afdxMsg.TxRefreshPeriod)
        except:
            raise Exception, "Bad TxRefreshPeriod"
            
        try:
            self.msgA653RefreshPeriod = ival(afdxMsg.A653PortRefreshPeriod)
        except:
            if direction == 'input' and self.queueLength > 0:
                raise Exception, "Bad Receive Refresh Period"
            else:
                self.msgA653RefreshPeriod = 0

        if self.direction == "input":
            try:
                self.msgRxSamplePeriod = ival(afdxMsg.RxSamplePeriod)
            except:
                raise Exception, "Bad RxSamplePeriod"
            
            try:
                self.msgInvalidConfirmationTime = ival(afdxMsg.InvalidConfirmationTime)
            except:
                raise Exception, "Bad InvalidConfirmationTime"
                
            try:
                self.msgValidConfirmationTime = ival(afdxMsg.ValidConfirmationTime)
            except:
                raise Exception, "Bad ValidConfirmationTime"
            
        try:
            if self.direction == 'input':
                self.portId         = ival(afdxMsg.RxComPortID)
            else:
                self.portId         = ival(afdxMsg.TxComPortID)
        except:            
            raise Exception, "No PortID defined"

        try:
            self.portName         = sval(afdxMsg.A653PortName)
        except:            
            raise Exception, "No Port Name defined"

        try:
            self.EdeActive      = bval(afdxMsg.EdeEnabled)
        except:
            raise Exception, "Bad value for EdeEnabled"
        
        if self.EdeActive:
            try:
                self.EdeSource      = ival(afdxMsg.EdeSourceId)
            except:
                raise Exception, "Bad value for EDE Source ID"
        else:
            self.EdeSource = 0
            

        try:
            self.srcPortId      = ival(afdxMsg.SourceUDP)
        except:            
            raise Exception, "Bad value for Source UDP Port"

        try:
            self.dstPortId      = ival(afdxMsg.DestUDP)
        except:
            raise Exception, "Bad value for Destination UDP Port"

        try:
            self.vlId           = ival(afdxMsg.Vlid)
        except:
            raise Exception, "Bad value for VL Id"
        
        try:
            self.subVl          = ival(afdxMsg.SubVl)
        except:
            self.subVl          = None
            
        try:
            self.dstIp          = sval(afdxMsg.DestIP)
        except:
            self.dstIp          = None

        try:
            self.macSrc         = sval(afdxMsg.SourceMAC)
            self.srcIp          = sval(afdxMsg.SourceIP)
        except:
            self.macSrc         = None
            self.srcIp          = None
        
        try:
            self.crcOffset      = ival(afdxMsg.CrcOffset)
            self.crcFsbOffset   = ival(afdxMsg.CrcFsbOffset)
            if self.crcFsbOffset is None or self.crcFsbOffset is None:
                self.crcOffset    = "None"
                self.crcFsbOffset = "None"
        except:
            self.crcOffset      = "None"
            self.crcFsbOffset   = "None"

        try:
            self.fcOffset       = ival(afdxMsg.FcOffset)
            self.fcFsbOffset    = ival(afdxMsg.FcFsbOffset)
            if self.fcFsbOffset is None or self.fcFsbOffset is None:
                self.fcOffset    = "None"
                self.fcFsbOffset = "None"
        except:
            self.fcOffset       = "None"
            self.fcFsbOffset    = "None"

        if direction == "input":
            if apprate != 0 and int(self.msgA653RefreshPeriod/2) >= int(apprate):
                # compute receive schedule rate 
                self.schedRate = int(self.msgA653RefreshPeriod/2) / int(apprate) 
            else:
                self.schedRate = 1
        else:
            if apprate != 0 and int(self.msgTxInterval) >= int(apprate):
                # compute receive schedule rate 
                self.schedRate = int(self.msgTxInterval) / int(apprate) 
            else:
                self.schedRate = 1

class CanMessage(object):
    '''
    Class representing an CAN Message
    Constructor builds a message object from an excel row
    '''
    def __init__(self, msgid, canMsg, direction):
        self.msgclass       = "CAN"
        self.direction      = direction
        self.msgUsed        = False                             # remember if message is used by a signal
        self.msgid          = msgid
        self.msgName        = sval(canMsg.Message)
        self.lruName        = sval(canMsg.TxLru)
        self.portName       = sval(canMsg.TxPort)
        self.fullname       = ".".join((self.lruName, self.msgName))

        try:
            self.msgLength  = ival(canMsg.A825MsgLength)
        except:
            raise Exception, "Bad message length value"
        if self.msgLength < 1 or self.msgLength > 8:
            raise Exception, "Bad CAN message length value: should be between 1 and 8"
            
        try:
            self.msgRate    = ival(canMsg.TxInterval)
        except:
            raise Exception, "Bad value for CAN Message TxInterval"
        
        try:
            self.msgTxRefreshPeriod = ival(canMsg.TxRefreshPeriod)
        except:
            raise Exception, "Bad TxRefreshPeriod"
            
        if self.direction == "input":
            try:
                self.msgRxSamplePeriod = ival(canMsg.RxSamplePeriod)
            except:
                raise Exception, "Bad RxSamplePeriod"
                
            try:
                self.msgInvalidConfirmationTime = ival(canMsg.InvalidConfirmationTime)
            except:
                raise Exception, "Bad InvalidConfirmationTime"
                
            try:
                self.msgValidConfirmationTime = ival(canMsg.ValidConfirmationTime)
            except:
                raise Exception, "Bad ValidConfirmationTime"

        try:
            self.msgCanID       = ival(canMsg.CanMsgID, base=16)
        except:            
            raise Exception, "Bad value for CAN Message ID"

        try:
            self.msgPhysPort    = sval(canMsg.PhysPort)
        except:            
            raise Exception, "Bad value for CAN Receive Port"

class A429Port(object):
    def __init__(self, portName, portId, physPort, direction, portType="QUEUING", queueLength=4):
        self.portName       = portName
        self.portId         = portId
        self.physPort       = physPort
        self.portDirection  = direction
        self.portType       = portType
        self.queueLength    = queueLength
        self.msgSize        = 4
        
        
class A429Label(object):
    '''
    Class representing an A429 Label
    Constructor builds a message object from an excel row
    Port parameters are gathered in a A429Port object added to the portDict
    '''
    def __init__(self, msgid, a429Label, direction, portDict):
        self.msgclass       = "A429"
        self.direction      = direction
        self.msgUsed        = False         # remember if message is used by a signal
        self.msgid          = msgid
        self.lruName        = sval(a429Label.TxLru)
        self.msgName        = sval(a429Label.Message)
        self.portName       = sval(a429Label.TxPort)
        self.fullname       = ".".join((self.lruName, self.msgName))
        self.msgLength      = 4

        try:
            physPort    = sval(a429Label.PhysPort)
        except:            
            raise Exception, "Bad value for A429 Physical Port"
        
      
        portName = physPort
        port = portDict.get(portName)
        if not port:
            port = A429Port(portName, len(portDict) + 1, physPort, direction)
            portDict[portName] = port
        
        self.portId = port.portId
        
        try:
            self.msgRate        = ival(a429Label.TxInterval)
        except:
            raise Exception, "Bad value for A429 Label transmission TxInterval"
        try:
            self.msgLabel       = ival(a429Label.LabelID, base=8)
        except:            
            raise Exception, "Bad value for A429 LabelID"

        try:
            self.msgSDI         = ival(a429Label.SDI)
        except:            
            raise Exception, "Bad value for A429 SDI"
        
        self.msgPhysPort = physPort

        try:
            self.msgTxRefreshPeriod = ival(a429Label.TxRefreshPeriod)
        except:
            raise Exception, "Bad TxRefreshPeriod"

        if self.direction == "input":
            try:
                self.msgRxSamplePeriod = ival(a429Label.RxSamplePeriod)
            except:
                raise Exception, "Bad RxSamplePeriod"
                    
            try:
                self.msgInvalidConfirmationTime = ival(a429Label.InvalidConfirmationTime)
            except:
                raise Exception, "Bad InvalidConfirmationTime"
                
            try:
                self.msgValidConfirmationTime = ival(a429Label.ValidConfirmationTime)
            except:
                raise Exception, "Bad ValidConfirmationTime"            
                        
VALIDITY_FRESHNESS      = 1
VALIDITY_A664FSB        = 2
VALIDITY_A429SSM_BNR    = 4
VALIDITY_A429SSM_BCD    = 8
VALIDITY_A429SSM_DIS    = 16
VALIDITY_PARAM          = 32
VALIDITY_RANGE_INT      = 64
VALIDITY_RANGE_UINT     = 128
VALIDITY_RANGE_FLOAT    = 256
VALIDITY_RANGE_FLOATBNR = 512
VALIDITY_A429SSM_CUSTOM    = 1024
VALIDITY_A429SSM        = (VALIDITY_A429SSM_DIS | VALIDITY_A429SSM_BNR | VALIDITY_A429SSM_BCD | VALIDITY_A429SSM_CUSTOM)

    
class InputSignal(object):
    def __init__(self, inputSignal, message, ddmap, signalXref, noparams=False):
        '''
        inputSignal: InputSignal record from Excel Reader
        message:     message object 
        ddmap:       ddmap (parameter - offset) dictionary, indexed by parameter name
        signalXref:  dictionary of all currently collected signal records, indexed by RP name
        noparams:    flag to ignore parameters
                        when called with noparam=True, we ignore DD-RP and DD offset map
                        such a model can not be used for generation of IOM configuration
                        but can be used to generate system level test system configuration
        '''
        
        if noparams:
            paramname    = None
            datatype     = None
            datasize     = None
            paramtype    = None
            paramoffset  = None
            statusoffset = None
        else:
            paramname = sval(inputSignal.Parameter)
            datatype  = sval(inputSignal.DataType)
            datasize  = ival(inputSignal.DataSize)

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
                        raise Exception, "Missing Status Variable for Variable %s (expected _Status)" % paramname
                else:
                    paramtype    = datatype
                    paramoffset  = -1
                    paramelem    = -1
                    statusoffset = -1
            
                if not ((datatype == paramtype) or  \
                        (datatype == "COUNT" and paramtype == "INT") or \
                        (datatype == "BYTES" and paramtype == "CHAR")):
                    raise Exception, "Incompatible data types: Model Parameter: %s,  ICD Map: %s" % \
                        (ddmap[paramname].type, datatype)
                        
                if (datatype == "BYTES" and datasize != paramelem * 8):
                    raise Exception, "Incompatible data size for %s: Model: %d,  IOLIST: %d" % \
                        (paramname, paramelem, datasize)
                    
        
        self.msgRef           = message           
        self.signalsRef       = signalXref
        self.paramName        = paramname
        self.paramDatatype    = datatype
        self.paramDatasize    = datasize
        self.paramOffset      = paramoffset
        self.paramOffsetStatus= statusoffset
        self.busType          = sval(inputSignal.BusType)
        self.rpName           = sval(inputSignal.RpName)
        self.pubref           = sval(inputSignal.Pubref)
        self.dsName           = sval(inputSignal.DataSet)
        self.dsDsOffset       = ival(inputSignal.DSOffset)
        self.dsDsSize         = ival(inputSignal.DSSize)
        self.sigName          = sval(inputSignal.DpName)
        self.sigDsOffset      = ival(inputSignal.BitOffsetWithinDS)
        self.sigSize          = ival(inputSignal.ParameterSize)
        self.sigType          = normalizeSigType(sval(inputSignal.ParameterType), self.sigSize)
        self.paramMin         = "TBD"
        self.paramMax         = "TBD"  
        
        if self.sigType == "BCD":
            try:
                self.sigLsbValue  = fval(inputSignal.Multiplier)
                if self.sigLsbValue == None:
                    self.sigLsbValue = 1
            except:
                self.sigLsbValue = 1
        elif self.sigType in ("BNR","UBNR","UINT","SINT"):
            try:
                self.sigLsbValue  = fval(inputSignal.LsbRes)
                if self.sigLsbValue == None:
                    self.sigLsbValue = 1
            except:
                self.sigLsbValue  = 1
        else:
            self.sigLsbValue  = 1
          
        try:
            self.alertId     = ival(inputSignal.AlertID)
        except:
            self.alertId     = None

        if self.alertId is not None:
            if self.alertId > MAX_ALERT_ID:
                raise Exception, "Bad alert ID: Expect integer value in the range 1-2000"
            self.sigDsOffset   = (30+((int)((self.alertId-1)/16))*32) - (((self.alertId-1)%16) *2 )        # bit offset within DataSet
            self.sigSize       = 2;
            self.sigType       = "COD";
            
        if self.sigType == "UNFRESH":
            self.sigByteOffset = 0
            self.sigBitOffset = 0
            self.sigAccess = 0
        else:
            self.sigByteOffset, self.sigBitOffset, self.sigAccess = computeSignalAccess(
                  self.msgRef.msgclass, self.sigType, 
                  sigsize   = self.sigSize,
                  sigoffset = self.sigDsOffset,
                  dssize    = self.dsDsSize,
                  dspos     = self.dsDsOffset, 
            )

        sselstr     = sval(inputSignal.ValidityCriteria)
        ssel        = [p.strip().upper() for p in sselstr.split(',')]
        
        try:
            self.sourceName = sval(inputSignal.SourceName)
            self.selectionOrder = ival(inputSignal.SelectionOrder)
        except:
            self.sourceName = ""
            self.selectionOrder = 0

        self.sourceSelect = 0
        for p in ssel:
            if p == "FRESH":
                self.sourceSelect |= VALIDITY_FRESHNESS
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
            elif p == "SSM_CUSTOM":
                if self.sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                    raise Exception, "Illegal source selection method: %s" % sselstr
                self.sourceSelect |= VALIDITY_A429SSM_CUSTOM
            elif p == "PARAM":
                self.sourceSelect |= VALIDITY_PARAM
                self.validityParamName  = sval(inputSignal.ValidityParamName)
                self.validityParamValue = ival(inputSignal.ValidityParamValue)
            elif p == "RANGE_INT" or p == "RANGE_UINT":
                if p == "RANGE_INT":
                    self.sourceSelect |= VALIDITY_RANGE_INT
                else:
                    self.sourceSelect |= VALIDITY_RANGE_UINT
                self.paramMin = ival(inputSignal.PublisherFunctionalMinRange)
                self.paramMax = ival(inputSignal.PublisherFunctionalMaxRange)
            elif p == "RANGE_FLOAT":
                self.sourceSelect |= VALIDITY_RANGE_FLOAT
                self.paramMin = fval(inputSignal.PublisherFunctionalMinRange)
                self.paramMax = fval(inputSignal.PublisherFunctionalMaxRange)
            elif p == "RANGE_FLOATBNR":
                self.sourceSelect |= VALIDITY_RANGE_FLOATBNR
                self.paramMin = fval(inputSignal.PublisherFunctionalMinRange)
                self.paramMax = fval(inputSignal.PublisherFunctionalMaxRange)                
            elif p != '':
                raise Exception, "Illegal source selection method: %s" % sselstr
        
        if self.sourceSelect & VALIDITY_A664FSB:
            self.dsFsbOffset      = ival(inputSignal.FsbOffset)
        else:
            self.dsFsbOffset      = None
            
        if ddmap != None:
            self.selectionSet   = "None"
        
            if self.paramDatatype == "FLOAT":
                self.paramDefault   = fval(inputSignal.DefaultVal)
                #self.paramMin       = fval(inputSignal.FunctionalMinRange)
                #self.paramMax       = fval(inputSignal.FunctionalMaxRange)
            else:
                self.paramDefault   = ival(inputSignal.DefaultVal)
                #self.paramMin       = ival(inputSignal.FunctionalMinRange)
                #self.paramMax       = ival(inputSignal.FunctionalMaxRange)
        
               
        if not noparams:
            compatParamSignal(self.paramName, self.paramDatatype, self.paramDatasize, self.sigType, self.sigSize)
            
    def sselFreshness(self):
        return self.sourceSelect & VALIDITY_FRESHNESS
    
    def sselRangeInt(self):
        return self.sourceSelect & VALIDITY_RANGE_INT
    
    def sselRangeUInt(self):
        return self.sourceSelect & VALIDITY_RANGE_UINT
        
    def sselRangeFloat(self):
        return self.sourceSelect & VALIDITY_RANGE_FLOAT
        
    def sselRangeFloatBnr(self):
        return self.sourceSelect & VALIDITY_RANGE_FLOATBNR
        
    def sselValParam(self):
        return self.sourceSelect & VALIDITY_PARAM
    
    def sselValParamData(self):
        '''
        return a bunch with msgid, offset, mask and value for constructing the condition
        '''
        # find input signal definition referred to by validityParam field
        sigs = self.signalsRef.get(self.validityParamName)
        if not sigs:
            logerror("Input Signals", self.paramName, 
                     "Parameter referred to by MaskValidParam not found: %s" % self.validityParamName)
            return None

        if len(sigs) > 1:
            logerror("Input Signals", self.paramName, 
                     "Parameter referred to by MaskValidParam not unique: %s" % self.validityParamName)
            return None
            
        sig = sigs[0]
        res = Bunch(
            msgid  = sig.msgRef.msgid,
            lsb    = sig.sigBitOffset,
            lsbval = sig.sigLsbValue,
            offset = sig.sigByteOffset,
            access = sig.sigAccess,
            bits   = sig.sigSize,
            value  = self.validityParamValue
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

    def sselA429SSM_CUSTOM(self):
        return self.sourceSelect & VALIDITY_A429SSM_CUSTOM
		
    def getSelectionOrder(self):                
        return self.selectionOrder 
            
class OutputSignal(object):
    def __init__(self, outputSignal, message, ddmap, noparams=False):
        '''
        outputSignal: OutputSignals record from Excel Reader
        message:     message object 
        ddmap:       ddmap (parameter - offset) dictionary, indexed by parameter name
        noparams:    flag to ignore parameters
        '''

        if noparams:
            paramname   = None
            datatype    = None
            datasize    = None
            paramtype   = None
            paramoffset = None
            statusoffset= None
        else:
            paramname = sval(outputSignal.Parameter)
            datatype  = sval(outputSignal.DataType)
            datasize  = ival(outputSignal.DataSize)
        
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
        
        self.msgRef           = message           
        self.paramName        = paramname
        self.paramDatatype    = datatype
        self.paramDatasize    = datasize
        self.paramOffset      = paramoffset
        self.paramOffsetStatus= statusoffset
        self.busType          = sval(outputSignal.BusType)
        self.dsName           = sval(outputSignal.DataSet)
        self.dsDsOffset       = ival(outputSignal.DSOffset)
        self.dsDsSize         = ival(outputSignal.DSSize)
        self.DpName           = sval(outputSignal.DpName)
        self.sigDsOffset      = ival(outputSignal.BitOffsetWithinDS)
        self.sigSize          = ival(outputSignal.ParameterSize)
        self.sigType          = normalizeSigType(sval(outputSignal.ParameterType), self.sigSize)
        if self.sigType == "BCD":
            try:
                self.sigLsbValue  = fval(outputSignal.Multiplier)
                if self.sigLsbValue == None:
                    self.sigLsbValue = 1                
            except:
                self.sigLsbValue = 1
        elif self.sigType in ("BNR", "UBNR", "UINT", "SINT"):
            try:
                self.sigLsbValue  = fval(outputSignal.LsbRes)
                if self.sigLsbValue == None:
                    self.sigLsbValue = 1
            except:
                self.sigLsbValue  = 1
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

        #TODO: To Be Investigated. Is there any other Used value (e.g. VALIDITY_A429SSM)?
        #validstr    = sval(row, cidx["Validity"])
        #validlst    = [p.strip().upper() for p in validstr.split(',')]
        
        self.validity = 0
        
        #TODO: To Be Investigated. Is there any other Used value (e.g. VALIDITY_A429SSM)?
        # At least BLK case, we don't want to consider the FSB
        if sval(outputSignal.ParameterType) != "BLK":
            self.validity |= VALIDITY_A664FSB
        #for p in validlst:
        #    if p == "FSB":
        #        self.validity |= VALIDITY_A664FSB
        #    elif p == "SSM_BNR":
        #        if self.validity & VALIDITY_A429SSM:     # check there is only one SSM mode 
        #            raise Exception, "Illegal validity method: %s" % sselstr
        #        self.validity |= VALIDITY_A429SSM_BNR
        #    elif p == "SSM_DIS":
        #        if self.validity & VALIDITY_A429SSM:     # check there is only one SSM mode 
        #            raise Exception, "Illegal validity method: %s" % sselstr
        #        self.validity |= VALIDITY_A429SSM_DIS
        #    elif p == "SSM_BCD":
        #        if self.validity & VALIDITY_A429SSM:     # check there is only one SSM mode 
        #            raise Exception, "Illegal validity method: %s" % sselstr
        #        self.validity |= VALIDITY_A429SSM_BCD
        #    elif p != '':
        #        raise Exception, "Illegal validity method: %s" % sselstr
            
        if self.validity & VALIDITY_A664FSB:
            self.dsFsbOffset      = ival(outputSignal.FsbOffset)
        else:
            self.dsFsbOffset      = None

        if not noparams:
            compatParamSignal(self.paramName, self.paramDatatype, self.paramDatasize, self.sigType, self.sigSize)
                
            
    def sselA664Fsb(self):
        return self.validity & VALIDITY_A664FSB

    def sselA429SSM(self):
        return self.validity & VALIDITY_A429SSM

                
class MapReader(object):
    def __init__(self, fname, dd=None, msgonly=False, noparams=False, 
                 direction='input', apprate=0, ignoreSrc=False):
        
        global filename
        filename = fname
        
        self.errorCount = 0
        
        # should be read from the mapping file, but is not propagated yet
        self.identification = Bunch(application="", revision="", icd="")

        if direction == 'input':
            # Read Excel Map File
            afdxInputMsgs,  canInputMsgs, inputA429Labels, inputSignals  =  \
                readExcelFile(filename, ('InputAfdxMessages' , 'InputCanMessages' , 'InputA429Labels' ,'InputSignals'))
            if ignoreSrc:
                sourceTable = []
            else:
                sourceTable = readExcelFile(filename, ('Sources',))[0]
    
            self.afdx           = self.readAfdxMessages(afdxInputMsgs, direction, apprate)                
            self.can            = self.readCanMessages(canInputMsgs, direction, apprate)    
            self.a429           = self.readA429Labels(inputA429Labels, direction, apprate)
            
            self.parameters     = dict()

            # these are needed only by the reader and not used by the applications
            self.sourceXref     = defaultdict(list)
            self.signalXref     = defaultdict(list)
        
            if not msgonly:
                self.readInputSignals(dd, inputSignals, noparams)
            
            self.selectionSets   = self.readSources(sourceTable)
            
        else:
            # Read Excel Map File
            afdxOutputMsgs,  canOutputMsgs, ouputA429Labels, outputSignals,  =  \
            readExcelFile(filename, ('OutputAfdxMessages' , 'OutputCanMessages' , 'OutputA429Labels' ,'OutputSignals'))
            
            self.afdx           = self.readAfdxMessages(afdxOutputMsgs, direction, apprate)
            self.afdx.datasets = dict()
            self.can            = self.readCanMessages(canOutputMsgs, direction, apprate)
            self.a429           = self.readA429Labels(ouputA429Labels, direction, apprate)
            
            self.parameters      = dict()

            if not msgonly:
                self.readOutputSignals(dd, outputSignals, noparams)

    def logerr(self, sheet, objid, msg):
        logerror(sheet, objid, msg)
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
        
    def readAfdxMessages(self, afdxMsgs, direction, apprate=0):
        messages    = dict()
        vls         = dict()
        messageKeys = list()
        msgidx      = 0
        schedtab = defaultdict(list)

        for afdxMsg in afdxMsgs:
            if sval(afdxMsg.Status).startswith("Ignore"):
                continue

            msgidx += 1
            msgname = sval(afdxMsg.UniqueKey)
            try:
                newmessage = AfdxMessage(msgidx, afdxMsg, direction, apprate)
                messages[msgname] = newmessage
            except Exception, msg:
                self.logerr("Afdx %s messages" % direction, msgname, str(msg) + ' - message skipped')
                continue

            messageKeys.append(msgname)
            #check and update the VL if necessary:
            vlId = messages[msgname].vlId
            vls[vlId] = Vl(vlId, afdxMsg, messages[msgname], vls.get(vlId))
            
            # maintain a dictionary of messages by rate.
            if apprate != 0:
                schedtab[newmessage.schedRate].append(newmessage)
                
        # distribute load by starting message processing cycle in different frames 
        if apprate != 0:
            for rate, msglist in schedtab.items():
                offset = 0
                for msg in msglist:
                    msg.schedOffset = offset
                    offset = (offset + 1) % rate

        return Bunch(messages=messages, vls=vls, messageKeys=messageKeys, signals=dict())

    def readCanMessages(self, canMsgs, direction, apprate=0):

        messages    = dict()
        messageKeys = []
        msgidx      = 0

        for canMsg in canMsgs:
            if sval(canMsg.Status).startswith("Ignore"):
                continue
            msgidx += 1
            msgname = sval(canMsg.UniqueKey)
            try:
                messages[msgname] = CanMessage(msgidx, canMsg, direction)
            except Exception, msg:
                self.logerr("CAN %s messages" % direction, msgname, str(msg) + ' - message skipped')
                continue

            messageKeys.append(msgname)

        return Bunch(messages=messages, messageKeys=messageKeys, signals=dict())

    def readA429Labels(self, a429Labels, direction, apprate=0):
        messages    = dict()
        ports       = dict()
        messageKeys = []
        msgidx      = 0

        for a429Label in a429Labels:
            if sval(a429Label.Status).startswith("Ignore"):
                continue
            msgidx += 1
            msgname = sval(a429Label.UniqueKey)
            try:
                messages[msgname] = A429Label(msgidx, a429Label, direction, ports)
            except Exception, msg:
                self.logerr("A429 %s labels" % direction, a429Label, str(msg) + ' - label skipped')
                continue
            messageKeys.append(msgname)

        return Bunch(ports=ports, messages=messages, messageKeys=messageKeys, signals=dict())

    def readInputSignals(self, ddmap, inputSignals, noparams):

        for inputSignal in inputSignals:
            if sval(inputSignal.Status).startswith('Ignore'):
                continue

            # identify message the signal belongs too
            msgRef = sval(inputSignal.MessageRef)
            message = self.afdx.messages.get(msgRef)
            if message is None:
                message = self.can.messages.get(msgRef)
                if message is None:
                    message = self.a429.messages.get(msgRef)
                    if message is None:
                        self.logerr("Input Signals", inputSignal.RpName, "Message %s not found in input message sheets" % msgRef)
                        continue
            
            try:
                sig = InputSignal(inputSignal, message, ddmap, self.signalXref, noparams)
            except Exception, excmsg:
                self.logerr("Input Signals", inputSignal.RpName, str(excmsg))
                continue

            if (sig.sigType == "PAD"):
                continue

            self.sourceXref[sig.sourceName].append(sig)
            self.signalXref[sig.rpName].append(sig)
                    
            message.msgUsed = True
            
            if sig.paramOffset != -1 or noparams:
                if sig.paramName not in self.parameters:
                    self.parameters[sig.paramName] = list()
                self.parameters[sig.paramName].append(sig)

                if message.msgclass == 'AFDX':
                    if msgRef not in self.afdx.signals:
                        self.afdx.signals[msgRef] = list()
                    self.afdx.signals[msgRef].append(sig)
                elif message.msgclass == 'A429':
                    if msgRef not in self.a429.signals:
                        self.a429.signals[msgRef] = list()
                    self.a429.signals[msgRef].append(sig)
                elif message.msgclass == 'CAN':
                    if msgRef not in self.can.signals:
                        self.can.signals[msgRef] = list()
                    self.can.signals[msgRef].append(sig)
                    
        for siglist in self.parameters.values():
            siglist.sort(key=InputSignal.getSelectionOrder)

    def readOutputSignals(self, ddmap, outputSignals, noparams):

        for outputSignal in outputSignals:
            if sval(outputSignal.Status).startswith('Ignore'):
                continue

            # identify message the signal belongs too
            msgRef = sval(outputSignal.MessageRef)
            message = self.afdx.messages.get(msgRef)
            if message is None:
                message = self.can.messages.get(msgRef)
                if message is None:
                    message = self.a429.messages.get(msgRef)
                    if message is None:
                        self.logerr("Output Signals", outputSignal.DpName, "Message %s not found in output message sheets" % msgRef)
                        continue
            try:
                sig = OutputSignal(outputSignal, message, ddmap, noparams)
            except Exception, excmsg:
                self.logerr("Output Signals", outputSignal.DpName, str(excmsg))
                continue

            if (sig.sigType == "PAD"):
                continue

            message.msgUsed = True
            
            if sig.paramOffset != -1 or noparams:
                if sig.paramName not in self.parameters:
                    self.parameters[sig.paramName] = list()
                self.parameters[sig.paramName].append(sig)

                if message.msgclass == 'AFDX':
                    # used by genXml
                    dskey = (message.fullname, sig.dsName)
                    if dskey not in self.afdx.datasets:
                        self.afdx.datasets[dskey] = list()
                    self.afdx.datasets[dskey].append(sig)
                    # used by genAds2
                    if msgRef not in self.afdx.signals:
                        self.afdx.signals[msgRef] = list()
                    self.afdx.signals[msgRef].append(sig)
                elif message.msgclass == 'CAN':
                    if msgRef not in self.can.signals:
                        self.can.signals[msgRef] = list()
                    self.can.signals[msgRef].append(sig)
                elif message.msgclass == 'A429':
                    if msgRef not in self.a429.signals:
                        self.a429.signals[msgRef] = list()
                    self.a429.signals[msgRef].append(sig)
    

    def readSources(self, sourceTable):
        
        def mkCond(seltype, sigmap):
            if seltype == "A429SSM":
                valflg = sigmap.sourceSelect
                if valflg & VALIDITY_A429SSM_BCD:
                    seltype = "A429SSM_BCD"
                elif valflg & VALIDITY_A429SSM_BNR:
                    seltype = "A429SSM_BNR"
                elif valflg & VALIDITY_A429SSM_DIS:
                    seltype = "A429SSM_DIS"
                else:
                    logerror("Sources", "Bad SSM")
                    seltype = "A429SSM_DIS"
                    
            return Bunch(condType=seltype, sigRef = sigmap)
            
        selSets = {}
        
        for source in sourceTable:

            src = Bunch(
                sourceName          = sval(source.SourceName),
                selectionSet        = sval(source.SelectionSet),
                selectionOrder      = ival(source.SelectionOrder),
                selectionCriteria   = sval(source.SelectionCriteria),
                granularity         = sval(source.Granularity),
                LICparam            = sval(source.LICParameter),
                LICvalue            = ival(source.LICValue),
                lockInterval        = "0",
                conditions          = []
            )
            try:
                src.lockInterval = str(ival(source.LockInterval))
            except:
                s = sval(source.LockInterval)
                if s == "Permanent":
                    src.lockInterval = s
                else:
                    logerror("Sources", src.sourceName, 
                             "Bad value for LockInterval: Expect integer number or Permanent")
            
            
            sigmaps = self.sourceXref[src.sourceName]
            if sigmaps:
                src.selectionSet = src.selectionSet + '.' + sigmaps[0].paramName
                # cross link signals to selection set, needed for generating the XML output
                for sig in sigmaps:
                    sig.selectionSet = src.selectionSet

            
            if not selSets.has_key(src.selectionSet):
                selSets[src.selectionSet] = Bunch(
                        selectionCriteria = src.selectionCriteria,
                        lockInterval = src.lockInterval,
                        sources = []
                    ) 
                    
            selSets[src.selectionSet].sources.append(src)
            
            if src.selectionCriteria == "OBJECT_VALID":
                # extract conditions
                maplist = self.sourceXref[src.sourceName]
                if not maplist:
                    logerror("Sources", src.sourceName, "Unused source, discarded")
                    continue
                map0 = maplist[0]

                if src.granularity == "Message":
                    src.conditions = [mkCond("FRESH", map0)]
                elif src.granularity == "DataSet":
                    src.conditions = [mkCond("FRESH", map0), 
                                         mkCond("A664FS", map0)]
                elif src.granularity == "Container":
                    src.conditions = [mkCond("FRESH", map0), 
                                         mkCond("A664FS", map0), 
                                         mkCond("A429SSM", map0)]
                elif src.granularity == "Parameter":
                    # conditions list remains empty, selection is done by parameter validity
                    src.conditions = []
                elif src.granularity == "Custom":
                    # OBJECT_VALID with CUSTOM not supported
                    src.conditions = []
                    logerror("Sources", src.sourceName, "OBJECT_VALID source selection criteria not supported for granularity Custom")
                    # discard this source
                    continue
                else:
                    src.conditions = []
                    logerror("Sources", src.sourceName, "Unknown source selection criteria: %s" % src.selectionCriteria)
                    # discard this source
                    continue
                
        for selset in selSets.values():            
            selset.sources.sort(key=getSourceSelectionOrder)

        return selSets
    
# used for sorting the sources
def getSourceSelectionOrder(source):
    return source.selectionOrder
    
            