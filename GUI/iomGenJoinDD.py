
import sys
from imtExcelRW import readExcelFile, genExcelFile
from bunch import Bunch

paramInputColumns = (
    # header,                         value,                         len
      ("Status",                      "Status",                      10),
      ("RpName",                      "RpName",                      30),
      ("Parameter",                   "Parameter",                   30),
      ("External",                    "External",                    10),
      ("BusType",                     "BusType",                     10),
      ("Pubref",                      "Pubref",                      40),
      ("TxLru",                       "TxLru",                       30),
      ("TxPort",                      "TxPort",                      30),
      ("Message",                     "Message",                     40),
      ("DataSet",                     "DataSet",                     40),
      ("Container",                   "Container",                   40),
      ("DpName",                      "DpName",                      40),
      ("ValidityCriteria",            "ValidityCriteria",            30),
      ("FsbOffset",                   "FsbOffset",                   10),
      ("DSOffset",                    "DSOffset",                    10),
      ("DSSize",                      "DSSize",                      10),
      ("ParameterType",               "ParameterType",               15),
      ("DataType",                    "DataType",                    10),
      ("BitOffsetWithinDS",           "BitOffsetWithinDS",           20),
      ("ParameterSize",               "ParameterSize",               15),
      ("DataSize",                    "DataSize",                    10),
      ("LsbRes",                      "LsbRes",                      10),
      ("Multiplier",                  "Multiplier",                  15),
      ("PublisherFunctionalMinRange", "PublisherFunctionalMinRange", 35),
      ("PublisherFunctionalMaxRange", "PublisherFunctionalMaxRange", 35),
      ("FunctionalMinRange",          "FunctionalMinRange",          25),
      ("FunctionalMaxRange",          "FunctionalMaxRange",          25),
      ("CodedSet",                    "CodedSet",                    35),
      ("ZeroState",                   "ZeroState",                   20),
      ("OneState",                    "OneState",                    20),
      ("Units",                       "Units",                       10),
      ("DefaultVal",                  "DefaultVal",                  10),
      ("AlertID",                     "AlertID",                     10),
      ("SourceName",                  "SourceName",                  15),
      ("SelectionOrder",              "SelectionOrder",              10),
      ("ValidityParamName",           "ValidityParamName",           25),
      ("ValidityParamValue",          "ValidityParamValue",          25),      
      ("Comment",                     "Comment",                     40),
      ("ChangeHistory",               "ChangeHistory",               40),
      ("ICDFix",                      "ICDFix",                      15),
      ("MessageRef",                  "MessageRef",                  40),
)

paramOutputColumns = (
    # header,                         value,                         len
      ("Status",                      "Status",                      10),
      ("DpName",                      "DpName",                      40),
      ("Parameter",                   "Parameter",                   30),
      ("BusType",                     "BusType",                     10),
      ("TxLru",                       "TxLru",                       30),
      ("TxPort",                      "TxPort",                      30),
      ("Message",                     "Message",                     40),
      ("DataSet",                     "DataSet",                     40),
      ("FsbOffset",                   "FsbOffset",                   10),
      ("DSOffset",                    "DSOffset",                    10),
      ("DSSize",                      "DSSize",                      10),
      ("ParameterType",               "ParameterType",               15),
      ("DataType",                    "DataType",                    10),
      ("BitOffsetWithinDS",           "BitOffsetWithinDS",           20),
      ("ParameterSize",               "ParameterSize",               15),
      ("DataSize",                    "DataSize",                    10),
      ("LsbRes",                      "LsbRes",                      10),
      ("Multiplier",                  "Multiplier",                  15),
      ("PublisherFunctionalMinRange", "PublisherFunctionalMinRange", 35),
      ("PublisherFunctionalMaxRange", "PublisherFunctionalMaxRange", 35),
      ("CodedSet",                    "CodedSet",                    35),
      ("ZeroState",                   "ZeroState",                   20),
      ("OneState",                    "OneState",                    20),
      ("Units",                       "Units",                       10),
      ("Consumer",                    "Consumer",                    40),
      ("Comment",                     "Comment",                     40),
      ("ChangeHistory",               "ChangeHistory",               40),
      ("ICDFix",                      "ICDFix",                      15),
      ("UniqueName",                  "UniqueName",                  40),
      ("MessageRef",                  "MessageRef",                  40),
)

