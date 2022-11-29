
import os        
import sys
from imtExcelRW import *
from iomGenBinConst import IOM
from iomGenBinConst import IOM

sheetInputAfdxMessages = (
    # header,                            value,                                width
    ("Status",                           "Status",                             10),
    ("TxLru",                            "TxLru",                              30),
    ("Message",                          "Message",                            30),
    ("ProtocolType",                     "ProtocolType",                       20),
    ("A664MsgMaxLength",                 "A664MsgMaxLength",                   20),
    ("A653MsgLength",                    "A653MsgLength",                      20),
    ("PortType",                         "PortType",                           15),
    ("PortQueueLength",                  "PortQueueLength",                    20),
    ("TxInterval",                       "TxInterval",                         15),
    ("A653PortRefreshPeriod",            "A653PortRefreshPeriod",              20),
    ("MaxAge",                           "MaxAge",                             10),
    ("RxComPortID",                      "RxComPortID",                        15),
    ("A653PortName",                     "A653PortName",                       40),
    ("Vlid",                             "Vlid",                               10),
    ("SubVl",                            "SubVl",                              10),
    ("BAG",                              "BAG",                                10),
    ("MTU",                              "MTU",                                10),
    ("Networks",                         "Networks",                           10),
    ("EdeEnabled",                       "EdeEnabled",                         15),
    ("EdeSourceId",                      "EdeSourceId",                        15),
    ("DestIP",                           "DestIP",                             20),
    ("DestUDP",                          "DestUDP",                            10),
    ("SourceMAC",                        "SourceMAC",                          20),
    ("SourceIP",                         "SourceIP",                           20),
    ("SourceUDP",                        "SourceUDP",                          10),
    ("ICDFix",                           "ICDFix",                             40),
    ("Change History",                   "Change History",                     40),
    ("Comment",                          "Comment",                            40),
    ("UniqueKey",                        "UniqueKey",                          60),
)


sheetInputCanMessages = (
    # header,                            value,                                width
    ("Status",                           "Status",                             10),
    ("TxLru",                            "TxLru",                              20),
    ("Message",                          "Message",                            40),
    ("A825MsgLength",                    "A825MsgLength",                      15),
    ("TxInterval",                       "TxInterval",                         15),
    ("MaxAge",                           "MaxAge",                             15),
    ("CanMsgID",                         "CanMsgID",                           20),
    ("PhysPort",                         "PhysPort",                           40),
    ("UniqueKey",                        "UniqueKey",                          40),
    ("Change History",                   "Change History",                     40),
    ("ICDFix",                           "ICDFix",                             40),
    ("Comment",                          "Comment",                            40),
)


sheetInputA429Messages = (
    # header,                            value,                                width
    ("Status",                           "Status",                             10),
    ("TxLru",                            "TxLru",                              20),
    ("Message",                          "Message",                            40),
    ("TxInterval",                       "TxInterval",                         15),
    ("MaxAge",                           "MaxAge",                             15),
    ("LabelID",                          "LabelID",                            20),
    ("PhysPort",                         "PhysPort",                           40),
    ("UniqueKey",                        "UniqueKey",                          40),
    ("Change History",                   "Change History",                     40),
    ("ICDFix",                           "ICDFix",                             40),
    ("Comment",                          "Comment",                            40),
)


sheetInputSignals = (
    # header,                            value,                                width
    ("Status",                           "Status",                             10),
    ("RpName",                           "RpName",                             40),
    ("Pubref",                           "Pubref",                             40),
    ("TxLru",                            "TxLru",                              30),
    ("Message",                          "Message",                            40),
    ("DataSet",                          "DataSet",                            40),
    ("DPName",                           "DPName",                             40),
    ("ValidityCriteria",                 "ValidityCriteria",                   20),
    ("FsbOffset",                        "FsbOffset",                          10),
    ("DSOffset",                         "DSOffset",                           10),
    ("DSSize",                           "DSSize",                             10),
    ("BitOffsetWithinDS",                "BitOffsetWithinDS",                  20),
    ("ParameterType",                    "ParameterType",                      15),
    ("ParameterSize",                    "ParameterSize",                      15),
    ("LsbRes",                           "LsbRes",                             10),
    ("PublisherFunctionalMinRange",      "PublisherFunctionalMinRange",        30),
    ("PublisherFunctionalMaxRange",      "PublisherFunctionalMaxRange",        30),
    ("Multiplier",                       "Multiplier",                         40),
    ("MessageRef",                       "MessageRef",                         40),
    ("Change History",                   "Change History",                     40),
    ("ICDFix",                           "ICDFix",                             40),
    ("Comment",                          "Comment",                            40),
)


