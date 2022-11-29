'''
Created on 30.11.2015

@author: jn

IOM Binary Config Generator for A429
'''


import struct
from bunch import Bunch

from iomGenBinConst import IOM
from iomGenBinEndian import ENDIAN
from stringtab import stringtable

import ctypes

encoding_table = {
        ("BOOL",  4, "BOOL"):  IOM.SIGINTYPE_BOOL,
        ("BOOL",  4, "INT"):   IOM.SIGINTYPE_CODED32,
        ("COD",   4, "ENUM"):  IOM.SIGINTYPE_CODED32,
        ("COD",   4, "INT"):   IOM.SIGINTYPE_CODED32,
        ("BNR",   4, "FLOAT"): IOM.SIGINTYPE_BNR,
        ("BNR",   4, "INT"):   IOM.SIGINTYPE_BNR_F2I,
        ("UBNR",  4, "FLOAT"): IOM.SIGINTYPE_UBNR,
        ("UBNR",  4, "INT"):   IOM.SIGINTYPE_UBNR_F2I,
        ("BCD",   4, "FLOAT"): IOM.SIGINTYPE_BCD,
        ("BCD",   4, "INT"):   IOM.SIGINTYPE_BCD_F2I,
        ("UBCD",  4, "FLOAT"): IOM.SIGINTYPE_UBCD,
        ("UBCD",  4, "INT"):   IOM.SIGINTYPE_UBCD_F2I,
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


message_offset = 0          # next offset into message buffer  
message_dict = {}           # dictionary of message with their offset in message buffer
message_index = {}          # dictionary of message with their index in message buffer

def messageOffset(messageId, msgOffset):
    intMsgId = int(messageId)
    if not message_dict.has_key(intMsgId):
        raise Exception, "Message Id <%s> not found" % messageId

    hdroffset = message_dict[intMsgId]
    return hdroffset + IOM.A429_MESSAGE_HEADER_LENGTH + msgOffset




# 
# Build functions: convert the XML tag into corresponding binary structure
# side effect: build up string table and message dictionary + message offset
#

def buildLogicSource(xmllogic, message):
    '''
    Build one logicSource config  structure from XML
    '''

    numconditions = 0
    setNumber     = 0 #Not used in A429
    conditions    = ""
    condtypes     = [0, 0, 0, 0]

    for x in xmllogic.iterfind("condition"):
        t = x.attrib["type"].lower()
        if t == "freshness":
            condtype = IOM.CONDTYPE_FRESHNESS
            offset   = int(x.attrib["offset"])  # for A429, message freshness is always in the first word, data in the second word
            sizeBits = 0     # not used
            offBits  = 0     # not used
            value    = 0     # not used
        elif t == "a429ssm_bnr":
            condtype = IOM.CONDTYPE_A429SSM_BNR
            offset   = int(x.attrib["offset"])
            sizeBits = 0     # not used
            offBits  = 0     # not used
            value    = 0     # not used
        elif t == "a429ssm_dis":
            condtype = IOM.CONDTYPE_A429SSM_DIS
            offset   = int(x.attrib["offset"])
            sizeBits = 0     # not used
            offBits  = 0     # not used
            value    = 0     # not used
        elif t == "a429ssm_bcd":
            condtype = IOM.CONDTYPE_A429SSM_BCD
            offset   = int(x.attrib["offset"])
            sizeBits = 0    # not used
            offBits  = 0    # not used
            value    = 0    # not used
        else:
            raise Exception, "Illegal condition type: %s" % t

        if numconditions > 3:
            raise Exception, "Two many conditions"

        cond = struct.pack(ENDIAN + "IIII", offset, sizeBits, offBits, value)
        condtypes[numconditions] = condtype
        
        conditions += cond
        numconditions += 1

    #pack conditions to fixed array size of 4
    totalConditions = numconditions
    condEmpty       = struct.pack(ENDIAN + "IIII", 0, 0, 0, 0)
    while (totalConditions < 4):
        conditions += condEmpty
        totalConditions += 1

    hdr = struct.pack(ENDIAN + "hhbbbb", numconditions, setNumber, 
                                 condtypes[0], condtypes[1], condtypes[2], condtypes[3])
    return hdr + conditions




def buildParam(xmlparam):
    '''
    Build one parameter config structure from XML
    '''
    global message_index

    paramsources = 0
    param = ""
    logic = ""
    paramType  = xmlparam.attrib['paramType']
    paramName  = xmlparam.attrib['paramNameValue']

    xInput = xmlparam.find("input")
    sigType    = xInput.attrib["type"]
    sigAccess  = int(xInput.attrib["access"])
    byteoffset = int(xInput.attrib["offset"])
    bitlen     = int(xInput.attrib["bits"])
    lsb        = int(xInput.attrib["lsb"])
    scale      = float(xInput.attrib["lsbvalue"])

    key = (sigType, sigAccess, paramType)
    encoding   = encoding_table.get(key)

    if encoding is None:
        raise Exception, "Bad parameter-signal type combination for %s: %s" % (paramName, str(key))
        
    input = struct.pack(ENDIAN + "Iihhf", byteoffset, bitlen, lsb, encoding, scale)

    paramsources = 0
    srcMsg       = [7, 7, 7, 7, 7, 7, 7, 7]  # default value of 7, means not used
    for xSource in xInput.iterfind("source"):
        msgId            = int(xSource.attrib["message"])
        msgIdx           = message_index[msgId] #convert to index
        srcMsg[msgIdx]   = paramsources #save source in message list
        logic           += buildLogicSource (xSource, xSource.attrib["message"])
        paramsources    += 1

    sourceMsg      = struct.pack(ENDIAN + "bbbbbbbb", 
                                 srcMsg[0], srcMsg[1], srcMsg[2], srcMsg[3],
                                 srcMsg[4], srcMsg[5], srcMsg[6], srcMsg[7])


    valueOffset      = int(xmlparam.attrib["paramOffsetValue"])
    statusOffset     = int(xmlparam.attrib["paramOffsetStatus"])
    valueNameOffset  = stringtable.append(xmlparam.attrib["paramNameValue"])
    statusNameOffset = stringtable.append(xmlparam.attrib["paramNameStatus"])
 
    # Get optional min / max / default values
    if paramType == "FLOAT":
        # Get min / max / default values as 32 bit float
        minVal = -IOM.MAX_VALUE_FLOAT32
        maxVal = IOM.MAX_VALUE_FLOAT32
        defVal = 0.0
        if xmlparam.get("paramMin"):
            minVal = float(xmlparam.attrib["paramMin"])

        if xmlparam.get("paramMax"):
            maxVal = float(xmlparam.attrib["paramMax"])

        if xmlparam.get("paramDefault"):
            defVal = float(xmlparam.attrib["paramDefault"])

        param = struct.pack(ENDIAN + "iihhiifff", valueOffset, statusOffset, paramsources, 0, valueNameOffset, statusNameOffset, minVal, maxVal, defVal)
    else:
        # Get min / max / default values as 32 integers
        minValInt = 0
        maxValInt = IOM.MAX_VALUE_UTINT32
        defValInt = 0
        if xmlparam.get("paramMin"):
            minValInt = ctypes.c_ulong(int(xmlparam.attrib["paramMin"])).value

        if xmlparam.get("paramMax"):
            maxValInt = ctypes.c_ulong(int(xmlparam.attrib["paramMax"])).value

        if xmlparam.get("paramDefault"):
            defValInt = ctypes.c_ulong(int(xmlparam.attrib["paramDefault"])).value

        param = struct.pack(ENDIAN + "iihhiiLLL", valueOffset, statusOffset, paramsources, 0, valueNameOffset, statusNameOffset, minValInt, maxValInt, defValInt)

    return paramsources, sourceMsg + param + input + logic


def octToBin(codeOctal):
    '''
    covert integer coded as octal to binary
    eg. Octal 273 converted to 0xBB or 187 decimal
    '''

    return codeOctal

def buildLabel(xmlds):
    '''
    Build one Label config structure from XML to binary
    '''

    codeString   = xmlds.attrib["code"] # NB: "code" is octal string without prefix 'o'
    codeBinary   = int(codeString, 8)
    codeOctal    = int(codeString)
    sdi          = int(xmlds.attrib["sdi"])
    rate         = int(xmlds.attrib["rate"])

    if (rate > 1430):
        raise Exception, "Label %s: maximum rate exceeded: %s (max allowed 1430)" % (codeString, str(rate))

    refreshTime  = ((rate * 1000000) * 3) # Convert millisec rate to timeout in systemtime (nanosec)

    xParam = xmlds.find("Parameter")
    if xParam is None:
        raise Exception, "Parameter not found in Label %s:" % (paramName, str(key))
    numSources, param = buildParam(xParam)

    labelSize = 12 + len(param)

    hdr = struct.pack(ENDIAN + "BBBBLL", codeBinary, sdi, numSources, 0,
                      refreshTime, labelSize)

    return hdr + param



def buildA429InputMessage(xmlmsg, msgIdx):
    '''
    Fill the structure
        UInt32_t messageId;           // Message ID from XML Configuration
        UInt32_t messageLength;       // Length of message payload (what is read from port)
        UInt32_t queueLength;         // Queue Length, 0 for Sampling
        UInt32_t messageRate;         // expected update rate of message in ms
        UInt32_t messageHdrOffset;    // Offset in message buffer
        UInt32_t portNameOffset;      // Offset of port Name (or CVT name) into string table
    '''
    
    global message_offset
    global message_dict
    global message_index

    msgid  = int(xmlmsg.attrib["id"])
    msglen = int(xmlmsg.attrib["length"])
    porttype = xmlmsg.attrib["portType"]
    porttype = porttype.lower()
    if porttype[0] == "q":
        queuelen = int(xmlmsg.attrib["queueLength"])
    else:
        queuelen = 0

    if message_dict.has_key(msgid):
        raise Exception, "Duplicate message id: %d" % msgid

    message_dict[msgid]  = message_offset
    message_index[msgid] = msgIdx

    msg = struct.pack(ENDIAN + "iiiii",
                      msgid,
                      msglen,
                      queuelen,
                      message_offset,
                      stringtable.append(xmlmsg.attrib["portName"]))

    # increment message offset: message length padded to MESSAGE_PADDING bytes
    blocklen = ((msglen + IOM.A429_MESSAGE_PADDING - 1) & ~(IOM.A429_MESSAGE_PADDING-1))
    message_offset += blocklen
    return msg

def buildA429Input(endianess, xmlroot):

    global ENDIAN
    ENDIAN = endianess

    # initialize objects build here global variables
    labels           = ""
    numLabels        = 0
    messages         = ""
    nofMessages      = 0
    global message_dict
    global message_offset
    global message_index

    message_dict = {}
    message_offset = 0

    xA429Input = xmlroot.find("A429Input")
    if xA429Input is not None:
        for x in xA429Input.iterfind("A429Message"):
            messages    += buildA429InputMessage(x, nofMessages)
            nofMessages += 1
            
        for x in xA429Input.iterfind("Label"):
            labels    += buildLabel(x)
            numLabels += 1

    #else set A429 config as empty

    return Bunch(labels=labels, 
                 labelStart=0, 
                 labelCount=numLabels, 
                 messages=messages, 
                 messageStart=0, 
                 messageCount=nofMessages,
                 messageSize=message_offset)

                    
