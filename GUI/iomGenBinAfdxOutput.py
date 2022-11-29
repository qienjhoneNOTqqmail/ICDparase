'''
Created on 30.11.2014

@author: dk

IOM Binary Config Generator for AFDX Output
'''

import struct
from bunch import Bunch

from iomGenBinConst import IOM
from iomGenBinEndian import ENDIAN
from stringtab import stringtable

numberOfOutputParams = 0    # used for calculating buffer sizes  
max_param      = 0          # stores the largest param offset, so the buffer size can be calculated
message_offset = 0          # next offset into message buffer  
message_dict   = {}         # dictionary of message with their offset in message buffer


def getMessagenameFromDSName(DsName):
    prefix,sep,suffixlist=DsName.partition("\'")
    prefixlist,sep,suffixlist=suffixlist.partition("\'")
    return prefixlist

def invertA429Label(inp):
    out =  ((inp & 0x01) << 7) | \
           ((inp & 0x02) << 5) | \
           ((inp & 0x04) << 3) | \
           ((inp & 0x08) << 1) | \
           ((inp & 0x10) >> 1) | \
           ((inp & 0x20) >> 3) | \
           ((inp & 0x40) >> 5) | \
           ((inp & 0x80) >> 7)
    return (out & 0xff)

# compute offset into message buffer from offset into a message and the message Id
def messageBufferOffset(messageId, msgOffset):
    intMsgId = int(messageId)
    if not intMsgId in message_dict:
        raise Exception, "Message Id <%s> not found" % messageId
    
    return message_dict[intMsgId] + msgOffset

encoding_table = {
        ('FLOAT', 4, 'FLOAT'):  IOM.SIGOUTTYPE_SIG32,
        ('FLOAT', 8, 'FLOAT'):  IOM.SIGOUTTYPE_SIG64,
        ('INT',   1, 'INT'):    IOM.SIGOUTTYPE_SIG8,
        ('INT',   2, 'INT'):    IOM.SIGOUTTYPE_SIG16,
        ('INT',   4, 'INT'):    IOM.SIGOUTTYPE_SIG32,
        ('INT',   8, 'INT'):    IOM.SIGOUTTYPE_SIG64,
        ('UINT',  4, 'INT'):    IOM.SIGOUTTYPE_SIG32,
        ('UINT',  8, 'INT'):    IOM.SIGOUTTYPE_SIG64,
        ('BOOL',  4, 'BOOL'):   IOM.SIGOUTTYPE_A664_BOOLEAN,
        ('COD',   4, 'ENUM'):   IOM.SIGOUTTYPE_BITFIELD32,
        ('COD',   4, 'INT'):    IOM.SIGOUTTYPE_BITFIELD32,
        ('BYTES', 1, 'BYTES'):  IOM.SIGOUTTYPE_MULTIPLE_BYTES,
        ('BNR',   4, 'FLOAT'):  IOM.SIGOUTTYPE_A429BNR_FLOAT,
        ('UBNR',  4, 'FLOAT'):  IOM.SIGOUTTYPE_A429UBNR_FLOAT,
        ('BNR',   4, 'INT'):    IOM.SIGOUTTYPE_A429BNR_INTEGER,
        ('UBNR',  4, 'INT'):    IOM.SIGOUTTYPE_A429UBNR_INTEGER,
        ('BCD',   4, 'FLOAT'):  IOM.SIGOUTTYPE_A429BCD_FLOAT,
        ('BCD',   4, 'INT'):    IOM.SIGOUTTYPE_A429BCD_INTEGER,
}


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



def buildParam(xmlparam):
    '''
    Build one parameter config  structure from XML
    '''
    global max_param

    paramType        = xmlparam.attrib['paramType']
    paramName        = xmlparam.attrib['paramNameValue']
    paramSize        = int(xmlparam.attrib["paramSize"])
    valueOffset      = int(xmlparam.attrib["paramOffsetValue"])
    statusOffset     = int(xmlparam.attrib["paramOffsetStatus"])
    valueNameOffset  = stringtable.append(xmlparam.attrib["paramNameValue"])
    statusNameOffset = stringtable.append(xmlparam.attrib["paramNameStatus"])
    paramSources     = 0
    
    if valueOffset > max_param:
        max_param = valueOffset

    if statusOffset > max_param:
        max_param = statusOffset

    param = struct.pack(ENDIAN + "iiihhiiL", 
                valueOffset, 
                statusOffset,
                paramSize,
                1, # always one destination
                0, # padding
                valueNameOffset, 
                statusNameOffset,
                0)  # default value not used

    x = xmlparam.find('destination')
    sigType    = x.attrib["type"]
    sigAccess  = int(x.attrib["access"])
    byteoffset = messageBufferOffset(x.attrib["message"], int(x.attrib["offset"]))
    bitlen     = int(x.attrib["bits"])
    lsb        = int(x.attrib["lsb"])
    scale      = float(x.attrib["lsbvalue"])

    key = (sigType, sigAccess, paramType)
    encoding = encoding_table.get(key)

    if encoding is None:
        raise Exception, "Illegal combination of signal and parameter types for %s: %s" % (paramName, str(key))

    msgIdx      = 0
    transportId = IOM.TRANSPORT_A664
    parOffset   = 0
    valOffset   = 0
    
    signal = struct.pack(ENDIAN + "hhLihhfLL", msgIdx, transportId, byteoffset, bitlen, lsb, encoding, scale, parOffset, valOffset)
    return param + signal 

