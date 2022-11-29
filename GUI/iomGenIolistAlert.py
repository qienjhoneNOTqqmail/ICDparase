
import os        
import sys
from imtExcelRW import *
from iomGenBinConst import IOM
from iomGenBinConst import IOM


alertColumns = (
    # header,                                                    value,                                                    width
    ("Status",                                                  "Status",                                                   10),
    ("Reference Number",                                        "Reference Number",                                         20),
    ("Alert ID",                                                "Alert ID",                                                 10),
    ("Text of the Alert Message",                               "Text of the Alert Message",                                25),
    ("High Level Description",                                  "High Level Description",                                   25),
    ("Alert Type",                                              "Alert Type",                                               10),
    ("Display Allocation",                                      "Display Allocation",                                       20),
    ("Synoptic Page",                                           "Synoptic Page",                                            20),
    ("Other Display Window Effects",                            "Other Display Window Effects",                             20),
    ("Control Panel Annunciator Effect",                        "Control Panel Annunciator Effect",                         20),
    ("CPA Lamp ID",                                             "CPA Lamp ID",                                              20),
    ("Aural Alert Message",                                     "Aural Alert Message",                                      20),
    ("Aural Alert IDs",                                         "Aural Alert IDs",                                          20),
    ("Aural Alert Priority",                                    "Aural Alert Priority",                                     20),
    ("Aural Alert Type",                                        "Aural Alert Type",                                         20),
    ("Alert Message Logic Statements",                          "Alert Message Logic Statements",                           40),
    ("Message Classification",                                  "Message Classification",                                   20),
    ("Flight Phase Inhibit",                                    "Flight Phase Inhibit",                                     20),
    ("Umbrella Messages Associated with the Alert Message",     "Umbrella Messages Associated with the Alert Message",      20),
    ("Collector Messages Associated with the Alert Message",    "Collector Messages Associated with the Alert Message",     20),
    ("Pilot Action",                                            "Pilot Action",                                             20),
    ("Action Time",                                             "Action Time",                                              15),
    ("Additional Comments",                                     "Additional Comments",                                      20),
    ("Alert Reference List",                                    "Alert Reference List",                                     20),
    ("Parameter Reference List",                                "Parameter Reference List",                                 20),
)

icdParamsColumns = (
    # header,                                                    value,                                                    width
    ("Status",                                                  "Status",                                                   10),
    ("Parameter",                                               "Parameter",                                                30),
    ("External",                                                "External",                                                 10),
    ("DataType",                                                "DataType",                                                 10),
    ("DataSize",                                                "DataSize",                                                 15),
    ("DataDefaultVal",                                          "DataDefaultVal",                                           15),
    ("DataMinVal",                                              "DataMinVal",                                               15),
    ("DataMaxVal",                                              "DataMaxVal",                                               15),
    ("SourceName",                                              "SourceName",                                               20),
    ("SpecialFunction",                                         "SpecialFunction",                                          20),
    ("RpName",                                                  "RpName",                                                   40), 
    # RpName used instead of pub ref, to keep compatibility with other io lists
)


sourceColumns = (                                              
    # header,                                                    value,                                                    width
    ("Status",                                                  "Status",                                                   10),
    ("Consumer",                                                "Consumer",                                                 10),
    ("Destination LRUs",                                        "Destination LRUs",                                         25),
    ("Source Name",                                             "Source Name",                                              20),
    ("Selection Set",                                           "Selection Set",                                            20),
    ("Selection Criteria",                                      "Selection Criteria",                                       25),
    ("Selection Order",                                         "Selection Order",                                          15),
    ("LIC Parameter",                                           "LIC Parameter",                                            30),
    ("LIC Value",                                               "LIC Value",                                                15),
    ("Lock Interval",                                           "Lock Interval",                                            15),
    ("Comments",                                                "Comments",                                                 15),
    ("Change History",                                          "Change History",                                           15),
    ("UniqueKey",                                               "UniqueKey",                                                40),
)                                                              

identificationColumns = (                                              
    # header,                                                    value,                                                    width
    ("Type",                                                    "Type",                                                     40),
    ("Value",                                                   "Value",                                                    20),
)                                                              



errcount = 0


def logerr(msg):
    global errcount

    sys.stderr.write("\nERROR****: " + msg + "\n")
    sys.stderr.flush()
    errcount+=1

def getMinMax(type):
    type = type.lower()
    if type.startswith('int'):
        return IOM.MIN_VALUE_SINT32, IOM.MAX_VALUE_SINT32
    elif type.startswith('unsigned'):
        return 0, IOM.MAX_VALUE_UTINT32
    elif type == "bitfield":
        return 0, IOM.MAX_VALUE_UTINT32
    elif type.startswith('float'):
        return IOM.MIN_VALUE_FLOAT32, IOM.MAX_VALUE_FLOAT32
    elif type.startswith('real'):
        return IOM.MIN_VALUE_FLOAT32, IOM.MAX_VALUE_FLOAT32
    elif type.startswith('bool'):
        return 0, 1
    else:
        return 0, IOM.MAX_VALUE_UTINT32


