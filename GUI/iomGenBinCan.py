'''
Created on 30.11.2014

@author: dk

IOM Binary Config Generator for CAN
'''

from bunch import Bunch
import struct

from iomGenBinConst import IOM
from iomGenBinEndian import ENDIAN
from stringtab import stringtable

# --------------------------------------------------------------
# CAN Input: 
# --------------------------------------------------------------

encoding_table_input = {
    ("INT",   1,   "INT"):   IOM.SIGINTYPE_INT8,
    ("INT",   2,   "INT"):   IOM.SIGINTYPE_INT16,
    ("INT",   4,   "INT"):   IOM.SIGINTYPE_INT32,

    ("UINT",  1,  "INT"):    IOM.SIGINTYPE_UINT8,
    ("UINT",  2,  "INT"):    IOM.SIGINTYPE_UINT16,
    ("UINT",  4,  "INT"):    IOM.SIGINTYPE_UINT32,

    ("FLOAT", 4, "FLOAT"):   IOM.SIGINTYPE_FLOATS,

    ("BOOL",  1, "BOOL"):    IOM.SIGINTYPE_BOOL_8BIT,
    ("BOOL",  1, "INT"):     IOM.SIGINTYPE_CODED8,
    ("BOOL",  4, "BOOL"):    IOM.SIGINTYPE_BOOL,
    ("BOOL",  4, "INT"):     IOM.SIGINTYPE_CODED32,
    ("COD",   4, "ENUM"):    IOM.SIGINTYPE_CODED32,
    ("COD",   1, "INT"):     IOM.SIGINTYPE_CODED8,
    ("COD",   4, "INT"):     IOM.SIGINTYPE_CODED32,
    ("COD",   8, "ENUM"):    IOM.SIGINTYPE_CODED64,
    ("COD",   8, "INT"):     IOM.SIGINTYPE_CODED64,
    ("BYTES", 1, "OPAQUE"):  IOM.SIGINTYPE_OPAQUE, 
    ("INT",   1, "COUNT"):   IOM.SIGINTYPE_INT8_ADD,
}

encoding_table_output = {
        ('INT',      1, 'INT'):    IOM.SIGOUTTYPE_BITFIELD32,
        ('UINT',     1, 'INT'):    IOM.SIGOUTTYPE_BITFIELD32,
        ('INT',      2, 'INT'):    IOM.SIGOUTTYPE_BITFIELD32,
        ('UINT',     2, 'INT'):    IOM.SIGOUTTYPE_BITFIELD32,
        ('INT',      4, 'INT'):    IOM.SIGOUTTYPE_SIG32,
        ('UINT',     4, 'INT'):    IOM.SIGOUTTYPE_SIG32,
        ('BOOL',     4, 'BOOL'):   IOM.SIGOUTTYPE_A664_BOOLEAN,
        ('COD',      4, 'ENUM'):   IOM.SIGOUTTYPE_BITFIELD32,
        ('COD',      4, 'INT'):    IOM.SIGOUTTYPE_BITFIELD32,
        ('BYTES',    1, 'BYTES'):  IOM.SIGOUTTYPE_MULTIPLE_BYTES,
        ('VALIDITY', 4, 'BOOL'):   IOM.SIGOUTTYPE_VALIDITY_STATUS,
}

# Global data
parameter_offset     = 0        # next offset into internal parameter buffer for storing data from all sources  
outParam_size        = 0        # stores the largest param offset, so the buffer size can be calculated
numberOfInputParams  = 0        # used for calculating buffer sizes  
numberOfInputSignals = 0        # used for calculating buffer sizes  
numberOfOutputParams = 0        # used for calculating buffer sizes  
externalParamSize    = 0        # used for calculating buffer sizes  


def paramOffsetInternalBuffer(sizeBytes):
    global parameter_offset

    offset = parameter_offset
    
    parameter_offset += sizeBytes
    
    return offset

# 
# Build functions: convert the XML tag into corresponding binary structure
# side effect: build up string table and message dictionary + message offset
#