def buildAfdxOutputDataset(xmlds):
    '''
    Build one data set config structure from XML to binary
    '''
    global numberOfOutputParams
    numparams = 0
    params = ""
    for x in xmlds.iterfind("Parameter"):
        params += buildParam(x)
        numparams += 1
        numberOfOutputParams += 1


    dslen = 32 + len(params)
    
    msgId     = int(xmlds.attrib['messageId'])
    fsboffset = int(xmlds.attrib['fsbOffset'])
    dsoffset  = int(xmlds.attrib['dsOffset'])
    dsname    = xmlds.attrib['name']
    dstypestr   = xmlds.attrib['dsType']

    if dstypestr == 'A429':
        dstype   = 1
        label    = int(xmlds.attrib['dsA429Label'])
        sdi      = int(xmlds.attrib['dsA429SDI'])
        labelsdi = invertA429Label(label) | (sdi << 8)

        ssmtypestr = int(xmlds.attrib['dsA429SSMType'])
        ssmtype = {"NONE": 0, "BNR": 1, "BCD": 2, "DIS": 3}[ssmtypestr]
    else:
        dstype    = 0  
        labelsdi  = 0
        ssmtype   = 0  
    
    messagename = getMessagenameFromDSName(dsname)
    if cmp(messagename[messagename.rfind("_"):],'_XTALK'):
        isPeerXtalk = 0
    else:
        isPeerXtalk= 1
    hdr = struct.pack(ENDIAN + "iiiiiiii",
            dstype,   # 0: normal / 1: has embedded 429 label / 2: has embedded CAN Message (not supported)
            dslen,    
            messageBufferOffset(msgId, fsboffset),
            messageBufferOffset(msgId, dsoffset),
            numparams,
            labelsdi,
            ssmtype,
            isPeerXtalk
            )
    return hdr + params 



def buildAfdxOutputMessage(xmlmsg):
    '''
    Fill the structure
        UInt32_t messageId;           // Message ID from XML Configuration
        UInt32_t messageLength;       // Length of message payload (what is read from port)
        UInt32_t queueLength;         // Queue Length, 0 for Sampling
        UInt32_t messageRate;         // expected update rate of message in ms
        UInt32_t messageHdrOffset;    // Offset in message buffer
        UInt32_t portId;              // Whatever that is on the platform
        UInt32_t portNameOffset;      // Offset of port Name (or CVT name) into string table
    '''
    
    global message_offset
    global message_dict
    
    msgid    = int(xmlmsg.attrib["id"])
    msglen   = int(xmlmsg.attrib["length"])
    rate     = int(xmlmsg.attrib["a653PortRefreshPeriod"])
    porttype = xmlmsg.attrib["portType"]
    if porttype[0] == "Q":
        queuelen = int(xmlmsg.attrib["queueLength"])
    else:
        queuelen = 0

    if message_dict.has_key(msgid):
        raise Exception, "Duplicate message id: %d" % msgid
    
    message_dict[msgid] = message_offset

    out = struct.pack(ENDIAN + "iiiiiiiiiiiiii",
                      msgid,
                      msglen,
                      queuelen,
                      rate,
                      0,              #validConfirmationTime
                      0,              #invalidConfirmationTime
                      message_offset,
                      stringtable.append(xmlmsg.attrib["portName"]),
                      getIntOrZero(xmlmsg.attrib["crcFsbOffset"], "crcFsbOffset"),
                      getIntOrZero(xmlmsg.attrib["crcOffset"], "crcOffset"),  
                      getIntOrZero(xmlmsg.attrib["fcFsbOffset"], "fcFsbOffset"),
                      getIntOrZero(xmlmsg.attrib["fcOffset"], "fcOffset"),   
                      0,              #schedOffset
                      0               #schedRate
                      )

    # increment message offset: message length padded to IOM.MESSAGE_PADDING bytes
    blocklen = (msglen + IOM.A664_MESSAGE_PADDING - 1) & ~(IOM.A664_MESSAGE_PADDING-1)
    message_offset += blocklen
    return out

def buildAfdxOutput(endianess, xmlroot):

    global message_offset
    global message_dict
    global ENDIAN
    global max_param
    global numberOfOutputParams

    ENDIAN = endianess
	     
    message_offset = 0
    message_dict = {}
    
    # initialize objects build here global variables
    datasets     = ""
    numdataset   = 0
    messages     = ""
    nummessages  = 0
    max_param    = 0
    
    section = xmlroot.find("Output/AfdxOutput")
    if section is not None:
        for x in section.iterfind("AfdxMessage"):
            messages += buildAfdxOutputMessage(x)
            nummessages += 1
            
        for x in section.iterfind("DataSet"):
            datasets += buildAfdxOutputDataset(x)
            numdataset += 1

    return Bunch(datasets=datasets, 
                 datasetStart=0, 
                 datasetCount=numdataset, 
                 messages=messages, 
                 messageStart=0, 
                 messageCount=nummessages,
                 messageSize=message_offset,
                 paramBufferSize=max_param,
                 numberOfOutputParams=numberOfOutputParams)