sheetOutputAfdxMessages = (
    # header,                            value,                                width
    ("Status",                           "Status",                             10),
    ("TxLru",                            "TxLru",                              10),
    ("Message",                          "Message",                            40),
    ("ProtocolType",                     "ProtocolType",                       20),
    ("A664MsgMaxLength",                 "A664MsgMaxLength",                   20),
    ("A653MsgLength",                    "A653MsgLength",                      20),
    ("PortType",                         "PortType",                           20),
    ("PortQueueLength",                  "PortQueueLength",                    20),
    ("TxInterval",                       "TxInterval",                         15),
    ("TxComPortID",                      "TxComPortID",                        15),
    ("A653PortName",                     "A653PortName",                       40),
    ("Vlid",                             "Vlid",                               10),
    ("SubVl",                            "SubVl",                              10),
    ("BAG",                              "BAG",                                10),
    ("MTU",                              "MTU",                                10),
    ("Networks",                         "Networks",                           40),
    ("EdeEnabled",                       "EdeEnabled",                         10),
    ("EdeSourceId",                      "EdeSourceId",                        10),
    ("DestIP",                           "DestIP",                             20),
    ("DestUDP",                          "DestUDP",                            10),
    ("SourceMAC",                        "SourceMAC",                          20),
    ("SourceIP",                         "SourceIP",                           20),
    ("SourceUDP",                        "SourceUDP",                          10),
    ("Change History",                   "Change History",                     40),
    ("ICDFix",                           "ICDFix",                             40),
    ("UniqueKey",                        "UniqueKey",                          40),
)                                                                            
                                                                             
                                                                             
sheetOutputCanMessages = (                                                   
    # header,                            value,                                width
    ("Status",                           "Status",                             10),
    ("TxLru",                            "TxLru",                              20),
    ("Message",                          "Message",                            40),
    ("A825MsgLength",                    "A825MsgLength",                      15),
    ("TxInterval",                       "TxInterval",                         15),
    ("CanMsgID",                         "CanMsgID",                           20),
    ("PhysPort",                         "PhysPort",                           40),
    ("Change History",                   "Change History",                     40),
    ("ICDFix",                           "ICDFix",                             40),
    ("Comment",                          "Comment",                            40),
    ("UniqueKey",                        "UniqueKey",                          40),
)                                                                            
                                                                             
                                                                             
sheetOutputA429Messages = (                                                   
    # header,                            value,                                width
    ("Status",                           "Status",                             10),
    ("TxLru",                            "TxLru",                              20),
    ("Message",                          "Message",                            40),
    ("TxInterval",                       "TxInterval",                         15),
    ("LabelID",                          "LabelID",                            20),
    ("PhysPort",                         "PhysPort",                           40),
    ("Change History",                   "Change History",                     40),
    ("ICDFix",                           "ICDFix",                             40),
    ("Comment",                          "Comment",                            40),
    ("UniqueKey",                        "UniqueKey",                          40),
)                                                                            
                                                                             
                                                                             
sheetOutputSignals = (                                                       
    # header,                            value,                                width
    ("Status",                           "Status",                             10),
    ("TxLru",                            "TxLru",                              20),
    ("Message",                          "Message",                            40),
    ("DataSet",                          "DataSet",                            40),
    ("DPName",                           "DPName",                             40),
    ("FsbOffset",                        "FsbOffset",                          10),
    ("DSOffset",                         "DSOffset",                           10),
    ("DSSize",                           "DSSize",                             10),
    ("BitOffsetWithinDS",                "BitOffsetWithinDS",                  10),
    ("ParameterType",                    "ParameterType",                      20),
    ("ParameterSize",                    "ParameterSize",                      20),
    ("LsbRes",                           "LsbRes",                             10),
    ("MessageRef",                       "MessageRef",                         40),
    ("ICDFix",                           "ICDFix",                             40),
    ("Change History",                   "Change History",                     40),
    ("Comment",                          "Comment",                            40),
    ("UniqueName",                       "UniqueName",                         60),
)





