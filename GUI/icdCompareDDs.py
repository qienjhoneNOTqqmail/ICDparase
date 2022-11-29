
import os        
import sys
import copy
from imtExcelRW import *
from Cheetah.Template import Template


TFG_ROOT = os.path.join('C:', '\\TechSAT', 'TestFrameGen', 'lib', 'python')
sys.path.append(TFG_ROOT)

from ScadeImport.importScadeType import XscadeReader
errcount = 0
logFile  = None

        
TEMPLATE_XMLDD = '''<namelist model="TOPLEVEL">
 #set $offset = 0
 #set $status = "_Status"
 #for $dataEntry in $dd
    #set $dataSize    = $dataEntry['Data Size']/8
    #set $dataType    = $dataEntry['Data Type'].lower()
    #if $dataType == "float":
        #set $dataType = "real"
    #end if
    #if $dataEntry['InIOBuffer'] == "Yes":
        #set $offset = int($dataEntry['IOBufferOffset'])
    #end if
    #set $dataTypePad = "     "[:-len($dataType)]
    #set $offsetPad   = "     "[:-len(str($offset))]
    <parameter offset="$offset"$offsetPad size="$dataSize" elements="1" type="$dataType"$dataTypePad name="$dataEntry['Parameter Name']"/>
    #set $offset += $dataSize
    #set $offsetPad   = "     "[:-len(str($offset))]
    <parameter offset="$offset"$offsetPad size="4" elements="1" type="int"   name="$dataEntry['Parameter Name']$status"/>
    #set $offset += 4
 #end for
</namelist>
'''


def listToDict(keyFunc,list,convFunc=lambda element:element):
    dico={}
    for element in list:
        dico[keyFunc(element)]=convFunc(element)
    return dico
    

def genDDMapOutOfModel(inputNamelist, outputNamelist, modelname, path):
    endOffset = 0
    txt = '<namelist model="%s">\n' % modelname
    if inputNamelist:
        for n in inputNamelist:
            if n['structoffset'] > endOffset:
                endOffset = n['structoffset']+n['scadesize']*n['scadeelements']
            n['name']=n['name'].strip().split(".")[-1]
            n['dataTypePad']="     "[:-len(n['scadetype'])]            
            n['offsetPad'] = "     "[:-len(str(n['structoffset']))]
            txt += '    <parameter offset="%(structoffset)s"%(offsetPad)s size="%(scadesize)s" elements="%(scadeelements)s" ' \
                   'type="%(scadetype)s"%(dataTypePad)s name="%(name)s"/>\n' % n
        txt  += '</namelist>\n'
        open(os.path.join(path, modelname) + '.fromModelInddmap.xml', "w").write(txt)
    
    if outputNamelist:
        txt = '<namelist model="%s">\n' % modelname
        for n in outputNamelist:
            n['name']=n['name'].strip().split(".")[-1]
            txt += '    <parameter offset="%(structoffset)s"  size="%(scadesize)s" elements="%(scadeelements)s" ' \
                   'type="%(scadetype)s" name="%(name)s"/>\n' % n
        txt += '</namelist>\n' 
        open(os.path.join(path, modelname) + '.fromModelOutddmap.xml', "w").write(txt)
    return endOffset

    
def logerr(msg):
    global errcount

    sys.stderr.write("\nERROR****: " + msg + "\n")
    sys.stderr.flush()
    errcount+=1
    
def appendToLog(msg,paramname=None):
    global logFile
    spaceLine = "                                                     "
    if paramname:
        msg = paramname+spaceLine[:-len(paramname)]+":"+msg
    print msg    
    logFile.write(msg+"\n")

def fromSWdata(element):
    dataSize    = element['Data Size']/8
    dataType    = element['Data Type'].lower()
    if dataType == "float":
        dataType = "real"
    
    return Bunch(Offset   = element['IOBufferOffset'],
                 Size     = dataSize,
                 Elements = 1,
                 Type     = dataType,
                 Name     = element['Parameter Name'],
                 OrigData = element
                )
                
def fromMDdata(element):
    return Bunch(Offset   = element['structoffset'],
                 Size     = element['scadesize'],
                 Elements = element['scadeelements'],
                 Type     = element['scadetype'],
                 Name     = element['name'],
                 OrigData = element
                )                

def compareParams(ddData,mdData,param):
    if ddData[param] == mdData[param]:
        return 0
    else:
        appendToLog("usage in the model is not compliant with the SW DD definition:",mdData.Name)
        appendToLog("    '"+param+"' Model value:"+str(mdData[param])+"   SW DD:"+str(ddData[param]),"")
        return 1
                