def buildConditions(xmllogic, byteoffsetSig, bitlenSig, lsbSig, accessSig, scaleSig):
    '''
    Build one logicSource config  structure from XML
    '''

    useFloat      = 0
    numconditions = 0
    conditions    = ""
    condtypes     = [0, 0]

    for x in xmllogic.iterfind("condition"):
        msgIdx      = 0 # Not used
        transportId = IOM.TRANSPORT_A825
        t           = x.attrib["type"].lower()

        if t == "validity_input":
            condtype = IOM.CONDTYPE_VALIDITY_PARAM
            offset   = int(x.attrib["offset"])
            access   = int(x.attrib["access"])
            sizeBits = int(x.attrib["bits"])
            offBits  = int(x.attrib["lsb"])
            scale    = float(x.attrib["lsbvalue"])
            min      = int(x.attrib["value"])
            max      = int(x.attrib["value"])
        elif t == "range_int":
            condtype = IOM.CONDTYPE_RANGE_INT
            offset   = byteoffsetSig
            access   = accessSig
            sizeBits = bitlenSig
            offBits  = lsbSig
            scale    = scaleSig
            min      = int(x.attrib["min"])
            max      = int(x.attrib["max"])
        elif t == "range_float":
            condtype   = IOM.CONDTYPE_RANGE_FLOAT
            offset   = byteoffsetSig
            access   = accessSig
            sizeBits = bitlenSig
            offBits  = lsbSig
            scale    = scaleSig
            minf     = float(x.attrib["min"])
            maxf     = float(x.attrib["max"])
            useFloat = 1
        else:
            raise Exception, "Illegal condition type: %s" % t

        if useFloat == 1:
            cond = struct.pack(ENDIAN + "hhIIIIfff", msgIdx, transportId, offset, access, sizeBits, offBits, scale, minf, maxf)
        else:
            cond = struct.pack(ENDIAN + "hhIIIIfii", msgIdx, transportId, offset, access, sizeBits, offBits, scale, min, max)

        condtypes[numconditions] = condtype

        conditions += cond
        numconditions += 1

    extraConditions = 0
    for i in range (0,2-numconditions):
        cond = struct.pack(ENDIAN + "hhIIIIfii", 0, 0, 0, 0, 0, 0, 0.0, 0, 0)  # Padding
        condtypes[numconditions + i] = IOM.CONDTYPE_INVALID
        conditions      += cond
        extraConditions += 1

    if (extraConditions + numconditions) > 4:
        raise Exception, "Too many Validation conditions: %s" % (extraConditions + numconditions)

    hdr = struct.pack(ENDIAN + "hhbbbb", numconditions, 0, 
                                 condtypes[0], condtypes[1], 0, 0)
    return hdr + conditions


def buildCanOutputParam(xpar):

    paramNameValue  = xpar.attrib["paramNameValue"]
    paramNameStatus = xpar.attrib["paramNameStatus"]
    paramType       = xpar.attrib["paramType"]


    signal = ""
    count  = 0
    for xdest in xpar.iterfind("destination"):

        sigtype    = xdest.attrib["type"]
        access     = int(xdest.attrib["access"])
        byteoffset = int(xdest.attrib["offset"])
        bitlen     = int(xdest.attrib["bits"])
        lsb        = int(xdest.attrib["lsb"])
        scale      = float(xdest.attrib["lsbvalue"])
        
        if sigtype == "VALIDITY":
            encoding = IOM.SIGOUTTYPE_VALIDITY_STATUS
        else:
            key        = (sigtype, access, paramType)
            encoding   = encoding_table_output.get(key)

        if encoding is None:
            raise Exception, "Bad parameter-signal type combination for %s: %s" % (paramNameValue, str(key))

        signal += struct.pack(ENDIAN + "Iihhf", byteoffset, bitlen, lsb, encoding, scale)
        count  += 1

    valueOffset      = int(xpar.attrib["paramOffsetValue"])
    statusOffset     = int(xpar.attrib["paramOffsetStatus"])

    if valueOffset > max_param:
        max_param = valueOffset

    if statusOffset > max_param:
        max_param = statusOffset

    param = struct.pack (ENDIAN + "iihhiiL",
                            valueOffset,
                            statusOffset,
                            count,                                 # number of destinations to write to
                            0,                                     # spare 0
                            stringtable.append(paramNameValue),
                            stringtable.append(paramNameStatus),
                            0                                      # no default for output params
                        )        

    if count == 1:
        # Only one destination, add a second empty destination, so all CAN configs are the same size
        signal += struct.pack(ENDIAN + "Iihhf", 0, 0, 0, 0, 0)
        count  += 1

    if count != 2:
        raise Exception, "Bad number of CAN Output destinations (min 1, max 2) %s: %s" % (paramNameValue, str(count))

    return param + signal



