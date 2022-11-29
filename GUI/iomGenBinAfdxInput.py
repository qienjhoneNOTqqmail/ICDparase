'''
Created on 30.11.2014

@author: dk

IOM Binary Config Generator for AFDX Input
'''

import struct
from bunch import Bunch

from iomGenBinConst import IOM
from iomGenBinEndian import ENDIAN
from stringtab import stringtable

import ctypes

encoding_table = {
        #Signal, Access, Param,     ID of function to call
        ("INT",     4,   "INT"):     IOM.SIGINTYPE_INT32,
        ("UINT",    4,   "INT"):     IOM.SIGINTYPE_UINT32,
        ("INT",     4,   "FLOAT"):   IOM.SIGINTYPE_SIG32_I2F,
        ("INT",     2,   "INT"):     IOM.SIGINTYPE_INT16,
        ("UINT",    2,   "INT"):     IOM.SIGINTYPE_UINT16,
        ("INT",     1,   "INT"):     IOM.SIGINTYPE_INT8,
        ("UINT",    1,   "INT"):     IOM.SIGINTYPE_UINT8,
        ("FLOAT",   4,   "FLOAT"):   IOM.SIGINTYPE_FLOATS,
        ("FLOAT",   8,   "FLOAT"):   IOM.SIGINTYPE_DOUBLE,
        ("FLOAT",   4,   "INT"):     IOM.SIGINTYPE_SIG32_F2I,
        ("BOOL",    4,   "BOOL"):    IOM.SIGINTYPE_BOOL,
        ("BOOL",    4,   "INT"):     IOM.SIGINTYPE_CODED32,
        ("COD",     4,   "ENUM"):    IOM.SIGINTYPE_CODED32,
        ("COD",     4,   "INT"):     IOM.SIGINTYPE_CODED32,
        ("COD",     8,   "ENUM"):    IOM.SIGINTYPE_CODED64,
        ("COD",     8,   "INT"):     IOM.SIGINTYPE_CODED64,
        ("BNR",     4,   "FLOAT"):   IOM.SIGINTYPE_BNR,
        ("BNR",     4,   "INT"):     IOM.SIGINTYPE_BNR_F2I,
        ("UBNR",    4,   "FLOAT"):   IOM.SIGINTYPE_BNR,
        ("UBNR",    4,   "INT"):     IOM.SIGINTYPE_BNR_F2I,
        ("BCD",     4,   "FLOAT"):   IOM.SIGINTYPE_BCD,
        ("BCD",     4,   "INT"):     IOM.SIGINTYPE_BCD_F2I,
        ("UBCD",    4,   "FLOAT"):   IOM.SIGINTYPE_BCD,
        ("UBCD",    4,   "INT"):     IOM.SIGINTYPE_BCD_F2I,
        ("BYTES",   1,   "BYTES"):   IOM.SIGINTYPE_OPAQUE,
        ("UNFRESH", 0,   "BOOL"):    IOM.SIGINTYPE_UNFRESH
}


encoding_table_transport = {
        ("A664"):     IOM.TRANSPORT_A664,
        ("A429"):     IOM.TRANSPORT_A429,
        ("A825"):     IOM.TRANSPORT_A825,
}




# At runtime we assume a message buffer with space for all input messages 
# The message buffer has per message:
#         A 32 byte header (used among others to store message freshness
#         The actual message, padded to 32 bytes (for better DMA performance)
#         A 32 additional header used by IMA SCOE 
#         Rounded to multiple of 64
#
#         In IMA we read the message at buffer start +32 and access the parameters starting
#         at buffer start +64
#         In IDU we read the message at buffer start + 64 AND access data at buffer start + 64
#


numberOfInputParams  = 0          # used for calculating buffer sizes  
numberOfInputSignals = 0          # used for calculating buffer sizes  
parameter_offset     = 0          # next offset into internal parameter buffer for storing data from all sources  
externalParamSize = 0     # Maximum offset for external parameter  

messageAfdx_offset   = 0          # next offset into message buffer  
messageAfdx_dict     = {}         # dictionary of message with their offset in message buffer
                    
messageA429_offset   = 0          # next offset into message buffer  
portA429_dict        = {}         # dictionary of ports with their index in message buffer
messageA429_dict     = {}         # dictionary of message with their offset in message buffer