errcount = 0


def logerr(msg):
    global errcount

    sys.stderr.write("\nERROR****: " + msg + "\n")
    sys.stderr.flush()
    errcount+=1


def saveIt(outputfn, icdInAfdxMessages, icdInCanMessages, icdInA429Messages, icdInSignals,
           icdOutAfdxMessages, icdOutCanMessages, icdOutA429Messages, icdOutSignals):

    
    genExcelFile(outputfn, 
        (
            ("InputAfdxMessages",   sheetInputAfdxMessages,  icdInAfdxMessages),
            ("InputCanMessages",    sheetInputCanMessages,   icdInCanMessages ),
            ("InputA429Labels",     sheetInputA429Messages,  icdInA429Messages ),
            ("InputSignals",        sheetInputSignals,       icdInSignals),
            ("OutputAfdxMessages",  sheetOutputAfdxMessages, icdOutAfdxMessages ),
            ("OutputCanMessages",   sheetOutputCanMessages,  icdOutCanMessages),
            ("OutputA429Labels",    sheetOutputA429Messages, icdOutA429Messages),
            ("OutputSignals",       sheetOutputSignals,      icdOutSignals ),

            #("Sources",  sourceColumns, 
            #    sorted(selectionSet, 
            #           key=lambda sig: (sig["Selection Set"], sig["Source Name"], sig["Selection Order"])
            #    )
            #),
        )
    )


  
def convertToDict(filename):
    # create empty dict
    dictData = dict()

    if os.path.exists(filename):
        # Read Excel Export from DOORS AFDX Message In
        sheetNames = getExcelFileSheetNames(filename)
        excelData  = readExcelFile(filename, (sheetNames[0],))[0]

        # fill in dict
        row = 0
        for m in excelData:
            dictData[row] = m
            row = row + 1

    return dictData

def main(args):
    # read Excel files exported from DOOORS
    argOutfn      = args[0]
    argInAfdxMsg  = args[1]
    argInCanMsg   = args[2]
    argInA429Msg  = args[3]
    argInParam    = args[4]
    argOutAfdxMsg = args[5]
    argOutCanMsg  = args[6]
    argOutA429Msg = args[7]
    argOutParam   = args[8]

    # check parameters
    try:
        FILE = open(argOutfn,"w")
        FILE.writelines("Hello")
        FILE.close()
    except:
        logerr("Output File already open: %s" % argOutfn )
        usage()
        return -1

    icdInAfdxMsg  = convertToDict (argInAfdxMsg )
    icdInCanMsg   = convertToDict (argInCanMsg  )
    icdInA429Msg  = convertToDict (argInA429Msg )
    icdInParam    = convertToDict (argInParam   )
    icdOutAfdxMsg = convertToDict (argOutAfdxMsg)
    icdOutCanMsg  = convertToDict (argOutCanMsg )
    icdOutA429Msg = convertToDict (argOutA429Msg)
    icdOutParam   = convertToDict (argOutParam  )

    
    # Write Excel HF ICD
    saveIt(argOutfn, 
           icdInAfdxMsg.values(),  icdInCanMsg.values(),  icdInA429Msg.values(),  icdInParam.values(),
           icdOutAfdxMsg.values(), icdOutCanMsg.values(), icdOutA429Msg.values(), icdOutParam.values())
 
    return 0


def usage():
    sys.stderr.write('Usage: outputfile   afdxMsgIn canMsgIn a429MsgIn paramIn afdxMsgOut canMsgOut a429MsgOut paramOut\n\n')

if __name__ == '__main__':
    if len(sys.argv) < 10:
        print sys.argv
        usage()
        sys.exit(1)
    else:
        sys.exit(main(sys.argv[1:]))
        
    