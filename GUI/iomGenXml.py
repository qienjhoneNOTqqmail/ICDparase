import sys
import getopt
    
from Cheetah.Template import Template
import iomGenCommon
import iomGenReadDD

from iomGenConst import APPLICATION_RATE

import pdb
def excepthook(ex_cls, ex, tb):
    pdb.post_mortem(tb)
#sys.excepthook = excepthook


TEMPLATE_HEADER = '''<IOMConfiguration HF="$model.identification.application" REV="$model.identification.revision" ICD="$model.identification.icd">
'''

TEMPLATE_CANIN = '''
#for $key in $model.can.messageKeys
 #set msg=$model.can.messages[$key]
  #if $msg.msgUsed
    <CanMessage id="$msg.msgid" messageName="$msg.fullname" canId="$msg.msgCanID" validConfirmationTime="$msg.msgValidConfirmationTime" invalidConfirmationTime="$msg.msgInvalidConfirmationTime" length="$msg.msgLength">
        #for p in $model.can.signals[$key]
         <Parameter paramNameValue="$p.paramName" paramSize="$p.paramDatasize" paramType="$p.paramDatatype" paramNameStatus="$(p.paramName).Status" paramOffsetValue="$p.paramOffset" paramOffsetStatus="$p.paramOffsetStatus" paramDefault="$p.paramDefault">
         #if $p.sselValParam() or $p.sselRangeInt()
             <source type="$p.sigType" message="$p.msgRef.msgid" offset="$p.sigByteOffset" lsb="$p.sigBitOffset" bits="$p.sigSize" access="$p.sigAccess" lsbvalue="$p.sigLsbValue">
             #if $p.sselValParam()
                 #set $valpar=$p.sselValParamData()
                 #if $valpar is not None
                 <condition type="VALIDITY_INPUT" paramNameValue="$p.validityParamName" message="$valpar.msgid" offset="$valpar.offset" access="$valpar.access" bits="$valpar.bits" lsb="$valpar.lsb" lsbvalue="$valpar.lsbval" value="$valpar.value"/>
                 #end if
             #end if
             #if $p.sselRangeInt()
                 <condition type="RANGE_INT" min="$p.paramMin" max="$p.paramMax"/>
             #end if
             </source>
         #else
             <source type="$p.sigType" message="$p.msgRef.msgid" offset="$p.sigByteOffset" lsb="$p.sigBitOffset" bits="$p.sigSize" access="$p.sigAccess" lsbvalue="$p.sigLsbValue"/>
         #end if
         </Parameter>
        #end for
    </CanMessage>
  #end if
#end for
'''

