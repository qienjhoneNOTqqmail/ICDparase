#import ../Common/bunch

import imtXmlReader
import os
import sys
import getopt
sys.path.append("..")
from Common.bunch import Bunch
import Common.logger as logger
from compiler.ast import Node
from collections import defaultdict
import imtExcelRW

ATA = dict()

encodelist = []

HFHA = ['HostedFunction','A653ApplicationComponent']

A653portType=['A653QueuingPort','A653SamplingPort']
HFportType = ['HFSamplingPort','HFQueuingPort','CANPort','A429Port']

porttomsgtype={
               'A653QueuingPort':'A664Message',
               'A653SamplingPort':'A664Message',
               'HFSamplingPort':'A664Message',
               'HFQueuingPort':'A664Message',
               'CANPort':'CANMessage',
               'A429Port':'A429Word',
               'AnalogPort':'AnalogDiscreteParameter'}

MessagePath = ['CANPort.CANMessage.DP',
               'HFSamplingPort.A664Message.DS.DP',
               'HFSamplingPort.A664Message.DS.A429Word.DP',
               'HFQueuingPort.A664Message.DS.DP',
               'HFQueuingPort.A664Message.DS.A429Word.DP',
               'A653SamplingPort.A664Message.DS.DP',
               'A653QueuingPort.A664Message.DS.DP',
               'A653SamplingPort.A664Message.DS.A429Word.DP',
               'CANPort.CANMessage.A429Word.DP',
               'A653QueuingPort.A664Message.DS.A429Word.DP',            
               
               ]

ErrorDict ={'EC001':'Missing attribute',
      'EC002':'Bad value for attribute',
      'EC003':'More than one Dataflow_ref',
      'EC004':'Duplicate RP',
      'EC005':'RP without Pub_Ref',
      'EC006':'Multiple Pub_Refs for one RP',
      'EC007':'No DP message found for RP',
      'EC008':'BitOffset of embedded A429 Word inconsistent',
      'EC009':'Duplicate DP name',
      'EC010':'No RX COM Port found',
      'EC011':'No TX COM Port found',
      'EC012':'VL not found',
      'EC013':'CAN Message ID mismatch between TX and RX',
      'EC014':'No Destination IP Address found',
      'EC015':'VL without ID',   
      'EC016':'ByteOffsetDS + ByteSizeDS > MessageSize',
      'EC017':'BitOffset + BitSize > ByteSizeDS',  
      'EC018':'Receive Refresh period less than 3* max(txrefresh, rxsample)',
      'EC019':'The Publish message: %s ActivityTimeout is not equal to 3* RefreshPeriod',
      'EC020':'The Pub RefreshPeriod > Pub TransmissionIntervalMinimum',
      'EC021':'The Pub RefreshPeriod < The Sub SamplePeriod'
    }


def _getAttrib(x, attrib, cast=None, default=None):
    '''
    Get value of XML Record attribute attrib, cast it according to cast.
    If not found or cast fails, return default or None.
    '''
    a = x.a.get(attrib)
    if a is None:
        if default is None:
            pass
            #logger.nerror("Missing attribute %s" % attrib, TYPE=x.tag, NAME=x.a.Name, FILE=x.filename)
        else:
            logger.nerror("Missing attribute %s. Set to default [%s]" % (attrib, default),
                                TYPE=x.tag, NAME=x.a.Name, FILE=x.filename)
            a = default
    else:
        if cast:
            try:
                a = cast(a)
            except:
                if default is None:
                    logger.nerror("Bad value for attribute %s" % attrib, TYPE=x.tag, NAME=x.a.Name, FILE=x.filename)
                else:
                    logger.nerror("Bad value for attribute %s. Replace with default [%s]" % \
                                (attrib, default), TYPE=x.tag, NAME=x.a.Name, FILE=x.filename)
                    a = default
    return a

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

def getrootnode(msg):
    while msg.parent.parent:
        msg = msg.parent
    return msg

def computeMAC(node):
    for childnodes in node.e.values():
        for node1 in childnodes:
            if node1.a.get('Name',None) == 'A':
                macA = node1.a.MACAddress
            if node1.a.get('Name',None) == 'B':
                macB = node1.a.MACAddress
    return (macA,macB)

def getsourceMAC(root,node):
    macA = None
    macB = None
    if '.' in node.a.Hardware:        
        for ccr in root.e.get('CCR',[]):
            for gpm in ccr.e.GPM:
                if ccr.a.Name+'.'+gpm.a.Name == node.a.Hardware:
                    return computeMAC(gpm)  

    else:       
        for lru in root.e.get('LRU',[])+root.e.get('RIU',[]):
            if lru.a.Name == node.a.Hardware:
                return computeMAC(lru)   
    return (macA, macB)

def _getDSPath(xdp1, msgtype):
    '''Get the path from outmost dataset to a DP'''
    xdp = xdp1
    res = xdp.tag
    while xdp.parent:
        xdp = xdp.parent
        res = xdp.tag + '.' + res
        if xdp.tag == msgtype:
            return res
    return xdp1.tag

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