def compare(DDIn,ModelIn):
    localModelIn = copy.copy(ModelIn)
    localDDIn    = copy.copy(DDIn)
    differences  = 0
    
    #first pass between SWDD and ModelIn    
    for ddParamName,ddParamData in DDIn.iteritems():        
        if ModelIn.has_key(ddParamName):
            mdParamData = ModelIn[ddParamName]
            for paramAttribute in ["Offset","Size","Type"]:
                differences += compareParams(ddParamData,mdParamData,paramAttribute)
            localModelIn.pop(ddParamName)
            localDDIn.pop(ddParamName)
            
    #second pass: if localDDIn is not empty, it means that some data 
    #specified in the SW DD re not used in the model
    notPublished = []
    for ddParamName,ddParamData in localDDIn.iteritems():
        #check if the param is really published to the model
        if ddParamData.OrigData.InIOBuffer == "Yes":
            appendToLog("defined in the SW DD, but not used in the model",ddParamName)
            differences +=1
        else:
            notPublished.append(ddParamName)            
                
    #third pass: if localModelIn is not empty, it means that some data used in the model
    # are not defined at the SW DD Level
    statusParams = []
    for mdParamName,mdParamData in localModelIn.iteritems():
        #check if the param is really coming from the SW DD
        if mdParamName.endswith("_Status"):
            statusParams.append(mdParamName)
            #do some basic consistency check on the model
            if ModelIn[mdParamName].Type != 'int':
                appendToLog("should be defined as an int in the model",mdParamName)
                differences +=1
            if ModelIn[mdParamName].Size != 4 or ModelIn[mdParamName].Elements != 1:
                appendToLog("does not follow the convention for a Status word",mdParamName)
                differences +=1
            if ModelIn.has_key(mdParamName[:-7]):
                param = ModelIn[mdParamName[:-7]]
                if param.Offset+param.Size*param.Elements != ModelIn[mdParamName].Offset:
                    appendToLog("Convention for Status parameter is they follow the parameter they qualify",mdParamName)
                    appendToLog("    Status at offset "+str(ModelIn[mdParamName].Offset)+", parameter at offset "+str(param.Offset))
                    differences +=1
            else:
                appendToLog("seems to be associated to no parameter (would expect "+mdParamName[:-7]+")",mdParamName)
        else:
            if mdParamName.lower().endswith("_status"):
                appendToLog("Status parameter should end with '_Status'. Check case...",mdParamName)
            else:
                appendToLog("used in the model, but not defined at the SW DD level",mdParamName)
            differences +=1
    
    for paramName in notPublished:
        localDDIn.pop(paramName)
    for paramName in statusParams:
        localModelIn.pop(paramName)
        
    if len(localDDIn) != 0 or len(localModelIn) != 0:
        appendToLog("***************************************************************************")    
        appendToLog("* Significant differences or errors have been found. Please check the log *")
        appendToLog("From SDD:"                                                                  )
        appendToLog(localDDIn.__repr__()                                                         )
        appendToLog("From Model:"                                                                )
        appendToLog(localModelIn.__repr__()                                                      )
        appendToLog("***************************************************************************")
        
    return differences,notPublished,statusParams       
       

                