def getIntOrZero(val, errmsg):
    try:
        res = int(val)
    except:
        sval = val.encode('utf-8').strip()
        if sval.lower() in ('', 'tbd', 'none', 'no', 'n/a'):
            res = 0
        else:
            raise Exception, "Unknown attribute value %s: for %s" % \
                (val, errmsg)
    return res


def paramOffsetInternalBuffer(sizeBytes):
    global parameter_offset

    offset = parameter_offset
    
    parameter_offset += sizeBytes
    
    return offset


def messageOffset(transport, messageId, msgOffset):

    if transport.lower() == "a664":
        #AFDX Calculation
        intMsgId = int(messageId)
        if not messageAfdx_dict.has_key(intMsgId):
            raise Exception, "Message Id <%s> not found" % messageId

        hdroffset = messageAfdx_dict[intMsgId].offset
        offset =  hdroffset + IOM.A664_MESSAGE_HEADER_LENGTH + msgOffset
    elif transport.lower() == "a429":
        #A429 Calculation
        msgId = int(messageId)
        if not messageA429_dict.has_key(msgId):
            raise Exception, "A429 Message Id <%s> not found" % messageId
        portId = messageA429_dict[msgId].port
        label  = messageA429_dict[msgId].code
        sdi    = messageA429_dict[msgId].sdi

        if not portA429_dict.has_key(portId):
            raise Exception, "A429 Port Id <%s> not found" % portId
        portOffset = portA429_dict[portId].offset

        # Get address for block of four A429 messages where to store this labels data
        # NB: four A429 messages = one for each SDI address
        # NB: Label is an eight bit field
        # offset = Message Base address for port + label offset (including 4 SDI's per label) + SDI offset + required offset (always 4)
        offset =  portOffset + (IOM.A429_MESSAGE_LENGTH * label * IOM.A429_NOF_SDI) + (IOM.A429_MESSAGE_LENGTH * sdi) + IOM.A429_DATA_OFFSET
    else:
        raise Exception, "Unknown transport: %s, for message ID: %s, message offset: %s" % (transport, messageId, msgOffset)

    return offset


def freshnessOffset(transport, messageId):
    if transport.lower() == "a664":
        #AFDX Calculation
        intMsgId = int(messageId)
        if not messageAfdx_dict.has_key(intMsgId):
            raise Exception, "Message Id <%s> not found" % messageId
        
        hdroffset = messageAfdx_dict[intMsgId].offset
        offset = hdroffset + IOM.A664_MESSAGE_HEADER_FRESHNESS_OFFSET
    elif transport.lower() == "a429":
        #A429 Calculation
        msgId = int(messageId)
        if not messageA429_dict.has_key(msgId):
            raise Exception, "A429 Message Id <%s> not found" % messageId
        portId = messageA429_dict[msgId].port
        label  = messageA429_dict[msgId].code
        sdi    = messageA429_dict[msgId].sdi

        if not portA429_dict.has_key(portId):
            raise Exception, "A429 Port Id <%s> not found" % portId
        portOffset = portA429_dict[portId].offset

        # Get address for block of four A429 messages where to store this labels data
        # NB: four A429 messages = one for each SDI address
        # NB: Label is an eight bit field
        # offset = Message Base address for port + label offset (including 4 SDI's per label) + SDI offset
        offset =  portOffset + (IOM.A429_MESSAGE_LENGTH * label * IOM.A429_NOF_SDI) + (IOM.A429_MESSAGE_LENGTH * sdi)
    else:
        raise Exception, "Unknown transport: %s, for message ID: %s" % (transport, messageId)

    return offset




def GetSelectionSet(xmlds, expectedSetName):
    '''
    '''
    setFound = -1
    numSets  = 0

    #get total number of sources
    for x in xmlds.iterfind("SelectionSet"):

        setName = x.attrib["selectionSetName"]

        if setName == expectedSetName:
            setFound = numSets

        numSets += 1

    if setFound < 0:
        raise Exception, "Set Name not found in list of source sets: %s" % (expectedSetName)

    return setFound 


	
# 
# Build functions: convert the XML tag into corresponding binary structure
# side effect: build up string table and message dictionary + message offset
#

