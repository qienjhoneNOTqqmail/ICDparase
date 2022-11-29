'''
Created on 30.11.2014

@author: dk

Generate IO Manager binary configuration from XML File.

 Structure of binary configuration:
    Header
    AFDX Input Messages
    AFDX Input Datasets
    AFDX Output Messages
    AFDX Output Datasets
    CAN Input Messages
    CAN Output Messages
    A429 Input Messages
    A429 Output Messages
    DIO Input
    DIO Output
    Stringtable
    CRC

 Header structure
    Magic number (0xC919DDCF)
    Totalsize
    AFDX Input Messages Start 
    AFDX Input Messages Number
    AFDX Input Datasets Start 
    AFDX Input Datasets Number
    AFDX Output Messages Start 
    AFDX Output Messages Number
    AFDX Output Datasets Start 
    AFDX Output Datasets Number
    CAN Input Messages Start
    CAN Input Messages Number
    CAN Output Messages Start
    CAN Output Messages Number
    A429 Input Messages Start
    A429 Input Messages Number
    A429 Output Messages Start
    A429 Output Messages Number
    DIO  Input Messages Start
    DIO  Input Messages Number
    DIO  Output Messages Start
    DIO  Output Messages Number
    Stringtable Start
    Stringtable Length
 ---------------------------------------------------------------------
'''

import sys
import struct
import zlib
from lxml import etree
from exceptions import Exception

from bunch import Bunch
from stringtab import stringtable

from iomGenBinEndian import ENDIAN
from iomGenBinConst import IOM

from iomGenBinAfdxInput import buildAfdxInput
from iomGenBinAfdxOutput import buildAfdxOutput
from iomGenBinCan import buildCanInput, buildCanOutput
from iomGenBinA429 import buildA429Input, buildA429Output
from iomGenBinDio import buildDioInput, buildDioOutput

magicNumber = 0xC919DDCF

def buildIOM(xmlroot):
    '''
    Build complete IOMConfig structure from XML
    '''
    stringtable.reset()
    
    # build sections
    afdxInput  = buildAfdxInput(ENDIAN,xmlroot)
    afdxOutput = buildAfdxOutput(ENDIAN,xmlroot)
    canInput   = buildCanInput(ENDIAN,xmlroot)
    canOutput  = buildCanOutput(ENDIAN,xmlroot)
    a429Input  = buildA429Input(xmlroot)
    a429Output = buildA429Output(xmlroot)
    dioInput   = buildDioInput(xmlroot)
    dioOutput  = buildDioOutput(xmlroot)


    # pad stringtable to multiple of 4 bytes
    stringtable.pad(4)
    
    # compute offsets of all sections
    headersize = 24 * 4
    offset = headersize
    afdxInput.messageStart = offset
    offset += len(afdxInput.messages)
    afdxInput.datasetStart = offset
    offset += len(afdxInput.datasets)

    afdxOutput.messageStart = offset
    offset += len(afdxOutput.messages)
    afdxOutput.datasetStart = offset
    offset += len(afdxOutput.datasets)
    
    canInput.messageStart = offset
    offset += len(canInput.messages)
    canOutput.messageStart = offset
    offset += len(canOutput.messages)

    a429Input.messageStart = offset
    offset += len(a429Input.messages)
    a429Output.messageStart = offset
    offset += len(a429Output.messages)

    dioInput.messageStart = offset
    offset += len(dioInput.messages)
    dioOutput.messageStart = offset
    offset += len(dioOutput.messages)

    strtabStart = offset
    strtabSize  = stringtable.len()
    offset += strtabSize

    totalSize    = offset + 4

    # assemble header
    header = struct.pack(ENDIAN + "Ii iiii iiii iiii iiii iiii ii", 
                magicNumber, 
                totalSize, 
                afdxInput.messageStart,
                afdxInput.messageCount,
                afdxInput.datasetStart,
                afdxInput.datasetCount,
                afdxOutput.messageStart,
                afdxOutput.messageCount,
                afdxOutput.datasetStart,
                afdxOutput.datasetCount,
                canInput.messageStart,
                canInput.messageCount,
                canOutput.messageStart,
                canOutput.messageCount,
                a429Input.messageStart,
                a429Input.messageCount,
                a429Output.messageStart,
                a429Output.messageCount,
                dioInput.messageStart,
                dioInput.messageCount,
                dioOutput.messageStart,
                dioOutput.messageCount,
                strtabStart, 
                strtabSize)

    # assemble IOM
    output = header + \
             afdxInput.messages + afdxInput.datasets + \
             afdxOutput.messages + afdxOutput.datasets + \
             canInput.messages +   \
             canOutput.messages +  \
             a429Input.messages +  \
             a429Output.messages + \
             dioInput.messages +   \
             dioOutput.messages +  \
             stringtable.buffer()
    
    # compute and append CRC
    crc = zlib.crc32(output) & 0xffffffff
    output += struct.pack(ENDIAN + "I", crc)

    # thats it
    
    #finally build defines with message buffer sizes
    s = '''
#define IOEN_MAX_INPUT_MESSAGE_BUFFER_SIZE    (%d)
#define IOEN_MAX_OUTPUT_MESSAGE_BUFFER_SIZE    (%d)
''' % ((afdxInput.messageSize  + 1023)/1024*1024, 
       (afdxOutput.messageSize + 1023)/1024*1024)
    
    return output, s


def bin2hex(s, namesuffix):
    output = "unsigned char iomConfig_%s[] = {\n  " % namesuffix
    n = 0
    for c in s[0:-1]:
        output += "0x%02x, " % ord(c)
        n += 1
        if n % 16 == 0:
            output += "\n  "
    output += "0x%02x" % ord(s[-1])
    output += "\n};\n"
    return output

def main(args):
    '''
    Main
    Open XML input file, parse it and build binary structure from it.
    Write binary structure to file
    '''
    global ENDIAN
    
    if args[0] == "--bigendian":
        ext = '.bigendian'
        ENDIAN=">"
        del args[0]
    elif args[0] == "--littleendian":
        ext = ".littleendian"
        ENDIAN="<"
        del args[0]

    input_filename  = args[0]
    basename = input_filename.rsplit('.', 1)[0]
    bin_filename = basename + ext + '.bin'
    c_filename = basename + ext + '.c'
    
    instance = args[1].rsplit('/')[-1]

    xmlfile = open(input_filename, "r")
    xmltree = etree.parse(xmlfile)
    root = xmltree.getroot()
    
    # build binary and write it to file
    output, cdefs = buildIOM(root)
    outfile = open(bin_filename, "wb")
    outfile.write(output)
    outfile.close()
    
    # convert binary into C hex data and write it to file
    outhex = bin2hex(output, instance)
    outfile = open(c_filename, "w");
    outfile.write(outhex)
    outfile.close()
    
    hdrfilename = basename  + "_msgbuf.h"
    open(hdrfilename, "w").write(cdefs)
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