afdxMsgInputColumns = (
    # header,                     value,                 width
      ("Status",                  "Status",                 10),
      ("TxLru",                   "TxLru",                  30),
      ("TxPort",                  "TxPort",                 30),
      ("Message",                 "Message",                40),
      ("ProtocolType",            "ProtocolType",           20),
      ("A664MsgMaxLength",        "A664MsgMaxLength",       20),
      ("A653MsgLength",           "A653MsgLength",          20),
      ("PortType",                "PortType",               10),
      ("PortQueueLength",         "PortQueueLength",        18),
      ("TxInterval",              "TxInterval",             10),
      ("TxRefreshPeriod",         "TxRefreshPeriod",        18),
      ("RxSamplePeriod",          "RxSamplePeriod",         18),
      ("A653PortRefreshPeriod",   "A653PortRefreshPeriod",  25),
      ("InvalidConfirmationTime", "InvalidConfirmationTime",25),
      ("ValidConfirmationTime",   "ValidConfirmationTime",  25),
      ("RxComPortID",             "RxComPortID",            15),
      ("A653PortName",            "A653PortName",           20),
      ("Vlid",                    "Vlid",                   10),
      ("SubVl",                   "SubVl",                  10),
      ("BAG",                     "BAG",                    10),
      ("MTU",                     "MTU",                    10),
      ("Networks",                "Networks",               10),
      ("EdeEnabled",              "EdeEnabled",             15),
      ("EdeSourceId",             "EdeSourceId",            15),
      ("DestIP",                  "DestIP",                 15),
      ("DestUDP",                 "DestUDP",                15),
      ("SourceMAC",               "SourceMAC",              15),
      ("SourceIP",                "SourceIP",               15),
      ("SourceUDP",               "SourceUDP",              15),
      ("CrcOffset",               "CrcOffset",              10),
      ("CrcFsbOffset",            "CrcFsbOffset",           10),
      ("FcOffset",                "FcOffset",               10),
      ("FcFsbOffset",             "FcFsbOffset",            10),
      ("Comment",                 "Comment",                50),
      ("ChangeHistory",           "ChangeHistory",          15),
      ("ICDFix",                  "ICDFix",                 10),
      ("UniqueKey",               "UniqueKey",              50),
)

afdxMsgOutputColumns = (
    # header,                   value,               width
      ("Status",                "Status",               10),
      ("TxLru",                 "TxLru",                30),
      ("TxPort",                "TxPort",               30),
      ("Message",               "Message",              40),
      ("ProtocolType",          "ProtocolType",         20),
      ("A664MsgMaxLength",      "A664MsgMaxLength",     20),
      ("A653MsgLength",         "A653MsgLength",        20),
      ("PortType",              "PortType",             10),
      ("PortQueueLength",       "PortQueueLength",      18),
      ("TxInterval",            "TxInterval",           10),
      ("TxRefreshPeriod",       "TxRefreshPeriod",      18),
      ("TxComPortID",           "TxComPortID",          15),
      ("A653PortName",          "A653PortName",         20),
      ("Vlid",                  "Vlid",                 10),
      ("SubVl",                 "SubVl",                10),
      ("BAG",                   "BAG",                  10),
      ("MTU",                   "MTU",                  10),
      ("Networks",              "Networks",             10),
      ("EdeEnabled",            "EdeEnabled",           15),
      ("EdeSourceId",           "EdeSourceId",          15),
      ("DestIP",                "DestIP",               15),
      ("DestUDP",               "DestUDP",              15),
      ("SourceMAC",             "SourceMAC",            15),
      ("SourceIP",              "SourceIP",             15),
      ("SourceUDP",             "SourceUDP",            15),
      ("CrcOffset",             "CrcOffset",            10),
      ("CrcFsbOffset",          "CrcFsbOffset",         10),
      ("FcOffset",              "FcOffset",             10),
      ("FcFsbOffset",           "FcFsbOffset",          10),
      ("Comment",               "Comment",              50),
      ("ChangeHistory",         "ChangeHistory",        15),
      ("ICDFix",                "ICDFix",               10),
      ("UniqueKey",             "UniqueKey",            50),
)

canMsgInColumns = (
    # header,                     value,                    width
      ("Status",                  "Status",                 10),
      ("TxLru",                   "TxLru",                  30),
      ("TxPort",                  "TxPort",                 30),
      ("Message",                 "Message",                40),
      ("A825MsgLength",           "A825MsgLength",          20),
      ("TxInterval",              "TxInterval",             10),
      ("TxRefreshPeriod",         "TxRefreshPeriod",        18),
      ("RxSamplePeriod",          "RxSamplePeriod",         18),
      ("InvalidConfirmationTime", "InvalidConfirmationTime",25),
      ("ValidConfirmationTime",   "ValidConfirmationTime",  25),
      ("CanMsgID",                "CanMsgID",               10),
      ("PhysPort",                "PhysPort",               20),
      ("Comment",                 "Comment",                50),
      ("ChangeHistory",           "ChangeHistory",          15),
      ("ICDFix",                  "ICDFix",                 10),
      ("UniqueKey",               "UniqueKey",              50),
)