def buildLogicSource(xmllogic, setNumber):
    '''
    Build one logicSource config  structure from XML
    '''

    useFloat      = 0
    numconditions = 0
    conditions    = ""
    condtypes     = [0, 0, 0, 0]

    for x in xmllogic.iterfind("condition"):
        t             = x.attrib["type"].lower()
        transportId   = encoding_table_transport.get(x.attrib["transport"])
        intMsgId      = int(x.attrib["message"])
        msgIdx = messageAfdx_dict[intMsgId].idx

        if t == "freshness":
            condtype = IOM.CONDTYPE_FRESHNESS
            offset   = freshnessOffset(x.attrib["transport"], x.attrib["message"])
            access   = 0    # not used
            sizeBits = 0    # not used
            offBits  = 0    # not used
            scale    = 1.0
            min      = 0    # not used
            max      = 0    # not used
        elif t == "a664fs":
            condtype = IOM.CONDTYPE_A664FS
            offset   = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
            access   = 0    # not used
            sizeBits = 0    # not used
            offBits  = 0    # not used
            scale    = 1.0
            min      = 0    # not used
            max      = 0    # not used
        elif t == "validity_input":
            condtype = IOM.CONDTYPE_VALIDITY_PARAM
            offset   = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
            access   = int(x.attrib["access"])
            sizeBits = int(x.attrib["bits"])
            offBits  = int(x.attrib["lsb"])
            scale    = 1.0
            min      = int(x.attrib["value"])
            max      = 0    # not used
        elif t == "a429ssm_bnr":
            condtype = IOM.CONDTYPE_A429SSM_BNR
            offset   = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
            access   = 0    # not used
            sizeBits = 0    # not used
            offBits  = 0    # not used
            scale    = 1.0
            min      = 0    # not used
            max      = 0    # not used
        elif t == "a429ssm_dis":
            condtype = IOM.CONDTYPE_A429SSM_DIS
            offset   = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
            access   = 0    # not used
            sizeBits = 0    # not used
            offBits  = 0    # not used
            scale    = 1.0
            min      = 0    # not used
            max      = 0    # not used
        elif t == "a429ssm_bcd":
            condtype = IOM.CONDTYPE_A429SSM_BCD
            offset   = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
            access   = 0    # not used
            sizeBits = 0    # not used
            offBits  = 0    # not used
            scale    = 1.0
            min      = 0    # not used
            max      = 0    # not used
        elif t == "range_int":
            condtype = IOM.CONDTYPE_RANGE_INT
            offset   = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
            access   = int(x.attrib["access"])
            sizeBits = int(x.attrib["bits"])
            offBits  = int(x.attrib["lsb"])
            scale    = 1.0
            min      = int(x.attrib["min"])
            max      = int(x.attrib["max"])
        elif t == "range_uint":
            condtype = IOM.CONDTYPE_RANGE_UINT
            offset   = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
            access   = int(x.attrib["access"])
            sizeBits = int(x.attrib["bits"])
            offBits  = int(x.attrib["lsb"])
            scale    = 1.0
            min      = int(x.attrib["min"])
            max      = int(x.attrib["max"])
        elif t == "range_float":
            condtype   = IOM.CONDTYPE_RANGE_FLOAT
            offset     = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
            access     = int(x.attrib["access"])
            sizeBits   = int(x.attrib["bits"])
            offBits    = int(x.attrib["lsb"])
            scale      = 1.0
            minf       = float(x.attrib["min"])
            maxf       = float(x.attrib["max"])
            useFloat = 1
        elif t == "range_floatbnr":
            condtype   = IOM.CONDTYPE_RANGE_FLOATBNR
            offset     = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
            access     = int(x.attrib["access"])
            sizeBits   = int(x.attrib["bits"])
            offBits    = int(x.attrib["lsb"])
            scale      = float(x.attrib["lsbvalue"])
            minf       = float(x.attrib["min"])
            maxf       = float(x.attrib["max"])
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
    for i in range (0,4-numconditions):
        cond = struct.pack(ENDIAN + "hhIIIIfii", 0, 0, 0, 0, 0, 0, 0.0, 0, 0)  # Padding
        condtypes[numconditions + i] = IOM.CONDTYPE_INVALID
        conditions += cond
        extraConditions += 1

    if (extraConditions + numconditions) > 4:
        raise Exception, "Too many Validation conditions: %s" % (extraConditions + numconditions)

    hdr = struct.pack(ENDIAN + "hhbbbb", numconditions, setNumber, 
                                 condtypes[0], condtypes[1], condtypes[2], condtypes[3])
    return hdr + conditions


