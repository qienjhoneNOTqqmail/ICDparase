
import os        
import sys
from imtExcelRW import readExcelFile, getExcelFileSheetNames, genExcelFile
from bunch import Bunch



icdInParamsColumns = (
    # header,                    value,                         width
    ("Status",                  "Status",                        10),
    ("Parameter",               "Parameter",                     40),
    ("SysParameter",            "SysParameter",                  40),
    ("External",                "External",                      10),
    ("DataType",                "DataType",                      10),
    ("DataSize",                "DataSize",                      10),
    ("DataDefaultVal",          "DataDefaultVal",                15),
    ("DataMinVal",              "DataMinVal",                    15),
    ("DataMaxVal",              "DataMaxVal",                    15),
    ("SourceName",              "SourceName",                    15),
    ("SpecialFunction",         "SpecialFunction",               20),
    ("RpName",                  "RpName",                        40),
)

icdOutParamsColumns = (
    # header,                    value,                         width
    ("Status",                  "Status",                        10),
    ("Parameter",               "Parameter",                     40),
    ("SysParameter",            "SysParameter",                  40),
    ("DataType",                "DataType",                      10),
    ("DataSize",                "DataSize",                      10),
    ("SpecialFunction",         "SpecialFunction",               20),
    ("DpName",                  "DpName",                        40),
)


sourceColumns = (              
    # header,                    value,                         width
    ("Status",                  "Status",                        10),
    ("Consumer",                "Consumer",                      10),
    ("Destination LRUs",        "Destination LRUs",              25),
    ("Source Name",             "Source Name",                   20),
    ("Selection Set",           "Selection Set",                 20),
    ("Granularity",             "Granularity",                   20),
    ("Selection Criteria",      "Selection Criteria",            25),
    ("Selection Order",         "Selection Order",               15),
    ("LIC Parameter",           "LIC Parameter",                 30),
    ("LIC Value",               "LIC Value",                     15),
    ("Lock Interval",           "Lock Interval",                 15),
    ("Comments",                "Comments",                      15),
    ("Change History",          "Change History",                15),
    ("UniqueKey",               "UniqueKey",                     40),
)                                                              




errcount = 0


def logerr(msg):
    global errcount

    sys.stderr.write("\nERROR****: " + msg + "\n")
    sys.stderr.flush()
    errcount+=1

# Not used anymore, but may be needed in the near future
#def getMinMax(type):
#    type = type.lower()
#    if type.startswith('int'):
#        return IOM.MIN_VALUE_SINT32, IOM.MAX_VALUE_SINT32
#    elif type.startswith('unsigned'):
#        return 0, IOM.MAX_VALUE_UTINT32
#    elif type == "bitfield":
#        return 0, IOM.MAX_VALUE_UTINT32
#    elif type.startswith('float'):
#        return -IOM.MAX_VALUE_FLOAT32, IOM.MAX_VALUE_FLOAT32
#    elif type.startswith('real'):
#        return -IOM.MAX_VALUE_FLOAT32, IOM.MAX_VALUE_FLOAT32
#    elif type.startswith('bool'):
#        return 0, 1
#    elif type.startswith('char'):
#        return 0, 255
#    else:
#        return 0, IOM.MAX_VALUE_UTINT32


def saveIt(outputfn, icdInParam, icdOutParam, selectionSet):

    
    genExcelFile(outputfn, 
        (
            ("ICD Input Parameters",  icdInParamsColumns, icdInParam),

            ("ICD Output Parameters",  icdOutParamsColumns, icdOutParam ),

            ("Sources",  sourceColumns, 
                sorted(selectionSet, 
                       key=lambda sig: (sig["Selection Set"], sig["Source Name"], sig["Selection Order"])
                )
            ),
        )
    )


def joinIcdInputParam(ddInExcel, mapInExcel):
    reclst = []

    # create Selection Set Source dict
    newDdIn = dict()
    for m in ddInExcel:
        if m["System Parameter Name"] != "N/A":
            key = m["System Parameter Name"]
            newDdIn[key] = m

    for mapping in mapInExcel:
        key = mapping["Logic Parameter"]
        if newDdIn.has_key(key):
            dd  = newDdIn[key]
            
            # Get range if present, otherwise use type default
            if dd["Functional Min Range"] == None:
                minval = "TBD"
            else:
                minval = dd["Functional Min Range"]
                
            if dd["Functional Max Range"] == None:
                maxval = "TBD"
            else:
                maxval = dd["Functional Max Range"]
            
            rec = Bunch(
                Status           = mapping["Status"],
                Parameter        = dd["Parameter Name"],
                SysParameter     = mapping["Logic Parameter"],
                External         = mapping["External"],
                DataType         = dd["Data Type"],
                DataSize         = dd["Data Size"],
                DataDefaultVal   = 0,
                DataMinVal       = minval,
                DataMaxVal       = maxval,
                SourceName       = mapping["Source Name"],
                SpecialFunction  = mapping["SpecialFunction"],
                RpName           = mapping["Req RPName"],
            )
            reclst.append(rec)

    return reclst