canMsgOutColumns = (
    # header,                     value,                    width
      ("Status",                  "Status",                 10),
      ("TxLru",                   "TxLru",                  30),
      ("TxPort",                  "TxPort",                 30),
      ("Message",                 "Message",                40),
      ("A825MsgLength",           "A825MsgLength",          20),
      ("TxInterval",              "TxInterval",             10),
      ("TxRefreshPeriod",         "TxRefreshPeriod",        18),
      ("CanMsgID",                "CanMsgID",               10),
      ("PhysPort",                "PhysPort",               20),
      ("Comment",                 "Comment",                50),
      ("ChangeHistory",           "ChangeHistory",          15),
      ("ICDFix",                  "ICDFix",                 10),
      ("UniqueKey",               "UniqueKey",              50),
)

a429LabelsInColumns = (
    # header,                     value,                    width
      ("Status",                  "Status",                 10),
      ("TxLru",                   "TxLru",                  30),
      ("TxPort",                  "TxPort",                 30),
      ("Message",                 "Message",                40),
      ("TxInterval",              "TxInterval",             10),
      ("TxRefreshPeriod",         "TxRefreshPeriod",        18),
      ("RxSamplePeriod",          "RxSamplePeriod",         18),
      ("InvalidConfirmationTime", "InvalidConfirmationTime",25),
      ("ValidConfirmationTime",   "ValidConfirmationTime",  25),
      ("LabelID",                 "LabelID",                10),
      ("SDI",                     "SDI",                    10),
      ("PhysPort",                "PhysPort",               20),
      ("Comment",                 "Comment",                50),
      ("ChangeHistory",           "ChangeHistory",          15),
      ("ICDFix",                  "ICDFix",                 10),
      ("UniqueKey",               "UniqueKey",              50),
)

a429LabelsOutColumns = (
    # header,                     value,                    width
      ("Status",                  "Status",                 10),
      ("TxLru",                   "TxLru",                  30),
      ("TxPort",                  "TxPort",                 30),
      ("Message",                 "Message",                40),
      ("TxInterval",              "TxInterval",             10),
      ("TxRefreshPeriod",         "TxRefreshPeriod",        18),
      ("LabelID",                 "LabelID",                10),
      ("SDI",                     "SDI",                    10),
      ("PhysPort",                "PhysPort",               20),
      ("Comment",                 "Comment",                50),
      ("ChangeHistory",           "ChangeHistory",          15),
      ("ICDFix",                  "ICDFix",                 10),
      ("UniqueKey",               "UniqueKey",              50),
)

sourcesColumns = (
    # header,               value,           width
    ("Status",            "Status",             10),
    ("Consumer",          "Consumer",           10),
    ("DestLRUs",          "Destination LRUs",   20),
    ("SourceName",        "Source Name",        15),
    ("SelectionSet",      "Selection Set",      20),
    ("SelectionCriteria", "Selection Criteria", 25),
    ("SelectionOrder",    "Selection Order",    20),
    ("LICParameter",      "LIC Parameter",      20),
    ("LICValue",          "LIC Value",          15),
    ("LockInterval",      "Lock Interval",      15),
    ("Comments",          "Comments",           10),
    ("ChangeHistory",     "Change History",     15),
    ("UniqueKey",         "UniqueKey",          15),
    ("Granularity",       "Granularity",        15),
    ("OrigSourceName",    "Orig Source Name",   20),
)

errcount = 0

def logerr(msg):
    global errcount

    sys.stderr.write(msg + "\n")
    sys.stderr.flush()
    errcount+=1

def normalize_datatype(s):
    s = s.lower()
    if s.startswith('int'):
        return 'INT'
    elif s.startswith('count'):
        return 'COUNT'
    elif s == "bitfield":
        return 'INT'
    elif s in ('float', 'real'):
        return "FLOAT"
    elif s.startswith('bool'):
        return "BOOL"
    elif s == 'string':
        return "STRING"
    elif s.startswith('opaq'):
        return "BYTES"
    elif s == 'cod':
        return "INT"
    elif s == 'bnr':
        return "BNR"    
    elif s == 'ubnr':
        return "UBNR"
    elif s == 'uint':
        return "UINT"
    elif s == 'dis':
        return "BOOL"
    elif s == "bytes":
        return "BYTES"
    else:
        logerr("Unknown data type name: %s" % s)
        return ""