def buildParam(xmlparam, numsources):
    '''
    Build one parameter config structure from XML
    '''
    global numberOfInputSignals
    global externalParamSize

    paramSources = 0
    param        = ""
    paramType    = xmlparam.attrib['paramType']
    paramName    = xmlparam.attrib['paramNameValue']
    paramSize    = int(xmlparam.attrib["paramSize"])

    for x in xmlparam.iterfind("source"):
        intMsgId   = int(x.attrib["message"])
        transport  = x.attrib["transport"]
        sigType    = x.attrib["type"]
        sigAccess  = int(x.attrib["access"])
        byteoffset = messageOffset(x.attrib["transport"], x.attrib["message"], int(x.attrib["offset"]))
        bitlen     = int(x.attrib["bits"])
        lsb        = int(x.attrib["lsb"])
        scale      = float(x.attrib["lsbvalue"])
        parOffset  = paramOffsetInternalBuffer((paramSize / 8))
        valOffset  = paramOffsetInternalBuffer(IOM.PARAMETER_VALUE_SIZE)

        key = (sigType, sigAccess, paramType)
        encoding   = encoding_table.get(key)

        if encoding is None:
            raise Exception, "Bad parameter-signal type combination for %s: %s" % (paramName, str(key))

        transportId = encoding_table_transport.get(transport)

        if transportId is None:
            raise Exception, "Bad parameter-signal Transport %s: %s" % (paramName, transport)

        if transport.lower() == "a664":
            if not messageAfdx_dict.has_key(intMsgId):
                raise Exception, "Message Id <%s> not found" % intMsgId

            msgIdx = messageAfdx_dict[intMsgId].idx
        elif transport.lower() == "a429":
            if not messageA429_dict.has_key(intMsgId):
                raise Exception, "Message Id <%s> not found" % intMsgId

            msgIdx = messageA429_dict[intMsgId].idx
        else:
            raise Exception, "Unknown transport: %s, for message ID: %s" % (transport, intMsgId)

        source = struct.pack(ENDIAN + "hhLihhfLL", msgIdx, transportId, byteoffset, bitlen, lsb, encoding, scale, parOffset, valOffset)
        paramSources += 1
        numberOfInputSignals += 1
        param += source

    if paramSources != numsources:
        raise Exception, "Number of sources mismatch: Logic:%d Parameter:%d" % (numsources, paramSources)

    valueOffset      = int(xmlparam.attrib["paramOffsetValue"])
    statusOffset     = int(xmlparam.attrib["paramOffsetStatus"])
    valueNameOffset  = stringtable.append(xmlparam.attrib["paramNameValue"])
    statusNameOffset = stringtable.append(xmlparam.attrib["paramNameStatus"])
 
    if valueOffset > externalParamSize:
        externalParamSize = valueOffset

    if statusOffset > externalParamSize:
        externalParamSize = statusOffset

    # Get optional min / max / default values
    if paramType == "FLOAT":
        # Get min / max / default values as 32 bit float
        defVal = 0.0
        if xmlparam.get("paramDefault"):
            defVal = float(xmlparam.attrib["paramDefault"])

        hdr = struct.pack(ENDIAN + "iiihhiif", valueOffset, statusOffset, paramSize, paramSources, 0, valueNameOffset, statusNameOffset, defVal)
    else:
        # Get min / max / default values as 32 integers
        defValInt = 0
        if xmlparam.get("paramDefault"):
            defValInt = ctypes.c_ulong(int(xmlparam.attrib["paramDefault"])).value

        hdr = struct.pack(ENDIAN + "iiihhiiL", valueOffset, statusOffset, paramSize, paramSources, 0, valueNameOffset, statusNameOffset, defValInt)

    return hdr + param 


def buildAfdxInputDataset(xmlds):
    '''
    Build one data set config structure from XML to binary
    '''
    global numberOfInputParams
    numsources = 0
    setNumber  = 0
    logic      = ""
    
    xmlLogic   = xmlds.find("Logic")
    
    for x in xmlLogic.iterfind("sourceLogic"):
        logic += buildLogicSource(x, setNumber)
        numsources += 1

    numparams = 0
    param = ""
    for x in xmlds.iterfind("Parameter"):
        param += buildParam(x, numsources)
        numparams += 1
        numberOfInputParams +=1

    dslen = 12 + len(logic) + len(param)

    hdr = struct.pack(ENDIAN + "hhii", numsources, numparams, len(logic), dslen)
    return hdr + logic + param 