# This template deals with AFDX and A429 - needs cleanup
TEMPLATE_AFDXIN = '''
 #for $key in $model.afdx.messageKeys
  #set map=$model.afdx.messages[$key]
  #if $map.msgUsed
    <AfdxMessage id="$map.msgid" messageName="$map.fullname" portType="$map.portType" queueLength="$map.queueLength"
        portId="$map.portId" portName="$map.portName" length="$map.msgRxLength"
        a653PortRefreshPeriod="$map.msgA653RefreshPeriod" validConfirmationTime="$map.msgValidConfirmationTime"
        invalidConfirmationTime="$map.msgInvalidConfirmationTime"
        crcOffset="$map.crcOffset" crcFsbOffset="$map.crcFsbOffset" fcOffset="$map.fcOffset" fcFsbOffset="$map.fcFsbOffset"
        schedOffset="$map.schedOffset" schedRate="$map.schedRate"/>
  #end if
 #end for

 #for port in $model.a429.ports.values()
    <A429Port id="$port.portId" portName="$port.portName" portType="$port.portType" queueLength="$port.queueLength" length="$port.msgSize" physPort="$port.physPort"/>
 #end for
 
 #for $key in $model.a429.messageKeys
  #set map=$model.a429.messages[$key]
  #if $map.msgUsed
    <A429Message id="$map.msgid" messageName="$map.fullname" port="$map.portId" labelNumber="$map.msgLabel" sdi="$map.msgSDI" length="$map.msgLength" validConfirmationTime="$map.msgValidConfirmationTime" invalidConfirmationTime="$map.msgInvalidConfirmationTime"/>
  #end if
 #end for
 #for $ssName in $model.selectionSets.keys()
    #set $ssRec = $model.selectionSets[$ssName]
    #set $selCrit = $ssRec.selectionCriteria
    <SelectionSet selectionSetName="$ssName" criteria="$selCrit" interval="$ssRec.lockInterval">
    #for source in $ssRec.sources
        #if $selCrit == "LIC_PARAMETER"
          #if $model.parameters.has_key($source.LICparam)
            #set $param = $model.parameters[$source.LICparam][0]
            #set $paramType         = $param.paramDatatype
            #set $paramOffsetValue  = $param.paramOffset
            #set $paramOffsetStatus = $param.paramOffsetStatus
          #else
            #set $paramType         = 'Not Found'
            #set $paramOffsetValue  = -1
            #set $paramOffsetStatus = -1
          #end if
        <source name="$source.sourceName" order="$source.selectionOrder" 
                      paramNameValue="$source.LICparam" paramType="$paramType" paramOffsetValue="$paramOffsetValue" 
                      paramOffsetStatus="$paramOffsetStatus" expectedValue="$source.LICvalue"/>
        #else if $selCrit == "OBJECT_VALID"
        <source name="$source.sourceName" order="$source.selectionOrder">
            <sourceLogic>
            #for $condition in $source.conditions
                #set $map = $condition.sigRef
                #if $map.msgRef.msgclass == "AFDX"
                    #set $transport = "A664"
                #else if $map.msgRef.msgclass == "CAN"
                    #set $transport = "A825"
                #else if $map.msgRef.msgclass == "A429"
                    #set $transport = "A429"
                #end if
                #if $condition.condType == "FRESH"
                <condition type="Freshness"     transport="$transport" message="$map.msgRef.msgid"/>
                #end if
                #if $condition.condType == "A664FS"
                <condition type="A664FS"        transport="$transport" message="$map.msgRef.msgid" offset="$map.dsFsbOffset"/>
                #end if
                #if $condition.condType.startswith("A429SSM")
                <condition type="$condition.condType" transport="$transport" message="$map.msgRef.msgid" offset="$map.sigByteOffset"/>
                #end if
            #end for
            </sourceLogic>
        </source>
        #else if $selCrit == "SOURCE_HEALTH_SCORE"
        <source name="$source.sourceName" order="$source.selectionOrder"/>
        #end if
    #end for
    </SelectionSet>   
 #end for

 #for $dsname in $model.parameters.keys()
    #set $sources = $model.parameters[$dsname]
    #if $sources[0].msgRef.msgclass != "CAN"
        <DataSet name="$dsname" selectionSetName="$sources[0].selectionSet">
            <Logic>
            #for $map in $sources
                #if map.msgRef.msgclass == "AFDX"
                    #set $transport = "A664"
                #else if map.msgRef.msgclass == "A429"
                    #set $transport = "A429"
                #else if map.msgRef.msgclass == "CAN"
                    #set $transport = "A825"
                #end if
                #if $transport == "A664" or $transport == "A429"
                <sourceLogic>
                    #if $map.sselFreshness()
                    <condition type="Freshness"      transport="$transport" message="$map.msgRef.msgid"/>
                    #end if
                    #if $map.sselA664Fsb()
                    <condition type="A664FS"         transport="$transport" message="$map.msgRef.msgid" offset="$map.dsFsbOffset"/>
                    #end if
                    #if $map.sselA429SSM_BCD()
                    <condition type="A429SSM_BCD"    transport="$transport" message="$map.msgRef.msgid" offset="$map.sigByteOffset"/>
                    #else if $map.sselA429SSM_BNR()
                    <condition type="A429SSM_BNR"    transport="$transport" message="$map.msgRef.msgid" offset="$map.sigByteOffset"/>
                    #else if $map.sselA429SSM_DIS()
                    <condition type="A429SSM_DIS"    transport="$transport" message="$map.msgRef.msgid" offset="$map.sigByteOffset"/>
                    #end if
                    #if $map.sselRangeInt()
                    <condition type="RANGE_INT"      transport="$transport" message="$map.msgRef.msgid" offset="$map.sigByteOffset" access="$map.sigAccess" lsb="$map.sigBitOffset" bits="$map.sigSize" lsbvalue="$map.sigLsbValue" min="$map.paramMin" max="$map.paramMax"/>
                    #else if $map.sselRangeInt()
                    <condition type="RANGE_UINT"     transport="$transport" message="$map.msgRef.msgid" offset="$map.sigByteOffset" access="$map.sigAccess" lsb="$map.sigBitOffset" bits="$map.sigSize" lsbvalue="$map.sigLsbValue" min="$map.paramMin" max="$map.paramMax"/>
                    #else if $map.sselRangeFloat()
                    <condition type="RANGE_FLOAT"    transport="$transport" message="$map.msgRef.msgid" offset="$map.sigByteOffset" access="$map.sigAccess" lsb="$map.sigBitOffset" bits="$map.sigSize" lsbvalue="$map.sigLsbValue" min="$map.paramMin" max="$map.paramMax"/>
                    #else if $map.sselRangeFloatBnr()
                    <condition type="RANGE_FLOATBNR" transport="$transport" message="$map.msgRef.msgid" offset="$map.sigByteOffset" access="$map.sigAccess" lsb="$map.sigBitOffset" bits="$map.sigSize" lsbvalue="$map.sigLsbValue" min="$map.paramMin" max="$map.paramMax"/>
                    #end if                
                    #if $map.sselValParam()
                    #set $par=$map.sselValParamData()
                    #if $par is not None
                    <condition type="VALIDITY_INPUT" transport="$transport" message="$par.msgid" offset="$par.offset" access="$par.access" bits="$par.bits" lsb="$par.lsb" value="$par.value"/>
                    #end if
                    #end if
                </sourceLogic>
                #end if
            #end for
            </Logic>
            #set $p = $sources[0]
            <Parameter paramNameValue="$p.paramName" paramSize="$p.paramDatasize" paramType="$p.paramDatatype" paramNameStatus="$(p.paramName).Status" paramOffsetValue="$p.paramOffset" paramOffsetStatus="$p.paramOffsetStatus" paramDefault="$p.paramDefault">
            #for $map in $sources
                #if map.msgRef.msgclass == "AFDX"
                    #set $transport = "A664"
                #else if map.msgRef.msgclass == "CAN"
                    #set $transport = "A825"
                #else if map.msgRef.msgclass == "A429"
                    #set $transport = "A429"
                #end if            
                #if $transport == "A664" or $transport == "A429"
                <source type="$map.sigType" transport="$transport" message="$map.msgRef.msgid" offset="$map.sigByteOffset" access="$map.sigAccess" lsb="$map.sigBitOffset" bits="$map.sigSize" lsbvalue="$map.sigLsbValue"/>
                #end if            
            #end for
            </Parameter>
        </DataSet>
    #end if
 #end for
'''

