
from __future__ import print_function
import sys
import os
import getopt
from collections import defaultdict

from bunch import Bunch
import logger


from imtXmlReader import icdReadAll  
from imtExcelRW import genExcelFile


# ---------------------------------------------------------------
# - install extended traceback handler to provide
#   all stack variables and their values, and drop
#   into pdb when an exception occurs

import pdb

def excepthook(ex_cls, ex, tb):
    # from xtraceback import format_exception
    # tblist = format_exception(ex_cls, ex, tb, with_vars=True)
    # print('\n'.join(tblist))
    pdb.post_mortem(tb)
    
# sys.excepthook = excepthook

# ---------------------------------------------------------------
# helper

def _getAttrib(x, attrib, cast=None, default=None, reportMissingValue=True, reportBadValue=True):
    '''
    Get value of XML Record attribute attrib, cast it according to cast.
    If not found or cast fails, return default or None.
    '''
    a = x.a.get(attrib)
    if a is None:
        if default is None:
            if reportMissingValue:
                logger.nerror("Missing attribute %s" % attrib, TYPE=x.tag, NAME=x.a.Name, FILE=x.filename)
        else:
            if reportMissingValue:
                logger.nerror("Missing attribute %s. Set to default [%s]" % (attrib, default),
                                TYPE=x.tag, NAME=x.a.Name, FILE=x.filename)
            a = default
    else:
        if cast:
            try:
                a = cast(a)
            except:
                if default is None:
                    if reportBadValue:
                        logger.nerror("Bad value for attribute %s" % attrib, TYPE=x.tag, NAME=x.a.Name, FILE=x.filename)
                else:
                    if reportBadValue:
                        logger.nerror("Bad value for attribute %s. Replace with default [%s]" % \
                                (attrib, default), TYPE=x.tag, NAME=x.a.Name, FILE=x.filename)
                    a = default
    return a
# ---------------------------------------------------------------
def _getCodedSetMinMax(codeSet):
    minval = None
    maxval = None
          
    for entry in codeSet.split(";"):
        key = int(entry.split("=")[0].strip())
        if minval == None or key < minval:
            minval = key
        if maxval == None or key > maxval:
            maxval = key
    return minval, maxval

def _getCodedSetConst(codeSet):
    val = None

    for entry in codeSet.split(";"):
        try:
            key = int(entry.split("=")[0].strip())
            val = key
            break
        except:
            pass
        
    return val
    
    
def _getParentMsg(obj, msgtype):
    '''
    Return Msg parent of an object 
    Ascend the parent hierarchy until an A664Message or the tree root is found
    '''
    while obj.parent:
        obj = obj.parent
        if obj.tag == msgtype:
            return obj
    return None

# ---------------------------------------------------------------

def _getSSMType(xdpclass):
    '''
    Return SSM Type applicable for a signal in a A429 Word. For this
    locate SSM and return its Data Format Type
    This is very inefficient code, but its not used in DS anyway.
    '''
    if xdpclass.tag == "A429Word":
        searchin=xdpclass
    else:
        searchin=xdpclass.parent
    for odp in searchin.e.DP:
        if odp.a.Name == "SSM":
            s = odp.a.DataFormatType
            if s.startswith("A429_"):
                return s[5:]
            else:
                return s
    return ''

def _getTopNode(node):
    '''Get the root node of the HF/HA: this is directly under xroot'''
    while node.parent.parent:
        node = node.parent
    return node

def _getDSPath(xdp, msgtype):
    '''Get the path from outmost dataset to a DP'''
    res = xdp.tag
    if res == msgtype:
        return res
    
    while xdp.parent:
        xdp = xdp.parent
        res = xdp.tag + '.' + res
        if xdp.tag == msgtype:
            return res
    return None

def _getContainer(xdp):
    '''Get the path from outmost dataset to a DP'''    
    res = None    
    while xdp.parent:
        xdp = xdp.parent
        if xdp.tag == 'DS':
            break
        else:        
            if res != None:
                res = xdp.a.Name + '.' + res
            else:
                res = xdp.a.Name
    
    if xdp.tag == 'DS':
        return res
    else:
        return None
    
_a249labeldpnames = frozenset(("LABEL", "SDI", "SSM", "PARITY"))
        
def _getA429SingleDP(xword):
    '''
    Get the single Data DP from a 429 word. 
    If the word has more than one data DP or none at all, return None
    '''
      
    count = 0
    found = None
    for xdp in xword.e.get('DP', []):
        if xdp.a.Name.upper() not in _a249labeldpnames:
            found = xdp
            count += 1
    if count == 1:
        return found
    else:
        return None
    
def _makeMulticastIpAddr(vlid):
    return "224.224.%d.%d" % (vlid / 256, vlid % 256)

def getApplicationCRCandFCoffset(xmsg):
    '''
    Traverse message and look for DPs with name CRC/DataFormatType CRC and name Freshness_Counter
    Return a tuple with corresponding offsets (CRC Offset, CRC FSB Offset, FC Offset, FC FSB Offset)
    '''
    crcOffset       = "N/A"
    crcFsbOffset    = "N/A"
    fcOffset        = "N/A"
    fcFsbOffset     = "N/A"

    for xds in xmsg.e.get('DS', []):
        for xdp in xds.e.get('DP', []):
            if xdp.a.Name == "Application_CRC" and xdp.a.DataFormatType == "CRC":
                crcOffset    = int(xds.a.ByteOffsetWithinMsg) + int(xdp.a.BitOffsetWithinDS) / 8
                crcFsbOffset = int(xds.a.ByteOffsetFSF)

            elif xdp.a.Name == "Freshness_Counter" and xdp.a.DataFormatType == "UINT":
                fcOffset     = int(xds.a.ByteOffsetWithinMsg) + int(xdp.a.BitOffsetWithinDS) / 8
                fcFsbOffset  = int(xds.a.ByteOffsetFSF)

    return (crcOffset, crcFsbOffset, fcOffset, fcFsbOffset)

# ---------------------------------------------------------------