def buildAfdxInputDatasetMultiSource(xmlAfdxInput, xmlds):
    '''
    Build one data set config structure from XML to binary
    '''
    global numberOfInputParams
    numsources = 0
    logic      = ""

    setNumber  = GetSelectionSet (xmlAfdxInput, xmlds.attrib["selectionSetName"])

    xmlLogic   = xmlds.find("Logic")
    
    for x in xmlLogic.iterfind("sourceLogic"):
        logic += buildLogicSource(x, setNumber)
        numsources += 1

    numparams = 0
    param = ""
    for x in xmlds.iterfind("Parameter"):
        param += buildParam(x, numsources)
        numparams += 1
        numberOfInputParams +=1


    dslen = 12 + len(logic) + len(param)

    hdr = struct.pack(ENDIAN + "hhii", numsources, numparams, len(logic), dslen)
    return hdr + logic + param 



def buildSourceLic(xmlSource):
    '''
    Build one Source config structure (LicParamConfig_t) from XML to binary
    /* Single Source Configuration */
    typedef struct LicParamConfig_t
    {
        UInt32_t        valueMode;   /* Mode of source value: Exact value, any value  */
        UInt32_t        valueExp;    /* expected value of LIC_PARAMETER               */
        UInt32_t        valOffset;   /* Offset of the Parameter Validity in the Input Parameter Buffer */
        UInt32_t        parOffset;   /* Offset of the Parameter in the Input Parameter Buffer */
        UInt32_t        parType;     /* Type of the Parameter in the Input Parameter Buffer, eg IOEN_INPUT_MAPPING_A664_BOOLEAN */
    } LicParamConfig_t;
    '''

    expectedMode    = 0
    expectedValue   = 0
    expected        = xmlSource.attrib["expectedValue"]
    valueOffset     = int(xmlSource.attrib["paramOffsetValue"])
    statusOffset    = int(xmlSource.attrib["paramOffsetStatus"])
    paramType       = xmlSource.attrib["paramType"]

    if paramType == "BOOL":
        type = IOM.SIGINTYPE_BOOL
    else:
        type = IOM.SIGINTYPE_INT32


    if expected == "Any":
        expectedMode  = IOM.SET_SOURCE_PARAM_VALUE_ANY
        expectedValue = 0
    else:
        expectedMode  = IOM.SET_SOURCE_PARAM_VALUE_EXACT
        expectedValue = int(expected)
    

    hdr = struct.pack(ENDIAN + "LLLLL", expectedMode, expectedValue, statusOffset, valueOffset, type)

    return hdr