TEMPLATE_AFDXOUT= '''    
    <AfdxOutput>
 #for $key in $model.afdx.messageKeys
  #set map=$model.afdx.messages[$key]
  #if $map.msgUsed
        <AfdxMessage id="$map.msgid" messageName="$map.fullname" portType="$map.portType" queueLength="$map.queueLength" 
                     portId="$map.portId" portName="$map.portName" a653PortRefreshPeriod="$map.msgTxInterval" length="$map.msgLength"
                     crcOffset="$map.crcOffset" crcFsbOffset="$map.crcFsbOffset" fcOffset="$map.fcOffset" fcFsbOffset="$map.fcFsbOffset"
                     schedRate="$map.schedRate" schedOffset="$map.schedOffset"/>
  #end if
 #end for

 #for key in $model.afdx.datasets.keys()
    #set ds = $model.afdx.datasets[$key]
    #set dsName = ".".join($key)
        <DataSet name="$dsName" dsOffset="$ds[0].dsDsOffset" fsbOffset="$ds[0].dsFsbOffset" messageId="$ds[0].msgRef.msgid" dsType="A664" dsA429Label="" dsA429SDI="" dsA429SSMType="">
        #for $p in $ds:
            <Parameter paramNameValue="$p.paramName" paramSize="$p.paramDatasize" paramType="$p.paramDatatype" paramNameStatus="$(p.paramName).Status" paramOffsetValue="$p.paramOffset" paramOffsetStatus="$p.paramOffsetStatus">
                <destination type="$p.sigType" message="$p.msgRef.msgid" offset="$p.sigByteOffset" access="$p.sigAccess" lsb="$p.sigBitOffset" bits="$p.sigSize" lsbvalue="$p.sigLsbValue"/>
            </Parameter>
        #end for
        </DataSet>
 #end for
    </AfdxOutput>
'''