def saveIt(outputfn, identlst, fdasAlertIds, fdasAlertIcd, selectionSet):

    genExcelFile(outputfn, 
        (
            ("Identification",  identificationColumns, identlst ),
            ("Alert",  alertColumns, 
                sorted(fdasAlertIds, 
                       key=lambda sig: (sig["Alert ID"])
                )
            ),
            ("ICD Parameters",  icdParamsColumns, fdasAlertIcd ),
            ("Sources",  sourceColumns, 
                sorted(selectionSet, 
                       key=lambda sig: (sig["Selection Set"], sig["Source Name"], sig["Selection Order"])
                )
            ),
        )
    )


def joinOutputSignals(fdasAlertIcdExcel):
    reclst = []
    usedSelSet = dict() 

    for icd in fdasAlertIcdExcel:

        min, max = getMinMax(icd["Data Type"])
        
        rec = Bunch(
            Status           = icd["Status"],
            Parameter        = icd["Logic Parameter"],
            External         = icd["External"],
            DataType         = icd["Data Type"],
            DataSize         = 32,
            DataDefaultVal   = icd["Default Value"],
            DataMinVal       = min,
            DataMaxVal       = max,
            SourceName       = icd["SourceName"],
            SpecialFunction  = icd["SpecialFunction"],
            RpName           = icd["Req Pubref"],   # RpName used instead of pub ref, to keep compatibility with other io lists
        )
        usedSelSet[rec.SourceName]=""
        reclst.append(rec)

    return reclst,usedSelSet

def getIdentification(outFilename):
    identlst = []

    # Get ATA and member system from outFilename eg. "c:/tmp/ATA21_AMS_Alert.xlsx"
    # Get ATA and member system from outFilename eg. "c:/tmp/Configuration_Warning.xlsx"
    fileParts = os.path.split (outFilename)  # split outFilename to path and filename
    filename  = fileParts[1]                 # get filename without path
    
    if filename[0:6] == "Config":
        ataNr     = "N/A"
        member    = "CONFIG"
    else:
        ataNr     = filename[3:5]
        splitted  = filename.split("_")
        member    = splitted[1]
    
    rec1 = Bunch(Type = "ATA",              Value = ataNr)
    rec2 = Bunch(Type = "Member System",    Value = member)
    rec3 = Bunch(Type = "Version",          Value = "1.0")
    rec4 = Bunch(Type = "Template Version", Value = "1.1")
    identlst.append(rec1)
    identlst.append(rec2)
    identlst.append(rec3)
    identlst.append(rec4)

    return identlst



def main(args):
    # read Excel files exported from DOOORS
    outfn = args[0]
    inSrc = args[1]
    infn  = args[2]
    inIcd = args[3]

    # check parameters
    try:
        FILE = open(outfn,"w")
        FILE.writelines("Hello")
        FILE.close()
    except:
        logerr("Output File already open: %s" % outfn )
        usage()
        return -1
    
    
    if not os.path.exists(infn):
        logerr("Can't open Excel ICD file: %s" % infn )
        usage()
        return -1
    
    if not os.path.exists(inSrc):
        logerr("Can't open Excel ICD file: %s" % inSrc )
        usage()
        return -1
    
    if not os.path.exists(inIcd):
        logerr("Can't open Excel ICD file: %s" % inIcd )
        usage()
        return -1
    
    # Read Excel Export from DOORS Alert ID's
    sheetNames        = getExcelFileSheetNames(infn)
    fdasAlertIdsExcel = readExcelFile(infn,  (sheetNames[0],))[0]

    # Read Excel Export from DOORS Alert ICD
    sheetNames        = getExcelFileSheetNames(inIcd)
    fdasAlertIcdExcel = readExcelFile(inIcd,  (sheetNames[0],))[0]

    # Read Excel Export from DOORS Selection Set sources
    sheetNames        = getExcelFileSheetNames(inSrc)
    selectionSetExcel = readExcelFile(inSrc, (sheetNames[0],))[0]

    # create Alert ID dict
    newFdasAlertIds = dict()
    for m in fdasAlertIdsExcel:
        key = m["Alert ID"]
        newFdasAlertIds[key] = m
        
    # create Alert ICD dict
    newFdasAlertIcd, usedSelSet = joinOutputSignals(fdasAlertIcdExcel)
    
    # create Identification dict
    identlst = getIdentification(outfn)

    # create Selection Set Source dict
    newSelectionSet = dict()
    for m in selectionSetExcel:
        key = m["Source Name"]
        if usedSelSet.has_key(key):
            newSelectionSet[key] = m

    # Write Excel HF ICD
    saveIt(outfn, 
           identlst, newFdasAlertIds.values(), newFdasAlertIcd, newSelectionSet.values())
 
    return 0


def usage():
    sys.stderr.write('Usage: outputfile selectionSetSourcesFile alertIdFile  icdfile...\n\n')

if __name__ == '__main__':
    if len(sys.argv) < 4:
        usage()
        sys.exit(1)
    else:
        sys.exit(main(sys.argv[1:]))
        
    