def buildAfdxInputSourceSet(xmlss, setNumber):
    '''
    Build one source set config structure from XML to binary
    {
        UInt32_t nofSources;               /* Number of sources in a source set                                                     */
        UInt32_t criteria;                 /* LIC_PARAMETER or SOURCE_HEALTH_SCORE                                                  */
        UInt32_t sourceHealthMode;         /* Source Health Mode: No Lock, Lock Time, Permanent Lock                                */
        UInt32_t sourceHealthValue;        /* lock time in ms                                                                       */
        UInt32_t sourceParamOffset;        /* Offset (in words) of the first source (SourceParamConfig_t) in this set               */
        UInt32_t sourceParamListSize;      /* Total words of the source list for this set (SetConfig_t + (n * SourceParamConfig_t)) */
    }
   '''

    logic        = ""
    sources      = ""
    oneSourceSet = ""
    numsources   = 0
    numLogic     = 0
    criteria     = xmlss.attrib["criteria"]
    setName      = xmlss.attrib["selectionSetName"]
    global SOURCE_SET_OFFSET
    SOURCE_SET_OFFSET += IOM.SET_HEADER_SIZE


    if criteria == "LIC_PARAMETER":
        # LIC_PARAMETER

        #get total number of sources
        for x in xmlss.iterfind("source"):
            sources    += buildSourceLic(x)
            numsources += 1

        if numsources > IOM.SET_MAX_SOURCES:
            raise Exception, "Too many sources found for selection set: %s, %s found, only %s allowed" % (setName, numsources, IOM.SET_MAX_SOURCES)

        size = IOM.SET_HEADER_SIZE + len(sources)

        oneSourceSet  = struct.pack(ENDIAN + "LLLLLL", numsources, IOM.SET_SOURCE_LIC_PARAMETER, 0, 0, SOURCE_SET_OFFSET, size)

        oneSourceSet += sources
        SOURCE_SET_OFFSET += len(sources)

    elif criteria == "OBJECT_VALID":
        # OBJECT_VALID

        #build sourceLogic
        #get total number of sources
        for xmlLogic in xmlss.iterfind("source"):
            numsources += 1
            numLogic    = 0
            sourceName  = xmlLogic.attrib["name"]
            for x in xmlLogic.iterfind("sourceLogic"):
                logic += buildLogicSource(x, setNumber)
                numLogic += 1

            if numLogic == 0:
                raise Exception, "No <sourceLogic> found for selection set: %s, source: %s" % (setName, sourceName)

        if numsources > IOM.SET_MAX_SOURCES:
            raise Exception, "Too many sources found for selection set: %s, %s found, only %s allowed" % (setName, numsources, IOM.SET_MAX_SOURCES)

        size = IOM.SET_HEADER_SIZE + len(logic)

        oneSourceSet  = struct.pack(ENDIAN + "LLLLLL", numsources, IOM.SET_SOURCE_OBJECT_VALID, 0, 0, SOURCE_SET_OFFSET, size)

        # Add logic parameters
        oneSourceSet += logic
        SOURCE_SET_OFFSET += len(logic)

    else:
        # SOURCE_HEALTH_SCORE

        intervalString = xmlss.attrib["interval"]

        #get total number of sources
        for x in xmlss.iterfind("source"):
            numsources += 1

        if numsources > IOM.SET_MAX_SOURCES:
            raise Exception, "Too many sources found for selection set: %s, %s found, only %s allowed" % (setName, numsources, IOM.SET_MAX_SOURCES)

        #Check lock interval (millisecs, none, permanent)
        if intervalString.lower() == "permanent":
            interval = 0
            intervalmode = IOM.SET_SOURCE_HEALTH_LOCK_PERMANENT
        else:
            interval = int(intervalString)
            
            if interval == 0:
                intervalmode = IOM.SET_SOURCE_HEALTH_NO_LOCK
            else:
                intervalmode = IOM.SET_SOURCE_HEALTH_LOCK

        oneSourceSet = struct.pack(ENDIAN + "LLLLLL", numsources, IOM.SET_SOURCE_HEALTH_SCORE, intervalmode, interval, 0, IOM.SET_HEADER_SIZE)


    return oneSourceSet


def buildMessageA429(xmlmsg, msgIdx):
    '''
    Fill the structure per message (label)
        Byte_t   code;                      /* Label Code in binary, eg. Label Code octal 271 = 0xB9 (binary) */
        Byte_t   sdi;                       /* Source Destination Identifier (SDI) 2 bit field range 0 to 3   */
        Byte_t   port;                      /* port index on which message is received                        */
        Byte_t   pad;                       /* alignment                                                      */
        UInt32_t validConfirmationTime;                 /* Max duration, before a message is marked as fresh in ms */
        UInt32_t invalidConfirmationTime;               /* Max duration, before a message is marked as unfresh in ms */
    '''
    global portA429_dict

    msgId        = int(xmlmsg.attrib["id"])
    name         = xmlmsg.attrib["messageName"]
    portid       = int(xmlmsg.attrib["port"])
    codeString   = xmlmsg.attrib["labelNumber"]       # NB: "code" is octal string without prefix 'o'
    codeDecimal  = int(codeString, 8)                 # Convert to decimal integer from octal as string
    codeOctal    = int(codeString)                    # Convert to octal integer from octal as string
    sdi          = int(xmlmsg.attrib["sdi"])          # Source Destination Identifier range 0 to 3
    validConfirmationTime    = int(xmlmsg.attrib["validConfirmationTime"])    # freshness in millisecs eg. 50 = 50millisecs
    invalidConfirmationTime  = int(xmlmsg.attrib["invalidConfirmationTime"])  # unfreshness in millisecs eg. 50 = 50millisecs

    if not portA429_dict.has_key(portid):
        raise Exception, "Port ID not found for Message : %s" % name

    if messageA429_dict.has_key(msgId):
        raise Exception, "Duplicate Message id: %d for A429 driver: %s" % (msgId, name)

    messageA429_dict[msgId]  = Bunch (idx=msgIdx, port=portid, code=codeDecimal, sdi=sdi)
    msg = struct.pack(ENDIAN + "BbBBLL", codeDecimal, sdi, portA429_dict[portid].idx, 0, validConfirmationTime, invalidConfirmationTime)

    return msg