def saveIt(outputfn, 
    afdxInputMsgs , canInputMsgs , inputA429Labels , inputSignals,
    afdxOutputMsgs, canOutputMsgs, outputA429Labels, outputSignals,
    sources
):

    genExcelFile(outputfn, 
        (
            ("InputAfdxMessages", afdxMsgInputColumns, 
                sorted(afdxInputMsgs, key=lambda msg: (msg.TxLru, msg.Message)
                )
            ),
            ("InputCanMessages", canMsgInColumns, 
                sorted(canInputMsgs, key=lambda msg: (msg.TxLru, msg.Message)
                )
            ),
            ("InputA429Labels", a429LabelsInColumns, 
                sorted(inputA429Labels, key=lambda msg: (msg.TxLru, msg.Message)
                )
            ),
            ("InputSignals",  paramInputColumns, 
                sorted(inputSignals, 
                       key=lambda sig: (sig.DataSet, sig.DpName, sig.SelectionOrder, sig.Message)
                )
            ),
            ("OutputAfdxMessages", afdxMsgOutputColumns, 
                sorted(afdxOutputMsgs, key=lambda msg: (msg.TxLru, msg.Message)
                )
            ),
            ("OutputCanMessages", canMsgOutColumns, 
                sorted(canOutputMsgs, key=lambda msg: (msg.TxLru, msg.Message)
                )
            ),
            ("OutputA429Labels", a429LabelsOutColumns, 
                sorted(outputA429Labels, key=lambda msg: (msg.TxLru, msg.Message)
                )
            ),
            ("OutputSignals",  paramOutputColumns, 
                sorted(outputSignals, 
                       key=lambda sig: (sig.Message, sig.DataSet, sig.DpName)
                )
            ),
            ("Sources",  sourcesColumns, 
                sorted(sources, 
                       key=lambda src: (src["Selection Set"], src["Selection Order"])
                )
            ),            
        )
    )


def parseSpecialFunction(paramrec):
    sf  = paramrec.get("SpecialFunction")
    if sf is None or sf.strip().lower() in ("n/a", "none", ""):
        return (None, None)

    sf = sf.strip()             # strip trailing and leading blanks
    sf = sf.replace("(",",")    # Replace opening brackets with comma
    sf = sf.replace(")","")     # Remove closing bracket
    lst = sf.split(",")         # split by comma into list
    sfCode    = lst[0].lower()  # make lower case
    try:
        sfArgs    = lst[1:]
    except:
        sfArgs    = []
    
    return sfCode, sfArgs