def joinIcdOutputParam(ddOutExcel, mapOutExcel):
    reclst = []

    # create Selection Set Source dict
    newDdOut = dict()
    for m in ddOutExcel:
        if m["System Parameter Name"] != "N/A":
            key = m["System Parameter Name"]
            newDdOut[key] = m

    for mapping in mapOutExcel:
        key = mapping["Logic Parameter"]
        if newDdOut.has_key(key):
            dd  = newDdOut[key]
            
            rec = Bunch(
                Status           = mapping["Status"],
                Parameter        = dd["Parameter Name"],
                SysParameter     = mapping["Logic Parameter"],
                DataType         = dd["Data Type"],
                DataSize         = dd["Data Size"],
                SpecialFunction  = mapping["SpecialFunction"],
                DpName           = mapping["DPNameRef"],
            )
            reclst.append(rec)

    return reclst

    
        

def main(args):
    # read Excel files exported from DOOORS
    outfn   = args[0]
    inSrc   = args[1]
    ddIn    = args[2]
    ddOut   = args[3]
    mapIn   = args[4]
    mapOut  = args[5]
    
    currLRU = None
    if len(args)== 7:
        currLRU = args[6]

    # check parameters
    try:
        FILE = open(outfn,"w")
        FILE.writelines("Hello")
        FILE.close()
    except:
        logerr("Output File already open: %s" % outfn )
        usage()
        return -1

    if not os.path.exists(inSrc):
        logerr("Can't open Excel ICD file: %s" % inSrc )
        usage()
        return -1
    
    if not os.path.exists(ddIn):
        logerr("Can't open Excel ICD file: %s" % ddIn )
        usage()
        return -1
    
    if not os.path.exists(ddOut):
        logerr("Can't open Excel ICD file: %s" % ddOut )
        usage()
        return -1
    
    if not os.path.exists(mapIn):
        logerr("Can't open Excel ICD file: %s" % mapIn )
        usage()
        return -1
    
    if not os.path.exists(mapOut):
        logerr("Can't open Excel ICD file: %s" % mapOut )
        usage()
        return -1
    
    # Read Excel Export from DOORS Selection Set sources
    sheetNames    = getExcelFileSheetNames(inSrc)
    selectionSet  = readExcelFile(inSrc, (sheetNames[0],))[0]
    
    if len(selectionSet) and currLRU:
        #select only the appropriate source for this LRU
        selectionSet = filter(lambda source: currLRU in source["Destination LRUs"] ,selectionSet)

    # Read Excel Export from DOORS DD IN
    sheetNames    = getExcelFileSheetNames(ddIn)
    ddInExcel     = readExcelFile(ddIn,  (sheetNames[0],))[0]

    # Read Excel Export from DOORS DD OUT
    sheetNames    = getExcelFileSheetNames(ddOut)
    ddOutExcel    = readExcelFile(ddOut,  (sheetNames[0],))[0]

    # Read Excel Export from DOORS Mapping IN
    sheetNames    = getExcelFileSheetNames(mapIn)
    mapInExcel    = readExcelFile(mapIn,  (sheetNames[0],))[0]
    if len(mapInExcel) and currLRU:
        #select only the appropriate parameters for this LRU
        mapInExcel = filter(lambda param: currLRU in param["Destination LRUs"] ,mapInExcel)

    # Read Excel Export from DOORS Mapping OUT
    sheetNames    = getExcelFileSheetNames(mapOut)
    mapOutExcel   = readExcelFile(mapOut,  (sheetNames[0],))[0]
    if len(mapOutExcel) and currLRU:
        #select only the appropriate parameters for this LRU
        mapOutExcel = filter(lambda param: currLRU in param["Source LRU"] ,mapOutExcel)    

    # create ICD IN dict
    icdInParam = joinIcdInputParam(ddInExcel, mapInExcel)

    # create ICD OUT dict
    icdOutParam = joinIcdOutputParam(ddOutExcel, mapOutExcel)


    # create Selection Set Source dict
    newSelectionSet = dict()
    for m in selectionSet:
        key = m["Source Name"]
        newSelectionSet[key] = m
    
    # Write Excel HF ICD
    saveIt(outfn, 
           icdInParam, icdOutParam, newSelectionSet.values())
 
    return 0


def usage():
    sys.stderr.write('Usage: outputfile   selectionSetSourcesFile   dd_in   dd_out   mapping_in   mapping_out [current LRU]\n\n')

if __name__ == '__main__':
    if len(sys.argv) < 6:
        usage()
        sys.exit(1)
    else:
        sys.exit(main(sys.argv[1:]))
        
    