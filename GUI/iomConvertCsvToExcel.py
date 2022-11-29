
import os
import sys
import mkpath
from imtExcelRW import *

paramInputColumns = (
    # header,                         value,                         len\
)

csvSeparator = ";"
csvLfChar    = "$"

errcount = 0

def logerr(msg):
    global errcount

    sys.stderr.write(msg + "\n")
    sys.stderr.flush()
    errcount+=1
    

def saveIt(outputfn, paramInputColumns, data):

    genExcelFile(outputfn, (("Sheet 1", paramInputColumns, data),))


def splitcomma(line):
    global paramInputColumns
    global csvSeparator
    global csvLfChar

    entry={}
    entryData = line.decode('utf-8').split(csvSeparator)[:-1]
    i = 0
    
    for item in entryData:
        entry[paramInputColumns[i][0]]=item.replace(csvLfChar, "\n")
        i+=1
    
    return entry

    
def main(separator, lfChar, outputfn,inputfn):
    global paramInputColumns
    global csvSeparator
    global csvLfChar

    splitName = os.path.split(outputfn)
    mkpath.makePath (splitName[0])    # create the path of the output file if it does not exist

    if separator != None:
        csvSeparator = separator
    
    if lfChar != None:
        csvLfChar = lfChar
    
    inputfile  = open(inputfn)
    inputlines = inputfile.readlines()
    
    title = inputlines[0].decode("utf-8").split(csvSeparator)[:-1]
    
    #populate the column description
    paramInputColumns=tuple(zip(title,title,map(len,title)))
    
    inputlines = inputlines[1:]
    data = tuple(map(splitcomma,inputlines))
    
    saveIt(outputfn,paramInputColumns,data)
       

def usage():
    sys.stderr.write('Usage: separator LF_character outputxls inputcsv\n')

if __name__ == '__main__':
    if len(sys.argv) < 5:
        usage()
        sys.exit(1)
    else:
        sys.exit(main(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]))
        
    