TEMPLATE_CANOUT = '''
    <CanOutput>
 #for $key in $model.can.messageKeys
  #set $msg=$model.can.messages[$key]
  #if $msg.msgUsed
        <CanMessage id="$msg.msgid" messageName="$msg.fullname" canId="$msg.msgCanID" canbusName="$msg.msgPhysPort" rate="$msg.msgTxInterval" length="$msg.msgLength">
    #set $params = $model.can.signals[$key]
    #for $p in $params:
            <Parameter paramNameValue="$p.paramName" paramSize="$p.paramDatasize" paramType="$p.paramDatatype" paramNameStatus="$(p.paramName).Status" 
            paramOffsetValue="$p.paramOffset" paramOffsetStatus="$p.paramOffsetStatus">
                <destination type="$p.sigType" access="$p.sigAccess" offset="$p.sigByteOffset" lsb="$p.sigBitOffset" bits="$p.sigSize" lsbvalue="$p.sigLsbValue"/>
            </Parameter>
    #end for
        </DataSet>
  #end if
 #end for
    </CanOutput>
'''

class Bunch(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

def genXml(inputModel, outputModel, outfn):

    xmlfile = open(outfn, "w")
    
    # finout model to use for extracting the header
    m = inputModel
    if m is None:
        m = outputModel
    if m is None:
        return

    # write header
    tmpl = Template(TEMPLATE_HEADER, searchList=[{ "model" : m }])
    xmlfile.write(tmpl.respond())

    # write input definitions
    if inputModel:
        xmlfile.write("<Input>\n")
        for tmplstr in (TEMPLATE_AFDXIN, TEMPLATE_CANIN):
            tmpl = Template(tmplstr, searchList=[{ "model" : inputModel }])
            xmlfile.write(tmpl.respond())
        xmlfile.write("</Input>\n")

    # write output definitions
    if outputModel:
        xmlfile.write("\n\n<Output>\n")
        for tmplstr in (TEMPLATE_AFDXOUT, TEMPLATE_CANOUT):
            tmpl = Template(tmplstr, searchList=[{ "model" : outputModel }])
            xmlfile.write(tmpl.respond())
        xmlfile.write("</Output>\n")
    
    xmlfile.write("</IOMConfiguration>\n")

def usage():
    sys.stderr.write("Usage: iomGenXml excelicd [--indd inputdd] [--outdd outputdd] [-o outputfile] [-a appname]")

def main(arglist):

    # Parse command line arguments
    inputddfiles    = []
    outputddfiles   = []
    xmlfile         = None
    appname         = None
    apprate         = 0

    opts, args = getopt.getopt(arglist, 'ha:o:', ['appname=', 'indd=', 'outdd=', 'output=', 'help'])

    for o, a in opts:
        if o in ['-h', '--help']:
            usage()
            return -1
        elif o in [ '--indd']:
            if a is not "":
                inputddfiles.append(a)
        elif o in [ '--outdd']:
            if a is not "":
                outputddfiles.append(a)
        elif o in [ '-o', '--output']:
            xmlfile = a
        elif o in [ '-a', '--appname']:
            appname = a
        else:
            usage()
            return -1

    if len(args) != 1:
        usage()
        return -1
        
    excelicdfile = args[0]

    if xmlfile is None:
        xmlfile = excelicdfile.rsplit(".", 1)[0] + '.xml'
        
    if appname:
        try:
            apprate = APPLICATION_RATE[appname]
        except:
            pass

    if len(inputddfiles) > 0:
        inputDD = iomGenReadDD.ddread(inputddfiles)
    else:
        inputDD = None

    if len(outputddfiles) > 0:
        outputDD = iomGenReadDD.ddread(outputddfiles)
    else:
        outputDD = None
        
    inputModel  = iomGenCommon.MapReader(excelicdfile, dd=inputDD,  msgonly=False, direction='input',  apprate=apprate)
    outputModel = iomGenCommon.MapReader(excelicdfile, dd=outputDD, msgonly=False, direction='output', apprate=apprate)
    genXml(inputModel, outputModel, xmlfile)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))