'''
Created on 30.11.2014

@author: dk

IOM Binary Config Generator for Discrete IO
'''

from bunch import Bunch
import struct

from iomGenBinConst import IOM
from iomGenBinEndian import ENDIAN
from stringtab import stringtable


# ------------------------------------------------------------------------------------
#    DIO Support (Dummy Only)
# ------------------------------------------------------------------------------------

def buildDioInputMessage(x):
    return ""

def buildDioInput(xmlroot):
    messages     = ""
    nummessages  = 0
    
    section = xmlroot.find("DioInput")
    if section is not None:
        for x in section.iterfind("DioMessage"):
            messages += buildDioInputMessage(x)
            nummessages += 1

    return Bunch(messages=messages, 
                 messageCount=nummessages, 
                 messageStart=0)

def buildDioOutputMessage(x):
    return ""

def buildDioOutput(xmlroot):
    messages     = ""
    nummessages  = 0
    
    section = xmlroot.find("DioOutput")
    if section is not None:
        for x in section.iterfind("DioMessage"):
            messages += buildDioOutputMessage(x)
            nummessages += 1

    return Bunch(messages=messages, 
                 messageCount=nummessages, 
                 messageStart=0)