def main(args):
    global logFile
    # read Excel files exported from DOOORS
    outputDir    = args[0]
    icdRootDir   = args[1]
    swDDIn       = args[2]
    swDDOut      = args[3]
    modelRootDir = args[4]
    modelName    = args[5]
    
    logFile = open(outputDir+"/"+modelName+"CompareDDs.txt","w")
    
    
    swDDInFullPath  = icdRootDir+'/'+swDDIn
    swDDOutFullPath = icdRootDir+'/'+swDDOut
    
    # check parameters
    if not os.path.exists(swDDInFullPath):
        logerr("Can't open SW_DD_IN Excel ICD file: %s" % swDDInFullPath )
        usage()
        return 2

    if swDDOut != "None" and not os.path.exists(swDDOutFullPath):
        logerr("Can't open SW_DD_OUT Excel ICD file: %s" % swDDOutFullPath )
        usage()
        return 2       
        
    searchlist = [modelRootDir + '/' + modelName, modelRootDir + '/Common', modelRootDir ] 
    try:
        # The names of input model and output model must be "ModelInput" and "ModelOutput"
        reader = XscadeReader('%s.xscade' % modelName, searchlist)
        reader.processNode()
    except Exception as e:
        print "Error: XscadeReader initialize failed. Abort." + str(e)
        return 2   

    # create variable list with attributes
    inputNamelist = []
    outputNamelist = []

    for _output in reader.OutputList:
        nl = []
        try:
            reader.mkNameList(nl, _output[0], _output[1], 0)
        except KeyError as k:
            print "Error: Unresolved output symbol found: %s. Abort.\n" % k
            # sys.exit(2)
        outputNamelist.extend(nl)

    for _input in reader.InputList:
        nl = []
        try:
            reader.mkNameList(nl, _input[0], _input[1], 1)
        except KeyError as k:
            print "Error: Unresolved input symbol found: %s. Abort.\n" % k
            # sys.exit(2)
        inputNamelist.extend(nl)
    
    # Read Excel Export from DOORS Selection Set sources
    ddInSheetNames = getExcelFileSheetNames(swDDInFullPath)
    ddIn           = readExcelFile(swDDInFullPath, (ddInSheetNames[0],))[0]
    ddIn           = sorted(ddIn, key=lambda data:(data.IOBufferOffset))
    ddOut          = []
    if swDDOut != "None":
        ddOutsheetNames = getExcelFileSheetNames(swDDOutFullPath)    
        ddOut           = readExcelFile(swDDOutFullPath, (ddOutsheetNames[0],))[0]
        ddOut           = sorted(ddOut, key=lambda data: data.IOBufferOffset)
    
    dicoSWIn         = listToDict(lambda data:data["Parameter Name"]             ,ddIn          ,fromSWdata)
    dicoMDIn         = listToDict(lambda data:data["name"].strip().split(".")[-1],inputNamelist ,fromMDdata)
    dicoSWOut        = listToDict(lambda data:data["Parameter Name"]             ,ddOut         ,fromSWdata)
    dicoMDOut        = listToDict(lambda data:data["name"].strip().split(".")[-1],outputNamelist,fromMDdata)    
    
    diffIn ,notPubIn ,statiiIn  = compare(dicoSWIn ,dicoMDIn)
    diffOut,notPubOut,statiiOut = compare(dicoSWOut,dicoMDOut)

    for dir,dd,md,diffs in [("IN.xml",ddIn,inputNamelist,diffIn),("OUT.xml",ddOut,outputNamelist,diffOut)]:
        if diffs and len(dd):
            outfn = outputDir+"/"+modelName+"_fromSWDD_"+dir
            try:
                FILE = open(outfn,"w")
                FILE.writelines("Hello")
                FILE.close()
            except:
                logerr("Output File already open: %s" % outfn )
                usage()
                return -1
                
            tmpl = Template(TEMPLATE_XMLDD, searchList=[{ "dd" : dd }])
            FILE = open(outfn,"w")
            FILE.write(tmpl.respond())
            FILE.close()
            
    if len(notPubIn):
        appendToLog("")
        appendToLog("------------------------------------------------------------")
        appendToLog("|Note that the SW DD defines the following parameter, as   |")
        appendToLog("|IOM Internal (not visible by the Model):                  |")
        for internal in notPubIn: 
            appendToLog("|       "+internal+"                                                   |"[len(internal):])
        appendToLog("------------------------------------------------------------")
        
        
    if diffIn or diffOut:
        genDDMapOutOfModel(inputNamelist,outputNamelist,"TOPLEVEL",outputDir)
        appendToLog("")
        appendToLog("************************************************************")
        appendToLog("*    SW DD and model are NOT compliant. Errors found       *")
        appendToLog("*       "+swDDIn+"                                                   *"[len(swDDIn):])
        appendToLog("*       "+swDDOut+"                                                   *"[len(swDDOut):])
        appendToLog("*       "+modelName+"                                                   *"[len(modelName):])
        appendToLog("************************************************************")        
    else:
        appendToLog("")
        appendToLog("************************************************************")
        appendToLog("*    SW DD and model are fully compliant. No error found   *")
        appendToLog("*       "+swDDIn+"                                                   *"[len(swDDIn):])
        appendToLog("*       "+swDDOut+"                                                   *"[len(swDDOut):])
        appendToLog("*       "+modelName+"                                                   *"[len(modelName):])
        appendToLog("************************************************************")
    
    logFile.close()
    
    
    return 0


def usage():
    sys.stderr.write('Usage: OutputDir ExportsRootDir SW_DD_IN SW_DD_OUT ModelRootDir ModelName\n\n')

if __name__ == '__main__':
    if len(sys.argv) < 7:
        usage()
        sys.exit(1)
    else:
        sys.exit(main(sys.argv[1:]))
        
    