def buildCanInputParam(xpar, msgIdx):

    global parameter_offset
    global externalParamSize

    paramNameValue  = xpar.attrib["paramNameValue"]
    paramNameStatus = xpar.attrib["paramNameStatus"]
    paramType       = xpar.attrib["paramType"]
    paramSize       = int(xpar.attrib["paramSize"])
    valueOffset     = int(xpar.attrib["paramOffsetValue"])
    statusOffset    = int(xpar.attrib["paramOffsetStatus"])

    if valueOffset > externalParamSize:
        externalParamSize = valueOffset

    if statusOffset > externalParamSize:
        externalParamSize = statusOffset

    validity = xpar.find("validity")
    if validity is not None:
        nofInputs = 2
    else:
        nofInputs = 1

    # Get optional default value
    if paramType == "FLOAT":
        # Get default values as float, setting default values if they are not present
        defVal = xpar.get("paramDefault", 0.0)
        if defVal not in ["TBD","N/A"]:
            defValFloat = float(xpar.get("paramDefault", 0.0))
        else:
            defValFloat = 0.0

        param = struct.pack (ENDIAN + "iiihhiif",
                                valueOffset,
                                statusOffset,
                                paramSize,
                                nofInputs,
                                0,
                                stringtable.append(paramNameValue),
                                stringtable.append(paramNameStatus),
                                defValFloat
                            )        
    else:
        # Get default values as integer, setting default values if they are not present
        defVal = xpar.get("paramDefault", 0)
        if defVal not in ["TBD","N/A"]:
            defValInt = int(xpar.get("paramDefault", 0))
        else:
            defValInt = 0
        
        param = struct.pack (ENDIAN + "iiihhiiL",
                                valueOffset,
                                statusOffset,
                                paramSize,
                                nofInputs,
                                0,
                                stringtable.append(paramNameValue),
                                stringtable.append(paramNameStatus),
                                defValInt
                            )        


    xSrc = xpar.find('source')

    sigtype    = xSrc.attrib["type"]
    access     = int(xSrc.attrib["access"])
    byteoffset = int(xSrc.attrib["offset"])
    bitlen     = int(xSrc.attrib["bits"])
    lsb        = int(xSrc.attrib["lsb"])
    scale      = float(xSrc.attrib["lsbvalue"])
    
    key        = (sigtype, access, paramType)
    encoding   = encoding_table_input.get(key)

    if encoding is None:
        raise Exception, "Bad parameter-signal type combination for %s: %s" % (paramNameValue, str(key))

    #canParOffset  = paramOffsetInternalBuffer((paramSize / 8))             # only used for buffer size calculation
    #canValOffset  = paramOffsetInternalBuffer(IOM.PARAMETER_VALUE_SIZE)    # only used for buffer size calculation
    parOffset  = parameter_offset + int(xpar.attrib["paramOffsetValue"])   # different messages can write to the same parameter, eg set value, increment value
    valOffset  = parameter_offset + int(xpar.attrib["paramOffsetStatus"])  # different messages can write to the same parameter, eg set value, increment value
    signal = struct.pack(ENDIAN + "hhLihhfLL",
                                msgIdx,
                                IOM.TRANSPORT_A825,
                                byteoffset,
                                bitlen,
                                lsb,
                                encoding,
                                scale,
                                parOffset,
                                valOffset)

    # Add Validity conditions, when not configured, an empty validity is added
    conditions = buildConditions(xSrc, byteoffset, bitlen, lsb, access, scale)

    return param + signal + conditions