class IcdProcessor():

    '''
    Process Aviage input model and create an in-core output model
    isomorph to the IMT data model.
    The output IMT model will then be traversed by the save function
    and recursively saved to DB.
    The ouput model is an ad-hoc construct of bunches and lists
    suitable for simple traversal.
    '''

    #
    def __init__(self, xroot):

        self.xroot = xroot                      # root of input model
        self.xindex         = dict()            # cross reference for Guid's
        self.vlxref         = dict()
        self.gwsignalxref   = dict()            # index to find signals from gateways refering to an RP by RP Guid
        self.pubrefxref     = defaultdict(list) # index to find DP by PUBREF
        self.appportXref    = dict()
        self.guidIndex(self.xroot)              # build Guid lookup dictionary
        self.merged         = False             # flag if multiple HA/HF are processed

    def reset(self):
        self.rplist         = dict()            # table indexed by RP containing all info per signal for  IOM Generation
        self.rpuniq         = dict()            # table indexed by RP containing all info per signal for  IOM Generation
        self.dplist         = dict()            # table indexed by RP containing all info per signal for  IOM Generation
        self.rxMessagelist  = dict()            # table indexed by msg Name containing all info per message 
        self.txMessagelist  = dict()            # table indexed by msg Name containing all info per message
        self.merged         = False
        

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    EXCLUDE_FROM_INDEX = set(['Port_Ref'])
    PARAMETRIC_TYPES   = ["Parametric data","A429 Block"]
    RANGED_ENCODINGS   = ["INT", "UINT", "SINT", "BNR", "UBNR", "FLOAT", "BCD"]

    def guidIndex(self, node):
        '''
        Build Guid lookup dictionary
        Parameters:
        - node: tree node to index

        Recursively traverse model tree and gather all Guid's
        in a cross reference dictionary.
        '''
        if not node.tag in IcdProcessor.EXCLUDE_FROM_INDEX:
            guid = node.a.get("Guid")
            if guid:
                if guid in self.xindex:
                    logger.nerror(
                        "IMPORT.GUIDINDEX",
                        "Duplicate Guid",
                        TAG     = node.tag, 
                        GUID    = guid, 
                        OTHER   = self.xindex[guid].tag)
                else:
                    self.xindex[guid] = node

        for nodelist in node.e.values():
            for node in nodelist:
                self.guidIndex(node)
    
    def getClass(self, node):
        return self.xindex[node.a.GuidDef]

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    def recursiveGwLink(self, parent):
        '''
        Recursively traverse tree and gather Gw_Pub_Refs
        '''
        for objtype, objlist in parent.e.items():
            if objtype == "Gw_Pub_Ref":
                for xgw in objlist:
                    self.gwsignalxref[xgw.a.DestGuid] = xgw.parent
            else:
                for obj in objlist:
                    self.recursiveGwLink(obj)
    
                    
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    def makeGatewayReverseMap(self):
        '''
        Traverse all Gateways and build cross ref
        '''
        for xha in self.xroot.e.get('RemoteGateway', []):
            for xport in xha.e.get('HFQueuingPort',[]) + xha.e.get('HFSamplingPort', []) + xha.e.get('CANPort', []) + xha.e.get('A429Port', []):
                if xport.a.Direction != 'Source':
                    continue
                for xmsg in xport.e.get('A664Message', []):
                    for xds in xmsg.e.get('DS', []):
                        self.recursiveGwLink(xds)
                for xmsg in xport.e.get('CANMessage', []):
                    for xds in xmsg.e.get('DP', []):
                        self.recursiveGwLink(xds)
                for xch in xport.e.get('A429Channel', []):
                    for xaw in xch.e.get('A429Word', []):
                        self.recursiveGwLink(xaw)
    
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    def checkContainment(self, xinner, xouter):
        '''
        Generic function to check whether xinner is contained by xouter
        '''
        container = xinner.parent
        while container:
            if container == xouter:
                return True
            container = container.parent
        return False
            
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    porttype2msgtype = {
        "HFSamplingPort":   "A664Message",
        "HFQueuingPort":    "A664Message",
        "A653SamplingPort": "A664Message",
        "A653QueuingPort":  "A664Message",
        "CANPort":          "CANMessage",
        "A429Port":         "A429Word",
    }

    def processFunctionRPs(self, hfnamelist):
        '''
        Traverse hosted function/application and process all RP
        '''
        functypes =  ("A653ApplicationComponent", "HostedFunction")
        porttypes =  ("A653SamplingPort", "A653QueuingPort", "HFSamplingPort", "HFQueuingPort", "CANPort", "A429Port")
        self.merged = len(hfnamelist) > 1
        for functype in functypes:
            for xha in self.xroot.e.get(functype, []):
                if xha.a.Name in hfnamelist:                   
                    for porttype in porttypes:
                        msgtype = self.porttype2msgtype[porttype]
                        for xport in xha.e.get(porttype, []):
                            dataflowreflist = xport.e.get("Dataflow_Ref", [])
                            if len(dataflowreflist) > 1:
                                logger.nerror("More than one Dataflow_ref [%d]" % len(dataflowreflist),
                                        HF=xha.a.Name, PORT=xport.a.Name, DF=dataflowreflist[0].a.SrcName
                                )

                            rplist = xport.e.get("RP", [])
                            for xrp in rplist:

                                self.processOneRP(xha, msgtype, xport, dataflowreflist, xrp, hfnamelist)
    # ----------------------------------------------------------------------
    def processOneRP(self, xha, msgtype, xport, dataflowreflist, xrp, hfnamelist):
        '''
        Process one RP:
        Locate corresponding DP either by the Pub_Ref or the GW_Pub_Ref back reference
        Do all checks and create a bunch of information for the signal and for the message
        '''
        # local helper
        def alreadySubscribedInPort(xport, xsig, isgw):
            '''
            check of xsig is subscribed by a pubref in the current port
            if xsig is in a gateway, we have to check if a GW_Pub_Ref is pointing to
            an RP in the current port
            Else we have to check if any of the Pub_Refs in the port are pointing the the DP
            '''
            if isgw:
                for xgwpref in xsig.e.get("Gw_Pub_Ref", []):
                    tgt = self.xindex[xgwpref.a.DestGuid]
                    if tgt.isChildOf(xport):
                        return True
                return False
            else:
                for r in xport.e.get("RP", []):
                    for pr in r.e.get("Pub_Ref", []):
                        if pr.a.SrcGuid == xsig.a.Guid:
                            return True
                return False

        def alreadySubscribedInHF(xhf, xsig, isgw):
            '''
            check of xsig is subscribed by a pubref in the current port
            if xsig is in a gateway, we have to check if a GW_Pub_Ref is pointing to
            an RP in the current port
            Else we have to check if any of the Pub_Refs in the HF are pointing the the DP
            '''
            if isgw:
                for xgwpref in xsig.e.get("Gw_Pub_Ref", []):
                    tgt = self.xindex[xgwpref.a.DestGuid]
                    if tgt.isChildOf(xhf):
                        return True
                return False
            else:
                for ref in self.pubrefxref[xsig.a.Guid]:
                    if ref[0] == xhf:
                        return True
                return False

        def addA429ContainerRP(rprec, xport, isgw):
            
            #if(self.merged):
            #    return
            
            Xsig            = rprec.dp.parent
            xhf             = _getTopNode(rprec.xrp)

            if alreadySubscribedInHF(xhf, Xsig, isgw):
                return 
			
			#add by zheng chao, if only has one rp link to the DP inside 429 word, we also need other DP, extract them.
            for xsig in Xsig.e.get('DP', []):
                if not alreadySubscribedInPort(xport, xsig, isgw):
                    # create new rp object by copying current RP:
                    if isgw:
                        xsigclass = xsig
                    else:
                        xsigclass = self.getClass(xsig)
                    newrp = Bunch(
                        status     = 'Initial',
                        icdFix      = 'E',
                        xrp        = None,
                        rpName     = Xsig.a.Name + '.' + xsig.a.Name,   #modify by zhengchao original is rprec.rpName
                        PubrefName = '.'.join(rprec.PubrefName.split('.')[:-1])+'.'+ xsig.a.Name,
                        msg        = rprec.msg,
                        dfref      = rprec.dfref,
                        dp         = xsig,
                        dpclass    = xsigclass,
                    )
                    
                    rpkey = (xha.a.Name, newrp.rpName)
                    addRp(newrp, rpkey, skip=False)
        
        def addA429SignalRPs(rprec, xport, isgw):
            '''
            Expand an RP subscribing a A429 Label Word (instead of the individual signals)
            Create an RP with correspond info for each signal of the label (including label SDI, etc)
            The RP is linked to the corresponding signal and will create one line in the excel ICD
            If RPs linked to signals of the label already exist, they are not duplicated.
            '''
            for xsig in rprec.dp.e.get('DP', []):
                if not alreadySubscribedInPort(xport, xsig, isgw):
                    # create new rp object by copying current RP:
                    if isgw:
                        xsigclass = xsig
                    else:
                        xsigclass = self.getClass(xsig)
                    newrp = Bunch(
                        status     = 'Initial',
                        icdFix      = 'E',
                        xrp        = None,
                        rpName     = rprec.rpName + '.' + xsig.a.Name,   # modify by zhengchao, original is rprec.rpName
                        PubrefName = rprec.PubrefName  + '.' + xsig.a.Name,
                        msg        = rprec.msg,
                        dfref      = rprec.dfref,
                        dp         = xsig,
                        dpclass    = xsigclass,
                    )
                    
                    rpkey = (xha.a.Name, newrp.rpName)
                    addRp(newrp, rpkey, skip=False)
                    
        def isRpInList(rprec):
            for rp in self.rplist[rprec.rpName]:
                if rp.PubrefName == rprec.PubrefName \
                    and rp.dp == rprec.dp \
                    and rp.msg == rprec.msg:
                    return True

            return False
        
        def addRp(rprec, rpkey, skip=False):
            if skip:
                rprec.status = 'Ignore'
            else:
                rprec.status = 'Initial'

            self.rpuniq[rpkey] = rprec
                
            rpname = rpkey[1] 
            if not rpname in self.rplist:
                self.rplist[rpname] = [rprec]
            elif not isRpInList(rprec):
                self.rplist[rpname].append(rprec)

        def isDuplicateRp(rpkey,log=True):
            if rpkey in self.rpuniq:
                if log:
                    logger.nerror("Duplicate RP", 
                        HF=xha.a.Name, PORT=xport.a.Name, RP=xrp.a.Name,
                    )
                return True
            else:
                return False

        # ------------------------------------------------------
        # start of Function Body
        # ------------------------------------------------------

        # gather the results in a Bunch
        rprec = Bunch(
                status          = 'Initial',
                xrp             = xrp,
                rpName          = xrp.a.Name, 
                dfref           = None,
                dp              = None,
                dpclass         = None,
                msg             = None,
                PubrefName      = None)
        rpkey = (xha.a.Name, xrp.a.Name)
        

        # check for duplicate RP Name. This is not allowed and we discard this RP
        if isDuplicateRp(rpkey):
            return  # nothing else we can do

        # check for pubref
        pubreflst = xrp.e.get("Pub_Ref", [])
        if not pubreflst: 
            logger.nerror("RP without Pub_Ref",
                  HF=xha.a.Name, PORT=xport.a.Name, RP=xrp.a.Name
            )
            addRp(rprec, rpkey, skip=True)
            return # nothing else we can do. RP will be in the signal table but only with its name

        # multiple pubrefs are always an error, but we try our best and use the first in the list
        # for further processing
        if len(pubreflst) > 1:
            logger.nerror("Multiple Pub_Refs for one RP", 
                  HF=xha.a.Name, PORT=xport.a.Name, RP=xrp.a.Name
            )
        pubref = pubreflst[0]
        rprec.PubrefName = pubref.a.SrcName
        
        # either the RP is referenced by Gateway or the TX Signal is the Pubref 
        xdp = self.gwsignalxref.get(xrp.a.Guid)
        if xdp:
            isgw = True
        else:
            xdp = self.xindex.get(pubref.a.SrcGuid, None)
            isgw = False
        
        if not xdp: 
            logger.nerror("No DP message found for RP", 
                  HF=xha.a.Name, PORT=xport.a.Name, RP=xrp.a.Name)
            addRp(rprec, rpkey, skip=True)
            return  # nothing else we can do
        
        
        # now get the message containing the DP
        # for A429 the xdp object can already be a A429Word
        if xdp.tag == "A429Word" and msgtype == "A429Word":
            xmsg = xdp
        else:
            xmsg = _getParentMsg(xdp, msgtype)
        if not xmsg:
            # xmsg is bit an AFDX DP, so there is a mess with Gateways and Pubrefs.
            logger.nerror("Pubref/Gateway mismatch: sender is not on same bus type",
                          HF=xha.a.Name, PORT=xport.a.Name, RP=xrp.a.Name
            )
            addRp(rprec, rpkey, skip=True)
            return # nothing else we can do on this RP

        # Check if data source is one of the systems we are stimulating.
        # In this case, we skip the signal, since we don't need to stimulate this.
        # When we process the RP we will generate a receiver for it for monitoring
        
        txlru = _getTopNode(xmsg)
        if txlru.a.Name in hfnamelist:
            # no need to process this further. We also don't store it, it is simply discarded.
            return 
            
        if isgw:
            xdpclass  = xdp
            xmsgclass = xmsg
        else:
            xdpclass  = self.getClass(xdp)
            xmsgclass = self.getClass(xmsg)

        # link to message object
        if xmsg.a.Guid in self.rxMessagelist:
            msgrec = self.rxMessagelist[xmsg.a.Guid]
            #mode: merged
            portDefined = False
            for port in msgrec.rxport:
                if  str(port.a.Guid) == str(xport.a.Guid):
                    portDefined = True
                    break
            if not portDefined:
                msgrec.rxport.append(xport)  
        else:
            msgrec = Bunch(msgtype=msgtype, txmsg=xmsg, txmsgclass=xmsgclass, rxport=[xport])
            self.rxMessagelist[xmsg.a.Guid] = msgrec
        
        
        rprec.dp      = xdp
        rprec.dpclass = xdpclass
        rprec.msg     = msgrec
    
        # check consistency of Dataflow_Ref with Pub_Ref
        if len(dataflowreflist):
            ok = False
            for dfref in dataflowreflist:
                if self.checkContainment(xdp, self.xindex[dfref.a.SrcGuid]):
                    rprec.dfref = dfref
                    ok = True
                    break

            if not ok:
                logger.nerror("Bad Dataflow_ref containment", 
                      HF=xha.a.Name, PORT=xport.a.Name, RP=xrp.a.Name,
                      DP=xdp.a.Guid,
                      DF=dataflowreflist[0].a.SrcGuid
                )
        else:
            logger.nerror("No Dataflow_ref containment", HF=xha.a.Name, PORT=xport.a.Name, RP=xrp.a.Name,
                      DP=xdp.a.Guid)
                
        # if the RP is linked to a A429 Label (instead of its signals)
        # expand the RP so each signal is linked individually
        # If the expanded signal does not already exists in the same port, add it
        
        addRp(rprec, rpkey, skip=False)

        if rprec.dp.tag == "A429Word":
            # this needs cleanup. It doesnt play properly with real A429
            addA429SignalRPs(rprec, xport, isgw)
        else:
            if rprec.dp.parent.tag == "A429Word":
                addA429ContainerRP(rprec, xport, isgw)
       
                       

    # ----------------------------------------------------------------------
    def gatherRxSignalDetails(self):

        def getDSAttrib(rp, xdp, xds, xdpclass, xdsclass):
            rp.DsName        = xds.a.Name
            rp.ByteOffsetFSB = _getAttrib(xdsclass, "ByteOffsetFSF", int)
            rp.ByteOffsetDS  = _getAttrib(xdsclass, "ByteOffsetWithinMsg", int)
            rp.ByteSizeDS    = _getAttrib(xdsclass, "DataSetSize", int)
        
        def getZeroOneState(rp, xdp, xdpclass):
            rp.ZeroState = xdpclass.a.get("ZeroState", "TBD")
            rp.OneState  = xdpclass.a.get("OneState", "TBD")
            rp.MaxValue  = "N/A"
            rp.MinValue  = "N/A"    
            
        def getCodedSet(rp, xdp, xdpclass):
            codeSet = _getAttrib(xdpclass, "CodedSet")
            if codeSet:
                rp.CodedSet = codeSet.replace(";",",\n")                                      
                rp.MinValue, rp.MaxValue = _getCodedSetMinMax(codeSet)
            else:
                rp.CodedSet = "TBD"
                    
        
        def getA429SSM(rp, xdp, xdpclass):
            rp.MinValue = 0
            rp.MaxValue = 3
            
            if rp.Encoding == "A429_SSM_BNR":
                rp.CodedSet = "0=No Data,\n1=No Computed Data,\n2=Functional Test,\n3=Normal Operation"
            elif rp.Encoding == "A429_SSM_BCD":
                rp.CodedSet = "0=Normal Operation,\n1=No Computed Data,\n2=Functional Test,\n3=Normal Operation"
            elif rp.Encoding == "A429_SSM_DIS":
                rp.CodedSet = "0=Normal Operation,\n1=No Computed Data,\n2=Functional Test,\n3=No Data"
            elif rp.Encoding == "A429_SSM_CUSTOM":
                codeset = _getAttrib(xdpclass, "CodedSet")
                if codeset:
                    rp.CodedSet = codeset.replace(";",",\n");
                else:
                    rp.CodedSet = "TBD"
        
        def getA429StandardAttribs(rp, xdp, xdpclass):
            # CodedSet and Range
            if rp.Encoding.startswith("A429_SSM"):
                getA429SSM(rp, xdp, xdpclass)
            elif rp.Encoding == "A429SDI":
                getCodedSet(rp, xdp, xdpclass)              
            elif rp.Encoding == "COD":
                getCodedSet(rp, xdp, xdpclass)
            elif rp.Encoding == "DIS":
                getZeroOneState(rp, xdp, xdpclass)
            elif rp.Encoding in IcdProcessor.RANGED_ENCODINGS:
                if rp.Encoding in ("BNR","UBNR","BCD"): 
                    rp.MaxValue = _getAttrib(xdpclass,  "FuncRngMax",float, default="TBD", reportMissingValue=False)
                    rp.MinValue = _getAttrib(xdpclass,  "FuncRngMin",float, default="TBD", reportMissingValue=False)
                else:
                    rp.MaxValue = _getAttrib(xdpclass,  "FuncRngMax",int, default="TBD", reportMissingValue=False)
                    rp.MinValue = _getAttrib(xdpclass,  "FuncRngMin",int, default="TBD", reportMissingValue=False)
                if rp.MinValue == "TBD" or rp.MaxValue == "TBD":
                    logger.nerror("Missing attribute FuncRngMin and/or FuncRngMax",
                                  TYPE=xdpclass.tag, NAME=xdpclass.a.Name, FILE=xdpclass.filename)
                    

            # Multiplier: Only used for BCD
            # Sometimes LsbRes is used instead
            
            if rp.Encoding in ("BCD"):
                rp.Multiplier = _getAttrib(xdpclass, "Multiplier", float, default="TBD", reportMissingValue=False)
                if rp.Multiplier == "TBD":
                    rp.Multiplier = _getAttrib(xdpclass, "LsbRes", float, default="TBD", reportMissingValue=False)
                    if rp.Multiplier == "TBD":
                        logger.nerror("Missing both attributes Multiplier and LsbRes for BCD Signal",
                                      TYPE=xdpclass.tag, NAME=xdpclass.a.Name, FILE=xdpclass.filename)
                        
                        
                    
            
            # LsbValue: Only used for BNR, UBNR 
            if rp.Encoding in ("BNR", "UBNR"):
                rp.LsbValue = _getAttrib(xdpclass, "LsbRes", float, 1.0)

        def getDPDSAttrib(rp, xdp, xds, xdpclass, xdsclass):
            rp.BusType       = "A664"
            rp.SigName       = xdp.a.Name
            rp.DsName        = xds.a.Name
            rp.Container     = _getContainer(xdp)
            rp.ByteOffsetDS  = _getAttrib(xdsclass, "ByteOffsetWithinMsg", int)
            rp.ByteSizeDS    = _getAttrib(xdsclass, "DataSetSize", int)
            rp.BitOffset     = _getAttrib(xdpclass, "BitOffsetWithinDS", int)
            rp.BitSize       = _getAttrib(xdpclass, "ParameterSize", int)
            rp.Encoding      = _getAttrib(xdpclass, "DataFormatType")

            if rp.Encoding != "A664_FSS" and rp.ByteOffsetDS != 0:
                rp.ByteOffsetFSB = _getAttrib(xdsclass, "ByteOffsetFSF", int, "TBD")
            else:
                rp.ByteOffsetFSB = "N/A"
            
            # CodedSet and Range            
            if rp.Encoding == "COD":
                getCodedSet(rp, xdp, xdpclass)
            elif rp.Encoding == "DIS":
                getZeroOneState(rp, xdp, xdpclass)
            elif rp.Encoding in IcdProcessor.RANGED_ENCODINGS:
                if rp.Encoding == "FLOAT":
                    rp.MaxValue = _getAttrib(xdpclass,  "FuncRngMax", float,default="TBD", reportMissingValue=False)
                    rp.MinValue = _getAttrib(xdpclass,  "FuncRngMin", float,default="TBD", reportMissingValue=False)
                else:
                    rp.MaxValue = _getAttrib(xdpclass,  "FuncRngMax",int,default="TBD", reportMissingValue=False)
                    rp.MinValue = _getAttrib(xdpclass,  "FuncRngMin",int,default="TBD", reportMissingValue=False)
                if rp.MaxValue == "TBD" or rp.MinValue == "TBD":
                    logger.nerror("Missing attribute FuncRngMin and/or FuncRngMax", 
                                  TYPE=xdpclass.tag, NAME=xdpclass.a.Name, FILE=xdpclass.filename)

                    

            # LsbValue: For UINT and SINT we may need to manually adjust the values based on 
            # RDIU Template, UDC or other. These are normally also something like BNR, but not 
            # properly handled by ICD Format
            if rp.Encoding in ("UINT", "SINT", "BNR"):  # modify by zheng chao ,add the BNR type
                rp.LsbValue = _getAttrib(xdpclass, "LsbRes", float, default = 1,
                                         reportMissingValue = False)

            # Validation Criteria
            rp.ValidityCriteria = 'FRESH'
            if rp.ByteOffsetFSB not in ("N/A", "TBD"):
                rp.ValidityCriteria += ',FSB'
                
                
        # extract attributes from a full embedded A429Word
        # not applicable for direct A429 inputs 
        def getDPDSAttribA429Word(rp, xdp, xds, xdpclass, xdsclass):
            rp.BusType       = "A664"
            rp.SigName       = xdp.a.Name
            rp.DsName        = xds.a.Name
            rp.Container     = ""
            rp.ByteOffsetFSB = _getAttrib(xdsclass, "ByteOffsetFSF", int, "TBD")
            rp.ByteOffsetDS  = _getAttrib(xdsclass, "ByteOffsetWithinMsg", int)
            rp.ByteSizeDS    = _getAttrib(xdsclass, "DataSetSize", int)

            # if this is a "Virtual RP for full label inserted by tool"
            rp.BitSize  = 32
            rp.Encoding = "OPAQUE"
            rp.BitOffset = _getAttrib(xdpclass, "BitOffsetWithinDS", int, 0)

            # determine ValidityCriteria
            rp.ValidityCriteria = 'FRESH'
            if rp.ByteOffsetFSB not in ("N/A", "TBD"):
                rp.ValidityCriteria += ',FSB'


        # extract attributes from a signal in an embedded A429Word
        # not applicable for direct A429 inputs 
        def getDPDSAttribA429Sig(rp, xdp, xds, xdpclass, xdsclass):
            rp.BusType       = "A664"
            rp.SigName       = xdp.a.Name
            rp.DsName        = xds.a.Name
            rp.Container     = _getContainer(xdp)
            rp.ByteOffsetFSB = _getAttrib(xdsclass, "ByteOffsetFSF", int, "TBD")
            rp.ByteOffsetDS  = _getAttrib(xdsclass, "ByteOffsetWithinMsg", int)
            rp.ByteSizeDS    = _getAttrib(xdsclass, "DataSetSize", int)
            rp.BitOffset     = _getAttrib(xdpclass, "BitOffsetWithinDS", int)
            rp.BitSize       = _getAttrib(xdpclass, "ParameterSize", int)
            rp.Encoding      = _getAttrib(xdpclass, "DataFormatType")

            # The ICD contains many errors regarding BitOffset of Signals embedded in 429 Words
            # We do a plausibility check and repair the value if it is wrong
            # get parent (A429Word) offset and check wether signal offset is within the word
            # If not compute the most plausible value but create an entry in the log
            a429wordoffset = _getAttrib(xdpclass.parent, "BitOffsetWithinDS", int)
            if rp.BitOffset < 0 or rp.BitOffset > 32:
                logger.nerror("BitOffset of embedded A429 Word inconsistent", DP=xdp.a.Name, DS=xds.a.Name)

            if a429wordoffset is not None:
                rp.BitOffset = rp.BitOffset % 32 + a429wordoffset
             
            getA429StandardAttribs(rp, xdp, xdpclass)
                
            # determine ValidityCriteria
            rp.ValidityCriteria = 'FRESH'
            if rp.ByteOffsetFSB not in ("N/A", "TBD"):
                rp.ValidityCriteria += ',FSB'

            if rp.BitSize != 32 or rp.Encoding != "OPAQUE":
                # only for genuine signals, the virtual signal for full label has only freshness
                ssmtype = _getSSMType(xdpclass)
                if ssmtype:
                    rprec.ValidityCriteria += ',' + ssmtype

        # extract attributes from a direct A429Word
        def getA429DPAttribWord(rp, xdp, xdpclass):
            rp.BusType       = "A429"
            rp.SigName       = xdp.a.Name
            rp.DsName        = ""
            rp.ByteOffsetFSB = "N/A"
            rp.ByteOffsetDS  = 0
            rp.ByteSizeDS    = 4
            rp.BitOffset     = 0
            rp.BitSize       = 32
            rp.Encoding      = "OPAQUE"
            rprec.ValidityCriteria = 'FRESH'
            

        # extract attributes from a signal in an direct A429Word 
        def getA429DPAttribSig(rp, xdp, xdpclass):
            rp.BusType       = "A429"
            rp.SigName       = xdp.a.Name
            rp.DsName        = ""
            rp.ByteOffsetFSB = "N/A"
            rp.ByteOffsetDS  = 0
            rp.ByteSizeDS    = 4
            rp.BitOffset     = _getAttrib(xdpclass, "BitOffsetWithinDS", int)
            rp.BitSize       = _getAttrib(xdpclass, "ParameterSize", int)
            rp.Encoding      = _getAttrib(xdpclass, "DataFormatType", "OPAQUE")
        
            getA429StandardAttribs(rp, xdp, xdpclass)
     
            # determine ValidityCriteria
            rprec.ValidityCriteria = 'FRESH'
            ssmtype = _getSSMType(xdpclass)
            if ssmtype:
                rprec.ValidityCriteria += ',' + ssmtype
            
            # check if the message already has the label and sdi
            # if not, add it,
            # if yes, check it
            
            if rp.get("xrp"):
                # this is a genuine RP, not a virtual one added by expansion
                xrpclass = self.getClass(rp.xrp)
                label = xrpclass.a.Label
                sdi   = xrpclass.a.SDIExpected
                
                if rp.msg.get("Label") is None:
                    rp.msg.Label = label
                    rp.msg.SDI = sdi
                else:
                    if rp.msg.Label != label:
                        logger.error("Inconsistent LABEL Values: RP=%s Label=%s Message=%s Label=%s",
                                     rp.rpName, label, rp.msg.txmsg.a.Name, rp.msg.Label)
                    if rp.msg.SDI != sdi:
                        logger.error("Inconsistent SDI Values: RP=%s Label=%s Message=%s Label=%s",
                                     rp.rpName, label, rp.msg.txmsg.a.Name, rp.msg.Label)
                    
            
                
        # extract attributes from a signal in a direct CAN/A825 Message
        # not applicable for embedded CANMessage - which seems not to exist anymore                
        def getCANDPAttrib(rp, xdp, xdpclass):
            rp.BusType   = "A825"
            rp.SigName       = xdp.a.Name
            rp.DsName        = "N/A"
            rp.ByteOffsetFSB = "N/A"
            rp.ByteOffsetDS  = 0
            rp.ByteSizeDS    = _getAttrib(xdpclass.parent, "MessageSize", int)
            rp.BitOffset     = _getAttrib(xdpclass, "BitOffsetWithinDS", int)
            rp.BitSize       = _getAttrib(xdpclass, "ParameterSize", int)
            rp.Encoding      = _getAttrib(xdpclass, "DataFormatType")
            if rp.Encoding == "COD":
                getCodedSet(rp, xdp, xdpclass)

            # determine ValidityCriteria
            rprec.ValidityCriteria = 'FRESH'
         
            
        def consistencyCheck(rp, path):
            msgLength = 0
            if path in ('CANMessage.DP', 'A429Word.DP', 'A429Word'):
                msgLength = rp.msg.Length
            else:
                msgLength = rp.msg.A653MsgLength
                
            if (rp.ByteOffsetDS + rp.ByteSizeDS) > msgLength:
                rp.status     = 'Ignore'
                rp.msg.status = 'Ignore'
                logger.nerror("RP Dataset size inconsistent with message size, skipped.", 
                              DS=rp.DsName, DSsize=rp.ByteSizeDS, 
                              Msg=rp.msg.Message, MsgSize=msgLength)
            
        #------ start function body -------------------------
        
        for rpreclist in self.rplist.values():
            for rprec in rpreclist:
                # initialize all attributes to none
                rprec.LruName         = ''
                rprec.MsgName         = ''
                rprec.nesting         = ''
                rprec.DsName          = ''
                rprec.SigName         = ''
                rprec.ValidityCriteria = ''
                rprec.ByteOffsetFSB   = ''
                rprec.ByteOffsetDS    = ''
                rprec.ByteSizeDS      = ''
                rprec.BitOffset       = ''
                rprec.BitSize         = ''
                rprec.LsbValue        = 'N/A'
                rprec.Encoding        = ''
                rprec.MinValue        = 'N/A'
                rprec.MaxValue        = 'N/A'
                rprec.Multiplier      = 'N/A'
                rprec.Units           = ''
                rprec.ZeroState       = 'N/A'
                rprec.OneState        = 'N/A'
                rprec.CodedSet        = 'N/A'
                rprec.BusType         = ''
                rprec.Comment         = ''
                
                if not rprec.dp:
                    # no further processing is possible
                    continue

                # set attributes independant from RP Type
                rprec.LruName         = rprec.msg.TxLru
                rprec.PortName        = rprec.msg.TxPort
                rprec.MsgName         = rprec.msg.Message
                rprec.MessageRef      = rprec.msg.UniqueKey
                rprec.nesting         = _getDSPath(rprec.dp, rprec.msg.msgtype)
                
                xdp                   = rprec.dp
                xdpclass              = rprec.dpclass
                path                  = rprec.nesting 
                
                rprec.Units           = xdpclass.a.get("Units", "")
  
                if path == 'A664Message.DS.DP':
                    getDPDSAttrib(rprec, xdp, xdp.parent, xdpclass, xdpclass.parent) 
                elif path == 'A664Message.DS.A429Word.DP':
                    getDPDSAttribA429Sig(rprec, xdp, xdp.parent.parent, xdpclass, xdpclass.parent.parent)
                elif path == 'A664Message.DS.A429Word':
                    getDPDSAttribA429Word(rprec, xdp, xdp.parent, xdpclass, xdpclass.parent)
                elif path == 'A664Message.DS.CANMessage.DP':
                    getDPDSAttrib(rprec, xdp, xdp.parent.parent, xdpclass, xdpclass.parent.parent)
                elif path == 'A664Message.DS.CANMessage.A429Word.DP':
                    getDPDSAttribA429Sig(rprec, xdp, xdp.parent.parent.parent, xdpclass, xdpclass.parent.parent.parent)
                elif path == 'CANMessage.DP':
                    getCANDPAttrib(rprec, xdp, xdpclass)
                elif path == 'A429Word.DP':
                    getA429DPAttribSig(rprec, xdp, xdpclass)
                elif path == 'A429Word':
                    getA429DPAttribWord(rprec, xdp, xdpclass)
                else:
                    logger.nerror("Unsupported signal nesting [%s]" % path, RP=rprec.rpName)
                    
                consistencyCheck(rprec,path)
    
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    def consistencyCheckDPs(self):
        for dp in self.dplist.values():
            msgLength = None
            if dp.msg.msgtype == "CANMessage":
                msgLength = dp.msg.Length
            elif dp.msg.msgtype == "A429Word":
                msgLength = dp.msg.Length
            else:
                msgLength = dp.msg.A653MsgLength
                
            if(dp.ByteSizeDS == None) or (dp.ByteOffsetDS == None) or (msgLength == None):
                dp.status     = 'Ignore'
                dp.msg.status = 'Ignore'
                logger.nerror("DP Dataset size inconsistent with message size, skipped.", 
                              DS=dp.DsName)
            if(type(dp.ByteSizeDS)==tuple):
                dp.ByteSizeDS = dp.ByteSizeDS[0]

            if (dp.ByteOffsetDS + dp.ByteSizeDS) > msgLength:
                dp.status     = 'Ignore'
                dp.msg.status = 'Ignore'
                logger.nerror("DP Dataset size inconsistent with message size, skipped.", 
                              DS=dp.DsName, DSsize=dp.ByteSizeDS, 
                              Msg=dp.msg.Message, MsgSize=msgLength)

    def processFunctionDPs(self, hfnamelist):    
        '''
        Traverse hosted function/application and create a list of DPs with associated information
        '''

        def processDP(hfname, xdp, xpath, xds, xmsg, msgtype, xport): 
            '''
            process one DP, either directly below DS or inside a A429Word or CAN Message
            '''
            # gather the results in a Bunch
            xdpclass  = self.xindex[xdp.a.GuidDef]
            xmsgclass = self.xindex[xmsg.a.GuidDef]
            xdsclass  = self.xindex[xds.a.GuidDef]

            # link to message object
            if xmsg.a.Guid in self.txMessagelist:
                msgrec = self.txMessagelist[xmsg.a.Guid]
            else:
                msgrec = Bunch(msgtype=msgtype, txmsg=xmsg, txmsgclass=xmsgclass, rxport=None)
                self.txMessagelist[xmsg.a.Guid] = msgrec
                            
            signame = xdp.a.Name
            for o in xpath:
                signame = o.a.Name + '.' + signame
            
            dprec = Bunch(
                status          = 'Initial',
                BusType         = '',
                dpName          = signame, 
                dpclass         = xdpclass,
                msg             = msgrec,
                LruName         = hfname,
                DsName          = xds.a.Name,
                MsgName         = xmsg.a.Name,
                PortName        = xport.a.Name,
                ValidityCriteria= "",
                ByteOffsetFSB   = int(0),
                ByteOffsetDS    = int(0),
                ByteSizeDS      = int(0),
                BitOffset       = _getAttrib(xdpclass,  "BitOffsetWithinDS", int),
                BitSize         = _getAttrib(xdpclass,  "ParameterSize", int),
                Encoding        = _getAttrib(xdpclass,  "DataFormatType"),
                Multiplier      = 'N/A' ,
                LsbValue        = 'N/A' ,
                CodedSet        = 'N/A',
                ZeroState       = 'N/A',
                OneState        = 'N/A',
                Units           = xdpclass.a.get("Units", ""),		# don't issue warning, defaults to empty
                Consumer        = "",
                Comment         = ""
            )
            
            if dprec.Encoding == "A429_SSM_BNR":
                dprec.CodedSet = "0=No Data,\n1=No Computed Data,\n2=Test,\n3=Normal Operation"
                dprec.MinValue = 0
                dprec.MaxValue = 3
            elif dprec.Encoding == "A429_SSM_BCD":
                dprec.CodedSet = "0=Normal Operation,\n1=No Computed Data,\n2=Test,\n3=Normal Operation"
                dprec.MinValue = 0
                dprec.MaxValue = 3
            elif dprec.Encoding == "A429_SSM_DIS":
                dprec.CodedSet = "0=Normal Operation,\n1=No Computed Data,\n2=Test,\n3=No Data"
                dprec.MinValue = 0
                dprec.MaxValue = 3
            elif dprec.Encoding == "A664_FSB":
                dprec.CodedSet = "0=No Data,\n3=Normal Operation,\n12=Functional Test,\n48= Computed Data"
                dprec.MinValue = 0
                dprec.MaxValue = 3
            elif dprec.Encoding in ("COD", "A429SDI", "A429_SSM_CUSTOM"):
                codeset = _getAttrib(xdpclass, "CodedSet")
                if codeset:
                    dprec.CodedSet = codeset.replace(";", ",\n")
                    dprec.MinValue, dprec.MaxValue = _getCodedSetMinMax(codeset)
                else:
                    dprec.CodedSet = "TBD"
                    dprec.MaxValue = "TBD"
                    dprec.MinValue = "TBD"
            elif dprec.Encoding in ("DIS", "BOOL"):
                dprec.ZeroState = xdpclass.a.get("ZeroState", "TBD")
                dprec.OneState  = xdpclass.a.get("OneState", "TBD")
                dprec.MaxValue = "N/A"
                dprec.MinValue = "N/A"
            elif dprec.Encoding in IcdProcessor.RANGED_ENCODINGS:
                if dprec.Encoding in ("FLOAT", "BCD"):
                    dprec.MaxValue = _getAttrib(xdpclass,  "FuncRngMax", float, default="TBD", reportMissingValue=False)
                    dprec.MinValue = _getAttrib(xdpclass,  "FuncRngMin", float, default="TBD", reportMissingValue=False)
                else:
                    dprec.MaxValue = _getAttrib(xdpclass,  "FuncRngMax", int, default="TBD", reportMissingValue=False)
                    dprec.MinValue = _getAttrib(xdpclass,  "FuncRngMin", int, default="TBD", reportMissingValue=False)
                if dprec.MinValue == "TBD" or dprec.MaxValue == "TBD":
                    logger.nerror("Missing attribute FuncRngMin and/or FuncRngMax",
                              TYPE=xdpclass.tag, NAME=xdpclass.a.Name, FILE=xdpclass.filename)
                
            if dprec.Encoding in ("BNR", "UBNR"):
                dprec.LsbValue  = _getAttrib(xdpclass, "LsbRes", float)
            elif dprec.Encoding in ("SINT", "UINT"):
                dprec.LsbValue  = 1
                
            if dprec.Encoding == "BCD":
                dprec.Multiplier  = _getAttrib(xdpclass, "Multiplier", float, default="TBD", reportMissingValue=False)
                if dprec.Multiplier == "TBD":
                    dprec.Multiplier  = _getAttrib(xdpclass, "LsbRes", float, default="TBD", reportMissingValue=False)
                    if dprec.Multiplier == "TBD":
                        logger.nerror("Missing both attributes Multiplier and LsbRes for BCD Signal",
                              TYPE=xdpclass.tag, NAME=xdpclass.a.Name, FILE=xdpclass.filename)
                        

            dprec.UniqueName      = ".".join((dprec.LruName, dprec.PortName, dprec.MsgName, dprec.DsName, dprec.dpName))
            dprec.MessageRef      = "::".join((dprec.LruName, dprec.PortName, dprec.MsgName))

            if msgtype == "A664Message":
                dprec.ByteOffsetDS      = _getAttrib(xdsclass, "ByteOffsetWithinMsg", int)
                dprec.ByteSizeDS        = _getAttrib(xdsclass, "DataSetSize", int),
                dprec.BusType           = "A664"

                if xdsclass.a.DsDataProtocolType != 'A664_FSS' and dprec.ByteOffsetDS != 0:
                    dprec.ByteOffsetFSB = _getAttrib(xdsclass, "ByteOffsetFSF", int, default="TBD")
                    dprec.ValidityCriteria = "FSB"
                else:
                    dprec.ByteOffsetFSB = "N/A"
                    
                if xpath and xpath[0].tag == "A429Word":
                    dprec.ValidityCriteria += ',' + _getSSMType(self.xindex[xpath[0].a.GuidDef])
                        

            elif msgtype == "CANMessage":
                dprec.ByteSizeDS       = _getAttrib(xmsgclass, "MessageSize", int)
                dprec.Validity         = ''
                dprec.BusType          = "A825"

            elif msgtype == "A429Word":
                dprec.Validity         = _getSSMType(self.xindex[xpath[0].a.GuidDef])
                dprec.ByteOffsetDS     = int(0)
                dprec.ByteSizeDS       = int(4)
                dprec.BusType          = "A429"
                
                if xdpclass.a.DataFormatType == "A429OCTLBL":
                    try:
                        msgrec.Label = xdpclass.a.Label
                    except:
                        logger.nerror("Can't extract Label from [%s]" % dprec.UniqueName)
                        msgrec.Label = "TBD" 
                        
                if xdpclass.a.DataFormatType == "A429SDI":
                    try:
                        msgrec.SDI = _getCodedSetConst(xdp.a.CodedSet)
                    except:
                        logger.nerror("Can't extract SDI from [%s]" % dprec.UniqueName)
                        msgrec.SDI = "TBD" 


            if dprec.UniqueName in self.dplist:
                logger.nerror("Duplicate DP name [%s]" % dprec.UniqueName)
            else:
                self.dplist[dprec.UniqueName] = dprec
            
            consumerlist = self.pubrefxref[xdp.a.Guid]
            # also add those referencing the parent (i.e. the inclosing A429Word)
            consumerlist += self.pubrefxref[xdp.parent.a.Guid] 
            sep = ''
            for consumer in consumerlist:
                dprec.Consumer += sep + consumer[0].a.Name
                sep = ','
                
        
        #------- start of function -------------------------------
        functypes = ("HostedFunction", "A653ApplicationComponent")
        porttypes = ("HFSamplingPort", "HFQueuingPort", "A653SamplingPort", "A653QueuingPort", "CANPort", "A429Port")
        
        for functype in functypes:
            for xha in self.xroot.e.get(functype, []):
                if xha.a.Name in hfnamelist:
                    hfname = xha.a.Name
                    for porttype in porttypes:
                        for xport in xha.e.get(porttype, []):
                            for xmsg in xport.e.get('A664Message', []):
                                for xds in xmsg.e.get('DS', []):
                                    for xdp in xds.e.get('DP', []):
                                        processDP(hfname, xdp, (), xds, xmsg, "A664Message", xport)
                                    for xa4 in xds.e.get('A429Word', []):
                                        for xdp in xa4.e.get('DP', []):
                                            processDP(hfname, xdp, (xa4, ), xds, xmsg, "A664Message", xport)
                                    for xcanmsg in xds.e.get('CANMessage', []):
                                        for xdp in xcanmsg.e.get('DP', []):
                                            processDP(hfname, xdp, (xcanmsg, ), xds, xmsg, "A664Message", xport)
                                        for xa4 in xcanmsg.e.get('A429Word', []):
                                            for xdp in xa4.e.get('DP', []):
                                                processDP(hfname, xdp, (xa4, xcanmsg), xds, xmsg, "A664Message", xport)
                            for xcanmsg in xport.e.get('CANMessage', []):
                                for xdp in xcanmsg.e.get('DP', []):
                                    processDP(hfname, xdp, (), xcanmsg, xcanmsg, "CANMessage", xport)
                            for xa4c in xport.e.get('A429Channel', []):
                                for xa4w in xa4c.e.get('A429Word', []):
                                    for xdp in xa4w.e.get('DP', []):
                                        processDP(hfname, xdp, (xa4w,), xa4w, xa4w, "A429Word", xport) 
                               
                       
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------               

    def gatherRxMessageDetails(self):
        for msg in self.rxMessagelist.values():
            if msg.msgtype == "A664Message":
                self.gatherA664RxMessageDetails(msg)
            elif msg.msgtype == "CANMessage":
                self.gatherA825RxMessageDetails(msg)
            elif msg.msgtype == "A429Word":
                self.gatherA429RxMessageDetails(msg)


    def gatherA664RxMessageDetails(self, msg):
        '''
        Fill the details needed by the XLS table
        - TxLru           HF/HA name used (together with msg name) as key to match from the signal tab. 
        - Message         Message name used (together with lru name) as key to match from the signal tab. 
        - Rate            Transmit / Receive rate: used to determine freshness and for test bench configuration
        - Port ID         Port ID of receiving port, used to configure the APEX ports
        - Vlid            Test system configuration only
        - SubVl           Test system configuration only
        - BAG             Test system configuration only
        - MTU             Test system configuration only
        - Source MAC      Test system configuration only
        - Source IP       Test system configuration only
        - Source UDP      Test system configuration only
        - EdeEnabled      Test system configuration only
        - Source EDE ID   Test system configuration only
        - Destination IP  Test system configuration only
        - Destination UDP Test system configuration only
        - Length          Test system configuration only
        - QueueLength     Used for APEX port configuration system configuration only
        - Type:           Port Type or the receiving port (Queuing/Sampling)

        '''

        def getIpAddrType(vl, rxcomport):
            txport = vl.rx2txport[rxcomport.a.Name]
            return txport.a.IPDestAddrFormat

        def getMACAddress(lru):
            hw = self.hardwarexref.get(txlru.a.Hardware)
            if hw:
                physport = hw.get('A')
                if physport:
                    return physport.a.get("MACAddress", "")
            return ""

        txmsg               = msg.txmsg
        txmsgclass          = msg.txmsgclass
        txport              = msg.txmsg.parent
        txportclass         = txmsgclass.parent
        txlru               = _getTopNode(txport)
        rxport              = msg.rxport[0]
        rxportclass         = self.getClass(rxport)
        
        rxlru               = _getTopNode(rxport)

        if rxport.tag.endswith("SamplingPort"):
            rxtype = "SAMPLING"
        else:
            rxtype = "QUEUEING"
        
        if rxport.tag.endswith("QueuingPort"):
            msg.PortQueueLength = _getAttrib(rxportclass, "QueueLength", int, default=1)
        else:
            msg.PortQueueLength = 1

        msg.TxLru            = txlru.a.Name
        msg.TxPort           = txport.a.Name
        msg.Message          = txmsg.a.Name
        msg.UniqueKey        =  msg.TxLru + "::" + msg.TxPort + "::" + msg.Message
        msg.ProtocolType     = "PROTOCOL"
        protocolType         = _getAttrib(txmsgclass, "MsgDataProtocolType")

        if protocolType in IcdProcessor.PARAMETRIC_TYPES:
            msg.ProtocolType = "PARAMETRIC"        


        msg.A653MsgLength    = _getAttrib(txmsgclass, "MessageOverhead", int) + \
                               _getAttrib(txmsgclass, "MessageSize", int)
        msg.A664MsgMaxLength = _getAttrib(txmsgclass, "MessageSize", int)
        msg.TxInterval       = _getAttrib(txmsgclass, "TransmissionIntervalMinimum", float)
        msg.Networks         = _getAttrib(txportclass, "Networks")
        msg.TxRefreshPeriod  = _getAttrib(txportclass, "RefreshPeriod", float,
                                          reportMissingValue = txport.tag.endswith("SamplingPort"))
        msg.RxSamplePeriod   = _getAttrib(rxportclass, "SamplePeriod",  float)
        
        #If a refresh period is defined for the message, use it
        msg.A653PortRefreshPeriod = _getAttrib(rxportclass, "RefreshPeriod", float,
                                               default=msg.TxInterval * 3,
                                               reportMissingValue=rxportclass.tag.endswith("SamplingPort"))
        if msg.A653PortRefreshPeriod == None:
            #if not, apply the default IDU logic: RefreshRate = 3x Message emission rate
            msg.A653PortRefreshPeriod = msg.TxInterval * 3

        # value used for Validation and Invalidation Confirmation default
        msg.MaxAge           = 3 * max(msg.TxRefreshPeriod, msg.RxSamplePeriod)

        msg.PortType         = rxtype
        msg.Vlid             = _getAttrib(txmsg, 'VLID', int)
        msg.SubVl            = _getAttrib(txmsg, 'SubVLID', int,
                                          reportMissingValue = (msg.Vlid is not None),
                                          reportBadValue = (msg.Vlid is not None))
                           
        msg.RxComPortID       = None
        msg.A653PortName      = None
        msg.BAG               = None
        msg.MTU               = None
        msg.SourceMAC         = None
        msg.SourceIP          = None
        msg.SourceUDP         = None
        msg.DestIP            = None
        msg.DestUDP           = None
        msg.status            = "Initial"
        msg.CrcOffset, msg.CrcFsbOffset, msg.FcOffset, msg.FcFsbOffset = getApplicationCRCandFCoffset(txmsgclass)

        if msg.Vlid:
            vl = self.vlxref.get(msg.Vlid)
            if vl:
                rxcomport       = vl.rxports.get(rxlru.a.Name + '.' + rxport.a.Name)
                if not rxcomport:
                    logger.nerror("No RX COM Port found", HF=rxlru.a.Name, PORT=rxport.a.Name)
                else:
                    if self.merged: 
                        # this can happen only in merge mode
                        # in this case we set port id to 0 and as portname we build a comma separated list
                        # of names consisting of lruname and portname
                        
                        portNames = []

                        for port in msg.rxport:
                            lru = _getTopNode(port)
                            portNames.append(lru.a.Name + "." + port.a.Name)
                        # transform into comma separated string
                        msg.A653PortName = ",".join(portNames)                      
                        msg.RxComPortID  = 0
                    else:
                        msg.A653PortName  = msg.rxport[0].a.Name
                        msg.RxComPortID   = _getAttrib(rxcomport, "ID", int)
                        
                    msg.DestUDP     = _getAttrib(rxcomport, "UdpDstId", int)

                txcomport       = vl.txports.get(txlru.a.Name + '.' + txport.a.Name)
                if not txcomport:
                    logger.nerror("No TX COM Port found", HF=txlru.a.Name, PORT=txport.a.Name)
                else:
                    msg.SourceUDP   = _getAttrib(txcomport, "UdpSrcId", int)
                    msg.EdeSourceID = _getAttrib(txcomport, "ID", int)

                msg.SourceMAC   = getMACAddress(txlru)
                
                msg.SourceIP    = _getAttrib(txlru, 'IpAddress', default='10.0.0.1', 
                                             reportMissingValue = (txlru.tag != "RemoteGateway"))
                if txcomport.a.IPDestAddrFormat == "UNICAST":
                    msg.DestIP      = _getAttrib(rxlru, 'IpAddress')
                else:
                    msg.DestIP      = _makeMulticastIpAddr(msg.Vlid)
                msg.BAG         = _getAttrib(vl.xvl, "BAG", float)
                msg.MTU         = _getAttrib(vl.xvl, "MTU", int)
                msg.EdeEnabled  = _getAttrib(vl.xvl, 'EdeEnable', bool)
            else:
                logger.nerror("VL not found", VLID=msg.Vlid, MSG=txmsg.a.Name)

    def gatherA825RxMessageDetails(self, msg):
        '''
        Fill the details needed by the XLS table
        - Lru             HF/HA name used (together with msg name) as key to match from the signal tab. 
        - Message         Message name used (together with lru name) as key to match from the signal tab. 
        - Rate            Transmit / Receive rate: used to determine freshness and for test bench configuration
        - Length          Test system configuration only
        - CanMsgID        CanID of message
        - PhysPort        Physical port the message is received on
        '''

        txmsg               = msg.txmsg
        txmsgclass          = msg.txmsgclass
        txport              = msg.txmsg.parent
        txportclass         = msg.txmsgclass.parent
        txlru               = _getTopNode(txport)
        rxport              = msg.rxport[0]
        rxportclass         = self.getClass(rxport)

        msg.TxLru           = txlru.a.Name
        msg.TxPort          = txport.a.Name
        msg.Message         = txmsg.a.Name
        msg.Length          = _getAttrib(txmsgclass , "MessageSize", int)

        msg.TxInterval      = _getAttrib(txmsgclass,  "TransmissionIntervalMinimum", float)
        msg.TxRefreshPeriod = _getAttrib(txportclass, "RefreshPeriod", float, 0)
        msg.RxSamplePeriod  = _getAttrib(rxportclass, "SamplePeriod", float, 0)

        msg.MaxAge        = 3 * max(msg.TxRefreshPeriod, msg.RxSamplePeriod)
        
        msg.UniqueKey     = msg.TxLru + "::" + msg.TxPort + "::" + msg.Message
        
        msg.status        = "Initial"
        
        txid = _getAttrib(txport, "MessageID")
        rxid = _getAttrib(rxport, "MessageID")
        if txid != rxid:
            logger.nerror("CAN Message ID mismatch between TX and RX", TXPORT=txport.a.Name, RXPORT=rxport.a.Name)
       
        msg.CanMsgID  = rxid
        msg.PhysPort  = _getAttrib(rxport, "Physical")

    def gatherA429RxMessageDetails(self, msg):
        '''
        Fill the details needed by the XLS table
        - Lru             HF/HA name used (together with msg name) as key to match from the signal tab. 
        - Message         Label name used (together with lru name) as key to match from the signal tab. 
        - Rate            Transmit / Receive rate: used to determine freshness and for test bench configuration
        - Label           Label Number of message
        - PhysPort        Physical port the message is received on
        '''

        txmsg               = msg.txmsg
        txport              = msg.txmsg.parent.parent
        txchanclass         = msg.txmsgclass.parent
        txportclass         = msg.txmsgclass.parent.parent

        txlru               = _getTopNode(txport)
        rxport              = msg.rxport[0]
        rxportclass         = self.getClass(rxport)

        msg.TxLru           = txlru.a.Name
        msg.TxPort          = txport.a.Name
        msg.Message         = txmsg.a.Name
        msg.Length          = int(4) # allways 32 bit

        msg.RxSamplePeriod  = _getAttrib(rxportclass,  "SamplePeriod", float, 0)
        msg.TxRefreshPeriod = _getAttrib(txportclass,  "RefreshPeriod", float, 0)
        msg.TxInterval      = _getAttrib(txchanclass,  "TransmissionIntervalMinimum", float, 0)

        msg.MaxAge          = 3 * max(msg.RxSamplePeriod, msg.TxRefreshPeriod)
      
        msg.PhysPort        = _getAttrib(rxport, "Physical")
        msg.UniqueKey       = msg.TxLru + "::" + msg.TxPort + "::" + msg.Message
        msg.status          = "Initial"

    # ----------------------------------------------------------------------               
    #    Transmit Message Stuff
    # ----------------------------------------------------------------------               

    def gatherTxMessageDetails(self):
        for msg in self.txMessagelist.values():
            if msg.msgtype == "A664Message":
                self.gatherA664TxMessageDetails(msg)
            elif msg.msgtype == "CANMessage":
                self.gatherA825TxMessageDetails(msg)
            elif msg.msgtype == "A429Word":
                self.gatherA429TxMessageDetails(msg)

    def gatherA664TxMessageDetails(self, msg):
        '''
        Fill the details needed by the XLS table
        - TxLru            HF/HA name used (together with msg name) as key to match from the signal tab. 
        - Message          Message name used (together with lru name) as key to match from the signal tab.
        - ProtocolType     Message protocol type (Parametric or Protocol data)
        - A664MsgMaxLength Length of the transmitted message
        - A653MsgLength    Size of the message in the A653 Port
        - PortType:        Port Type or the receiving port (Queuing/Sampling)
        - PortQueueLength  Used for APEX port configuration system configuration only
        - TxInterval       Transmit rate: used to determine freshness and for test bench configuration
        - TxComPortID      Port ID of receiving port, used to configure the APEX ports
        - A653PortName     Name of the A653 Port
        - Vlid            Test system configuration only
        - SubVl           Test system configuration only
        - BAG             Test system configuration only
        - MTU             Test system configuration only
        - Networks        Test system configuration only
        - SourceMAC       Test system configuration only
        - SourceIP        Test system configuration only
        - SourceUDP       Test system configuration only
        - EdeEnabled      Test system configuration only
        - EdeSourceId     Test system configuration only
        - DestIP          Test system configuration only
        - DestUDP         Test system configuration only
        - UniqueKey       Used to uniquely identify the message

        '''

        def getMACAddress(lru):
            '''
            Find the mac Address of an LRU
            '''
            hw = self.hardwarexref.get(txlru.a.Hardware)
            if hw:
                physport = hw.get('A')
                if physport:
                    return physport.a.get("MACAddress", "")
            return ""

        def findDestinationUDP(vl, txcomport):
            '''
            Find the destination UDP Address for a transmit port
            '''
            rxports = vl.tx2rxports[txcomport.a.Name]
            udps = [p.a.UdpDstId for p in rxports]
            udps = set(udps)
            if len(udps) == 1:
                return int(list(udps)[0])
            elif len(udps) > 1:
                logger.nerror("Destination UDP not unique", VLID=msg.Vlid, MSG=txmsg.a.Name)
                return None
            else:
                logger.nerror("No Destination UDP address found", VLID=msg.Vlid, MSG=txmsg.a.Name)
                return None


        def findUnicastIpAddr(vl, txcomport):
            '''
            Find the unicast IP Address for a transmit port
            '''
            rxports = vl.tx2rxports[txcomport.a.Name]
            ipaddrset = set()

            # traverse receive ports receiving from the tx port
            for rxp in rxports:
                # traverse application ports linked to the receive com port
                for pref in rxp.e.Port_Ref:
                    # get corresponding application (HF or HA) from the Xref build during initialization
                    # extract the IP address and add it to our result set.
                    x = self.appportXref.get(pref.a.Name)
                    if x:
                        hf = x[0]
                        ipaddr = hf.a.get("IpAddress")
                        ipaddrset.add(ipaddr)
                    else:
                        logger.nerror("No Destination IP address found", VLID=msg.Vlid, MSG=txmsg.a.Name)

            # Since we are looking for a UNICAST address, we should find exactly one
            if len(ipaddrset) == 1:
                return list(ipaddrset)[0]
            elif len(ipaddrset) > 1:
                logger.nerror("Destination IP Address not unique", VLID=msg.Vlid, MSG=txmsg.a.Name)
                return None
            else:
                logger.nerror("No Destination IP Address found", VLID=msg.Vlid, MSG=txmsg.a.Name)
                return None

        
        # -------------------------------------------------------------------------------------------
        # Start of function
        # -------------------------------------------------------------------------------------------
        txmsg               = msg.txmsg
        txmsgclass          = msg.txmsgclass
        txport              = msg.txmsg.parent
        txportclass         = txmsgclass.parent
        txlru               = _getTopNode(txport)

        if txport.tag.endswith("SamplingPort"):
            txtype = "SAMPLING"
            msg.PortQueueLength = 1
        else:
            txtype = "QUEUEING"
            msg.PortQueueLength = _getAttrib(txportclass, "QueueLength", int, default=1)

        msg.TxLru            = txlru.a.Name
        msg.TxPort           = txport.a.Name
        msg.Message          = txmsg.a.Name
        msg.UniqueKey        = msg.TxLru + "::" + msg.TxPort + "::" + msg.Message

        msg.ProtocolType     = "PROTOCOL"

        protocolType         = _getAttrib(txmsgclass, "MsgDataProtocolType")
        if protocolType in IcdProcessor.PARAMETRIC_TYPES:
            msg.ProtocolType = "PARAMETRIC"

        msg.A653MsgLength    = _getAttrib(txmsgclass, "MessageOverhead",int) + \
                               _getAttrib(txmsgclass, "MessageSize",    int)

        msg.A664MsgMaxLength = _getAttrib(txmsgclass, "MessageSize",    int)            

        msg.TxInterval       = _getAttrib(txmsgclass,  "TransmissionIntervalMinimum", float)
        msg.TxRefreshPeriod  = _getAttrib(txportclass, "RefreshPeriod", float, 
                                          reportMissingValue = (txtype == "SAMPLING"))

        msg.Vlid             = _getAttrib(txmsg,       "VLID",          int)
        msg.SubVl            = _getAttrib(txmsg,       "SubVLID",       int, 
                                          reportMissingValue = (msg.Vlid is not None),
                                          reportBadValue     = (msg.Vlid is not None))
        msg.Networks         = _getAttrib(txportclass, "Networks")
        
        msg.PortType         = txtype                
        msg.TxComPortID      = None
        msg.A653PortName     = None
        msg.BAG              = None
        msg.MTU              = None
        msg.SourceMAC        = None
        msg.SourceIP         = None
        msg.SourceUDP        = None
        msg.DestIP           = None
        msg.DestUDP          = None
        msg.status           = "Initial"
        msg.CrcOffset, msg.CrcFsbOffset, msg.FcOffset, msg.FcFsbOffset = getApplicationCRCandFCoffset(txmsgclass)

        if msg.Vlid:
            vl = self.vlxref.get(msg.Vlid)
            if vl:
                txcomport       = vl.txports.get(txlru.a.Name + '.' + txport.a.Name)
                if not txcomport:
                    logger.nerror("No TX COM Port found", HF=txlru.a.Name, PORT=txport.a.Name)
                else:
                    msg.TxComPortID  = _getAttrib(txcomport, "ID", int)
                    if self.merged:
                        msg.A653PortName = txlru.a.Name + '.' + txport.a.Name
                    else:
                        msg.A653PortName = txport.a.Name
                    msg.SourceUDP    = _getAttrib(txcomport, "UdpSrcId", int)
                    msg.EdeSourceID  = _getAttrib(txcomport, "ID", int)
                    
                    # find destination UDP
                    msg.DestUDP = findDestinationUDP(vl, txcomport)

                    # find destination IP
                    if txcomport.a.IPDestAddrFormat == 'MULTICAST':
                        msg.DestIP = _makeMulticastIpAddr(msg.Vlid)
                    else:
                        msg.DestIP = findUnicastIpAddr(vl, txcomport)
                        

                msg.SourceMAC   = getMACAddress(txlru)
                msg.SourceIP    = _getAttrib(txlru,  "IpAddress", default="10.0.0.1",
                                             reportMissingValue = (txlru.tag != "RemoteGateway"))
                msg.BAG         = _getAttrib(vl.xvl, "BAG",         float)
                msg.MTU         = _getAttrib(vl.xvl, "MTU",         float)
                msg.EdeEnabled  = _getAttrib(vl.xvl, "EdeEnable",   bool)
            else:
                logger.nerror("VL not found", VLID=msg.Vlid, MSG=txmsg.a.Name)
            
    # ----------------------------------------------------------------------
    def gatherA825TxMessageDetails(self, msg):
        '''
            Fill in one A825 (CAN) Message Object
        '''
        # -------------------------------------------------------------------------------------------
        # Start of function
        # -------------------------------------------------------------------------------------------
        txmsg               = msg.txmsg
        txmsgclass          = msg.txmsgclass

        txport              = txmsg.parent
        txportclass         = txmsgclass.parent
        txlru               = _getTopNode(txport)

        msg.TxRefreshPeriod = _getAttrib(txportclass, "RefreshPeriod", int, default=0)
        msg.TxInterval      = _getAttrib(txmsgclass, "TransmissionIntervalMinimum")
        msg.QueueLength     = int(1)
        msg.PhysPort        = _getAttrib(txport, "Physical")
        msg.CanMsgID        = _getAttrib(txport, "MessageID")

        msg.TxLru           = txlru.a.Name
        msg.TxPort          = txport.a.Name
        msg.Message         = txmsg.a.Name
        msg.Length          = _getAttrib(txmsgclass, "MessageSize", int)
        msg.PortType        = "SAMPLING"
        msg.UniqueKey       = msg.TxLru + "::" + msg.TxPort + "::" + msg.Message
        msg.status          = "Initial"

    # ----------------------------------------------------------------------
    def gatherA429TxMessageDetails(self, msg):
        '''
            Fill in one A429  Message Object
        '''
        # -------------------------------------------------------------------------------------------
        # Start of function
        # -------------------------------------------------------------------------------------------
        txmsg                   = msg.txmsg
        txmsgclass              = msg.txmsgclass
        txchanclass             = msg.txmsgclass.parent

        txport                  = msg.txmsg.parent.parent
        txportclass             = txmsgclass.parent.parent
        txlru                   = _getTopNode(txport)

        msg.PhysPort            = _getAttrib(txport, "Physical")
        msg.TxRefreshPeriod     = _getAttrib(txportclass, "RefreshPeriod", int, default=0)
        msg.TxInterval          = _getAttrib(txchanclass, "TransmissionIntervalMinimum")
        msg.TxLru               = txlru.a.Name
        msg.TxPort              = txport.a.Name
        msg.Message             = txmsg.a.Name
        msg.Length              = int(4)
        msg.PortType            = "SAMPLING"                
        msg.QueueLength         = int(1)
        msg.UniqueKey           = msg.TxLru + "::" + msg.TxPort + "::" + msg.Message
        msg.status              = "Initial"

    # ----------------------------------------------------------------------
    # Build various cross reference dictionaries for fast access
    # ----------------------------------------------------------------------
    def makeVLxref(self):
        '''
        Create index for VLs: 
            lookup VL with all its RX and TX Ports by vlid 
        '''
        vls = self.xroot.e.VirtualLinks[0]
        for xvl in vls.e.VirtualLink:
            rxports     = dict()
            txports     = dict()
            tx2rxports   = defaultdict(list)

            try:
                vlid = int(xvl.a.get("ID"))
            except:
                logger.nerror("VL without ID", VLNAME=xvl.a.Name)
                continue
            
            for xrp in xvl.e.get("ComPortRx", []):
                for pref in xrp.e.Port_Ref:
                    key = pref.a.Name
                    rxports[key] = xrp
                for txref in xrp.e.TxPort_Ref:
                    key = txref.a.Name.split('.', 1)[1]
                    tx2rxports[key].append(xrp)

            for xtp in xvl.e.get("ComPortTx", []):
                for pref in xtp.e.Port_Ref:
                    key = pref.a.Name
                    txports[key] = xtp

            self.vlxref[vlid] = Bunch(xvl = xvl, rxports=rxports, txports=txports, tx2rxports=tx2rxports)
    
    # ----------------------------------------------------------------------
    def makeHardwareXref(self):
        '''
        Create index for Hardware: 
            lookup hardware by name with port dictionary indexed by port name
        '''
        def makePortDict(xlru):
            portdict = {}
            for porttype, portlist in xlru.e.items():
                if porttype.endswith("PhysPort"):
                    for port in portlist:
                        portdict[port.a.Name] = port
            return portdict
        
        self.hardwarexref = dict()
        for xlru in self.xroot.e.LRU + self.xroot.e.RIU:
            self.hardwarexref[xlru.a.Name] = makePortDict(xlru)
            
        for xccr in self.xroot.e.CCR:
            for xmod in xccr.e.GPM:
                self.hardwarexref[xccr.a.Name + '.' + xmod.a.Name] = makePortDict(xmod)

    # ----------------------------------------------------------------------
    def makeRpXref(self):
        '''
        Traverse hosted function/application and create an index RP->DP
        '''
        functypes = ("HostedFunction", "A653ApplicationComponent")
        porttypes = ("HFSamplingPort", "HFQueuingPort", "A653SamplingPort", "A653QueuingPort", "CANPort", "A429Port")
        
        for functype in functypes:
            for xha in self.xroot.e.get(functype, []):
                for porttype in porttypes:
                    for xport in xha.e.get(porttype, []):
                        for xrp in xport.e.get('RP', []):
                            for pubref in xrp.e.get("Pub_Ref", []):
                                self.pubrefxref[pubref.a.SrcGuid].append((xha, xport, xrp))
                                
        
    # ----------------------------------------------------------------------
    def makePortXref(self):
        '''
        Traverse hosted function/application and create an index Port Name -> Port
        '''
        functypes = ("HostedFunction", "A653ApplicationComponent")
        porttypes = ("HFSamplingPort", "HFQueuingPort", "A653SamplingPort", "A653QueuingPort", "CANPort", "A429Port")
        
        for functype in functypes:
            for xha in self.xroot.e.get(functype, []):
                for porttype in porttypes:
                    for xport in xha.e.get(porttype, []):
                        self.appportXref[xha.a.Name + '.' + xport.a.Name] = (xha, xport)


    # ----------------------------------------------------------------------
    # Format the output to Excel
    # ----------------------------------------------------------------------
    
    inSigColumns = (
        # header,                         value,                width
          ("Status",                      "status",             15),        
          ("BusType",                     "BusType",             8),
          ("RpName",                      "rpName",             40),
          ("Pubref",                      "PubrefName",         40),
          ("TxLru",                       "LruName",            25),
          ("TxPort",                      "PortName",           25),
          ("Message",                     "MsgName",            40),
          ("DataSet",                     "DsName",             40),
          ("Container",                   "Container",          40),          
          ("DpName",                      "SigName",            40),
          ("ValidityCriteria",            "ValidityCriteria",   15),
          ("FsbOffset",                   "ByteOffsetFSB",      10),
          ("DSOffset",                    "ByteOffsetDS",       10),
          ("DSSize",                      "ByteSizeDS",         10),
          ("ParameterType",               "Encoding",           15),
          ("BitOffsetWithinDS",           "BitOffset",          10),
          ("ParameterSize",               "BitSize",            10),
          ("LsbRes",                      "LsbValue",           10),
          ("Multiplier",                  "Multiplier",         10),
          ("PublisherFunctionalMinRange", "MinValue",           30),
          ("PublisherFunctionalMaxRange", "MaxValue",           30),
          ("CodedSet",                    "CodedSet",           30),
          ("ZeroState",                   "ZeroState",          15),
          ("OneState",                    "OneState",           15),
          ("Units",                       "Units",              15),
          ("Comment",                     None,                 10),
          ("Change History",              None,                 20),
          ("ICDFix",                      "icdFix",             10),
          ("MessageRef",                  "MessageRef",         65),
    )
    
    outSigColumns = (
        # header,                         value,                width
          ("Status",                      "status",             15),
          ("BusType",                     "BusType",             8),
          ("TxLru",                       "LruName",            25),
          ("TxPort",                      "PortName",           25),
          ("Message",                     "MsgName",            40),
          ("DataSet",                     "DsName",             40),
          ("DpName",                      "dpName",             40),
          ("ValidityCriteria",            "ValidityCriteria",   15),
          ("FsbOffset",                   "ByteOffsetFSB",      10),
          ("DSOffset",                    "ByteOffsetDS",       10),
          ("DSSize",                      "ByteSizeDS",         10),
          ("BitOffsetWithinDS",           "BitOffset",          10),
          ("ParameterType",               "Encoding",           15),
          ("ParameterSize",               "BitSize",            10),
          ("LsbRes",                      "LsbValue",           10),
          ("Multiplier",                  "Multiplier",         10),
          ("PublisherFunctionalMinRange", "MinValue",           30),
          ("PublisherFunctionalMaxRange", "MaxValue",           30),
          ("CodedSet",                    "CodedSet",           30),
          ("ZeroState",                   "ZeroState",          15),
          ("OneState",                    "OneState",           15),
          ("Units",                       "Units",              15),
          ("Comment",                     None,                 10),
          ("Change History",              None,                 20),
          ("ICDFix",                      "icdFix",             10),
          ("UniqueName",                  "UniqueName",         60),
          ("MessageRef",                  "MessageRef",         65),
    ) 
    
    msgRxAfdxColumns = (
         # header,                       value,                 width
          ("Status",                    "status",               15),
          ("TxLru",                     "TxLru",                25),
          ("TxPort",                    "TxPort",               25),
          ("Message",                   "Message",              40),
          ("ProtocolType",              "ProtocolType",         15),
          ("A664MsgMaxLength",          "A664MsgMaxLength",     20),
          ("A653MsgLength",             "A653MsgLength",        15),
          ("PortType",                  "PortType",             10),
          ("PortQueueLength",           "PortQueueLength",      10),
          ("TxInterval",                "TxInterval",           15),
          ("TxRefreshPeriod",           "TxRefreshPeriod",      15),
          ("RxSamplePeriod",            "RxSamplePeriod",       15),
          ("A653PortRefreshPeriod",     "A653PortRefreshPeriod",20),
          ("InvalidConfirmationTime",   "MaxAge",               20),
          ("ValidConfirmationTime",     "MaxAge",               20),
          ("RxComPortID",               "RxComPortID",          10),
          ("A653PortName",              "A653PortName",         40),
          ("Vlid",                      "Vlid",                 10),
          ("SubVl",                     "SubVl",                10),
          ("BAG",                       "BAG",                  10),
          ("MTU",                       "MTU",                  10),
          ("Networks",                  "Networks",             10),
          ("EdeEnabled",                "EdeEnabled",           12),
          ("EdeSourceId",               "EdeSourceID",          12),
          ("DestIP",                    "DestIP",               15),
          ("DestUDP",                   "DestUDP",              15),
          ("SourceMAC",                 "SourceMAC",            15),
          ("SourceIP",                  "SourceIP",             15),
          ("SourceUDP",                 "SourceUDP",            10),
          ("CrcOffset",                 "CrcOffset",            10),
          ("CrcFsbOffset",              "CrcFsbOffset",         10),
          ("FcOffset",                  "FcOffset",             10),
          ("FcFsbOffset",               "FcFsbOffset",          10),

          ("Comment",                   None,                   10),
          ("Change History",            None,                   20),
          ("ICDFix",                    None,                   10),
          ("UniqueKey",                 "UniqueKey",            65),
    )
    
    msgTxAfdxColumns = (
         # header,                      value,                  width
          ("Status",                    "status",               15),
          ("TxLru",                     "TxLru",                25),
          ("TxPort",                    "TxPort",               25),
          ("Message",                   "Message",              40),
          ("ProtocolType",              "ProtocolType",         15),
          ("A664MsgMaxLength",          "A664MsgMaxLength",     20),
          ("A653MsgLength",             "A653MsgLength",        15),
          ("PortType",                  "PortType",             10),
          ("PortQueueLength",           "PortQueueLength",      10),
          ("TxInterval",                "TxInterval",           15),
          ("TxRefreshPeriod",           "TxRefreshPeriod",      15),
          ("TxComPortID",               "TxComPortID",          10),
          ("A653PortName",              "A653PortName",         40),
          ("Vlid",                      "Vlid",                 10),
          ("SubVl",                     "SubVl",                10),
          ("BAG",                       "BAG",                  10),
          ("MTU",                       "MTU",                  10),
          ("Networks",                  "Networks",             10),
          ("EdeEnabled",                "EdeEnabled",           12),
          ("EdeSourceId",               "EdeSourceID",          12),
          ("DestIP",                    "DestIP",               15),
          ("DestUDP",                   "DestUDP",              15),
          ("SourceMAC",                 "SourceMAC",            15),
          ("SourceIP",                  "SourceIP",             15),
          ("SourceUDP",                 "SourceUDP",            10),
          ("CrcOffset",                 "CrcOffset",            10),
          ("CrcFsbOffset",              "CrcFsbOffset",         10),
          ("FcOffset",                  "FcOffset",             10),
          ("FcFsbOffset",               "FcFsbOffset",          10),
          ("Comment",                   None,                   10),
          ("Change History",            None,                   20),
          ("ICDFix",                    None,                   10),
          ("UniqueKey",                 "UniqueKey",            65),
    )

    msgRxCanColumns = (
          ("Status",                    "status",               15),
          ("TxLru",                     "TxLru",                25),
          ("TxPort",                    "TxPort",               25),
          ("Message",                   "Message",              30),
          ("A825MsgLength",             "Length",               25),
          ("TxInterval",                "TxInterval",           10),
          ("TxRefreshPeriod",           "TxRefreshPeriod",      15),
          ("RxSamplePeriod",            "RxSamplePeriod",       15),
          ("InvalidConfirmationTime",   "MaxAge",               20),
          ("ValidConfirmationTime",     "MaxAge",               20),
          ("CanMsgID",                  "CanMsgID",             10),
          ("PhysPort",                  "PhysPort",             20),
          ("Comment",                   None,                   10),
          ("Change History",            None,                   20),
          ("ICDFix",                    None,                   10),
          ("UniqueKey",                 "UniqueKey",            65),
    )
    
    msgTxCanColumns = (
          ("Status",                    "status",               15),
          ("TxLru",                     "TxLru",                25),
          ("TxPort",                    "TxPort",               25),
          ("Message",                   "Message",              30),
          ("A825MsgLength",             "Length",               25),
          ("TxInterval",                "TxInterval",           10),
          ("TxRefreshPeriod",           "TxRefreshPeriod",      10),
          ("CanMsgID",                  "CanMsgID",             10),
          ("PhysPort",                  "PhysPort",             20),
          ("Comment",                   None,                   10),
          ("Change History",            None,                   20),
          ("ICDFix",                    None,                   10),
          ("UniqueKey",                 "UniqueKey",            65),
    )    
    
    msgRxA429Columns = (
          ("Status",                    "status",               15),
          ("TxLru",                     "TxLru",                25),
          ("TxPort",                    "TxPort",               25),
          ("Message",                   "Message",              40),
          ("TxInterval",                "TxInterval",           15),
          ("TxRefreshPeriod",           "TxRefreshPeriod",      15),
          ("RxSamplePeriod",            "RxSamplePeriod",       15),
          ("InvalidConfirmationTime",   "MaxAge",               20),
          ("ValidConfirmationTime",     "MaxAge",               20),
          ("LabelID",                   "Label",                10),
          ("SDI",                       "SDI",                  6),
          ("PhysPort",                  "PhysPort",             20),
          ("Comment",                   None,                   10),
          ("Change History",            None,                   20),
          ("ICDFix",                    None,                   10),
          ("UniqueKey",                 "UniqueKey",            65),
    )
    
    msgTxA429Columns = (
          ("Status",                    "status",               15),
          ("TxLru",                     "TxLru",                25),
          ("TxPort",                    "TxPort",               25),
          ("Message",                   "Message",              40),
          ("TxInterval",                "TxInterval",           15),
          ("TxRefreshPeriod",           "TxRefreshPeriod",      15),
          ("LabelID",                   "Label",                10),
          ("SDI",                       "SDI",                  6),
          ("PhysPort",                  "PhysPort",             20),
          ("Comment",                   None,                   10),
          ("Change History",            None,                   20),
          ("ICDFix",                    None,                   10),
          ("UniqueKey",                 "UniqueKey",            65),
    )    
    
    def formatOutput(self, outputfn):

        def msgfilter(msglist, msgtype):
            return [m for m in msglist if m.msgtype == msgtype]
        
        # build final Input Signal List.

        inSignals = []
        for rpreclist in self.rplist.values():
            inSignals += rpreclist

        inSignals.sort(key=lambda sig: (sig.LruName, sig.MsgName, sig.ByteOffsetDS, sig.BitOffset))
        
        genExcelFile(outputfn, 
            (
                ("InputAfdxMessages", self.msgRxAfdxColumns, 
                    sorted(msgfilter(self.rxMessagelist.values(), "A664Message"), 
                           key=lambda msg: msg.UniqueKey)
                ),
                ("InputCanMessages", self.msgRxCanColumns, 
                    sorted(msgfilter(self.rxMessagelist.values(), "CANMessage"), 
                           key=lambda msg: msg.UniqueKey)
                ),
                ("InputA429Labels", self.msgRxA429Columns, 
                    sorted(msgfilter(self.rxMessagelist.values(), "A429Word"), 
                           key=lambda msg: msg.UniqueKey)
                ),
                ("InputSignals",  self.inSigColumns, inSignals),
                
                ("OutputAfdxMessages", self.msgTxAfdxColumns, 
                    sorted(msgfilter(self.txMessagelist.values(), "A664Message"), 
                           key=lambda msg: msg.UniqueKey)
                ),
                ("OutputCanMessages", self.msgTxCanColumns, 
                    sorted(msgfilter(self.txMessagelist.values(), "CANMessage"), 
                           key=lambda msg: msg.UniqueKey)
                ),
                ("OutputA429Labels", self.msgTxA429Columns, 
                    sorted(msgfilter(self.txMessagelist.values(), "A429Word"), 
                           key=lambda msg: msg.UniqueKey)
                ),
                ("OutputSignals",  self.outSigColumns, 
                    sorted(self.dplist.values(), 
                           key=lambda sig: (sig.LruName, sig.MsgName, sig.ByteOffsetDS, sig.BitOffset)
                    )
                ),
            )
        )

    def processHostedFunctions(self, hfnamelist, outfilename):
        self.reset()

        logger.ninfo("Constructing RP Index")
        logger.progress("Constructing RP Index", 3)
        self.processFunctionRPs(hfnamelist)
    
        logger.ninfo("Attaching Message Details")
        logger.progress("Attaching Message Details", 3)
        self.gatherRxMessageDetails()
    
        logger.ninfo("Attaching Signal Details")
        logger.progress("Attaching Signal Details", 1)
        self.gatherRxSignalDetails()
    
        self.processFunctionDPs(hfnamelist)
        self.gatherTxMessageDetails()
        self.consistencyCheckDPs()
    
        logger.progress("Formatting Output", 2)
        if outfilename == None:
            outfilename = '-'.join(hfnamelist) + '-icd.xlsx'
        self.formatOutput(outfilename)       
        