def joinOutputSignals(sigdict, totalparams):
    reclst = []
    bcdDict = {}
    
    for paramrec in totalparams:
        if paramrec.get('Status') and paramrec.Status == "Ignore" \
           or paramrec.has_key('Parameter') == False \
           or not paramrec.Parameter:
            continue


        rec = Bunch(
            Parameter           = paramrec.Parameter,
            DataType            = normalize_datatype(paramrec.DataType),
            DataSize            = paramrec.DataSize,
            DpName              = paramrec.DpName,
            DataSet             = "",
            Message             = "",
        )

        key = paramrec.DpName
        sigrec = sigdict.get(key)
        reclst.append(rec)

        if sigrec is None:
            rec.Status = "Ignore"
            logerr("Missing DP %s: Parameter %s will be ignored" % (key, rec.Parameter))
            continue

        # no special functions for output mapping supported (yet)
        sfCode, sfArgs = parseSpecialFunction(paramrec)
        if sfCode is None:
            pass
        else:
            logerr("Unknown special function: %s args %s" % (sfCode, str(sfArgs)))

        # join the BCD records
        if sigrec.ParameterType == "BCD":
            # lookup parameter in a dictionary by param name 
            # If not found, we are the first BCD digit for a parameter, 
            #    then create the record  and process is as normal
            # If found, we are the second digit (DP) for the same BCD value, so extend the parameter size, lsb 
            key = (sigrec.TxLru, sigrec.TxPort, sigrec.Message, sigrec.DataSet, paramrec.Parameter)
            prevrec = bcdDict.get(key)
            if prevrec is not None:
                # just adjust size and bit offset of the first record of the BCD sequence
                # since BCDs never cross 32bit boundaries, the smallest value of 
                # bit position is the bit position of the combined signal
                prevrec.ParameterSize    += sigrec.ParameterSize
                if sigrec.BitOffsetWithinDS < prevrec.BitOffsetWithinDS:
                    prevrec.BitOffsetWithinDS = sigrec.BitOffsetWithinDS
                    prevrec.Multiplier        = sigrec.Multiplier
                # set current record to ignore, the IOM will only process one signal containing the whole BCD value
                rec.Status = "Ignore"
            else:
                # first of a set of BCD digit RPs, put into dictionary and process normally
                bcdDict[key]  = rec
                rec.Status    = sigrec.Status
        else:
            rec.Status    = sigrec.Status
            

        rec.BusType                     = sigrec.BusType            
        rec.TxLru                       = sigrec.TxLru
        rec.TxPort                      = sigrec.TxPort
        rec.DataSet                     = sigrec.DataSet
        rec.Message                     = sigrec.Message
        rec.FsbOffset                   = sigrec.FsbOffset
        rec.DSOffset                    = sigrec.DSOffset
        rec.DSSize                      = sigrec.DSSize
        rec.ParameterType               = sigrec.ParameterType
        rec.BitOffsetWithinDS           = sigrec.BitOffsetWithinDS
        rec.ParameterSize               = sigrec.ParameterSize
        rec.LsbRes                      = sigrec.LsbRes
        rec.PublisherFunctionalMinRange = sigrec.PublisherFunctionalMinRange
        rec.PublisherFunctionalMaxRange = sigrec.PublisherFunctionalMaxRange
        rec.CodedSet                    = sigrec.CodedSet
        rec.ZeroState                   = sigrec.ZeroState
        rec.OneState                    = sigrec.OneState
        rec.Units                       = sigrec.Units
        rec.Multiplier                  = sigrec.Multiplier
        rec.Comment                     = sigrec.Comment
        rec.MessageRef                  = sigrec.MessageRef
        rec.UniqueName                  = sigrec.UniqueName

    return reclst


def expandSource(source,parameter,signal,expandedSources):
    groupId        = None
    expandedSource = None
    if source.Granularity == "Container":
        if signal.Container:
            groupId = ".".join([signal.Message, signal.DataSet, signal.Container])
        else:
            if signal.DataSet and signal.DataSet != "N/A":
                groupId = ".".join([signal.Message, signal.DataSet])
            else:
                groupId = ".".join([signal.Message])
            
    elif source.Granularity == "Parameter":
        groupId = parameter
    elif source.Granularity == "DataSet":
        groupId = ".".join([signal.Message, signal.DataSet])
        
    elif source.Granularity == "Message":
        groupId = signal.Message
        
    elif source.Granularity == "Custom" or source.Granularity == "Channel":
        #no expansion for custom sources
        pass        
    else:
        #basic consistency check
        logerr("Invalid Granularity value: %s" % source.Granularity)
    sourceName   = source["Source Name"]
    if groupId:
        sourceName   = ".".join([sourceName,groupId])
    
    if expandedSources.has_key(sourceName) is False:
        expandedSource = source.copy()
        expandedSource["Source Name"]        = sourceName
        expandedSource["Orig Source Name"]   = source["Source Name"]
        expandedSources[sourceName]          = expandedSource
        
    return expandedSources[sourceName]

def adjustValidityCriteria(currParam):
    if currParam.PublisherFunctionalMinRange not in ["TBD","N/A","",None] and \
        currParam.PublisherFunctionalMaxRange not in ["TBD","N/A","",None]:
       
        if currParam.ParameterType == "FLOAT":
            currParam.ValidityCriteria += ",RANGE_FLOAT"
        elif currParam.ParameterType == "COD" or currParam.ParameterType == "INT":
            if currParam.PublisherFunctionalMinRange >= 0:
                currParam.ValidityCriteria += ",RANGE_UINT"
            else:
                currParam.ValidityCriteria += ",RANGE_INT"
        else:
            if currParam.LsbRes == 1:
                if currParam.PublisherFunctionalMinRange >= 0:
                    currParam.ValidityCriteria += ",RANGE_UINT"
                else:
                    currParam.ValidityCriteria += ",RANGE_INT"
            elif type(currParam.LsbRes) == type(1.0):
                # paranoia check
                if "BNR" in currParam.ParameterType.upper():
                    currParam.ValidityCriteria += ",RANGE_FLOATBNR"
                else:
                    currParam.ValidityCriteria += ",RANGE_FLOAT"
            else:
                pass
            
    if currParam.ValidityParamName != "N/A":
        currParam.ValidityCriteria += ",PARAM"
    
    return currParam.ValidityCriteria

