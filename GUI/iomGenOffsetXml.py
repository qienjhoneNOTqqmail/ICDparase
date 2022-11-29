
import os        
import sys
from imtExcelRW import *
from Cheetah.Template import Template
errcount = 0


TEMPLATE_XMLDD = '''<namelist model="TOPLEVEL">
 #set $offset = 0
 #for $dataEntry in $dd
    #set $elements    = 1
    #set $dataSize    = $dataEntry['Data Size']/8
    #set $dataType    = $dataEntry['Data Type'].lower()
    #if $dataType == "float":
        #set $dataType = "real"
    #end if
    
    #if $dataType == "bytes":
        #set $dataType = "char"
        #set $elements = $dataSize
        #set $dataSize = 1
    #end if

    #set $offset = int($dataEntry['IOBufferOffset'])

    #set $dataTypePad = "     "[:-len($dataType)]
    #set $offsetPad   = "     "[:-len(str($offset))]
    <parameter offset="$offset"$offsetPad size="$dataSize" elements="$elements" type="$dataType"$dataTypePad name="$dataEntry['Parameter Name']"/>
 #end for
</namelist>
'''

def logerr(msg):
    global errcount

    sys.stderr.write("\nERROR****: " + msg + "\n")
    sys.stderr.flush()
    errcount+=1

        
def main(args):
    # read Excel files exported from DOOORS
    outfn  = args[0]
    xlsSrc = args[1]

    # check parameters
    try:
        FILE = open(outfn,"w")
        FILE.writelines("Hello")
        FILE.close()
    except:
        logerr("Output File already open: %s" % outfn )
        usage()
        return -1

    if not os.path.exists(xlsSrc):
        logerr("Can't open Excel ICD file: %s" % xlsSrc )
        usage()
        return -1
        
    # Read Excel Export from DOORS Selection Set sources
    sheetNames     = getExcelFileSheetNames(xlsSrc)
    dataDictionary = readExcelFile(xlsSrc, (sheetNames[0],))[0]
    
    dataDictionary = sorted(dataDictionary, key=lambda data:(data.IOBufferOffset))
    
    #basic checking on offsets (Information only...)
    inBufferMaxOffset = 0
    internalParams    = []
    for dataEntry in dataDictionary:
        currOffset = dataEntry['IOBufferOffset']
        if dataEntry['InIOBuffer'].upper() == 'YES':
            if currOffset > inBufferMaxOffset:
                inBufferMaxOffset = currOffset 
        else:
            internalParams.append(dataEntry)
    
    for internalParam in internalParams:
        if internalParam['IOBufferOffset'] <= inBufferMaxOffset:
            print " -- Offset for %s is invalid (%d <= %d)" % (internalParam['Parameter Name'],internalParam['IOBufferOffset'],inBufferMaxOffset)
            print " --      IOM Internal parameters should be stored at the end of the regular IOBuffer parameters"

    tmpl = Template(TEMPLATE_XMLDD, searchList=[{ "dd" : dataDictionary }])
    FILE = open(outfn,"w")
    FILE.write(tmpl.respond())
    FILE.close()
            
    return 0


def usage():
    sys.stderr.write('Usage: outputfile SW_DD_IN \n\n')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        usage()
        sys.exit(1)
    else:
        sys.exit(main(sys.argv[1:]))
        
    