# END OF CLASS


def processIcd(sourcedirs, hfnamelist, exclude=None, outfilename="", merge=True):

    xroot = icdReadAll(sourcedirs, exclude=exclude)
    worker = IcdProcessor(xroot)

    logger.ninfo("Constructing VL Cross Index")
    logger.progress("Constructing VL Cross Index", 1)
    worker.makeVLxref()

    logger.ninfo("Constructing Hardware Cross Index")
    logger.progress("Constructing Hardware Cross Index", 1)
    worker.makeHardwareXref()
    worker.makeRpXref()
    worker.makePortXref()

    logger.ninfo("Constructing Gateway Cross Index")
    logger.progress("Constructing Gateway Cross Index", 5)
    worker.makeGatewayReverseMap()

    if merge:
        print("processing", hfnamelist)
        worker.processHostedFunctions(hfnamelist, outfilename)
    else:
        for hf in hfnamelist:
            print("processing", hf)
            worker.processHostedFunctions([hf], outfilename)

    

def usage():
    print("iomGenXls [options] hostedfunctions -- icdpathlist")
    print("   options:")
    print("     --merge")
    print("     --workdir=work directory")
    print("     --loglevel=<TRACE|INFO|WARN|ERROR>")
    print("     --logfile=<filename>")
    print("     --exclude=<path>")
    print("     --output=<path>")
    print("     --help")
    print("   If --merge option is given, output file name option (--output or -o) is mandatory. Without merge, it will be ignored")