def buildInputPortA429(xmlPort, portIdx):
    '''
    Fill the structure
        UInt32_t portId;              // Port ID from XML Configuration
        UInt32_t messageLength;       // Length of message payload (what is read from port)
        UInt32_t queueLength;         // Queue Length, 0 for Sampling
        UInt32_t messagerOffset;      // Offset in message buffer
        UInt32_t portNameOffset;      // Offset of port Name (or CVT name) into string table
    '''
    
    global messageA429_offset
    global portA429_dict

    portid   = int(xmlPort.attrib["id"])
    name     = xmlPort.attrib["portName"]
    msglen   = int(xmlPort.attrib["length"])
    porttype = xmlPort.attrib["portType"].lower()
    if porttype[0] == "q":
        queuelen = int(xmlPort.attrib["queueLength"])
    else:
        raise Exception, "Sampling port not valid for A429 driver: %s" % name

    if portA429_dict.has_key(portid):
        raise Exception, "Duplicate Port id: %d for A429 driver: %s" % (portid, name)

    portA429_dict[portid]  = Bunch (idx=portIdx, offset=messageA429_offset)

    port = struct.pack(ENDIAN + "iiiii",
                       portid,
                       msglen,
                       queuelen,
                       messageA429_offset,
                       stringtable.append(xmlPort.attrib["portName"]))

    # increment message offset for next Port
    # Space for validity and data of all A429 labels including Source Destination Identifier
    messageA429_offset += ((4 + 4) * 256 * 4 )  # 32 bit validity + 32 bit data ) * 256 Labels ) * 4 SDI)

    return port


def buildInputMessageAfdx(xmlmsg, msgIdx):
    '''
    Fill the structure
        UInt32_t messageId;                 /* Message ID from XML Configuration                         */
        UInt32_t messageLength;             /* Length of message payload (what is read from port)        */
        UInt32_t queueLength;               /* Queue length, 0 if sampling message                       */
        UInt32_t refreshPeriod;             /* Sampling port freshness in ms                             */
        UInt32_t validTime;                 /* Max duration, before a message is marked as fresh in ms   */
        UInt32_t invalidTime;               /* Max duration, before a message is marked as unfresh in ms */
        UInt32_t messageHdrOffset;          /* Offset in message buffer                                  */
        UInt32_t portNameOffset;            /* Offset of port Name (or CVT name) into string table       */
    '''
    
    global messageAfdx_offset
    global messageAfdx_dict
    
    msgid       = int(xmlmsg.attrib["id"])
    msglen      = int(xmlmsg.attrib["length"])
    refreshRate = int(xmlmsg.attrib["a653PortRefreshPeriod"])
    porttype    = xmlmsg.attrib["portType"].lower()

    if porttype[0] == "q":
        queuelen = int(xmlmsg.attrib["queueLength"])
    else:
        queuelen = 0


    if messageAfdx_dict.has_key(msgid):
        raise Exception, "Duplicate message id: %d" % msgid
    
    messageAfdx_dict[msgid] = Bunch (idx=msgIdx, offset=messageAfdx_offset)

    out = struct.pack(ENDIAN + "iiiiiiiiiiiiii",
                      msgid,
                      msglen,
                      queuelen,
                      refreshRate,
                      int(xmlmsg.attrib["validConfirmationTime"]),
                      int(xmlmsg.attrib["invalidConfirmationTime"]),
                      messageAfdx_offset,
                      stringtable.append(xmlmsg.attrib["portName"]),
                      getIntOrZero(xmlmsg.attrib["crcFsbOffset"], "crcFsbOffset"),
                      getIntOrZero(xmlmsg.attrib["crcOffset"], "crcOffset"),  
                      getIntOrZero(xmlmsg.attrib["fcFsbOffset"], "fcFsbOffset"),
                      getIntOrZero(xmlmsg.attrib["fcOffset"], "fcOffset"),   
                      int(xmlmsg.attrib["schedOffset"]),
                      int(xmlmsg.attrib["schedRate"])   
                      )

    # increment message offset: 64 byte header + message length padded to MESSAGE_PADDING bytes
    blocklen = (IOM.A664_MESSAGE_HEADER_LENGTH + ((msglen + IOM.A664_MESSAGE_PADDING - 1) & ~(IOM.A664_MESSAGE_PADDING-1)))
    messageAfdx_offset += blocklen
    return out