def joinInputSignals(sigdict, totalparams, sourceDict):
    reclst      = []
    expandedSrc = {}
    bcdDict     = {}
    
    for paramrec in totalparams:
        if (paramrec.get('Status') and paramrec.Status == "Ignore") \
           or paramrec.has_key('Parameter') == False \
           or not paramrec.Parameter : 
            continue
        
        #decode SpecialFunction column
        sfAlertID                 = "N/A"
        sfMessageName             = "N/A"
        sfValidityParamName       = "N/A"
        sfValidityParamValue      = "N/A"
        sfOutputValidityParamName = "N/A"

        sfCode, sfArgs = parseSpecialFunction(paramrec)
        if sfCode is None:
            pass
        elif sfCode == "count":
            #Special Function count
            pass
        elif sfCode == "alertid":
            #Special Function AlertID(value)
            sfAlertID = sfArgs[0]
        elif sfCode == "validityparameter":
            #Special Function ValidityParameter(name, value)
            sfValidityParamName  = sfArgs[0]
            sfValidityParamValue = int(sfArgs[1])
        elif sfCode == "outputvalidityparameter":
            #Special Function OutputValidityParameter(name)
            sfOutputValidityParamName  = sfArgs[0]
        elif sfCode == "messageunfresh":
            #Special Function MessageUnfresh(UniqueMessageName)
            sfMessageName  = sfArgs[0]
        else:
            logerr("Unknown special function:%s %s" % (sfCode, str(sfArgs)))
                

        rec = Bunch(
            Parameter                   = paramrec.Parameter,
            External                    = paramrec.External,
            DataType                    = normalize_datatype(paramrec.DataType),
            DataSize                    = paramrec.DataSize,
            DefaultVal                  = paramrec.DataDefaultVal,
            RpName                      = paramrec.RpName,
            AlertID                     = sfAlertID,
            FunctionalMinRange          = paramrec.DataMinVal,
            FunctionalMaxRange          = paramrec.DataMaxVal,
            SourceName                  = "None",
            SelectionOrder              = "N/A",
            ValidityParamName           = sfValidityParamName,
            ValidityParamValue          = sfValidityParamValue,
            OutputValidityParamName     = sfOutputValidityParamName,
            Message                     = "",
            DataSet                     = "",
            DpName                      = "",
        )
        reclst.append(rec)
        
        if sfCode == "messageunfresh":
            rec.Status                  = "Initial"
            rec.MessageRef              = sfMessageName
            rec.ParameterType           = "UNFRESH"
            # some more defaults to avoid error messages in next stage
            rec.BusType                 = "N/A"
            rec.Pubref                  = "N/A"
            rec.DataSet                 = "N/A"
            rec.DpName                  = "N/A"
            rec.PubRef                  = "N/A"
            rec.ValidityCriteria        = "FRESH"
            rec.DSOffset                = "0"
            rec.DSSize                  = "0"
            rec.DSSize                  = "0"
            rec.BitOffsetWithinDS       = "0"
            rec.ParameterSize           = "1"
            continue
        
        sigrec = sigdict.get(paramrec.RpName)
        if not sigrec:
            rec.Status = "Ignore"
            logerr("Missing RP %s: Parameter %s will be ignored" % (paramrec.RpName, rec.Parameter))
            continue
        
        if sigrec.Status.startswith("Ignore"):
            logerr("signal related to RP %s is ignored. Mapping to %s won't be done" % (paramrec.RpName, rec.Parameter))
            rec.Status = "Ignore"
            continue
            
        # do the rest of the join work

        # join bcd digits
        if sigrec.ParameterType == "BCD":
            # lookup parameter in a dictionary by param name and source name. 
            # If not found, we are the first bcddigit for a parameter and source
            # then add then create the record and process is as normal
            # If found we have a second digit for the same RP item, so extend the parameter size, lsb and/or msb
            key = (paramrec.Parameter, paramrec.SourceName)
            prevrec = bcdDict.get(key)
            if prevrec is not None:
                # just adjust size and bit offset of the first record of the BCD sequence
                # since BCDs never cross 32bit boundaries, the smallest value of 
                # bit position is the bit position of the combined signal
                prevrec.ParameterSize    += sigrec.ParameterSize
                if sigrec.BitOffsetWithinDS < prevrec.BitOffsetWithinDS:
                    prevrec.BitOffsetWithinDS = sigrec.BitOffsetWithinDS
                    prevrec.Multiplier        = sigrec.Multiplier
                # set current record to ignore, the IOM will only process one signal containing the whole BCD value
                rec.Status   = "Ignore"
            else:
                # first of a set of BCD digit RPs, put into dictionary and process normally
                bcdDict[key] = rec
                rec.Status   = sigrec.Status
        else:
            rec.Status    = sigrec.Status
                    
        rec.BusType                     = sigrec.BusType
        rec.Pubref                      = sigrec.Pubref
        rec.TxLru                       = sigrec.TxLru
        rec.TxPort                      = sigrec.TxPort
        rec.Message                     = sigrec.Message
        rec.DataSet                     = sigrec.DataSet
        rec.Container                   = sigrec.Container
        rec.DpName                      = sigrec.DpName
        rec.ValidityCriteria            = sigrec.ValidityCriteria
        rec.FsbOffset                   = sigrec.FsbOffset
        rec.DSOffset                    = sigrec.DSOffset
        rec.DSSize                      = sigrec.DSSize

        if sfCode == "count":
            rec.ParameterType               = "COUNT"
        else:
            rec.ParameterType               = sigrec.ParameterType

        rec.BitOffsetWithinDS           = sigrec.BitOffsetWithinDS
        rec.ParameterSize               = sigrec.ParameterSize
        rec.LsbRes                      = sigrec.LsbRes
        rec.Multiplier                  = sigrec.Multiplier
        rec.PublisherFunctionalMinRange = sigrec.PublisherFunctionalMinRange
        rec.PublisherFunctionalMaxRange = sigrec.PublisherFunctionalMaxRange
        rec.CodedSet                    = sigrec.CodedSet
        rec.ZeroState                   = sigrec.ZeroState
        rec.OneState                    = sigrec.OneState
        rec.Units                       = sigrec.Units
        rec.Comment                     = sigrec.Comment
        rec.MessageRef                  = sigrec.MessageRef
        rec.ValidityCriteria            = adjustValidityCriteria(rec)
                    
        if paramrec.SourceName != 'None':
            if paramrec.SourceName in sourceDict:
                currSource         = expandSource(sourceDict[paramrec.SourceName],rec.Parameter,sigrec,expandedSrc)
                rec.SourceName     = currSource["Source Name"]
                rec.SelectionOrder = currSource["Selection Order"]
            else:
                logerr("Can't find source definition for source: %s" % paramrec.SourceName)
                rec.SelectionOrder = 0

        

    return reclst, expandedSrc.values()