def buildCanInputMessage(xmsg, msgIdx):
    global numberOfInputParams
    global numberOfInputSignals
    mappings = ""
    count = 0


    '''
    Fill the structure
        UInt32_t messageId;                 /* Message ID from XML Configuration */
        UInt32_t canId;                     /* CAN Message ID */
        UInt32_t validConfirmationTime;     /* Max duration, before a message is marked as fresh in ms */
        UInt32_t invalidConfirmationTime;   /* Max duration, before a message is marked as unfresh in ms */
        UInt16_t size;                      /* Size of message structure plus size of corresponding mappings */
        Byte_t   messageLength;             /* Length of message payload 1 - 8 bytes */
        Byte_t   numMappings;               /* number of mappings */
    '''

    for xpar in xmsg.iterfind("Parameter"):
        mappings += buildCanInputParam(xpar, msgIdx)
        count    += 1
        numberOfInputParams  += 1
        numberOfInputSignals += 1


    validConfirmationTime   = int(xmsg.attrib["validConfirmationTime"])     # freshness in millisecs eg. 50 = 50millisecs
    invalidConfirmationTime = int(xmsg.attrib["invalidConfirmationTime"])   # unfreshness in millisecs eg. 50 = 50millisecs

    validConfirmationTime   = validConfirmationTime   * 3  # Three times Tx rate for freshness
    invalidConfirmationTime = invalidConfirmationTime * 3  # Three times Tx rate for freshness

    
    header = struct.pack(ENDIAN + "iIIihbb", 
        int(xmsg.attrib["id"]),
        int(xmsg.attrib["canId"]),
        validConfirmationTime,    # freshness in millisecs eg. 50 = 50millisecs
        invalidConfirmationTime,  # unfreshness in millisecs eg. 50 = 50millisecs
        20 + len(mappings),       # size of structure plus mappings 
        int(xmsg.attrib["length"]),
        count
    )
    
    return header + mappings

def buildCanInput(endianess, xmlroot, internalParamOffset, outputParamSize, nofAfdxInputParams, nofAfdxInputSignals, max_afdx_param_external_offset):
    
    global ENDIAN
    global outParam_size
    global parameter_offset
    global numberOfInputParams
    global numberOfInputSignals
    global externalParamSize

    ENDIAN               = endianess
    parameter_offset     = internalParamOffset
    outParam_size        = outputParamSize
    numberOfInputParams  = nofAfdxInputParams
    numberOfInputSignals = nofAfdxInputSignals
    externalParamSize    = max_afdx_param_external_offset
    
    # initialize objects build here global variables
    messages     = ""
    nummessages  = 0
    
    section = xmlroot.find("Input")
    if section is not None:
        for x in section.iterfind("CanMessage"):
            messages += buildCanInputMessage(x, nummessages)
            nummessages += 1

    return Bunch(messages=messages, 
                 messageCount=nummessages, 
                 messageStart=0,
                 internalParamSize=(internalParamOffset + externalParamSize),
                 outputParamSize=outParam_size,
                 numberOfInputParams=numberOfInputParams,
                 numberOfInputSignals=numberOfInputSignals,
                 externalParamSize=externalParamSize)

# --------------------------------------------------------------
# CAN Output: Not yet implemented
# --------------------------------------------------------------
def buildCanOutputMessage(xmsg):
    global numberOfOutputParams

    mappings = ""
    count = 0
    
    for xpar in xmsg.iterfind("Parameter"):
        mappings += buildCanOutputParam(xpar)
        count    += 1
        numberOfOutputParams += 1


    header = struct.pack(ENDIAN + "iIihbb", 
        int(xmsg.attrib["id"]),
        int(xmsg.attrib["canId"]),
        int(xmsg.attrib["rate"]),
        16 + len(mappings),         # size of structure plus mappings 
        int(xmsg.attrib["length"]),
        count,

    )
    
    return header + mappings

def buildCanOutput(endianess, xmlroot, nofAfdxOutputParams):
    global ENDIAN
    global numberOfOutputParams

    ENDIAN = endianess
    
    messages     = ""
    nummessages  = 0
    numberOfOutputParams = nofAfdxOutputParams

    section = xmlroot.find("CanOutput")
    if section is not None:
        for x in section.iterfind("CanMessage"):
            messages += buildCanOutputMessage(x)
            nummessages += 1

    return Bunch(messages=messages, 
                 messageCount=nummessages, 
                 messageStart=0,
                 numberOfOutputParams=numberOfOutputParams)