def buildAfdxInput(endianess, xmlroot):

    global ENDIAN
    global messageAfdx_dict
    global messageAfdx_offset

    global messageA429_offset
    global portA429Index_dict
    global portA429Offset_dict
    global portA429_dict
    global messageA429_dict

    global parameter_offset
    global numberOfInputParams
    global numberOfInputSignals
    global externalParamSize

    # initialize common objects build here global variables
    ENDIAN               = endianess
    datasets             = ""
    numdataset           = 0
    datasetSource        = ""
    numdatasetSource     = 0
    numberOfInputParams  = 0
    numberOfInputSignals = 0
    externalParamSize    = 0

    parameter_offset     = 0
                        
    # AFDX Port/Message 
    messageAfdx_dict     = {}
    messagesAfdx         = ""
    nofMessagesAfdx      = 0
    messageAfdx_offset   = 0
                        
    #A429 Port          
    portA429_dict        = {}
    portsA429            = ""
    nofPortsA429         = 0
    messageA429_offset   = 0
                        
    #A429 Message       
    messageA429_dict     = {}
    messagesA429         = ""
    nofMessagesA429      = 0

    section = xmlroot.find("Input")
    if section is not None:
        for x in section.iterfind("AfdxMessage"):
            messagesAfdx += buildInputMessageAfdx(x, nofMessagesAfdx)
            nofMessagesAfdx += 1

        # Align A429 message data after AFDX message data
        messageA429_offset = (messageAfdx_offset + 1023)/1024*1024
        for x in section.iterfind("A429Port"):
            portsA429 += buildInputPortA429(x, nofPortsA429)
            nofPortsA429 += 1

        for x in section.iterfind("A429Message"):
            messagesA429    += buildMessageA429(x, nofMessagesA429)
            nofMessagesA429 += 1

        for x in section.iterfind("DataSet"):
            selectionSetName = x.attrib["selectionSetName"].lower()
            if selectionSetName != "none":
                datasetSource    += buildAfdxInputDatasetMultiSource(section, x)
                numdatasetSource += 1
            else:
                datasets   += buildAfdxInputDataset(x)
                numdataset += 1


    return Bunch(datasets=datasets, 
                 datasetStart=0, 
                 datasetCount=numdataset, 
                 datasetSource=datasetSource, 
                 datasetSourceStart=0, 
                 datasetSourceCount=numdatasetSource, 
                 messages=messagesAfdx, 
                 messageStart=0, 
                 messageCount=nofMessagesAfdx,
                 messageSize=messageAfdx_offset,
                 a429ports=portsA429, 
                 a429portsStart=0, 
                 a429portsCount=nofPortsA429,
                 inputMessageSize=messageA429_offset,
                 a429message=messagesA429, 
                 a429messageStart=0, 
                 a429messageCount=nofMessagesA429,
                 parameterOffsetInternal=parameter_offset,
                 numberOfInputParams=numberOfInputParams,
                 numberOfInputSignals=numberOfInputSignals,
                 externalParamSize=externalParamSize)

def buildSourceSet(endianess, xmlroot, offset):

    global ENDIAN
    global SOURCE_SET_OFFSET
    ENDIAN = endianess
    SOURCE_SET_OFFSET = offset + (2*4)

    # initialize objects build here global variables
    sourceSet    = ""
    sourceSets   = ""
    numSourceSet = 0
    
    section = xmlroot.find("Input")
    if section is not None:
        for x in section.iterfind("SelectionSet"):
            sourceSets   += buildAfdxInputSourceSet(x, numSourceSet)
            numSourceSet += 1

    if numSourceSet > 1024:
        raise Exception, "Too many Selection sets for IO Manager (max 1024 allowed): current: %s" % (numSourceSet)

    # Set the source set header size and offset
    sourceSetHeader = struct.pack(ENDIAN + "LL", numSourceSet, offset + (2*4))
    sourceSet       = sourceSetHeader + sourceSets


    return Bunch(   sourceSet=sourceSet, 
                    sourceSetStart=0, 
                    sourceSetSize=0,
                    numSourceSet=numSourceSet)