def main():
    # options + arguments
    opts, args = getopt.getopt(sys.argv[1:], 'hpmw:o:', ['output=', 'workdir=', 'loglevel=', 'logfile=', 'exclude=', 'merge', 'help', 'progress', 'console'])
    print ('here\n')
    # get arguments
    if len(args) < 2:
        usage()
        sys.exit(1)
    
    # A -- separates the hfname list from the source dir list.

    hfnamelist = []
    sourcedirs = []
    part = 1
    for x in args:
        if x == "--":
            part = 2
        elif part == 1:
            hfnamelist.append(x)
        elif part == 2:
            sourcedirs.append(x) 
    
    if part == 1:
        # no --, so to be compatible first argument is HF, rest are directories
        sourcedirs = hfnamelist[1:]
        hfnamelist = hfnamelist[:1]
            
    loglevel = logger.ERROR
    exclude  = '*/Default Configurations*'
    workdir  = '.'
    logprogress = False
    logconsole  = True
    merge       = False
    outfn       = None
    logfile     = None

    loglevels = {
        'INFO'  : logger.INFO,
        'WARN'  : logger.WARN,
        'ERROR' : logger.ERROR,
        'TRACE' : logger.TRACE,
    }

    # parse options
    for o, a in opts:
        if o in ['-h', '--help']:
            usage()
            return -1
        if o in ('-m', '--merge'):
            merge = True
        elif o in [ '--output', '-o']:
            outfn = a
        elif o in [ '--loglevel']:
            loglevel = loglevels.get(a, logger.INFO)
        elif o in [ '--loglevel']:
            loglevel = loglevels.get(a, logger.INFO)
        elif o in [ '--logfile']:
            logfile = a
        elif o in [ '--exclude']:
            exclude = a
        elif o in ['-w', '--workdir']:
            workdir = a
        elif o in ['-p', '--progress']:
            logprogress = True
            logconsole = False
        elif o in ['-c', '--console']:
            logconsole = True
            logprogress = False
        else:
            usage()
            return -1

    if merge and not outfn:
        usage()
        return -1
        
    if outfn and not outfn.endswith('.xlsx'):
        outfn += '-icd.xlsx'

    if logfile  is None:
        if outfn:
            logfile = '%s-iomgen.log' % outfn.rsplit('.', 1)[0]
        else:
            logfile = '%s-iomgen.log' % hfnamelist[0]

    os.chdir(workdir)

    logger.setup(filename=logfile, level=loglevel, console=logconsole, progress=logprogress)
    logger.info("STARTING Import")
    print (sourcedirs)
    processIcd(sourcedirs, hfnamelist, exclude=exclude, outfilename=outfn, merge=merge)
    return 0

if __name__ == '__main__':
    sys.exit(main())