class ICDProcess(object):
    def __init__(self,xroot):
        #self.rxsignals  = dict()
        #self.txsignals  = dict()
        self.inputmsgs  = dict()
        self.outputmsgs = dict()
        self.vls        = dict()
        self.guidref    = dict()
        self.pubrefxref = defaultdict(list)
        self.gwindex    = dict()
        self.rplists    = dict()
        self.dplists    = dict()
        self.rxmsglists = dict()
        self.txmsglists = dict()
        self.root = xroot
       
        self.Ignore_Tag = ['Loc_Ref','Aggregation_Ref','Mem_Access_Ref','Pub_Ref','Gw_Pub_Ref',
                           'Copy_Ref','Dataflow_Ref','Trans_Ref','GP_Usage_Ref','Ep_Ref',
                           'Separation_Ref','VirtualLinks','SeparationGroups','Group_Ref',
                           'MsgVLGroups','Gateway_Ref','Gw_Fb_Ref','Gw_Cmd_Ref','Emb_Ref',
                           'SigSepGroups','ScheduleWindow','ChannelGroups','GPMHostedGroups',
                           'MessageModeGroups','GPMSchedule','Gw_Emb_Ref','ExtoolMetadata','LogicalBuses',
                           'AreaZones','Icd','A653PortSharingGroups']
    
    def reset(self):
        self.inputmsgs  = dict()
        self.outputmsgs = dict()
        self.rplists    = dict()
        self.dplists    = dict()
        self.rxmsglists = dict()
        self.txmsglists = dict()
    
    def AnalysisGWPubred(self,root):
        remotegws = root.e.get('RemoteGateway',[])
        if len(remotegws) == 0:
            logger.error('has no gw')
        
        for gw in remotegws:
            for xp in gw.e.get('HFQueuingPort',[])+gw.e.get('HFSamplingPort',[])+gw.e.get('CANPort',[])+gw.e.get("A429Port",[]):
                if xp.a.get('Direction') != 'Source':
                    continue
                self.scanGw_Pub_Ref(xp)
    
    def scanGw_Pub_Ref(self,root):
        for nodetag, nodes in root.e.items():
            if nodetag == 'Gw_Pub_Ref':
                for node in nodes:
                    self.gwindex[node.a.DestGuid] = node.parent
            else:
                for node in nodes:
                    self.scanGw_Pub_Ref(node)
                
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
            for xport in xha.e.get('HFQueuingPort',[]) + xha.e.get('HFSamplingPort', [])+ xha.e.get('CANPort', []) + xha.e.get('A429Port', []):
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
    
    
    def AnalysisVLs(self,root):
        
        virtuallinkslist = root.e.VirtualLinks
        #virtuallinks = virtuallinkslist[len(virtuallinkslist)-1] #choose the most length, the method should be replaced by a better one
        for virtuallinks in virtuallinkslist:
            for virtuallink in virtuallinks.e.VirtualLink:
                rxports = dict()
                txports = dict()
                vlpaths = dict()
                
                try:
                    vlid = virtuallink.a.get('ID')
                except:
                    logger.nerror(' [%s] Without vlid %d' % ("EC012",virtuallink.a.get('Name')))
                    continue            
            
                for rxport in virtuallink.e.ComPortRx:
                    rxports[rxport.a.Name] = rxport
                for txport in virtuallink.e.ComPortTx:
                    txports[txport.a.Name]  = txport
                for vlpath in virtuallink.e.VLPath:
                    vlpaths[vlpath.a.Name] = vlpath
                if vlid in self.vls:
                    logger.nerror(' [%s] virtual has same vlid: %s' % ("EC015",vlid))
                    return
                self.vls[vlid] = Bunch(virtuallink=virtuallink, rxports = rxports,txports=txports,vlpaths=vlpaths)          
        
    
    
    def AnalysisGuid(self,root):        
        if root.tag not in self.Ignore_Tag:            
            guid = root.a.get('Guid')
            if not guid:
                logger.nerror("Missing Guid ", TYPE=root.tag, FILE=root.filename)
            else:
                if guid in self.guidref:
                    if root.tag != 'Port_Ref' and not root.tag.endswith('PhysPort') and root.tag !='Group_Ref':
                        logger.nerror("Duplicate Guid: %s " % guid,TYPE=root.tag, FILE=root.filename )
                else:
                    self.guidref[guid] = root
        
        for nodes in root.e.values():
            for node in nodes:
                self.AnalysisGuid(node)
    
    def AnalysisInterCANMessage(self,root,hfname):
        
        CPlist=['HF_CCD1','HF_CCD2','HF_DCP1','HF_DCP2','HF_MKB1','HF_MKB2','HF_RCP']
        
        for node in root.e.get('HostedFunction',[]):
            if node.a.Name in CPlist:
                for canport in node.e.get('CANPort',[]):
                    if 'PilotInputs' in canport.a.Name:
                        continue 
                    msgtype = 'CANMessage'                    
                    for txmsg in canport.e.get(msgtype,[]):
                        for dp in txmsg.e.get('DP',[]):
                            self.CreateCAN_IMSG_RP(dp,txmsg,canport,msgtype,node)                            #this function should be realized later            
    
    # only used for create CAN RP for IDU
    def CreateCAN_IMSG_RP(self,dp,txmsg,canport,msgtype,hfnode):
        
        def getNamePath(xdp):
                '''Get the path from outmost dataset to a DP'''
                res = xdp.a.Name
                while xdp.parent.parent:
                    xdp = xdp.parent
                    res = xdp.a.Name+ '.' + res
                return res
            
        # function start    
        rpkey = hfnode.a.Name +'_'+ dp.a.Name 
        if rpkey in self.rplists:
            logger.error(("Duplicate Rp: %s " % rpkey))
            return                        
        rp = Bunch()
        rp.skip = '#'
        rp.ErrorCode = None
        rp.ErrorContent = None
        
        rp.name = rpkey
        rp.rp = None
        rp.port = None
        self.rplists[rp.name] = rp  # can not use this key, it may has more than one, can use ha.a.Name+ rp.name 
        
        rp.dp = dp
        rp.dpclass = self.guidref.get(dp.a.GuidDef)
        rp.msgclass = self.guidref.get(txmsg.a.GuidDef)
        rp.msg = txmsg
        rp.rpclass = None
        rp.type = msgtype
        rp.msgref = None
        rp.pubref = None
        rp.blockflag = False  
                
        rp.pubref = getNamePath(dp)
        rp.pubsrcguid=dp.a.Guid                
           
                  
                   
        rp.originallru = hfnode.a.Name


        if txmsg.a.Guid in self.rxmsglists:
            rxmsgs = self.rxmsglists.get(txmsg.a.Guid)
            if rp.originallru not in rxmsgs.msglru:
                rxmsgs.msglru.append(rp.originallru)
        else:
            rxmsgs = Bunch(msgtype = msgtype, txmsg=txmsg, txmsgclass = rp.msgclass, rxport = None, msglru = [rp.originallru])
            self.rxmsglists[txmsg.a.Guid] = rxmsgs
        
        rp.msgref = rxmsgs
        #if rp.name == 'L173_Angular_Lateral_Deviation_Display_FMS_CORE_1':
        #    print ('stop')
     
        
    def AnalysisRPs(self,root,hfname):
        global HFportType,A653portType
        hfporttype= None
        hftype= None
        if hfname.startswith('HF_'):
            hftype = 'HostedFunction'
            hfporttype = HFportType
        else:
            hftype = 'A653ApplicationComponent'
            hfporttype = A653portType              
            
        #hfnode = None
        for node in root.e.get('HostedFunction',[])+root.e.get('A653ApplicationComponent',[]):
            if node.a.Name == hfname:
                for porttype in HFportType+A653portType:
                    msgtype = porttomsgtype[porttype]                    
                    for xport in node.e.get(porttype,[]):
                        dataflow = xport.e.get('Dataflow_Ref',[])
                        if len(dataflow) > 1:
                            pass#logger.nerror('Port: %s has more than one dataflow' % ( xport.a.Name , xport.filename))
                        for rpnode in xport.e.get('RP',[]):
                            self.ProcessRP(rpnode,dataflow,porttype,xport,msgtype)                            #this function should be realized later            

            
    def ProcessRP(self,rpnode,datafolw,porttype,port,msgtype):
        
        def getDPMessage(node,msgtype):
            if node.tag == msgtype:
                return node
            while node.parent:
                node = node.parent
                if node.tag == msgtype:
                    return node
            return None
        
        def dudgeexist429(dp,rxport,isgw):
            if isgw:
                for gw in dp.e.get('Gw_Pub_Ref',[]):
                    if self.guidref[gw.a.DestGuid].parent == rxport:
                        return True               
                return False    
            else:
                for rp in rxport.e.get('RP',[]):
                    for pubref in rp.e.get('Pub_Ref',[]):
                        if pubref.a.SrcGuid == dp.a.Guid:  # can panduan through pubref.SrcGuid == dp.Guid
                            return True
                return  False               
        
        def rebuild_a429_rp(rprec,isgw): # if a rp connect the dp in the 429word, we need to extract other dp like Label, SSM...
            if dudgeexist429(rprec.dp.parent, rprec.port, isgw):
                logger.info("Skip to extract the rp: %s that link to the DP inside a 429word, for that there is exist one Rp link to the A429 Word"% rprec.name)
                #rprec.skip = '#'
                return
            rxport = rprec.port
            pubrefname = rprec.pubref
            #rprec.skip = '*'
            for dp in rprec.dp.parent.e.get('DP',[]): 
                if dudgeexist429(dp,rxport,isgw):                   
                    continue
                if dp.a.Name == rprec.dp.a.Name:
                    continue
                                                                     
                newrp = Bunch()
                newrp.skip = '*'
                newrp.ErrorCode = ''
                newrp.blockflag = False
                #if isgw:
                #    newrp.name = getrootnode(dp).a.Name+'.'+ rprec.dp.parent.parent.parent.a.Name + '.'+ rprec.dp.parent.a.Name + '.'+dp.a.Name
                #else:
                newrp.name = getrootnode(dp).a.Name+'.'+'.'.join(rprec.pubref.split('.')[:-1])+'.'+dp.a.Name
                newrp.rp = None
                newrp.pubref = '.'.join(rprec.pubref.split('.')[:-1])+'.'+dp.a.Name
                newrp.port = rxport
                newrp.dp = dp
                if isgw:
                    dpclass = dp
                else:
                    dpclass = self.guidref[dp.a.GuidDef]
                newrp.dpclass = dpclass
                newrp.rpclass = None #rprec.rpclass    # rebuild rp has no rpclass or used the old rp rpclass 
                newrp.msgclass = rprec.msgclass
                newrp.msg = rprec.msg
                newrp.type = rprec.type
                newrp.msgref = rprec.msgref
                newrp.originallru= rprec.originallru
                    
                self.rplists[newrp.name] = newrp  # can not use this key, it may has more than one, can use ha.a.Name+ rp.name 
            #if rp just link to the DP inside the 429 word, add the virtual rp that link to 429 word
            newrp = Bunch()
            newrp.skip = '#'
            newrp.ErrorCode = ''
            newrp.blockflag = False
            #if isgw:
            #    newrp.name = getrootnode(dp).a.Name+'.'+ rprec.dp.parent.parent.parent.a.Name + '.'+ rprec.dp.parent.a.Name + '.'+dp.a.Name
            #else:
            newrp.name = getrootnode(dp).a.Name+'.'+'.'.join(rprec.pubref.split('.')[:-1])
            newrp.rp = None
            newrp.pubref = '.'.join(rprec.pubref.split('.')[:-1])
            newrp.port = rxport
            newrp.dp = dp.parent
            if isgw:
                dpclass = dp.parent
            else:
                dpclass = self.guidref[dp.parent.a.GuidDef]
            newrp.dpclass = dpclass
            newrp.rpclass = rprec.rpclass    # rebuild rp has no rpclass or used the old rp rpclass 
            newrp.msgclass = rprec.msgclass
            newrp.msg = rprec.msg
            newrp.type = rprec.type
            newrp.msgref = rprec.msgref
            newrp.originallru= rprec.originallru
                
            self.rplists[newrp.name] = newrp
            
            return  False
                
        
        def rebuild_a429_word(rprec,isgw):
            rxport = rprec.port
            pubrefname = rprec.pubref
            rprec.skip = '#'
            logger.info("Mark the Rp: %s status to #, for that it connects a 429 word"%rprec.name)
            for dp in rprec.dp.e.get('DP',[]): 
                if dudgeexist429(dp,rxport,isgw):                   
                    continue
                                     
                newrp = Bunch()
                newrp.skip = '*'
                newrp.ErrorCode = ''
                newrp.blockflag = False
                #if isgw:
                #    newrp.name = getrootnode(dp).a.Name+'.'+ rprec.dp.parent.parent.a.Name + '.'+rprec.dp.a.Name + '.'+dp.a.Name
                #else:
                newrp.name = rprec.name + '.'+dp.a.Name
                newrp.rp = None
                newrp.pubref = rprec.pubref+'.'+dp.a.Name
                newrp.port = rxport
                newrp.dp = dp
                if isgw:
                    dpclass = dp
                else:
                    dpclass = self.guidref[dp.a.GuidDef]
                newrp.dpclass = dpclass
                newrp.rpclass = rprec.rpclass    # rebuild rp has no rpclass or used the old rp rpclass 
                newrp.msgclass = rprec.msgclass
                newrp.msg = rprec.msg
                newrp.type = rprec.type
                newrp.msgref = rprec.msgref
                newrp.originallru= rprec.originallru
                    
                self.rplists[newrp.name] = newrp  # can not use this key, it may has more than one, can use ha.a.Name+ rp.name 
            
            return  False
        
        def rebuild_A664DS_block(rprec,isgw):
            rxport = rprec.port
            pubrefname = rprec.pubref
            pubrefsrcguid=rprec.pubsrcguid
            dsname = rprec.dp.a.Name
            byteOffsetFSB = rprec.dp.a.ByteOffsetFSF
            byteOffsetDS = rprec.dp.a.ByteOffsetWithinMsg
            byteSizeDS = rprec.dp.a.DataSetSize
            for dp in rprec.dp.e.get('DP',[]): 
                #if dudgeexist429(dp,rxport,isgw):                   
                #    continue
                rprec.skip = '#'                     

                if dp.a.Name == 'BLOCK':
                    originalnode = self.guidref[pubrefsrcguid]
                    offsetbegin = dp.a.BitOffsetWithinDS
                    wordcount = 0
                    for onea429w in originalnode.e.get("A429Word",[]):                        
                        for onedp in onea429w.e.get('DP',[]):
                            newrp = Bunch()
                            newrp.skip = '*'
                            newrp.ErrorCode = ''
                            newrp.name = getrootnode(originalnode).a.Name+'.'+onea429w.a.Name+'.'+onedp.a.Name
                            newrp.rp = None
                            newrp.blockflag = True
                            newrp.pubref = rprec.pubref+'.'+onea429w.a.Name+'.'+onedp.a.Name
                            newrp.port = rxport
                            newrp.dp = onedp
                            newrp.dpclass = self.guidref[onedp.a.GuidDef]
                            newrp.rpclass = rprec.rpclass    # rebuild rp has no rpclass or used the old rp rpclass 
                            newrp.msgclass = rprec.msgclass
                            newrp.msg = rprec.msg
                            newrp.type = rprec.type
                            newrp.msgref = rprec.msgref
                            newrp.originallru= rprec.originallru
                            newrp.DsName = dsname
                            newrp.ByteOffsetFSB = byteOffsetFSB
                            newrp.ByteOffsetDS  = byteOffsetDS
                            newrp.ByteSizeDS    = byteSizeDS
                            newrp.BitOffset     = int(offsetbegin)+ wordcount * 32 +_getAttrib(newrp.dpclass,"BitOffsetWithinDS", int) 
                            newrp.BitSize       = _getAttrib(newrp.dpclass,"ParameterSize", int)       
                            self.rplists[newrp.name] = newrp
                        wordcount += 1
                                                               
                else: 
                    newrp = Bunch()
                    newrp.skip = '*'
                    newrp.ErrorCode = ''
                    newrp.blockflag = False
                    newrp.name = rprec.name + '.'+dp.a.Name
                    newrp.rp = None
                    newrp.pubref = rprec.pubref+'.'+dp.a.Name
                    newrp.port = rxport
                    newrp.dp = dp
                    if isgw:
                        dpclass = dp
                    else:
                        dpclass = self.guidref[dp.a.GuidDef]
                    newrp.dpclass = dpclass                    
                    newrp.rpclass = rprec.rpclass    # rebuild rp has no rpclass or used the old rp rpclass 
                    newrp.msgclass = rprec.msgclass
                    newrp.msg = rprec.msg
                    newrp.type = rprec.type
                    newrp.msgref = rprec.msgref
                    newrp.originallru= rprec.originallru
                    newrp.DsName = dsname
                    rprec.ByteOffsetFSB = byteOffsetFSB
                    newrp.ByteOffsetDS  = byteOffsetDS
                    newrp.ByteSizeDS    = byteSizeDS
                    newrp.BitOffset     = _getAttrib(dpclass,"BitOffsetWithinDS", int)
                    newrp.BitSize       = _getAttrib(dpclass,"ParameterSize", int)
                    self.rplists[newrp.name] = newrp
        
        
        
        
        def rebuild_a429_block(rprec,isgw):
            rxport = rprec.port
            pubrefname = rprec.pubref
            pubrefsrcguid=rprec.pubsrcguid
            dsname = rprec.dp.a.Name
            byteOffsetFSB = rprec.dp.a.ByteOffsetFSF
            byteOffsetDS = rprec.dp.a.ByteOffsetWithinMsg
            byteSizeDS = rprec.dp.a.DataSetSize
            for dp in rprec.dp.e.get('DP',[]): 
                #if dudgeexist429(dp,rxport,isgw):                   
                #    continue
                rprec.skip = '#'                     

                if dp.a.Name == 'BLOCK':
                    originalnode = self.guidref[pubrefsrcguid]
                    offsetbegin = dp.a.BitOffsetWithinDS
                    wordcount = 0
                    for onea429w in originalnode.e.get("A429Word",[]):                        
                        for onedp in onea429w.e.get('DP',[]):
                            newrp = Bunch()
                            newrp.skip = '*'
                            newrp.ErrorCode = ''
                            newrp.name = getrootnode(originalnode).a.Name+'.'+onea429w.a.Name+'.'+onedp.a.Name
                            newrp.rp = None
                            newrp.blockflag = True
                            newrp.pubref = rprec.pubref+'.'+onea429w.a.Name+'.'+onedp.a.Name
                            newrp.port = rxport
                            newrp.dp = onedp
                            newrp.dpclass = self.guidref[onedp.a.GuidDef]
                            newrp.rpclass = rprec.rpclass    # rebuild rp has no rpclass or used the old rp rpclass 
                            newrp.msgclass = rprec.msgclass
                            newrp.msg = rprec.msg
                            newrp.type = rprec.type
                            newrp.msgref = rprec.msgref
                            newrp.originallru= rprec.originallru
                            newrp.DsName = dsname
                            newrp.ByteOffsetFSB = byteOffsetFSB
                            newrp.ByteOffsetDS  = byteOffsetDS
                            newrp.ByteSizeDS    = byteSizeDS
                            newrp.BitOffset     = int(offsetbegin)+ wordcount * 32 +_getAttrib(newrp.dpclass,"BitOffsetWithinDS", int) 
                            newrp.BitSize       = _getAttrib(newrp.dpclass,"ParameterSize", int)       
                            self.rplists[newrp.name] = newrp
                        wordcount += 1
                                                               
                else: 
                    newrp = Bunch()
                    newrp.skip = '*'
                    newrp.ErrorCode = ''
                    newrp.blockflag = False
                    newrp.name = rprec.name + '.'+dp.a.Name
                    newrp.rp = None
                    newrp.pubref = rprec.pubref+'.'+dp.a.Name
                    newrp.port = rxport
                    newrp.dp = dp
                    if isgw:
                        dpclass = dp
                    else:
                        dpclass = self.guidref[dp.a.GuidDef]
                    newrp.dpclass = dpclass                    
                    newrp.rpclass = rprec.rpclass    # rebuild rp has no rpclass or used the old rp rpclass 
                    newrp.msgclass = rprec.msgclass
                    newrp.msg = rprec.msg
                    newrp.type = rprec.type
                    newrp.msgref = rprec.msgref
                    newrp.originallru= rprec.originallru
                    newrp.DsName = dsname
                    rprec.ByteOffsetFSB = byteOffsetFSB
                    newrp.ByteOffsetDS  = byteOffsetDS
                    newrp.ByteSizeDS    = byteSizeDS
                    newrp.BitOffset     = _getAttrib(dpclass,"BitOffsetWithinDS", int)
                    newrp.BitSize       = _getAttrib(dpclass,"ParameterSize", int)
                    self.rplists[newrp.name] = newrp
                            
        #start this function
        if rpnode.a.Name in self.rplists:
            logger.error(("Duplicate Rp: %s " % rpnode.a.Name))
            return                        
        rp = Bunch()
        rp.skip = ''
        rp.ErrorCode = None
        rp.ErrorContent = None
        isgw = False
        rp.name = rpnode.a.Name
        rp.rp = rpnode
        rp.port = port
        self.rplists[rp.name] = rp  # can not use this key, it may has more than one, can use ha.a.Name+ rp.name 
        
        rp.dp = None
        rp.dpclass = None
        rp.msgclass = None
        rp.msg = None
        rp.rpclass = None
        rp.type = msgtype
        rp.msgref = None
        rp.pubref = None
        rp.blockflag = False 
        rp.dsblock = False 
        pubref = rpnode.e.get('Pub_Ref',[])
        if len(pubref) == 0:
            logger.nerror(' [%s] RP: %s has no Pubref or has more than one Pubref' % ("EC005",rpnode.a.Name), ERRORCODE='EC005',FILE=rpnode.filename )
            rp.skip='#'
            rp.ErrorCode = 'EC005'
            return
        elif len(pubref)>1:
            logger.nerror(' RP: %s has no Pubref or has more than one Pubref' % (rpnode.a.Name), ERRORCODE='EC005',FILE=rpnode.filename )
        pubref = pubref[0]
        
        rp.pubref = pubref.a.SrcName
        rp.pubsrcguid=pubref.a.SrcGuid
        rp.rpclass = self.guidref.get(rpnode.a.GuidDef,None)         
           
        xdp = self.gwindex.get(rpnode.a.Guid,None)
        if xdp:
            isgw = True
        else:
            xdp = self.guidref.get(pubref.a.SrcGuid,None)
            if xdp is None: 
                logger.nerror(' [%s] RP: %s has no DP'% ("EC007",rp.name),ERRORCODE = 'EC007',FILE=rpnode.filename)
                rp.skip='#'
                rp.ErrorCode = 'EC007'
                return
            isgw = False
        if xdp.tag == 'A429Word' and msgtype == 'A429Word':
            msg = xdp
        else:
            msg = getDPMessage(xdp,msgtype) 
        if msg is None:
            #if isgw == True and xdp.tag == 'A429Channel':  #add this to solve some rp that go through rgw, but link to 429 channel, for example rp L270_1_FMS_1_Status_Word_Master_Slave
            #    xdp = self.guidref.get(pubref.a.SrcGuid,None)
            #    msg = getDPMessage(xdp,msgtype)
            #    isgw = False
            #    rp.dsblock = True
            #else:
                print xdp.tag
                logger.nerror(' [%s] RP: %s has no DP Message' % ("EC007",rp.name),ERRORCODE = 'EC007',FILE=rpnode.filename)
                rp.skip='#'
                rp.ErrorCode = 'EC007'
                return
         # get the msg type from source, we can also get this value from port type
        if isgw:
            dpclass = xdp
            msgclass = msg
        else:
            dpclass = self.guidref.get(xdp.a.GuidDef) 
            msgclass = self.guidref.get(msg.a.GuidDef)  
           
                   
        rp.originallru = getrootnode(self.guidref.get(rp.pubsrcguid)).a.get("Name",None)

        
        rp.dp = xdp
        rp.dpclass = dpclass
        rp.msgclass = msgclass
        rp.msg = msg
        #rp.type = msgtype   
        
        if (msg.a.Guid,port.a.Guid) in self.rxmsglists:
            rxmsgs = self.rxmsglists.get((msg.a.Guid,port.a.Guid))
            if rp.originallru not in rxmsgs.msglru:
                rxmsgs.msglru.append(rp.originallru)
        else:
            rxmsgs = Bunch(msgtype = msgtype, txmsg=msg, txmsgclass = msgclass, rxport = port, msglru = [rp.originallru])
            self.rxmsglists[(msg.a.Guid,port.a.Guid)] = rxmsgs
        
        rp.msgref = rxmsgs
        #if rp.name == 'L173_Angular_Lateral_Deviation_Display_FMS_CORE_1':
        #    print ('stop')
        if rp.dp.tag =='A429Word':
            rebuild_a429_word(rp,isgw)
        elif rp.dp.parent.tag == 'A429Word':
            rebuild_a429_rp(rp,isgw)
		# if A429 link to block, add code to resolve
        if self.guidref[rp.pubsrcguid].tag == 'A429Channel':
            rebuild_a429_block(rp,isgw)
        #if rp.dsblock:
        #    rebuild_A664DS_block(rp, isgw)
               
        # check where xdp is contained by dataflow srcgid suo zhi xiang de node    
        
    def AnalysisDPs(self,root,hfname):
        global HFportType,A653portType
        hfporttype= None
        hftype= None
        if hfname.startswith('HF_'):
            hftype = 'HostedFunction'
            hfporttype = HFportType
        else:
            hftype = 'A653ApplicationComponent'
            hfporttype = A653portType              
            
        
        for node in root.e.get('HostedFunction',[])+root.e.get("A653ApplicationComponent",[]):
            if node.a.Name == hfname:
                for porttype in HFportType+A653portType:
                    #msgtype = porttomsgtype[porttype]    #will be A664Messgae or CANMessage                
                    for xport in node.e.get(porttype,[]):
                        for xmsg in xport.e.get( "A664Message",[]):
                            for xds in xmsg.e.get('DS',[]):  # used for A664Message
                                for xdp in xds.e.get('DP',[]):
                                    self.ProcessDP(hfname,xdp,(),xds,xmsg,xport,'A664Message')
                                for a429msg in xds.e.get('A429Word',[]):
                                    for xdp in a429msg.e.get('DP',[]):
                                        self.ProcessDP(hfname,xdp,(a429msg,),xds,xmsg,xport,'A664Message')                                
                                for canmsg in xds.e.get('CANMessage',[]):
                                    for xdp in canmsg.e.get('DP',[]):
                                        self.ProcessDP(hfname,xdp,(canmsg,),xds,xmsg,xport,'A664Message')
                                    for a429msg in canmsg.e.get('A429Word',[]):
                                        for xdp in a429msg.e.get('DP',[]):
                                            self.ProcessDP(hfname,xdp,(a429msg,canmsg),xds,xmsg,xport,'A664Message')
                        for xcanmsg in xport.e.get('CANMessage',[]):
                            for xdp in xcanmsg.e.get('DP',[]):  #use for CANMessage, below CANMessage is DPs
                                self.ProcessCANDP(hfname,xdp,xcanmsg,  xport,'CANMessage',x429word = None,embed429=False)
                            for x429 in xcanmsg.e.get('A429Word',[]):
                                for xdp in x429.e.get('DP',[]):
                                    self.ProcessCANDP(hfname, xdp, xcanmsg,  xport, 'CANMessage',x429word = x429, embed429=True)
                        for xchl in xport.e.get('A429Channel',[]):
                            for xw in xchl.e.get('A429Word',[]):
                                for xdp in xw.e.get('DP',[]):
                                    self.Process429DP(hfname,xdp,xw,xchl,xport,'A429Word')
                                        
    def Process429DP(self,hfname,xdp,msg,chl,port,msgtype):        
        
        dp = Bunch()
        dp.ErrorCode = None
        dp.lru = hfname
        dp.name = xdp.a.Name
        dp.dp = xdp
        dp.skip = ''
        dp.msgtype = msgtype
        dp.msg = msg     
        dp.dpclass = self.guidref.get(xdp.a.GuidDef)
        dp.msgclass = self.guidref.get(msg.a.GuidDef)
        dp.msgname = msg.a.get('Name',None)
        dp.msgref =None
        dp.ByteOffsetFSB   = None
        dp.ByteOffsetDS    = None
        dp.ByteSizeDS      = None
        dp.BitOffset       = _getAttrib(dp.dpclass,"BitOffsetWithinDS", int)
        dp.BitSize         = _getAttrib(dp.dpclass,"ParameterSize", int)
        dp.Encoding        = dp.dpclass.a.get("DataFormatType")
        dp.LsbValue        = _getAttrib(dp.dpclass, 'LsbRes', float, default=1.0)
        dp.transmissionintervalminimum  = _getAttrib(dp.dpclass,"TransmissionIntervalMinimum", float)
        dp.codedset                     = dp.dpclass.a.get("CodedSet",None)
        dp.fullscalerangemax            = dp.dpclass.a.get("FullScaleRngMax",None)
        dp.fullscalerangemin            = dp.dpclass.a.get("FullScaleRngMin",None)
        dp.functionalrangemax           = dp.dpclass.a.get("FuncRngMax",None)
        dp.functionalrangemin           = dp.dpclass.a.get("FuncRngMin",None)
        dp.publishedlatency             = _getAttrib(dp.dpclass,"PublishedLatency", int)
        dp.units                        = dp.dpclass.a.get("Units",None)
        dp.onestate                     = dp.dpclass.a.get("OneState",None) 
        dp.zerostate                    = dp.dpclass.a.get("ZereState",None)
        dp.txportname = port.a.Name
        dp.txchlname = chl.a.Name
        signame = xdp.a.Name        
        sigkey =(hfname,chl.a.Name,msg.a.Name,signame)
        
        if sigkey in self.dplists:
            logger.nerror(' [%s] Duplicate DP: %s ' % ("EC009",sigkey),ERRORCODE = 'EC009',FILE=xdp.filename)
            dp.skip='#'
            dp.ErrorCode = 'EC009'
            return
        else:
            self.dplists[sigkey] = dp
        
        
        if dp.msgname is None:
            logger.error('The DP: %s Message has no Name' % sigkey)        
        
        if msg.a.Guid in self.txmsglists:
            txmsgs = self.txmsglists.get(msg.a.Guid)
        else:
            txmsgs = Bunch(msgtype = msgtype, txmsg=msg, txmsgclass =self.guidref.get(msg.a.GuidDef), dp = None)
            self.txmsglists[msg.a.Guid] = txmsgs
            
        if msgtype == "A429Word":
        
            if dp.Encoding == "A429OCTLBL":
                try:
                    txmsgs.Label = dp.dpclass.a.Label
                except:
                    logger.nerror("Can't extract Label from [%s]" % dp.name)
                    txmsgs.Label = "" 
                
            if dp.Encoding == "A429SDI":
                #logger.info("DP ocdeset is %s" % dp.codedset)
                try:                    
                    txmsgs.SDI = _getCodedSetConst(dp.codedset)
                except:
                    logger.nerror("Can't extract SDI from [%s]" % dp.name)
                    txmsgs.SDI = "" 
            
        dp.msgref = txmsgs
    
                                
    def ProcessCANDP(self,hfname,xdp,msg,port,msgtype,x429word=None,embed429=False):        
        
        dp = Bunch()
        dp.embed429 = embed429
        dp.ErrorCode = None
        dp.lru = hfname
        dp.name = xdp.a.Name
        dp.dp = xdp
        dp.skip = ''
        dp.msgtype = msgtype
        dp.msg = msg     
        dp.dpclass = self.guidref.get(xdp.a.GuidDef)
        dp.msgclass = self.guidref.get(msg.a.GuidDef)
        if embed429:
            dp.msgname = msg.a.get('Name',None) +'.'+ x429word.a.get('Name',None)
        else:
            dp.msgname = msg.a.get('Name',None)
        dp.msgref =None
        dp.ByteOffsetFSB   = None
        dp.ByteOffsetDS    = None
        dp.ByteSizeDS      = None
        dp.BitOffset       = _getAttrib(dp.dpclass,"BitOffsetWithinDS", int)
        dp.BitSize         = _getAttrib(dp.dpclass,"ParameterSize", int)
        dp.Encoding        = dp.dpclass.a.get("DataFormatType")
        dp.LsbValue        = _getAttrib(dp.dpclass,"LsbRes",float,default=1.0)
        dp.transmissionintervalminimum  = _getAttrib(dp.dpclass,"TransmissionIntervalMinimum", float)
        dp.codedset                     = dp.dpclass.a.get("CodedSet",None)
        dp.fullscalerangemax            = dp.dpclass.a.get("FullScaleRngMax",None)
        dp.fullscalerangemin            = dp.dpclass.a.get("FullScaleRngMin",None)
        dp.functionalrangemax           = dp.dpclass.a.get("FuncRngMax",None)
        dp.functionalrangemin           = dp.dpclass.a.get("FuncRngMin",None)
        dp.publishedlatency             = _getAttrib(dp.dpclass,"PublishedLatency", int)
        dp.units                        = dp.dpclass.a.get("Units",None)
        dp.onestate                     = dp.dpclass.a.get("OneState",None) 
        dp.zerostate                    = dp.dpclass.a.get("ZereState",None)
        signame = xdp.a.Name        
        sigkey =(hfname,dp.msgname,signame)
        
        if sigkey in self.dplists:
            logger.nerror(' [%s] Duplicate DP: %s ' % ("EC009",sigkey),ERRORCODE = 'EC009',FILE=xdp.filename)
            dp.skip='#'
            dp.ErrorCode = 'EC009'
            return
        else:
            self.dplists[sigkey] = dp
        
        
        if dp.msgname is None:
            logger.error('The DP: %s Message has no Name' % sigkey)        
        
        if msg.a.Guid in self.txmsglists:
            txmsgs = self.txmsglists.get(msg.a.Guid)
        else:
            txmsgs = Bunch(msgtype = msgtype, txmsg=msg, txmsgclass =self.guidref.get(msg.a.GuidDef), dp = None, a429word = x429word)
            self.txmsglists[msg.a.Guid] = txmsgs
            
        dp.msgref = txmsgs
    
            
    def ProcessDP(self,hfname,xdp,dpparent,ds,msg,port,msgtype):
        
                    
        dp = Bunch()
        dp.ErrorCode = None
        
        dp.dp = xdp
        dp.lru = hfname
        dp.msgtype = msgtype
        signame = xdp.a.Name
        for o in dpparent:
            signame = o.a.Name +'.'+signame
            
        dp.name = signame # add the 429 word to the dp name, orginal is the xdp.a.Name
        sigkey =(hfname,msg.a.Name,ds.a.Name,signame)
        
        if sigkey in self.dplists:
            logger.nerror(' [%s] Duplicate DP: %s ' % ("EC009",sigkey),ERRORCODE = 'EC009',FILE=xdp.filename)
            dp.skip = '#'
            dp.ErrorCode = 'EC009'
            return
        else:
            self.dplists[sigkey] = dp
        
        dp.skip = ''
        dp.msg = msg
        dp.ds = ds
        dp.dpclass = self.guidref.get(xdp.a.GuidDef)
        dp.dsclass = self.guidref.get(ds.a.GuidDef)
        dp.msgclass = self.guidref.get(msg.a.GuidDef)
        dp.msgname = msg.a.get('Name',None)
        dp.ByteOffsetFSB   = None
        dp.ByteOffsetDS    = _getAttrib(dp.dsclass,"ByteOffsetWithinMsg",int)
        dp.ByteSizeDS      = _getAttrib(dp.dsclass,"DataSetSize", int)
        dp.BitOffset       = _getAttrib(dp.dpclass,"BitOffsetWithinDS", int)
        dp.BitSize         = _getAttrib(dp.dpclass,"ParameterSize", int)
        dp.Encoding        = dp.dpclass.a.get("DataFormatType")
        dp.LsbValue        = _getAttrib(dp.dpclass,"LsbRes",float,default=1.0)
        dp.label           = _getAttrib(dp.dpclass,"Label", int)
        dp.multiplier      = dp.dpclass.a.get("Multiplier", None)
        dp.transmissionintervalminimum  = _getAttrib(dp.dpclass,"TransmissionIntervalMinimum", float)
        dp.codedset                     = dp.dpclass.a.get("CodedSet",None)
        dp.fullscalerangemax            = dp.dpclass.a.get("FullScaleRngMax",None)
        dp.fullscalerangemin            = dp.dpclass.a.get("FullScaleRngMin",None)
        dp.functionalrangemax           = dp.dpclass.a.get("FuncRngMax",None)
        dp.functionalrangemin           = dp.dpclass.a.get("FuncRngMin",None)
        dp.publishedlatency             = _getAttrib(dp.dpclass,"PublishedLatency", int)
        dp.units                        = dp.dpclass.a.get("Units",None)
        dp.onestate                     = dp.dpclass.a.get("OneState",None) 
        dp.zerostate                    = dp.dpclass.a.get("ZereState",None)
        
        
        dp.Consumer        = ""
        if dp.msgname is None:
            logger.error('The DP: %s Message has no Name' % sigkey)
        dp.DsName = ds.a.get('Name',None)
        if dp.DsName is None:
            logger.error('The DP: %s has no DS Name' % sigkey)
        
        if dp.dsclass.a.DsDataProtocolType != 'A664_FSS':
            dp.ByteOffsetFSB = _getAttrib(dp.dsclass,"ByteOffsetFSF", int,default=0)
            if dp.ByteOffsetFSB == 0 and dp.ByteOffsetDS == 0:
                dp.Validity = ''
            else:
                if dpparent and dpparent[0].tag == "A429Word":
                    dp.Validity = 'FSB, ' + _getSSMType(self.guidref[dpparent[0].a.GuidDef])
                else:
                    dp.Validity = "FSB"

            if dp.Encoding == "BNR" or dp.Encoding == "UBNR" or dp.Encoding == "BCD":
                dp.LsbValue  = _getAttrib(dp.dpclass,"LsbRes",float,default=1.0)
        
        if msg.a.Guid in self.txmsglists:
            txmsgs = self.txmsglists.get(msg.a.Guid)
        else:
            txmsgs = Bunch(msgtype = msgtype, txmsg=msg, txmsgclass =self.guidref.get(msg.a.GuidDef), dp = None)
            self.txmsglists[msg.a.Guid] = txmsgs           
      
            
        dp.msgref = txmsgs

    def AnalysisInputMessages(self):     
                            
            
        def analysisAFDXRxMsg(msg):
            '''
            vlid
            subvl
            bag
            MTU
            edeid
            edeenabled
            messagename
            lru
            srcip
            destip
            srcudpport
            destiudpport
            sourceMAC
            destMAC  (broadcast or unicast)
            portid
            portname
            txmsglen (tx side)
            rxmsglen (rx side)
            msgtype
            overhead
            txrate
            rxrate
                        
            '''
            def getNamePath(xdp):
                '''Get the path from outmost dataset to a DP'''
                res = xdp.a.Name
                while xdp.parent.parent:
                    xdp = xdp.parent
                    res = xdp.a.Name+ '.' + res
                return res

            
            #def add_Fcm_rp():
                
            
            def Add_FCM_Fress_And_CRC(msg,txlruname):
                
                txmsg = msg.txmsg
                txmsgclass = msg.txmsgclass
 
                rxport = msg.rxport  # in receive side, below the Port is the RP. without the message defined, so the messagesize is defined in the rxportclass
  
                for ds in txmsg.e.get('DS',[]):                    
                    for dp in ds.e.get('DP',[]):
                        if dp.a.Name in ['Freshness_Counter','Application_CRC']:
                            newrp = Bunch()
                            newrp.skip = '*'
                            newrp.ErrorCode = ''
                            newrp.name = dp.a.Name+'_'+txlruname.a.Name+'_'+txmsg.a.Name.split('_')[-1]
                            newrp.rp = None
                            newrp.blockflag = False
                            newrp.pubref = getNamePath(dp)
                            newrp.port = rxport
                            newrp.dp = dp
                            newrp.dpclass = self.guidref[dp.a.GuidDef]
                            newrp.rpclass = None    # rebuild rp has no rpclass or used the old rp rpclass 
                            newrp.msgclass = txmsgclass
                            newrp.msg = txmsg
                            newrp.type = 'A664Message'
                            newrp.msgref = msg
                            newrp.originallru = getrootnode(txmsg).a.Name
                                    
                            self.rplists[newrp.name] = newrp
            
            txmsg = msg.txmsg
            txmsgclass = msg.txmsgclass
            txportclass = txmsgclass.parent
            rxport = msg.rxport  # in receive side, below the Port is the RP. without the message defined, so the messagesize is defined in the rxportclass
            txport = msg.txmsg.parent
            rxPathName = rxport.a.get('PathName',None)
            txlru = getrootnode(txmsg)
            rxlru = getrootnode(rxport)
            rxportclass = self.guidref[rxport.a.GuidDef]
            if rxport.tag.endswith("SamplingPort"):
                rxtype = "SAMPLING"
            else:
                rxtype = "QUEUEING"
            msg.skip = ''
            msg.ErrorCode = None
            msg.vlid = txmsg.a.get('VLID',None)
            
            if txlru.a.Name in ['HF_FCM_1','HF_FCM_2','HF_FCM_3']:
                Add_FCM_Fress_And_CRC(msg,txlru)
            
            
            msg.subvlid = _getAttrib(txmsg,'SubVLID',int)
            msg.edeenable = txmsgclass.a.get('EdeEnable',None)
            msg.overhead = txmsgclass.a.get('MessageOverhead', None)
            msg.txlength = _getAttrib(txmsgclass,'MessageSize',int)
            msg.msgdataprotocoltype   = txmsgclass.a.get('MsgDataProtocolType', None)
            msg.transmissionintervalminimum   = _getAttrib(txmsgclass,'TransmissionIntervalMinimum', float)
            msg.lru = txlru.a.get('Name',None)
            msg.msgname = txmsg.a.get('Name', None)
            msg.txportname = txport.a.Name
            msg.srcip = _getAttrib(txlru,'IpAddress', default='10.0.0.1')
            msg.destip = None #_getAttrib(rxlru,'IpAddress', None)#, '10.0.0.1')
            msg.type = rxtype
            msg.rxlength = _getAttrib(rxportclass,'MessageSize',int)
            msg.ActualPathA = None
            msg.ActualPathB = None
            msg.ata = []
            if msg.vlid:
                msg.MACDest = ('03:00:00:00:%02X:%02x' % (int(msg.vlid)/256, int(msg.vlid)%256))
            
            if rxport.tag.endswith("QueuingPort"):
                msg.queuelength = _getAttrib(rxportclass,"QueueLength", int)
            else:
                msg.queuelength = 1
            msg.portname = rxport.a.Name #receive side  #txlru.a.Name + '.' +   txport.a.Name  # tx side port name        
            if msg.vlid:
                node1 = self.vls.get(msg.vlid,None)
                if node1 is None:
                    logger.nerror(' [%s] Can not find VL: %s in VirtualLinks file '% ("EC012",str(msg.vlid)), ERRORCODE='EC012',FILE=txport.filename)
                    msg.skip='#'
                    msg.ErrorCode='EC012'
                    return
                node = node1.virtuallink
                if node:
                    msg.BAG = node.a.get('BAG',None)
                    msg.MTU = node.a.get('MTU',None)
                    
                    for comportrx in node.e.get('ComPortRx',[]):
                        for PortRefnode in comportrx.e.get('Port_Ref',[]):
                            if PortRefnode.a.Name == rxlru.a.Name +'.'+ rxport.a.Name:
                                msg.portid = comportrx.a.get('ID',None)
                                msg.udpdstid = comportrx.a.get('UdpDstId',None)
                    
                    for comporttx in node.e.get('ComPortTx',[]):
                        for portref in comporttx.e.get('Port_Ref',[]):
                            if portref.a.Name == txlru.a.Name +'.'+txport.a.Name:
                                msg.udpsrcid = comporttx.a.get('UdpSrcId',None)
                                msg.edesourceid = comporttx.a.get('ID',None)
                                if comporttx.a.IPDestAddrFormat == "UNICAST":
                                    msg.destip = _getAttrib(rxlru, 'IpAddress',None)
                                else:
                                    msg.destip = '224.224.%d.%d'%(int(msg.vlid)/256,int(msg.vlid)%256)
                                
                vlpath = node1.vlpaths.get(rxPathName)
                if vlpath:
                    temp = vlpath.a.ActualPath.split(',')[-1]
                    temp1 = temp
                    if temp.endswith('A'):
                        temp1 = temp[:-1]+'B'
                        msg.ActualPathA = vlpath.a.ActualPath
                        for vlp in node1.vlpaths.values():
                            if vlp.a.ActualPath.endswith(temp1):
                                msg.ActualPathB = vlp.a.ActualPath
                    elif temp.endswith('B'):
                        temp1 = temp[:-1]+'A'
                        msg.ActualPathB = vlpath.a.ActualPath
                        for vlp in node1.vlpaths.values():
                            if vlp.a.ActualPath.endswith(temp1):
                                msg.ActualPathA = vlp.a.ActualPath
                else:
                    logger.nerror(' [%s] Can not find VLpath: %s in VirtualLinks file '% ("EC015",rxPathName), VLID=str(msg.vlid), ERRORCODE='EC015',FILE=txport.filename)
                    msg.skip='#'
                    msg.ErrorCode='EC015'
                    #msg.ActualPath  = vlpath.a.ActualPath 
            for lru in msg.msglru:
                for ata, lrulists in ATA.items():
                    if lru in lrulists and ata not in msg.ata:
                        msg.ata.append(ata)
            msg.sourecMACA, msg.sourecMACB = getsourceMAC(self.root,txlru)
            msg.rxsamrate = rxportclass.a.get("SamplePeriod",None)
            msg.rxrefrate = rxportclass.a.get("RefreshPeriod",None)
            msg.txrate = txportclass.a.get('RefreshPeriod',None)
            if msg.rxrefrate is not None:
                if (float(msg.rxrefrate) < 3*max(float(msg.rxsamrate),float(msg.txrate))):                
                    msg.skip=''
                    msg.ErrorCode='EC018'
                    logger.nerror(' [%s] Message: %s Receive Refresh period less than 3* max(txrefresh, rxsample)' % ("EC018",msg.msgname), ERRORCODE='EC018',FILE=txport.filename)
            msg.networks = rxportclass.a.get("Networks",None)
            # ActivityTimeout(pub)= 3* RefreshPeriod(pub)  the DP that send to RP in DS system
            '''
            if float(txportclass.a.get('RefreshPeriod',0))*3 != float(txportclass.a.get('ActivityTimeout',0)):
                msg.skip='EC002'
                msg.ErrorCode='EC002'
                logger.nerror('Message: %s the ActivityTimeout is not equil to 3*RefreshPeriod' %msg.msgname, ERRORCODE='EC002',FILE=txport.filename) 
            '''
            msg.lrulist = '\n'.join(msg.msglru)
            msg.atalist = '\n'.join(msg.ata)
        def analysisCANRxMsg(msg):
            '''
            lru
            messagename
            txlength
            rxlength
            txrate
            rxrate
            canid
            physport
            '''
            txmsg = msg.txmsg
            txmsgclass = msg.txmsgclass
            txport = txmsg.parent
            rxport = msg.rxport
            if rxport is not None:
                rxportclass = self.guidref[rxport.a.GuidDef]
            else:
                rxportclass = None
            #rxlru = getrootnode(rxport)
            txlru = getrootnode(txmsg)
            msg.skip = ''
            msg.lru = txlru.a.get('Name',None)
            msg.msgname = txmsg.a.get('Name',None)
            msg.txlength = _getAttrib(txmsgclass,'MessageSize',int)
            #msg.rxlength = rxportclass.a.get('MessageSize',None) in rx side, can do not have message, below teh CANPort, it the RPs
            msg.txcanid =txport.a.get('MessageID',None)
            msg.txphysical = txport.a.get('Physical',None)
            msg.txacttime = _getAttrib(txmsgclass.parent,"ActivityTimeout",int)
            msg.txportname = txport.a.get('Name',None)
            msg.txrate = txmsgclass.parent.a.get('RefreshPeriod',None)
            if rxport is None:
                msg.skip='#'
                msg.rxphysical = msg.txphysical
                msg.rxcanid = msg.txcanid
                msg.rxrate = msg.txrate
            else:
                msg.rxphysical = rxport.a.get('Physical',None)
                msg.rxcanid = rxport.a.get('MessageID',None)
                msg.rxrate =  rxportclass.a.get('SamplePeriod',None)           
        
        
        def analysisA429RXMsg(msg):
            '''
            lru
            messagename
            txlength
            rxlength
            txrate
            rxrate
            canid
            physport
            '''
            txmsg = msg.txmsg
            txmsgclass = msg.txmsgclass
            txport = txmsg.parent.parent
            txportclass=txmsgclass.parent.parent
            rxport = msg.rxport
            if rxport is not None:
                rxportclass = self.guidref[rxport.a.GuidDef]
            else:
                rxportclass = None
            #rxlru = getrootnode(rxport)
            txlru = getrootnode(txmsg)
            msg.skip = ''
            msg.lru = txlru.a.get('Name',None)
            msg.msgname = txmsg.a.get('Name',None)
            msg.txlength = int(4)#_getAttrib(txmsgclass,'MessageSize',int)
            #msg.rxlength = rxportclass.a.get('MessageSize',None) in rx side, can do not have message, below teh CANPort, it the RPs
            #msg.txid =int(str(msg.msgname).split("_")[0][1:])
            msg.txphysical = txport.a.get('Physical',None)
            #msg.Label = None#int(str(msg.msgname).split("_")[0][1:])
            msg.txportname = txport.a.get('Name',None)
            #msg.txacttime = _getAttrib(txmsgclass.parent,"ActivityTimeout",int)
            if(txportclass.tag != 'A429Channel'):
                msg.txrate = _getAttrib(txportclass,  "RefreshPeriod", float)
            else:
                msg.txrate = _getAttrib(txportclass,  "TransmissionIntervalMinimum", float)
            
            if rxport is None:
                msg.skip='#'
                msg.rxphysical = msg.txphysical               
                msg.rxrate = msg.txrate
            else:
                msg.rxphysical = rxport.a.get('Physical',None)                
                msg.rxrate =  rxportclass.a.get('SamplePeriod',None)         
            msg.rxportname = rxport.a.Name
            msg.txchlname = txmsg.parent.a.Name
            msg.txprotocoltype = txmsgclass.parent.a.get('A429ProtocolType',None)
            
            
        #start the function
        for msgid, rxmsg in self.rxmsglists.items():
            if rxmsg.msgtype == 'A664Message':
                analysisAFDXRxMsg(rxmsg)                
            elif rxmsg.msgtype == 'CANMessage':
                analysisCANRxMsg(rxmsg)
            elif rxmsg.msgtype == 'A429Word':
                analysisA429RXMsg(rxmsg)
            else:
                logger.error('Unknown rx msg type:%s'% msgid)
        
    def AnalysisOutputMessages(self):

        
        def analysisAFDXTxMsg(msg):
            '''
            Fill the details needed by the XLS table
            - Lru             HF/HA name used (together with msg name) as key to match from the signal tab. 
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
            
            txmsg = msg.txmsg
            txmsgclass = msg.txmsgclass
            txportclass = txmsgclass.parent
            #rxport = msg.rp['port']  # in receive side, below the Port is the RP. without the message defined, so the messagesize is defined in the rxportclass
            txport = msg.txmsg.parent
            txlru =getrootnode(txmsg)
            #rxlru = getrootnode(rxport)
            #rxportclass = self.guidref[rxport.a.GuidDef]
            if txport.tag.endswith("SamplingPort"):
                txtype = "SAMPLING"
            else:
                txtype = "QUEUEING"
            msg.skip = ''
            msg.ErrorCode = None
            msg.vlid = txmsg.a.get('VLID',None)
            msg.subvlid = txmsg.a.get('SubVLID',None)
            msg.edeenable = txmsgclass.a.get('EdeEnable',None)
            msg.overhead = txmsgclass.a.get('MessageOverhead', None)
            msg.txlength =_getAttrib( txmsgclass,'MessageSize',int)
            msg.lru = txlru.a.get('Name',None)
            msg.msgname = txmsg.a.get('Name', None)
            msg.srcip = _getAttrib(txlru,'IpAddress', None)#, '10.0.0.1')
            msg.networks = txportclass.a.get("Networks", None)
            msg.acttime = _getAttrib(txportclass,'ActivityTimeout', int)
            msg.msgdataprotocoltype   = txmsgclass.a.get('MsgDataProtocolType', None)
            msg.transmissionintervalminimum   = _getAttrib(txmsgclass,'TransmissionIntervalMinimum', float)
            
            msg.type = txtype  
            if txport.tag.endswith("QueuingPort"):
                msg.queuelength =_getAttrib(txportclass,"QueueLength", int)
            else:
                msg.queuelength = 1        
                        
            msg.BAG = None
            msg.MTU = None
            
            msg.udpsrcid = None
            msg.edesourceid = None
            msg.portid = None
            msg.portname = None
            msg.udpdetiid = None
            msg.destip = None
            if msg.vlid:
                node1 = self.vls.get(msg.vlid,None)
                node = node1.virtuallink
                if node:
                    msg.BAG = node.a.get('BAG',None)
                    msg.MTU = node.a.get('MTU',None)
                    '''
                    for comportrx in node.e.get('ComPortRx',[]):
                        for PortRefnode in comportrx.e.get('Port_Ref',[]):
                            if PortRefnode.a.Name == rxlru.a.Name + rxport.a.Name:
                                msg.portid = comportrx.a.get('ID',None)
                                msg.udpdstid = comportrx.a.get('UdpDstId',None)
                    '''
                    comporttxNode = None 
                    for comporttx in node.e.get('ComPortTx',[]):

                        for portref in comporttx.e.get('Port_Ref',[]):
                            if portref.a.Name == txlru.a.Name +'.'+ txport.a.Name:
                                msg.udpsrcid = comporttx.a.get('UdpSrcId',None)
                                msg.edesourceid = comporttx.a.get('ID',None)
                                msg.portid = comporttx.a.get('ID',None)
                                msg.portname = comporttx.a.get('Name',None)
                                comporttxNode = comporttx                             
                    
                    if comporttxNode is None:
                        logger.nerror(' [%s] The DP: %s has no Comporttx in virtuallinks'% ("EC011",txlru.a.Name + txport.a.Name),ERRORCODE='EC011')
                        msg.skip = '#'
                        msg.ErrorCode = 'EC011'
                        return            
                    for comportrx in node.e.get('ComPortRx',[]):
                        txport_ref = comportrx.e.get('TxPort_Ref',[])
                        if len(txport_ref) > 1:
                            logger.error('The comportrx %s has more than one txport_ref' % comportrx.a.Guid)
                            return
                        if comporttxNode.a.Name == txport_ref[0].a.get('Name').split('.')[1]: 
                            msg.udpdetiid = comportrx.a.get('UdpDstId',None)
                            if comporttxNode.a.get('IPDestAddrFormat',None) == 'MULTICAST':
                                msg.destip = '224.224.%d.%d'%(int(msg.vlid)/256,int(msg.vlid)%256)
                            else:
                                compubrefname = comportrx.a.get('Name',[])
                                hfname = compubrefname.split('$')[0]
                                for hanodes in self.root.e.values():
                                    for hanode in hanodes:
                                        if hanode.a.get('Name',None) == hfname:
                                            msg.destip = hanode.a.get('IpAddress')                                    
                            
                    
            
            msg.sourecMACA, msg.sourecMACB = getsourceMAC(self.root,txlru)
            msg.txrate = txportclass.a.get('RefreshPeriod',None) 
           
             
            
        def analysisCANTxMsg(msg):
            '''
            lru
            messagename
            txlength
            rxlength
            txrate
            rxrate
            canid
            physport
            '''
            txmsg = msg.txmsg
            txmsgclass = msg.txmsgclass
            txport = txmsg.parent
            txportclass = txmsgclass.parent
            #rxport = msg.dp['port']            
            #rxportclass = self.guidref[rxport.a.GuidDef]
            #rxlru = getrootnode(rxport)
            txlru = getrootnode(txmsg)
            msg.skip = ''
            msg.lru = txlru.a.get('Name',None)
            if msg.a429word:
                msg.msgname = txmsg.a.get('Name',None) + '.' + msg.a429word.a.get('Name',None)
            else:
                msg.msgname = txmsg.a.get('Name',None)
            msg.acttime = _getAttrib( txmsgclass.parent,'ActivityTimeout',int)
            msg.partitionid = _getAttrib( txmsgclass.parent,'PartitionId',int)
            msg.canprotype = txmsgclass.parent.a.get('CANMessageProtocolType',None)
            
            msg.txlength =_getAttrib( txmsgclass,'MessageSize',int)
            #msg.rxlength = rxportclass.a.get('MessageSize',None) in rx side, can do not have message, below teh CANPort, it the RPs
            msg.txcanid =txport.a.get('MessageID',None)
            msg.txphysical = txport.a.get('Physical',None)
            #msg.rxphysical = rxport.a.get('Physical',None)
            #msg.rxcanid = rxport.a.get('MessageID',None)
            #msg.rxrate =  rxportclass.a.get('SamplePeriod',None)
            msg.txrate = txmsgclass.parent.a.get('RefreshPeriod',None)
             #   ActivityTimeout(pub)= 3* RefreshPeriod(sub) in the DP side of DS system only for can
            if msg.acttime is not None and msg.txrate is not None and 3*float(msg.txrate) != float(msg.acttime):
                msg.skip=''
                msg.ErrorCode='EC019'
                logger.nerror(' [%s] The Publish msg: %s ActivityTimeout != 3* RefreshPeriod'% ("EC019",msg.msgname), ERRORCODE='EC019',FILE=txport.filename)
         
        def analysis429TxMsg(msg):
            '''
            lru
            messagename
            txlength
            rxlength
            txrate
            rxrate
            canid
            physport
            '''
            txmsg = msg.txmsg
            txmsgclass = msg.txmsgclass
            txport = txmsg.parent.parent
            txportclass = txmsgclass.parent.parent
            #rxport = msg.dp['port']            
            #rxportclass = self.guidref[rxport.a.GuidDef]
            #rxlru = getrootnode(rxport)
            txlru = getrootnode(txmsg)
            msg.skip = ''
            msg.lru = txlru.a.get('Name',None)
            msg.msgname = txmsg.a.get('Name',None)
            msg.acttime = _getAttrib( txmsgclass.parent,'ActivityTimeout',int)           
            msg.a429protype = txmsgclass.parent.a.get('A429ProtocolType',None)
            
            msg.txlength =int(4)#_getAttrib( txmsgclass,'MessageSize',int)
            #msg.rxlength = rxportclass.a.get('MessageSize',None) in rx side, can do not have message, below teh CANPort, it the RPs
            #msg.txid = int(str(txmsg.a.Name).split("_")[0][1:])
            #msg.Label = None#int(str(txmsg.a.Name).split("_")[0][1:])
            #msg.SDI = None
            msg.txphysical = txport.a.get('Physical',None)
            #msg.rxphysical = rxport.a.get('Physical',None)
            #msg.rxcanid = rxport.a.get('MessageID',None)
            #msg.rxrate =  rxportclass.a.get('SamplePeriod',None)
            msg.txrate = txportclass.a.get('RefreshPeriod',None)
            msg.txportname = txport.a.Name
            msg.txchlname = txmsg.parent.a.Name
             #   ActivityTimeout(pub)= 3* RefreshPeriod(sub) in the DP side of DS system only for can
            if msg.acttime is not None and msg.txrate is not None and 3*float(msg.txrate) != float(msg.acttime):
                msg.skip=''
                msg.ErrorCode='EC019'
                logger.nerror(' [%s] The Publish msg: %s ActivityTimeout != 3* RefreshPeriod'% ("EC019",msg.msgname), ERRORCODE='EC019',FILE=txport.filename)
        
        #start function
        for msgid,txmsg in self.txmsglists.items():
            if txmsg.msgtype == 'A664Message':
                analysisAFDXTxMsg(txmsg)
            elif txmsg.msgtype == 'CANMessage':
                analysisCANTxMsg(txmsg)
            elif txmsg.msgtype == 'A429Word':
                analysis429TxMsg(txmsg)
            else:
                logger.error('Unknown tx msg type:%s'% msgid)    

    def AnalysisInputSignals(self): #RPlist          
            
        
        def getDSAttrib(rp, xdp, xds, xdpclass, xdsclass):
            rp.DsName        = xds.a.Name
            rp.ByteOffsetFSB = _getAttrib(xdsclass,"ByteOffsetFSF",int)
            rp.ByteOffsetDS  = _getAttrib(xdsclass,"ByteOffsetWithinMsg",int)
            rp.ByteSizeDS    = _getAttrib(xdsclass,"DataSetSize",int)

        def getDPDSAttrib(rp, xdp, xds, xdpclass, xdsclass):
            rp.SigName       = xdp.a.Name
            rp.DsName        = xds.a.Name
            rp.ByteOffsetFSB = _getAttrib(xdsclass,"ByteOffsetFSF",int)
            rp.ByteOffsetDS  = _getAttrib(xdsclass,"ByteOffsetWithinMsg",int)
            rp.ByteSizeDS    = _getAttrib(xdsclass,"DataSetSize",int)
            rp.BitOffset     = _getAttrib(xdpclass,"BitOffsetWithinDS", int)
            rp.BitSize       = _getAttrib(xdpclass,"ParameterSize", int)
            rp.transmissionintervalminimum = _getAttrib(xdpclass,"TransmissionIntervalMinimum", float)
            rp.publishedlatency = _getAttrib(xdpclass,"PublishedLatency", int)
            rp.fullscalerangemax = xdpclass.a.get("FullScaleRngMax",None)
            rp.fullscalerangemin = xdpclass.a.get("FullScaleRngMin",None)
            rp.functionalrangemax = xdpclass.a.get("FuncRngMax",None)
            rp.functionalrangemin = xdpclass.a.get("FuncRngMin",None)
            rp.codeset = xdpclass.a.get("CodedSet", None)
            rp.units = xdpclass.a.get("Units",None)
            rp.onestate = xdpclass.a.get("OneState",None)
            rp.zerostate = xdpclass.a.get("ZeroState",None)           
            rp.Encoding      = xdpclass.a.get("DataFormatType")
            if rp.Encoding == "BNR" or rp.Encoding == "UBNR" or rp.Encoding == "BCD":
                rp.LsbValue        = _getAttrib(xdpclass,"LsbRes", float,default=1)
            else:
                rp.LsbValue        = None

        def getDPDSAttribA429(rp, xdp, xds, xdpclass, xdsclass):
            rp.SigName       = xdp.a.Name
            rp.DsName        = xds.a.Name
            rp.ByteOffsetFSB = _getAttrib(xdsclass,"ByteOffsetFSF",int)
            rp.ByteOffsetDS  = _getAttrib(xdsclass,"ByteOffsetWithinMsg", int)
            rp.ByteSizeDS    = _getAttrib(xdsclass,"DataSetSize", int)
            
            rp.BitOffset     = _getAttrib(xdpclass,"BitOffsetWithinDS", int)

            rp.BitSize       = _getAttrib(xdpclass,"ParameterSize", int)
            rp.transmissionintervalminimum = _getAttrib(xdpclass,"TransmissionIntervalMinimum", float)
            rp.publishedlatency = _getAttrib(xdpclass,"PublishedLatency", int)
            rp.fullscalerangemax = xdpclass.a.get("FullScaleRngMax",None)
            rp.fullscalerangemin = xdpclass.a.get("FullScaleRngMin",None)
            rp.functionalrangemax = xdpclass.a.get("FuncRngMax",None)
            rp.functionalrangemin = xdpclass.a.get("FuncRngMin",None)
            rp.codeset = xdpclass.a.get("CodedSet", None)
            rp.units = xdpclass.a.get("Units",None)
            rp.onestate = xdpclass.a.get("OneState",None)
            rp.zerostate = xdpclass.a.get("ZeroState",None)       
            rp.Encoding      = xdpclass.a.get("DataFormatType")
            if rp.Encoding == "BNR" or rp.Encoding == "UBNR" or rp.Encoding == 'BCD':
                rp.LsbValue        = _getAttrib(xdpclass,"LsbRes",float,default = 1)
            else:
                rp.LsbValue        = 1  #set to 1 or nonoe
            
            

            # The ICD contains many errors regarding BitOffset of Signals embedded in 429 Words
            # We do a plausibility check and repair the value if it is wrong
            # get parent (A429Word) offset and check wether signal offset is within the word
            # If not compute the most plausible value but create an entry in the log
            a429wordoffset = _getAttrib(xdpclass.parent,"BitOffsetWithinDS", int)
            if rp.BitOffset < 0 or rp.BitOffset > 32:
                logger.nerror(" [%s] BitOffset of embedded A429 Word inconsistent"% 'EC008', DP=xdp.a.Name, DS=xds.a.Name ,ERRORCODE='EC008',FILE=xdp.filename)
                rp.skip = '#'
                rp.ErrorCode = 'EC008'

            if a429wordoffset is not None:
                rp.BitOffset = rp.BitOffset % 32 + a429wordoffset
                
        def getDirectAttribA429(rp, xdp, xds, xdpclass, xdsclass):
            #rp.txportname    = rp.msgref.txportname
            rp.txchannel     = rp.msgref.txchlname
            rp.SigName       = xdp.a.Name
            rp.DsName        = xds.a.Name
            rp.ByteOffsetFSB = _getAttrib(xdsclass,"ByteOffsetFSF",int)
            rp.ByteOffsetDS  = _getAttrib(xdsclass,"ByteOffsetWithinMsg", int)
            rp.ByteSizeDS    = _getAttrib(xdsclass,"DataSetSize", int)
            
            rp.BitOffset     = _getAttrib(xdpclass,"BitOffsetWithinDS", int)

            rp.BitSize       = _getAttrib(xdpclass,"ParameterSize", int)
            rp.transmissionintervalminimum = _getAttrib(xdpclass,"TransmissionIntervalMinimum", float)
            rp.publishedlatency = _getAttrib(xdpclass,"PublishedLatency", int)
            rp.fullscalerangemax = xdpclass.a.get("FullScaleRngMax",None)
            rp.fullscalerangemin = xdpclass.a.get("FullScaleRngMin",None)
            rp.functionalrangemax = xdpclass.a.get("FuncRngMax",None)
            rp.functionalrangemin = xdpclass.a.get("FuncRngMin",None)
            rp.codeset = xdpclass.a.get("CodedSet", None)
            rp.units = xdpclass.a.get("Units",None)
            rp.onestate = xdpclass.a.get("OneState",None)
            rp.zerostate = xdpclass.a.get("ZeroState",None)       
            rp.Encoding      = xdpclass.a.get("DataFormatType")
            if rp.Encoding == "BNR" or rp.Encoding == "UBNR" or rp.Encoding == 'BCD':
                rp.LsbValue        = _getAttrib(xdpclass,"LsbRes",float,default = 1)
            else:
                rp.LsbValue        = 1  #set to 1 or nonoe
            
            #print 'come into direct 429 rp analysis'
            if rp.get('rp'):
                
                # this is a genuine RP, not a virtual one added by expansion
                xrpclass = rp.rpclass
                label = xrpclass.a.Label
                sdi   = xrpclass.a.SDIExpected
                print 'label is %s' % label
                if rp.msgref.get("Label") is None:
                    rp.msgref.Label = label
                    rp.msgref.SDI = sdi
                else:
                    if rp.msgref.Label != label:
                        logger.error("Inconsistent LABEL Values: RP=%s Label=%s Message=%s Label=%s",
                                     rp.rpName, label, rp.msgref.txmsg.a.Name, rp.msgref.Label)
                    if rp.msgref.SDI != sdi:
                        logger.error("Inconsistent SDI Values: RP=%s Label=%s Message=%s Label=%s",
                                     rp.rpName, label, rp.msgref.txmsg.a.Name, rp.msgref.Label)
                    
            

            # The ICD contains many errors regarding BitOffset of Signals embedded in 429 Words
            # We do a plausibility check and repair the value if it is wrong
            # get parent (A429Word) offset and check wether signal offset is within the word
            # If not compute the most plausible value but create an entry in the log
            a429wordoffset = _getAttrib(xdpclass.parent,"BitOffsetWithinDS", int)
            if rp.BitOffset < 0 or rp.BitOffset > 32:
                logger.nerror(" [%s] BitOffset of embedded A429 Word inconsistent"% 'EC008', DP=xdp.a.Name, DS=xds.a.Name ,ERRORCODE='EC008',FILE=xdp.filename)
                rp.skip = '#'
                rp.ErrorCode = 'EC008'

            if a429wordoffset is not None:
                rp.BitOffset = rp.BitOffset % 32 + a429wordoffset
    
        def getDPDSAttribA429block(rp, xdp, xdpclass ):
            rp.SigName       = xdp.a.Name
            #rp.DsName        = None
            #rp.ByteOffsetFSB = None
            #rp.ByteOffsetDS  = None
            #rp.ByteSizeDS    = None
            
            #rp.BitOffset     = _getAttrib(xdpclass,"BitOffsetWithinDS", int)

            #rp.BitSize       = _getAttrib(xdpclass,"ParameterSize", int)
            rp.transmissionintervalminimum = _getAttrib(xdpclass,"TransmissionIntervalMinimum", float)
            rp.publishedlatency = _getAttrib(xdpclass,"PublishedLatency", int)
            rp.fullscalerangemax = xdpclass.a.get("FullScaleRngMax",None)
            rp.fullscalerangemin = xdpclass.a.get("FullScaleRngMin",None)
            rp.functionalrangemax = xdpclass.a.get("FuncRngMax",None)
            rp.functionalrangemin = xdpclass.a.get("FuncRngMin",None)
            rp.codeset = xdpclass.a.get("CodedSet", None)
            rp.units = xdpclass.a.get("Units",None)
            rp.onestate = xdpclass.a.get("OneState",None)
            rp.zerostate = xdpclass.a.get("ZeroState",None)       
            rp.Encoding      = xdpclass.a.get("DataFormatType")
            if rp.Encoding == "BNR" or rp.Encoding == "UBNR" or rp.Encoding == "BCD":
                rp.LsbValue        = _getAttrib(xdpclass,"LsbRes",float,default = 1)
            else:
                rp.LsbValue        = None  #set to 1 or nonoe

            # The ICD contains many errors regarding BitOffset of Signals embedded in 429 Words
            # We do a plausibility check and repair the value if it is wrong
            # get parent (A429Word) offset and check wether signal offset is within the word
            # If not compute the most plausible value but create an entry in the log
            '''
            a429wordoffset = _getAttrib(xdpclass.parent,"BitOffsetWithinDS", int)
            if rp.BitOffset < 0 or rp.BitOffset > 32:
                logger.nerror(" [%s] BitOffset of embedded A429 Word inconsistent" % 'EC008', DP=xdp.a.Name, DS='429block' ,ERRORCODE='EC008',FILE=xdp.filename)
                rp.skip = '#'
                rp.ErrorCode = 'EC008'
            if a429wordoffset is not None:
                rp.BitOffset = rp.BitOffset % 32 + a429wordoffset
            '''
        
        def getDPDSAttribA429_1(rp, xdp, xdpclass):
            if xdp.tag != 'A429Word':
                xds = xdp.parent.parent
                xdsclass = xdpclass.parent.parent
                                
                rp.BitOffset     = _getAttrib(xdpclass,"BitOffsetWithinDS", int)
    
                rp.BitSize       = _getAttrib(xdpclass,"ParameterSize", int)
                rp.transmissionintervalminimum = _getAttrib(xdpclass,"TransmissionIntervalMinimum", float)
                rp.publishedlatency = _getAttrib(xdpclass,"PublishedLatency", int)
                rp.Encoding      = xdpclass.a.get("DataFormatType")
                rp.fullscalerangemax = xdpclass.a.get("FullScaleRngMax",None)
                rp.fullscalerangemin = xdpclass.a.get("FullScaleRngMin",None)
                rp.functionalrangemax = xdpclass.a.get("FuncRngMax",None)
                rp.functionalrangemin = xdpclass.a.get("FuncRngMin",None)
                rp.units = xdpclass.a.get("Units",None)
                rp.codeset = xdpclass.a.get("CodedSet", None)
                rp.onestate = xdpclass.a.get("OneState",None)
                rp.zerostate = xdpclass.a.get("ZeroState",None)       
                if rp.Encoding == "BNR" or rp.Encoding == "UBNR" or rp.Encoding == "BCD":
                    rp.LsbValue        = _getAttrib(xdpclass,"LsbRes",float,default = 1)
                else:
                    rp.LsbValue        = None
    
                # The ICD contains many errors regarding BitOffset of Signals embedded in 429 Words
                # We do a plausibility check and repair the value if it is wrong
                # get parent (A429Word) offset and check wether signal offset is within the word
                # If not compute the most plausible value but create an entry in the log
                a429wordoffset = _getAttrib(xdpclass.parent,"BitOffsetWithinDS", int)
                if rp.BitOffset < 0 or rp.BitOffset > 32:
                    logger.nerror(" [%s] BitOffset of embedded A429 Word inconsistent"%'EC008', DP=xdp.a.Name, DS=xds.a.Name ,ERRORCODE='EC008',FILE=xdp.filename)
                    rp.skip = '#'
                    rp.ErrorCode = 'EC008'
                if a429wordoffset is not None:
                    rp.BitOffset = rp.BitOffset % 32 + a429wordoffset
            
            else:
                xds = xdp.parent
                xdsclass = xdpclass.parent
                rp.BitOffset     = None    
                rp.BitSize       = None
                rp.Encoding      = None             
                rp.LsbValue      = None
                rp.BitOffset = None
                
            rp.SigName       = xdp.a.Name
            rp.DsName        = xds.a.Name
            rp.ByteOffsetFSB = _getAttrib(xdsclass,"ByteOffsetFSF",int)
            rp.ByteOffsetDS  = _getAttrib(xdsclass,"ByteOffsetWithinMsg", int)
            rp.ByteSizeDS    = _getAttrib(xdsclass,"DataSetSize", int)

        def getCANDPAttrib(rp, xdp, xdpclass):
            rp.SigName       = xdp.a.Name
            rp.DsName        = "N/A"
            rp.ByteOffsetFSB = None
            rp.ByteOffsetDS  = None
            rp.ByteSizeDS    = _getAttrib(xdpclass.parent,"MessageSize", int)
            rp.BitOffset     = _getAttrib(xdpclass,"BitOffsetWithinDS", int)
            rp.BitSize       = _getAttrib(xdpclass,"ParameterSize", int)
            rp.Encoding      = xdpclass.a.get("DataFormatType")
            rp.msgsize = _getAttrib(rp.msgclass,'MessageSize',int)
            
            rp.transmissionintervalminimum = _getAttrib(xdpclass,"TransmissionIntervalMinimum", float)
            rp.publishedlatency = _getAttrib(xdpclass,"PublishedLatency", int)
            rp.fullscalerangemax = xdpclass.a.get("FullScaleRngMax",None)
            rp.fullscalerangemin = xdpclass.a.get("FullScaleRngMin",None)
            rp.functionalrangemax = xdpclass.a.get("FuncRngMax",None)
            rp.functionalrangemin = xdpclass.a.get("FuncRngMin",None)
            rp.codeset = xdpclass.a.get("CodedSet", None)
            rp.units = xdpclass.a.get("Units",None)
            rp.onestate = xdpclass.a.get("OneState",None)
            rp.zerostate = xdpclass.a.get("ZeroState",None)       
            
        def consistencyCheck(rp):
            if rp.blockflag:
                return
            if rp.ByteOffsetDS is None or rp.ByteSizeDS is None:
                logger.nerror("RP ByteOffsetDS and ByteSizeDS is None", 
                              RP= rp.name, DS=rp.DsName, Msg=rp.msgref.msgname, MsgSize=rp.msgref.txlength)
                return
            if ((rp.ByteOffsetDS + rp.ByteSizeDS) > rp.msgref.txlength):
                rp.skip = '#'
                rp.Errorcode = 'EC016'
                rp.msgref.skip = 'EC016'
                logger.nerror(" [%s] RP Dataset size inconsistent with message size, skipped."%'EC016', 
                              RP= rp.name, DS=rp.DsName, DSsize=rp.ByteSizeDS, 
                              Msg=rp.msgref.msgname, MsgSize=rp.msgref.txlength)
            if (rp.BitOffset is None or rp.BitSize is None):
                logger.nerror("RP BitOffset and BitSize is None", 
                              RP= rp.name, DS=rp.DsName, Msg=rp.msgref.msgname, MsgSize=rp.msgref.txlength)
                return    
            if ((rp.BitOffset+rp.BitSize) > rp.ByteSizeDS*8):
                rp.skip = '#'
                rp.Errorcode = 'EC017'
                logger.nerror(" [%s] RP bitoffset add bitsize is overflow the Dataset size."%'EC017', 
                              RP= rp.name, DS=rp.DsName, DSsize=rp.ByteSizeDS, 
                              RPoffset=rp.BitOffset, RPSize=rp.BitSize,ERRORCODE='EC017')
                
        
        def TiemCheck(rp):
            #1 RefreshPeriod(pub)= TransmissionIntervalMinimum(pub)
            if rp.transmissionintervalminimum is not None and rp.msgref.txrate is not None and float(rp.transmissionintervalminimum) < float(rp.msgref.txrate):
                #rp.skip = ''
                rp.Errorcode = 'EC020'
                logger.nerror(' [%s] RP = %s : RefreshPeriod(pub) > TransmissionIntervalMinimum(pub)'% ("EC020",rp.name), ERRORCODE='EC020',FILE=rp.port.filename)
            if rp.msgref.rxsamrate is not None and rp.msgref.txrate is not None and float(rp.msgref.rxsamrate) > float(rp.msgref.txrate):
                #rp.skip = ''
                rp.Errorcode = 'EC021'
                logger.nerror(' [%s] RP = %s : The Pub RefreshPeriod < The Sub SamplePeriod'%  ("EC021",rp.name), ERRORCODE='EC021',FILE=rp.port.filename)
                
        def Add_attr_analog(rp):
            
            def getportnode(xdp):
                
              
                if xdp.tag == 'AnalogPort':
                    return xdp                                    
                while xdp.parent:
                    xdp = xdp.parent
                    if xdp.tag == 'AnalogPort':
                        return xdp
                return None
            
            originaldp= self.guidref.get(rp.pubsrcguid,None)
            if originaldp:
                originaldpport = getportnode(originaldp)
                if originaldpport:
                    originaldpportclass = self.guidref.get(originaldpport.a.GuidDef,None)
                    rp.RIUTemplate = _getAttrib(originaldpportclass,"RIUTemplate", int)
                    rp.UDC  = originaldpportclass.a.get('UDC',None)
                    
                
        #------ start function body -------------------------
        
        for rprec in self.rplists.values():
        #for rprec in rpreclist:
            # initialize all attributes to none
            rprec.LruName         = None
            rprec.MsgName         = None
            rprec.nesting         = None
            #rprec.DsName          = None
            rprec.SigName         = None
            rprec.SourceSelection = None
            #rprec.ByteOffsetFSB   = None
            #rprec.ByteOffsetDS    = None
            #rprec.ByteSizeDS      = None
            #rprec.BitOffset       = None
            #rprec.BitSize         = None
            rprec.LsbValue        = None
            rprec.Encoding        = None
            rprec.sysLatencywclimit = None
            rprec.multiplier    =None
            rprec.label         =None
            rprec.transmissionintervalminimum = None
            rprec.codedset  = None
            rprec.fullscalerangemax = None
            rprec.fullscalerangemin = None
            rprec.functionalrangemax = None
            rprec.functionalrangemin = None
            rprec.publishedlatency = None
            rprec.units             = None
            rprec.onestate          = None
            rprec.zerostate         = None
            rprec.RIUTemplate       = None
            rprec.UDC               = None
            if rprec.blockflag is False:
                rprec.DsName        = None
                rprec.ByteOffsetFSB = None
                rprec.ByteOffsetDS  = None
                rprec.ByteSizeDS    = None
                rprec.BitOffset       = None
                rprec.BitSize         = None
            
            #rprec.originallru = None
            
            if rprec.dp is None:
                # no further processing is possible
                continue
            if rprec.ErrorCode == 'EC005':
                continue
            
            
            #print rprec.name
            rprec.LruName         = rprec.msgref.lru
            rprec.Portname        = rprec.msgref.txportname
            #if rprec.LruName in['HF_FCM_1','HF_FCM_2','HF_FCM_3']:
            #    rprec.originallru = rprec.LruName            
            
            #add this code to add UDC and RIUTemplate for analog signal
            #if "_Analog_" in rprec.LruName:
            #    Add_attr_analog(rprec)
            
            rprec.MsgName         = rprec.msgref.msgname
            if rprec.blockflag == False:
                rprec.nesting         = _getDSPath(rprec.dp, rprec.msgref.msgtype)
            else:
                rprec.nesting = None

            xdp           = rprec.dp
            xdpclass      = rprec.dpclass
            path          = rprec.nesting            
            xrpclass      = rprec.rpclass
            
            if xrpclass:
                rprec.sysLatencywclimit = _getAttrib(xrpclass,"SysLatencyWCLimit", int)
                rprec.multiplier    = xrpclass.a.get("Multiplier", None)
                rprec.label         = _getAttrib(xrpclass,"Label", int)
                #rprec.originallru = rprec.msgref.originallru

            if path == 'A664Message.DS.DP':
                # for gateways, this is the object itself
                getDPDSAttrib(rprec, xdp, xdp.parent, xdpclass, xdpclass.parent)
                if rprec.ByteOffsetFSB == 0 and rprec.ByteOffsetDS == 0:
                    # we find this for A661 Blocks
                    rprec.ByteOffsetFSB = None
                
                if rprec.ByteOffsetFSB is not None:
                    rprec.SourceSelection = 'FRESH,FSB'
                else:
                    rprec.SourceSelection = 'FRESH'
                #TiemCheck(rprec)
            elif path == 'A664Message.DS.A429Word.DP':
                
                getDPDSAttribA429(rprec, xdp, xdp.parent.parent, xdpclass, xdpclass.parent.parent)
                rprec.SourceSelection = 'FRESH,FSB'
                # lookup SSM in sibling DPs
                ssmtype = _getSSMType(xdpclass)
                if ssmtype:
                    rprec.SourceSelection += ',' + ssmtype
                #TiemCheck(rprec)
            elif path == 'A664Message.DS.A429Word':
                # Already expanded in ProcessRP
                getDPDSAttribA429_1(rprec,xdp,xdpclass) 
                rprec.SourceSelection = 'FRESH,FSB'
                # lookup SSM in sibling DPs
                ssmtype = _getSSMType(xdpclass)
                if ssmtype:
                    rprec.SourceSelection += ',' + ssmtype    
                #TiemCheck(rprec)           
                #logger.nerror("Unsupported signal nesting [%s]" % path, RP=rprec.name)
            elif path == 'A664Message.DS.CANMessage.DP':
                getDPDSAttrib(rprec, xdp, xdp.parent.parent, xdpclass, xdpclass.parent.parent)
                rprec.SourceSelection = 'FRESH, FSB'
                #TiemCheck(rprec)
            elif path == 'A664Message.DS.CANMessage.A429Word.DP':
                getDPDSAttrib(rprec, xdp, xdp.parent.parent.parent, xdpclass, xdpclass.parent.parent.parent)
                rprec.SourceSelection = 'FRESH,FSB'
                # lookup SSM in sibling DPs
                ssmtype = _getSSMType(xdpclass)
                if ssmtype:
                    rprec.SourceSelection += ',' + ssmtype   
                #TiemCheck(rprec)            
            elif path == 'CANMessage.DP':                      
                getCANDPAttrib(rprec, xdp, xdpclass)
            elif path == 'CANMessage.A429Word.DP':
                getCANDPAttrib(rprec, xdp, xdpclass)
            elif path == 'A429Word.DP' or path == 'A429Word':
                getDirectAttribA429(rprec, xdp, xdp.parent, xdpclass, xdpclass.parent)
                if rprec.LruName.startswith('RGW'):
                    rprec.SourceSelection = 'FRESH'
                else:
                    rprec.SourceSelection = ''
                # lookup SSM in sibling DPs
                #print rprec.name
                #print xdpclass.a.Name
                #print xdpclass.a.Guid
                ssmtype = _getSSMType(xdpclass)
                if ssmtype:
                    rprec.SourceSelection += ',' + ssmtype
            else:
                if rprec.blockflag is True:
                    getDPDSAttribA429block(rprec, xdp,  xdpclass )
                else:
                    logger.nerror("Unsupported signal nesting [%s]" % path, RP=rprec.name)
            if rprec.Encoding not in encodelist:
                encodelist.append(rprec.Encoding)
                
            if  rprec.name == 'DME4000L_429_CH1' :
                pass
            
            if rprec.type == 'A664Message':
                consistencyCheck(rprec)
                TiemCheck(rprec)
            

         
        
    
    def makeRpXref(self,root):
        '''
        Traverse hosted function/application and create an index RP->DP
        '''
        functypes = ("HostedFunction", "A653ApplicationComponent")
        porttypes = ("HFSamplingPort", "HFQueuingPort", "A653SamplingPort", "A653QueuingPort", "CANPort", "A429Port")
        
        for functype in functypes:
            for xha in root.e.get(functype, []):
                for porttype in porttypes:
                    for xport in xha.e.get(porttype, []):
                        for xrp in xport.e.get('RP', []):
                            for pubref in xrp.e.get("Pub_Ref", []):
                                self.pubrefxref[pubref.a.SrcGuid].append((xha, xport, xrp))



    inSigAFDXColumns = (
        # header,                    value,                   len
          ("Skip",                   "skip",                        5),
          ("RP",                     "name",                       40),
          #("DataFormatType",         "dataformattype",             40),
          ("Pub_Ref",                "pubref",                     40),
          ("HostedFunction",         "LruName",                    20),
          ("Original Soruce LRU",    "originallru",                20),
          ("PortName",            "Portname",                    40),
          ("A664Message",            "MsgName",                    40),
          ("DS",                     "DsName",                     40),
          ("DP",                     "SigName",                    30),
          ("Validity",        "SourceSelection",            15),  #how to define this para
          ("ByteOffsetFSF",          "ByteOffsetFSB",              10),
          ("ByteOffsetWithinMsg",    "ByteOffsetDS",               10),
          ("DataSetSize",            "ByteSizeDS",                 10),
          ("DataFormatType",                "Encoding",                   10),
          ("BitOffsetWithinDS",      "BitOffset",                  10),
          ("ParameterSize",          "BitSize",                    10),
          ("LsbRes",                 "LsbValue",                   10),
          ("SysLatencyWCLimit",      "sysLatencywclimit",          10),
          ("Multiplier",             "multiplier",                 10),
          ("Label",                  "label",                      10),
          ("TransmissionIntervalMinimum",    "transmissionintervalminimum",           10),
          ("CodedSet",               "codedset",                   10),
          ("FullScaleRngMax",      "fullscalerangemax",          10),
          ("FullScaleRngMin",      "fullscalerangemin",          10),
          ("FuncRngMax",     "functionalrangemax",         10),
          ("FuncRngMin",     "functionalrangemin",         10),
          ("PublishedLatency",       "publishedlatency",           10),
          ("Units",                  "units",                      10),
          ("OneState",               "onestate",                   20),
          ("ZeroState",              "zerostate",                  20),
          ("RIUTemplate",           "RIUTemplate",                  10),
          ("UDC",                   "UDC",                          20),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),
    )                  
        

    outSigAFDXColumns = (
        # header,         value,                len
          ("Skip",        "skip",                5),
          ("DP",      "name",               40),
          ("HostedFunction",         "lru",                30),
          ("DS",     "DsName",             40),
          ("A664Message",     "msgname",            40),
          ("Validity",    "Validity",           15),
          ("ByteOffsetFSF",   "ByteOffsetFSB",      10),
          ("ByteOffsetWithinMsg",    "ByteOffsetDS",       10),
          ("DataSetSize",      "ByteSizeDS",         10),
          ("DataFormatType",     "Encoding",           10),
          ("BitOffsetWithinDS",   "BitOffset",          10),
          ("ParameterSize",     "BitSize",            10),
          ("LsbRes",    "LsbValue",           10),
          ("Multiplier",    "multiplier",           10),                 #need to add 
          ("Label",     "label",            10),
          ("TransmissionIntervalMinimum",    "transmissionintervalminimum",           15),
          ("CodedSet",   "codedset",      10),
          ("FullScaleRangeMax",    "fullscalerangemax",       10),
          ("FullScaleRangeMin",      "fullscalerangemin",         10),
          ("FunctionalRangeMax",     "functionalrangemax",           10),
          ("FunctionalRangeMin",   "functionalrangemin",          10),
          ("PublishedLatency",     "publishedlatency",            10),
          ("Units",    "units",           10),          
          ("OneState",   "onestate",          10),
          ("ZeroState",     "zerostate",            10),
          ("Consumer",    "consumer",           10),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),
    )    
  
    outSigCANColumns = (
        # header,         value,                len
          ("Skip",        "skip",                5),
          ("HostedFunction",         "lru",                30),
          ("CANMessage",     "msgname",            40),
          ("DP",      "name",               40),
          ("Validity",    "Validity",           15),
          ("DataFormatType",     "Encoding",           10),
          ("BitOffsetWithinDS",   "BitOffset",          10),
          ("ParameterSize",     "BitSize",            10),
          ("LsbRes",    "LsbValue",           10),  
          ("TransmissionIntervalMinimum",    "transmissionintervalminimum",           15),
          ("PublishedLatency",     "publishedlatency",            10),
          ("CodedSet",   "codedset",      10),
          ("FullScaleRangeMax",    "fullscalerangemax",       10),
          ("FullScaleRangeMin",      "fullscalerangemin",         10),
          ("FunctionalRangeMax",     "functionalrangemax",           10),
          ("FunctionalRangeMin",   "functionalrangemin",          10),
          ("Units",    "units",           10),          
          ("OneState",   "onestate",          10),
          ("ZeroState",     "zerostate",            10),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),        
    )
    
    inSigCANColumns = (
        # header,         value,                len
          ("Skip",                   "skip",                        5),
          ("RP",                     "name",                       40),
          ("Pub_Ref",                "pubref",                     40),
          ("HostedFunction",         "LruName",                    20),
          ("CANMessage",            "MsgName",                    40),
          ("MessageSize",            "msgsize",                    10),
          ("DP",                     "SigName",                    30),
          ("Validity",        "SourceSelection",            15),  #how to define this para     
          ("DataFormatType",                "Encoding",                   10),
          ("BitOffsetWithinDS",      "BitOffset",                  10),
          ("ParameterSize",          "BitSize",                    10),
          ("LsbRes",                 "LsbValue",                   10),
          ("SysLatencyWCLimit",      "sysLatencywclimit",          10),
          ("TransmissionIntervalMinimum",    "transmissionintervalminimum",           10),
          ("CodedSet",               "codedset",                   10),
          ("FullScaleRngMax",      "fullscalerangemax",          10),
          ("FullScaleRngMin",      "fullscalerangemin",          10),
          ("FuncRngMax",     "functionalrangemax",         10),
          ("FuncRngMin",     "functionalrangemin",         10),
          ("Units",                  "units",                      10),
          ("OneState",               "onestate",                   20),
          ("ZeroState",              "zerostate",                  20),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),

    )
   
       
    msgAfdxRxColumns = (
        # header,               value,           width
          ("Skip",              "skip",           5),
          ("ATA",               "atalist",              15),
          ("HostedFunction",               "lru",           30),
		  ("Original Source LRU",   'lrulist',    20),
          ("A664Message",           "msgname",       40),
          #("MessageSize",            "txlength",        10),
          ("RxMessageSize",          "rxlength",      10),
          ("TxMessageSize",          "txlength",      10),
          ("MessageOverhead",          "overhead",      10),
          ("PortType",              "type",          10),
          ("QueueLength",       "queuelength",   10), 
          ("Pub_RefreshPeriod",              "txrate",          10),
          ("Sub_SamplePeriod",            "rxsamrate",        10),
          ("Sub_RefreshPeriod",            "rxrefrate",        10),
          ("ComPortRxID",            "portid",        10),
          ("Sub_Name",          "portname",      20), 
          ("VirtualLinkID",              "vlid",          10),
          ("SubVLID",             "subvlid",         10),
          ("BAG",               "BAG",           10),
          ("MTU",               "MTU",           10),
          ("EdeEnable",        "edeenable",    10),
          ("ComPortTxID",       "edesourceid",   10),
          ("Sub_IpAddress",            "destip",        15),
          ("Sub_UdpDstId",           "udpdstid",       15),
          ("Pub_MACAddress",         "sourecMACA",     15),
          #("SourceMACB",         "sourecMACB",     15),
          ("Pub_IpAddress",          "srcip",      15),
          ("Pub_UdpSrcId",         "udpsrcid",     10),          
          ("ActualPathA",        "ActualPathA",   60),
          ("ActualPathB",        "ActualPathB",   60),
          #("DestMAC",           "MACDest",      15)
          ("Networks",              "networks",           5),
          ("MsgDataProtocolType",               "msgdataprotocoltype",           30),
          ("TransmissionIntervalMinimum",           "transmissionintervalminimum",       10),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),
    )             
    
    msgAfdxTxColumns = (
        # header,               value,           width
          ("Skip",              "skip",           5),
          ("HostedFunction",               "lru",           30),
          ("A664Message",           "msgname",       40),   
          ("MessageSize",            "txlength",        10),
          ("MessageOverhead",          "overhead",      10),
          ("PortType",              "type",          10),
          ("QueueLength",       "queuelength",   10),
          ("ActivityTimeout",              "acttime",          10),
          ("Pub_RefreshPeriod",              "txrate",          10),
          ("ComPortRxID",            "portid",        10),
          ("Port_Name",          "portname",      20),
          ("VirtualLinkID",              "vlid",          10),
          ("SubVLID",             "subvlid",         10),
          ("BAG",               "BAG",           10),
          ("MTU",               "MTU",           10),
          ("EdeEnable",        "edeenable",    10),
          ("ComPortTxID",       "edesourceid",   10),
          ("Pub_MACAddress",         "sourecMACA",     15),
          #("SourceMACB",         "sourecMACB",     15),
          ("Pub_IpAddress",          "srcip",      15),
          ("Pub_UdpSrcId",         "udpsrcid",     10),
          ("Networks",              "networks",           5),
          ("MsgDataProtocolType",               "msgdataprotocoltype",           30),
          ("TransmissionIntervalMinimum",           "transmissionintervalminimum",       40),
          ("Sub_IpAddress",          "destip",      15),
          ("Sub_UdpDstId",         "udpdetiid",     10),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),
    )

    msgtxCanColumns = (
          ("Skip",              "skip",             5),
          ("HostedFunction",               "lru",             30),
          ("CANMessage",           "msgname",         40),
          ("MessageSize",            "txlength",        10),
          ("RefreshPeriod",              "txrate",          10),
          ("MessageID",          "txcanid",         10),
          ("Physical",          "txphysical",      20),
          ("ActivityTimeout",              "acttime",          10),
          ("CANMessageProtocolType",              "canprotype",          10),
          ("PartitionId",              "partitionid",          10),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),
    )
    
    msgrxCanColumns = (
          ("Skip",              "skip",             5),
          ("Pub_HostedFunction",               "lru",             30),
          ("Pub_CANMessage",           "msgname",         40),
          ("MessageSize",            "txlength",        10),
          ("Pub_RefreshPeriod",              "txrate",          10),
          ("Sub_SamplePeriod",              "rxrate",          10),

          #("TXCanMsgID",          "txcanid",         10),
          ("Pub_MessageID",          "rxcanid",         10),
          ("ActivityTimeout",              "txacttime",          10),
          ("CANMessageProtocolType",              "canprotype",          10),
          ("PartitionId",              "partitionid",          10),
          ("Pub_Physical",          "txphysical",      20),
          ("ErrorCode",             "ErrorCode",                    20),
          #("Physical",          "rxphysical",      20),
    )
    
    msgtx429Columns = (
          ("Skip",              "skip",             5),
          ("HostedFunction",               "lru",             30),
          ("A429Port",           "txportname",         40),
          ("A429Channel",           "txchlname",         40),          
          ("A429Message",           "msgname",         40),
          ("MessageSize",            "txlength",        10),
          ("RefreshPeriod",              "txrate",          10),
          #("MessageID/CanMsgID",          "txcanid",         10),
          ("Physical",          "txphysical",      20),
          #("ActivityTimeout",              "acttime",          10),
          ("MessageProtocolType",              "a429protype",          10),
          ("Label",              "Label",          10),
          ("SDI",               "SDI",            10),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),
    )
    
    msgrx429Columns = (
          ("Skip",              "skip",             5),
          ("Sub_A429Port",      'rxportname',      10),
          ("Sub_SamplePeriod",              "rxrate",          10),
          ("Sub_Physical",          "rxphysical",      20),
          ("Pub_HostedFunction",               "lru",             30),
          ("Pub_A429Port",           "txportname",         40),
          ("Pub_A429Channel",           "txchlname",         40),
          ("Pub_A429Word",           "msgname",         40),
          ("MessageSize",            "txlength",        10),
          ("Pub_RefreshPeriod",              "txrate",          10),

          ("A429ProtocolType",          "txprotocoltype",         10),
          ("Pub_Label",          "Label",         10),
          ('SDI',               "SDI",          10),          
          #("CANMessageProtocolType",              "canprotype",          10),
          #("PartitionId",              "partitionid",          10),
          ("Pub_Physical",          "txphysical",      20),
          ("ErrorCode",             "ErrorCode",                    20),
          #("Physical",          "rxphysical",      20),
    )
    
    outSig429Columns = (
        # header,         value,                len
          ("Skip",        "skip",                5),
          ("HostedFunction",         "lru",                30),
          ("A429Port",           "txportname",         40),
          ("A429Channel",           "txchlname",         40), 
          ("A429Message",     "msgname",            40),
          ("DP",      "name",               40),
          ("Validity",    "Validity",           15),
          ("DataFormatType",     "Encoding",           10),
          ("BitOffsetWithinDS",   "BitOffset",          10),
          ("ParameterSize",     "BitSize",            10),
          ("LsbRes",    "LsbValue",           10),  
          ("TransmissionIntervalMinimum",    "transmissionintervalminimum",           15),
          ("PublishedLatency",     "publishedlatency",            10),
          ("CodedSet",   "codedset",      10),
          ("FullScaleRangeMax",    "fullscalerangemax",       10),
          ("FullScaleRangeMin",      "fullscalerangemin",         10),
          ("FunctionalRangeMax",     "functionalrangemax",           10),
          ("FunctionalRangeMin",   "functionalrangemin",          10),
          ("Units",    "units",           10),          
          ("OneState",   "onestate",          10),
          ("ZeroState",     "zerostate",            10),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),        
    )
    
    inSig429Columns = (
        # header,         value,                len
          ("Skip",                   "skip",                        5),
          ("RP",                     "name",                       40),
          ("Pub_Ref",                "pubref",                     40),
          ("HostedFunction",         "LruName",                    20),
          ("Pub_A429Port",         "Portname",                    20),
          ("Pub_A429Channel",         "txchannel",                    20),
          ("A429Message",            "MsgName",                    40),
          #("MessageSize",            "msgsize",                    10),
          ("DP",                     "SigName",                    30),
          ("Validity",               "SourceSelection",            15),  #how to define this para     
          ("DataFormatType",         "Encoding",                   10),
          ("BitOffsetWithinDS",      "BitOffset",                  10),
          ("ParameterSize",          "BitSize",                    10),
          ("LsbRes",                 "LsbValue",                   10),
          ("SysLatencyWCLimit",      "sysLatencywclimit",          10),
          ("TransmissionIntervalMinimum",    "transmissionintervalminimum",           10),
          ("CodedSet",               "codedset",                   10),
          ("FullScaleRngMax",      "fullscalerangemax",          10),
          ("FullScaleRngMin",      "fullscalerangemin",          10),
          ("FuncRngMax",     "functionalrangemax",         10),
          ("FuncRngMin",     "functionalrangemin",         10),
          ("Units",                  "units",                      10),
          ("OneState",               "onestate",                   20),
          ("ZeroState",              "zerostate",                  20),
          ("ErrorCode",             "ErrorCode",                    20),
          ("Comment",    "comment",           30),

    )
    


    def formatOutput(self, outputfn):

        def msgfilter(msglist, msgtype):
            return [m for m in msglist if m.msgtype == msgtype]
        
        # build final Input Signal List.

        #inSignals = []
        def rpfilter(rplist,msgtype):
            return [rp for rp in rplist if rp.type == msgtype]
        '''
        inSignals = []
            for rpreclist in self.rplists.values():
                if rpreclist.type ==msgtype: #"A664Message":
                    inSignals.append(rpreclist)
            return inSignals.sort(key=lambda sig: (sig.LruName, sig.MsgName, sig.ByteOffsetDS, sig.BitOffset))
        '''                   
        imtExcelRW.genExcelFile(outputfn, 
            (
                ("Input664Messages", self.msgAfdxRxColumns, 
                    sorted(msgfilter(self.rxmsglists.values(), "A664Message"), 
                           key=lambda msg: (msg.lru, msg.msgname)
                    )
                ),

                ("Input664Signals",  self.inSigAFDXColumns, 
                    sorted(rpfilter(self.rplists.values(),"A664Message"),
                           key=lambda sig: (sig.LruName, sig.MsgName, sig.name)#sig.ByteOffsetDS, sig.BitOffset)
                    )
                ),
                ("Output664Messages", self.msgAfdxTxColumns, 
                    sorted(msgfilter(self.txmsglists.values(), "A664Message"),
                           key=lambda msg: (msg.lru, msg.msgname)
                    )
                ),
                ("Output664Signals",  self.outSigAFDXColumns, 
                    sorted(msgfilter(self.dplists.values(), "A664Message"),
                           key=lambda sig: (sig.lru, sig.msgname, sig.name)#sig.ByteOffsetDS, sig.BitOffset)
                    )
                ),
                ("Output825Messages", self.msgtxCanColumns, 
                    sorted(msgfilter(self.txmsglists.values(), "CANMessage"),
                           key=lambda msg: (msg.lru, msg.msgname)
                    )
                ),
                ("Output825Signals",  self.outSigCANColumns, 
                    sorted(msgfilter(self.dplists.values(), "CANMessage"),
                           key=lambda sig: (sig.lru, sig.msgname)
                    )
                ),
                ("Input825Messages", self.msgrxCanColumns, 
                    sorted(msgfilter(self.rxmsglists.values(), "CANMessage"),
                           key=lambda msg: (msg.lru, msg.msgname)
                    )
                ),
                ("Input825Signals",  self.inSigCANColumns, 
                    sorted(rpfilter(self.rplists.values(), "CANMessage"),
                           key=lambda sig: (sig.LruName, sig.MsgName)
                    )
                ),               
                ("Output429Messages", self.msgtx429Columns, 
                    sorted(msgfilter(self.txmsglists.values(), "A429Word"),
                           key=lambda msg: (msg.lru, msg.msgname)
                    )
                ),
                ("Output429Signals",  self.outSig429Columns, 
                    sorted(msgfilter(self.dplists.values(), "A429Word"),
                           key=lambda sig: (sig.lru, sig.msgname)
                    )
                ),
                ("Input429Messages", self.msgrx429Columns, 
                    sorted(msgfilter(self.rxmsglists.values(), "A429Word"),
                           key=lambda msg: (msg.lru, msg.msgname)
                    )
                ),
                ("Input429Signals",  self.inSig429Columns, 
                    sorted(rpfilter(self.rplists.values(), "A429Word"),
                           key=lambda sig: (sig.LruName, sig.MsgName)
                    )
                ),
            )
        )    

def CreateATADictory(workdir):#
    print "workdir is %s" % workdir
    for dir_path,subpaths,files in os.walk(workdir,True):
        if dir_path == workdir:
            for subdir in subpaths:
                ATA[subdir]=[]
        if dir_path.endswith('Instances'):
            key = dir_path.split('\\')[-3]
            print key
            for subfile in files:
                if subfile.endswith(".xml"):
                    ATA[key].append(subfile.split('.')[0])


def ProcessAll(workdir,outdir,hfnamelist):
    
    xroot = imtXmlReader.icdReadAll([workdir,]) #
    logger.info('Import XML ICD OK, ready to analysis it...')
    
    icdanalysis = ICDProcess(xroot)
        
    logger.info('process rpxref...\n')
    icdanalysis.makeRpXref(xroot)
    
    logger.info('analysis GW ref...\n')
    icdanalysis.AnalysisGWPubred(xroot)
    #print ('the of gw is %d' % len(icdanalysis.gwindex))
    logger.info("analysi guid ref...\n")
    icdanalysis.AnalysisGuid(xroot)
    #icdanalysis.AnalysisVLs()
    #for guid, node in icdanalysis.guidref.items():
        #logger.info("node name:%s node guid:%s"% (node.a.get('Name'),guid))
    logger.info('Analysis vl ref...\n')
    icdanalysis.AnalysisVLs(xroot)
    
    for hfname in hfnamelist:

        logger.info("Start to process %s \n" % hfname)        
        
        logger.info('Analysis RPs ...\n')
        icdanalysis.AnalysisRPs(xroot, hfname)
        
        #add below code to resolve CP Status Message, need to add input CAN input message and RP for 5 IDU
        if hfname in ['HF_IDULEFTINBOARD','HF_IDULEFTOUTBOARD','HF_IDUCENTER','HF_IDURIGHTINBOARD','HF_IDURIGHTOUTBOARD']:
            icdanalysis.AnalysisInterCANMessage(xroot,hfname)
        
        logger.info('Analysis DPs ...\n')
        icdanalysis.AnalysisDPs(xroot, hfname)
        logger.info('Analysis inputmessage..\n')
        icdanalysis.AnalysisInputMessages()
        logger.info('Analysis outputmessage..\n')
        icdanalysis.AnalysisOutputMessages()
        
        logger.info('Analysis input signals...\n')
        icdanalysis.AnalysisInputSignals()
        
        logger.info('Generate %s excel...\n' % hfname)
        icdanalysis.formatOutput(os.path.join(outdir,hfname) + "-icd.xlsx")
        #print(encodelist)
        logger.info('Finish %s  generate\n\n\n' % hfname)
        icdanalysis.reset()  # clear last data 

def usage():
    print ('Input args is invalid.....')
    print ('-c -- print out the log message to the sterr')
    print ('-p -- print out the progress')
    print ('--wordir -- define the root directory of ICD need to import ana analysis ')
    print ('--outdir -- define the ICD analysis results output directory')
    print ('--haname -- define the name list that need to generate')
    print ('--loglevel -- set the loglevel=[TRACE|INFO|WARN|ERROR]')
    print ('you must do as what as up')

if __name__ == "__main__":
    print sys.argv[1:]
    opts, args = getopt.getopt(sys.argv[1:], 'cp', ['workdir=','outdir=','hfname=','loglevel='])
    
    loglevels={
               'TRACE':logger.TRACE,
               'INFO' :logger.INFO,
               'WARN' :logger.WARN,
               'ERROR':logger.ERROR}
    
    workdir = None
    outdir = None
    hfname = None
    loglevel = loglevels.get('ERROR')
    logconsole = None
    logprogress = None
    
    if len(opts) == 0 :
        print ('The input opt can no be None')
        usage()
        sys.exit(0)
    
    for o, v in opts:
        if o in ['-c','--console']:
            logconsole = True
            logprogress = False
        elif o in ['-p','--progress']:
            logconsole = False
            logprogress = True
        elif o in ['--workdir']:
            workdir = v
        elif o in ['--outdir']:
            outdir = v
        elif o in ['--hfname']:
            hfname = v.split(',') 
        elif o in ['--loglevel']:
            loglevel = loglevels.get(v,logger.INFO) 
        else:
            usage()
            sys.exit(0)
    
    
    logger.setup(level = loglevel, filename=os.path.join(outdir,sys.argv[0].split('\\')[-1][:-3]) + "-icd.log", console = logconsole, progress=logprogress)
    logger.info('Start the ICD import....')
    print 'wordir is %s' % workdir

    CreateATADictory(workdir)
        
    ProcessAll(workdir,outdir,hfname)
    print ('Generate Finish')    
    
    '''
    -c   --loglevel=INFO --outdir=D:\C919Tools\GeneExcelICD\Output\bp4.2 --hfname=FDAS_L1,FDAS_L3,FDAS_R3,IMA_DM_L4,IMA_DM_L5,IMA_DM_R4,SYNOPTICMENUAPP_L,SYNOPTICMENUAPP_R,SYNOPTICPAGEAPP_L,SYNOPTICPAGEAPP_R,HF_IDULEFTINBOARD,HF_IDULEFTOUTBOARD,HF_IDUCENTER,HF_IDURIGHTINBOARD,HF_IDURIGHTOUTBOARD,HF_CCD1,HF_CCD2,HF_DCP1,HF_DCP2,HF_EVS,HF_HCU1,HF_HCU2,HF_HPU1,HF_HPU2,HF_ISIS,HF_MCMW1,HF_MCMW2,HF_MKB1,HF_MKB2,HF_RCP,HF_RLS1,HF_RLS2,ECL_L,ECL_R,VIRTUALCONTROLAPP_L,VIRTUALCONTROLAPP_R --workdir="D:\BP4.2\Model System Elements"
    '''
    
    '''
    HF_RIU_1,HF_TCP_3,HF_EMPC_EPS,HF_CARGO_FIRECNTRLPANEL,HF_ENGINEAPU_FIRECNTRLPANEL,HF_FUELOVERHEADPANEL,HF_L_ID,HF_R_ID,HF_L_NAISWITCH,HF_R_NAISWITCH,HF_WHCA,HF_GAGEASSY,HF_MCMW1,HF_MCMW2,HF_LGCU2,HF_AIR_COND_CPA,HF_DIM_CTRL_PWR,HF_ICE_CABIN_LT_CPA,HF_INSTR_CPA_L,HF_INSTR_CPA_R,HF_EMERGENCYLIGHTINGSW,HF_ACU,HF_FUELCONTROLSW_R
    '''