def joinOutputMessages(messages, signals):
    '''
    Select the subset of messages referred to by signals
    '''
    # put messages into dictionary indexed by Lru/MsgName
    inpMsgdict = dict()
    for m in messages:
        key = m.UniqueKey
        inpMsgdict[key] = m

    # traverse signals and put referenced message in output dict
    outMsgdict = dict()
    for s in signals:
        if s.Status == "Ignore":
            continue
        key = s.MessageRef
        if key in inpMsgdict and not key in outMsgdict:
            outMsgdict[key] = inpMsgdict[key]

    return outMsgdict.values()

def joinInputMessages(messages, signals):
    '''
    Select the subset of messages referred to by signals
    '''
    # put messages into dictionary indexed by Lru/MsgName
    inpMsgdict = dict()
    for m in messages:
        key = m.UniqueKey
        inpMsgdict[key] = m
    
    # traverse signals and put referenced message in output dict
    outMsgdict = dict()
    for s in signals:
        if s.Status == "Ignore":
            continue
        key = s.MessageRef
        if key in inpMsgdict and not key in outMsgdict:
            outMsgdict[key] = inpMsgdict[key]

    return outMsgdict.values()

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
    
def convertAlertParams(alertParams, currLRU):
    for alertParam in alertParams:
        if not currLRU in alertParam["Destination LRUs"]:
            del alertParam
        else:
            alertParam.Parameter      = alertParam["Logic Statements Parameter Alias"].strip()
            alertParam.SysParameter   = alertParam.Parameter
            alertParam.DataType       = alertParam["Data Type"]
            alertParam.DataSize       = alertParam["Data Size"]
            alertParam.DataDefaultVal = alertParam["Default value"]
            alertParam.RpName         = alertParam["Req RPName"].strip()
            alertParam.DataMinVal     = "N/A"
            alertParam.DataMaxVal     = "N/A"
            #alertParam.DataMinVal,alertParam.DataMaxVal = getMinMax(alertParam.DataType)
 
