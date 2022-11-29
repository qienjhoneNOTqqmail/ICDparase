import sys
import getopt
import iomGenReadDD

from imtExcelRW import *


class Bunch(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


def getIntParamsOffset(inputDD):
    endOffset = 0
    for input in inputDD.values():
        if input.offset > endOffset:
            endOffset = input.offset+input.elements*input.size
    return endOffset

def createIntDD(initialOffset, signalList, outputFileName):
    str = '<namelist model="INTERNAL_PARAMS">\n'
    currentOffset = initialOffset
    
    for signal in signalList:
        sigType = signal.type
        if sigType not in ['INT']:
            # list could be extended, with extra conversion, we don't have any need for that so far.
            raise Exception, "Unsupported type as internal parameter: %s (%s)" % (signal.type, signal.name)
        else:
            sigType = 'int'
            sigElements = 1
            sigSize = signal.size/8
            if sigSize != 4:
                sigElements = sigSize/4
                sigSize     = 4
            
            
        str+= '    <parameter offset="%s"  size="%s" elements="%s" type="%s" name="%s"/>\n' % (currentOffset, sigSize, sigElements, sigType, signal.name)
        currentOffset += sigSize*sigElements
        str+= '    <parameter offset="%s"  size="%s" elements="%s" type="%s" name="%s"/>\n' % (currentOffset, 4, 1, "int", signal.name+"_Status")
        currentOffset += 4
    str += '</namelist>\n'
    
    outputFile = open(outputFileName,"w")
    outputFile.write(str)
    outputFile.close()


def extractIntSignals(inputSignals):
    intParams = []
    for inputSignal in inputSignals:
        if inputSignal.Parameter.split(".")[0] == "InternalParam":
            intParams.append(Bunch(name=inputSignal.Parameter, type=inputSignal.DataType, size=inputSignal.DataSize))
    return intParams
        
def usage():
    sys.stderr.write("Usage: iomGenIntDD [--indd inputdd] [-o outputfile] excelicd")

def main(arglist):

    # Parse command line arguments
    inputddfiles   =  []
    outputddfiles  = []
    xmlfile        = None
    intParamOffset = 0
    intenalSignals = []

    opts, args = getopt.getopt(arglist, 'ho:', ['indd=', 'output=', 'help'])
    
    for o, a in opts:
        if o in ['-h', '--help']:
            usage()
            return -1
        elif o in [ '--indd']:
            if a is not "":
                inputddfiles.append(a)
        elif o in [ '-o', '--output']:
            xmlfile = a
        else:
            usage()
            return -1

    if len(args) != 1:
        usage()
        return -1
        
    excelicdfile = args[0]

    if len(inputddfiles) > 0:
        inputDD = iomGenReadDD.ddread(inputddfiles)
    else:
        inputDD = None

    inputSignals = readExcelFile(excelicdfile, ('InputSignals',))[0]
    
    intParamOffset  = getIntParamsOffset(inputDD)
    internalSignals = extractIntSignals(inputSignals)
   
    createIntDD(intParamOffset,internalSignals, xmlfile)
        
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))