import glob        
import os        
import getopt        

def main(arglist):
    # read ICD Excel
    opts, args = getopt.getopt(arglist, 'hl:', ['lru=', 'help'])
    currLRU = None

    for o, a in opts:
        if o in ['-h', '--help']:
            usage()
            return -1
        elif o in ['l', '--lru']:
            currLRU = a
        else: 
            usage()
            return -1

    outfn = args[0]
    infn  = args[1]
    mapfiles = []
    for f in args[2:]:
        mapfiles += glob.glob(f)

    # check parameters
    if len(mapfiles) == 0:
        if len(args[2:]) > 0:
            logerr("Can't open map files: %s" % str(args[2:]))
        usage()
        return -1

    if not os.path.exists(infn):
        logerr("Can't open Excel ICD file: %s" % infn )
        usage()
        return -1
    
    for mf in mapfiles:
        if not os.path.exists(mf):
            logerr("Can't open map file: %s" % mf)
            usage()
            return -1
    
    # Read Excel HF ICD
    afdxInputMsgs,  canInputMsgs, inputA429Labels, inputSignals, \
    afdxOutputMsgs, canOutputMsgs, outputA429Labels, outputSignals =  \
        readExcelFile(infn, ('InputAfdxMessages' , 'InputCanMessages' , 'InputA429Labels' ,'InputSignals', 
                             'OutputAfdxMessages', 'OutputCanMessages', 'OutputA429Labels', 'OutputSignals'))

    inputParams  = []
    outputParams = []
    sourcesData  = []

    # Read DD-RP Mapping Sheets 
    for f in mapfiles:
        inMap = None
        sheets = readExcelFile(f, ('ICD Input Parameters',))
        if sheets is None:
            sheets = readExcelFile(f, ('ICD Parameters',))
        if sheets is None:
            sheets = readExcelFile(f, ('ICD_Parameters',))
            
        if sheets is not None:
            inMap = sheets[0]
            if inMap[0].has_key("Logic Statements Parameter Alias"):
                #we deal with an alert file. Convert the parameters
                convertAlertParams(inMap, currLRU)
            inputParams.extend(inMap)
        
        sheets = readExcelFile(f, ('Sources',))
        if sheets is not None:
            srcData = sheets[0]
            sourcesData.extend(srcData)
            
        outMap = None
        sheets = readExcelFile(f, ('ICD Output Parameters',))
        if sheets is not None:
            outMap = sheets[0]
            outputParams.extend(outMap)
        
        if inMap is None and outMap is None:
            logerr("Can't find Parameter Sheets in map file: %s" % f)

    
    if inputParams == [] and outputParams == []:
        logerr("No parameters to join")
        return -1

    # Join input mappings

    # create signal dictionary to speed up join
    sigdict = dict()
    for sig in inputSignals:
        sigdict[sig.RpName] = sig
        
    srcdict = dict()
    for src in sourcesData:
        srcdict[src["Source Name"]] = src        
        
    # now do the join
    newInputSignals,expandedSources = joinInputSignals(sigdict, inputParams, srcdict)
    newAfdxInputMsgs                = joinInputMessages(afdxInputMsgs, newInputSignals)
    newCanInputMsgs                 = joinInputMessages(canInputMsgs, newInputSignals)
    newInputA429Labels              = joinInputMessages(inputA429Labels, newInputSignals)
    
    # Join output mappings

    # create signal dictionary to speed up join
    sigdict = dict()
    for sig in outputSignals:
        sigdict[sig.UniqueName] = sig
        
    # now do the join
    newOutputSignals    = joinOutputSignals(sigdict, outputParams)
    newAfdxOutputMsgs   = joinOutputMessages(afdxOutputMsgs, newOutputSignals)
    newCanOutputMsgs    = joinOutputMessages(canOutputMsgs, newOutputSignals)
    newOutputA429Labels = joinOutputMessages(inputA429Labels, newOutputSignals)
    
    saveIt(outfn, 
           newAfdxInputMsgs, newCanInputMsgs, newInputA429Labels, newInputSignals, 
           newAfdxOutputMsgs, newCanOutputMsgs, newOutputA429Labels, newOutputSignals,
           expandedSources)

    return 0


def usage():
    sys.stderr.write('Usage: outputfile icdfile mapfiles...\n')

if __name__ == '__main__':
    if len(sys.argv) < 4:
        usage()
        sys.exit(1)
    else:
        sys.exit(main(sys.argv[1:]))
        
    