

import os
import sys
import getopt
import time
sys.path.append("..")
import Common.logger as logger
from Common.bunch import Bunch
import xlrd
from collections import defaultdict
from Cheetah.Template import Template
from ssl import DefaultVerifyPaths





SHEETNAME= ["Input664Messages",
     "Input664Signals",
     "Output664Messages",
     "Output664Signals",
     "Input825Messages",
     "Input825Signals",
     "Output825Messages",
     "Output825Signals"]  


NORMALIZE_SIGTYPES = {
    'SINT'  : 'INT',
    'SHORT' : 'INT',
    'INT'   : 'INT',
    'USHORT': 'UINT',
    'UINT'  : 'UINT',
    'CHAR'  : 'INT',
    'DIS'   : 'BOOL',
    'BOOL'  : 'BOOL',
    'ENUM'  : 'COD',
    'COD'   : 'COD',
    'OPAQUE': 'BYTES',
    'BYTES' : 'BYTES',
    'BLK'   : 'BYTES',
    'STRING': 'STRING',
    'CHAR STRING':'STRING',
    'FLOAT' : 'FLOAT',
    'BNR'   : 'BNR',
    'UBNR'  : 'UBNR',
    'BCD'   : 'BCD',
    'UBCD'  : 'UBCD',
    'ISO-5' : 'COD',
    # special purpose types, all can be treated as bitfields alias COD
    'A429OCTLBL'    : 'COD',
    'A429SDI'       : 'COD',
    'A429_SSM_BNR'  : 'COD',
    'A429_SSM_DIS'  : 'COD',
    'A429_SSM_BCD'  : 'COD',
    'A429_SSM_CUSTOM': 'COD',
    'A429PARITY'    : 'COD',
    'PAD'           : 'COD',
    'RESV'          : 'COD',
    'CRC'           : 'UINT',
    'A664_FSB'      : 'UINT',
    'SPAR'          : 'COD',    
    'HEX'           : 'COD'
}


def normalizeSigType(sigtype, sigsize):
    if sigtype in ("INT8", "UINT8") and sigsize != 8:
        raise Exception, "Wrong signal size for data type %s" % sigtype

    if sigtype in ("SHORT", "INT16", "UINT16") and sigsize != 16:
        raise Exception, "Wrong signal size for data type %s" % sigtype

    if sigtype in ("UINT", ) and sigsize not in (8,16,32,64):
        sigtype = "COD"
    
    normalizedType = NORMALIZE_SIGTYPES.get(sigtype)
    if normalizedType is None:
        logger.error("unkonwn signal type %s" % sigtype)
        #raise Exception, "Unknown signal type %s" % sigtype
    
    return normalizedType

def loggererror(msg):
    sys.stderr.write("ERROR %s" % msg)

def loggerinfo(msg):
    sys.stdout.write("INFO %s" % msg)

def Get_Column_Index(sheet):
    cid=dict()
    for col in range(sheet.ncols):
        key = sval(sheet.row(0),col)
        cid[key]= col
    return cid

def ival(r, col, base= 10):
    f = r[col].value
    if type(f) == type(1.0):
        return int(r[col].value)
    elif type(f) == type(1):
        return f
    else:
        s = f.encode('utf-8').strip()
        if s =='':
            return None
        if s.startswith("0x"):
            return int(s[2:], 16)
        elif s.endswith("b"):
            return int(s[0:-1], 2)
        else: 
            return int(s, base)
def sval(row, index):
    return row[index].value.encode("UTF-8").strip() 

def fval(row, index):
    val = row[index].value
    if val and val not in ['N/A','NA']:
        #print row[index].value
        return float(row[index].value)
    else:
        return None

def bval(row, index):
    val = row[index].value.encode('UTF-8').strip()
    val = val.lower()
    if val in ['true','y','yes']:
        return True
    elif val in ['false','n','no']:
        return False
    else:
        return False         


class Virtuallink(object):
    def __init__(self,vid,msg,vl,hfname,direct):
        self.vlid = vid
        self.suvlid = None
        self.msgport = []
        self.vlname ='VL_%s_%s' % (msg['Lru'],str(vid))
        self.macaddr = msg['DestMAC']
        self.bag = msg['BAG']
        self.interface = 3 #A and B port
        self.mtu = msg['MTU']
        #self.msgport = [(msg['Message'],msg['DestUDP'])]
        #self.msgname = msg['Message']
        #self.destupd = msg['DestUDP']
        self.lru = msg['Lru']
        if direct == 'input':
            self.receivelru = [hfname]
        else:
            self.receivelru = []
        temvl = vl.get(vid,None)
        if temvl: # temvl will be corvered by this class instance
            subvlcount = temvl.suvlid
            if msg['SubVl'] > subvlcount:
                self.suvlid = msg['SubVl']
            else:
                self.suvlid = subvlcount
            temvl.msgport.append((msg['Message'],msg['DestUDP']))
            self.msgport = temvl.msgport
            #self.msgport.append((msg['Message'],msg['DestUDP']))
            
        else:
            self.suvlid = msg['SubVl']
            self.msgport.append((msg['Message'],msg['DestUDP']))

ONEBIT_TYPES   = set(("BOOL",))
FULLBYTE_TYPES = set(("INT", "UINT","CHAR", "FLOAT", "BYTES","STRING"))
INTEGER_TYPES  = set(("INT", "UINT"))
HALF_INTEGER_TYPES = set(("INT", "UINT"))
FULLWORD_TYPES = set(("INT", "UINT", "FLOAT"))
LONGWORD_TYPES = set(("INT", "UINT", "FLOAT"))
BLK_TYPES =set(("BYTES","STRING"))
BYTE_TYPES     = set(("INT", "UINT"))

   

def computeSignalAccessAFDX(sigtype, sigsize=0, sigoffset=0, dssize=0, dspos=0):
    print sigtype, sigsize, sigoffset, dssize, dspos
    # consistency checks
    #sigtype = TypeIcdToads2(sigtypeoriginal)

    # signal must fit in dataset
    # FIXME: if sigoffset + sigsize > dssize * 8:
    #    raise Exception, "Signal does not fit into data set or message"
    
    # for AFDX dataset must be 4 byte aligned and size must be multiple of 4 byte
    if sigtype == '':
        logger.error('signal is none')
        return None, None,None
    #logger.info('sigtyep:%s sigsize:%d sigoffset: %d dssize: %d dspos: %d \n' % (sigtype, sigsize, sigoffset, dssize, dspos))
    if (sigoffset + sigsize )> dssize * 8:
        logger.error ("Illegal Signal offset or size")
        #raise Exception, 'Illegal Signal offset or size'
    
    if dssize % 2 != 0 or dspos % 4 != 0:
    #if dspos % 4 != 0:
        print dssize
        print dspos
        time.sleep(1)
        raise Exception, "Illegal Data Set Alignment"

    #if sigtype in FULLBYTE_TYPES and sigoffset % 8 != 0:
    #    raise Exception, "Signal offset not aligned to byte boundary"

    if sigtype in ONEBIT_TYPES and sigsize != 1:
        raise Exception, "Illegal signal size for type %s %s" % (sigtype,sigsize)
    
    #if sigtype == 'BYTES' and sigoffset % 32 != 0:
    #    raise Exception, 'OPAQUE signal offset not aligned to word boundary %s' % sigtype
    
    if sigtype in INTEGER_TYPES and sigsize not in (7,8,16,32,64): #7 for some char
        raise Exception, 'Illegal signal size of type %s, %s' % (sigtype,sigsize)
        
    #if sigtype in INTEGER_TYPES and sigsize != 32:
    #    raise Exception, "Illegal signal size for type %s" % sigtype

    if sigtype == "FLOAT" and sigsize not in (32, 64):
        raise Exception, "Illegal signal size for type %s %s" % (sigtype,sigsize)
        
    # start byteoffset bitoffset calculator
    if  (sigtype == "BYTES"):
        # Opaque: sigoffset is least significant bit of first word
        # Only works for opaque which have bitoffset multiple of 4 bytes
        sigAccess = 1
        sigByteOffset = dspos + (sigoffset / 8)
        if sigsize < 32:
            sigByteOffset += 4 - sigsize / 8
        sigBitOffset  = 0
    elif sigtype == 'STRING' or (sigtype in BYTE_TYPES  and sigsize == 8 and sigoffset%8 == 0):# add sigoffset%8==0 for COMAC EPS
        # byte aligned data
        sigAccess = 1
        sigByteOffset = dspos + ((sigoffset/32 + 1) * 4) - (((sigoffset % 32) + sigsize - 1) / 8 + 1)
        sigBitOffset  = 0
    elif sigtype in HALF_INTEGER_TYPES and sigsize == 16:
        # 16 bit aligned data 
        sigAccess = 2
        sigByteOffset = dspos + ((sigoffset/32 + 1) * 4) - (((sigoffset % 32) + sigsize - 1) / 8 + 1)
        sigBitOffset  = 0
    elif sigtype in  FULLWORD_TYPES and sigsize == 32:
        # 32 bit aligned data 
        sigAccess = 4
        sigByteOffset = dspos + ((sigoffset/32 + 1) * 4) - (((sigoffset % 32) + sigsize - 1) / 8 + 1)
        sigBitOffset  = 0
    elif sigtype in LONGWORD_TYPES and sigsize == 64:
        # 64 bit aligned data 
        sigAccess = 8
        sigByteOffset = dspos + ((sigoffset/32 + 2) * 4) - (((sigoffset % 32) + sigsize - 1) / 8 + 1)
        sigBitOffset = 0
    #elif sigtype in BLK_TYPES:
    #    # 32 bit aligned data
    #    sigAccess = 4
    #    sigByteOffset = dspos + ((sigoffset/32) * 4)
    #    sigBitOffset = 0
    else: # COD, BITFIELD, BOOL, DIS, (U)BNR, (U)BCD for Request_Number, this can not be handle, should modify by hand
        # compute smallest containing access        
        startbyte = dspos + ((sigoffset/32 + 1) * 4) - (((sigoffset % 32 + sigsize - 1) / 8) + 1 )
        endbyte   = dspos + ((sigoffset/32 + 1) * 4) - (((sigoffset % 32) / 8) + 1 )
        bytes     = endbyte - startbyte + 1
        sigAccess = {1: 4, 2: 4, 3: 4, 4: 4, 5: 8, 6: 8, 7:8, 8: 8}.get(bytes)
        if sigAccess is None:
            logger.error( 'sigaccess is none')
        while sigAccess < 8 and startbyte / sigAccess != endbyte / sigAccess:
            sigAccess *= 2

        # access byte offset should now be aligned, 
        # i.e. round down start byte to multiples of sigAccess
        sigByteOffset = (startbyte / sigAccess) * sigAccess 

        lastbyte = (sigByteOffset + sigAccess - 1)
        sigBitOffset = (lastbyte - endbyte) * 8 + sigoffset % 8

    if sigByteOffset % sigAccess != 0:
        raise Exception, "Unaligned signal access: ByteOffset=%d BitOffset=%d Access=%d" % \
            (sigByteOffset, sigBitOffset, sigAccess)
    #logger.info('sigByteoffset:%d sigBitOffset:%d sigAccess:%d \n' % (sigByteOffset, sigBitOffset, sigAccess))       
    return sigByteOffset, sigBitOffset, sigAccess


def computeSignalAccessCAN(sigtype, sigsize=0, sigoffset=0):
    # consistency checks
    #sigtype = TypeIcdToads2(sigtypeoriginal)

    # signal must fit in dataset
    # FIXME: if sigoffset + sigsize > dssize * 8:
    #    raise Exception, "Signal does not fit into data set or message"
    
    # for AFDX dataset must be 4 byte aligned and size must be multiple of 4 byte
    if sigtype == '':
        logger.error('signal is none')
        return None, None,None
    #logger.info('sigtyep:%s sigsize:%d sigoffset: %d \n' % (sigtype, sigsize, sigoffset))
    
    #if sigtype in FULLBYTE_TYPES and sigoffset % 8 != 0:
    #    raise Exception, "Signal offset not aligned to byte boundary"

    if sigtype in ONEBIT_TYPES and sigsize != 1:
        raise Exception, "Illegal signal size for type %s" % sigtype
    
    if sigtype == 'CHAR' and sigsize != 8:
        raise Exception, 'Illegal signal size of type %s' % sigtype
    
    if sigtype == 'SINT' and sigsize != 16:
        raise Exception, 'Illegal signal size of type %s' % sigtype
        
    #if sigtype in INTEGER_TYPES and sigsize != 32:
    #    raise Exception, "Illegal signal size for type %s" % sigtype

    if sigtype == "FLOAT" and sigsize not in (32, 64):
        raise Exception, "Illegal signal size for type %s" % sigtype
    
    sigByteOffset = 0
    sigBitOffset= sigoffset
    sigAccess = 0    
       
    return sigByteOffset, sigBitOffset, sigAccess


def computeSignalAccess429(sigtype, sigsize=0, sigoffset=0):
    # consistency checks
    #sigtype = TypeIcdToads2(sigtypeoriginal)

    # signal must fit in dataset
    # FIXME: if sigoffset + sigsize > dssize * 8:
    #    raise Exception, "Signal does not fit into data set or message"
    
    # for AFDX dataset must be 4 byte aligned and size must be multiple of 4 byte
    if sigtype == '':
        logger.error('signal is none')
        return None, None,None
    #logger.info('sigtyep:%s sigsize:%d sigoffset: %d \n' % (sigtype, sigsize, sigoffset))
    
    if sigtype in FULLBYTE_TYPES and sigoffset % 8 != 0:
        print "Signal offset not aligned to byte boundary"

    if sigtype in ONEBIT_TYPES and sigsize != 1:
        print "Illegal signal size for type %s" % sigtype
    
    if sigtype == 'CHAR' and sigsize != 8:
        print 'Illegal signal size of type %s' % sigtype
    
    if sigtype == 'SINT' and sigsize != 16:
        print 'Illegal signal size of type %s' % sigtype
        
    #if sigtype in INTEGER_TYPES and sigsize != 32:
    #    raise Exception, "Illegal signal size for type %s" % sigtype

    if sigtype == "FLOAT" and sigsize not in (32, 64):
        print "Illegal signal size for type %s" % sigtype
    
    sigByteOffset = 0
    sigBitOffset= sigoffset
    sigAccess = 0    
       
    return sigByteOffset, sigBitOffset, sigAccess

VALIDITY_FRESHNESS   = 1
VALIDITY_MASK        = 2
VALIDITY_A664FSB     = 4
VALIDITY_A429SSM_DIS = 8
VALIDITY_A429SSM_BNR = 16
VALIDITY_A429SSM_BCD = 32
VALIDITY_A429SSM_CUSTOM = 64
VALIDITY_A429SSM     = (VALIDITY_A429SSM_DIS | VALIDITY_A429SSM_BNR | VALIDITY_A429SSM_BCD | VALIDITY_A429SSM_CUSTOM)

#used for cvt generate 
TypeIcdToads2 ={'SPAR': ('int32',4),
                 'DIS': ('int32',4),
                 'BOOL':('int32',4),
                 'BNR': ('real32',4),
                 'FLOAT':('real32',4),
                 'A429SDI':('int32',4),
                 'BLK':('byte',1),
                 'COD':('int32',4), 
                 'SINT':('int32',4), 
                 'RESV':('int32',4), 
                 'A429_SSM_DIS':('int32',4), 
                 'UINT':('uint32',4), 
                 'CHAR':('int32',4), 
                 'UBNR':('real32',4), 
                 'OPAQUE':('byte',1), 
                 'BCD':('real32',4), 
                 'ISO-5':('int32',4), 
                 'PAD':('int32',4), 
                 'A429_SSM_BNR':('int32',4),
                 'A429_SSM_CUSTOM':('int32',4),  
                 'A429PARITY':('int32',4), 
                 'A429_SSM_BCD':('int32',4), 
                 'A429OCTLBL':('int32',4)}


class ExcelRecord:
    def __init__(self, asUsed, asRcvdOld, asRcvdNew, diff):
        self.asUsed = asUsed
        self.asRcvdOld = asRcvdOld
        self.asRcvdNew = asRcvdNew
        self.diff = diff 
        
class GenerateAds2ConfByExcel(object):
    def __init__(self,hfnamelist): 
        
        self.inputafdxmsg = dict()
        self.inputafdxsignal = dict()
        self.outputafdxmsg = dict()
        self.outputafdxsignal = dict()
        self.inputCanMsg = dict()
        self.inputCanSignal = dict()
        self.outputCanMsg = dict()
        self.outputCanSignal = dict()  
        self.input429Signal = dict()
        self.input429Chl = dict()   
        self.output429Signal = dict()
        self.output429Chl = dict()    
        self.inputvl = dict()
        self.outputvl = dict()
        self.hfexecl = None 
        self.hfnamelist = hfnamelist
        self.hfname = None
        #self.cvts = dict()
           
    
    def readinputafdxmsg(self,sheet,cdix):
        Msgdicts = dict()
        vl = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            if sval(row,cdix['Skip']) == '#':
                continue
            msg = dict()     
            msg["Lru"] = sval(row,cdix['HostedFunction'])  
            if msg['Lru'] == 'R':
                pass          
            msg["Message"] = sval(row,cdix['A664Message'])
            msg['fullname'] = msg['Lru']+'.'+msg['Message']
            #print msg['fullname']
            #time.sleep(0.1)
            msgname = msg['Lru']+'.'+msg['Message']
            msg["TXLength"] = ival(row, cdix['TxMessageSize'])
            
            msg["RxLength"] = ival(row, cdix['RxMessageSize'])
            if msg['RxLength'] < 1 or msg['RxLength'] > 8500:
                logger.error('the rxlength of msg: %s is wrong' % msgname)
                continue
            
            msg["Overhead"] = ival(row, cdix['MessageOverhead'])
            msg["Type"] = sval(row, cdix['PortType'])
            if msg['Type'] == 'QUEUEING':
                msg["QueueLength"] = ival(row, cdix['QueueLength'])
            else:
                msg["QueueLength"] = 1
            msg["TXRate"] = int(fval(row, cdix['Pub_RefreshPeriod']))
            msg["RxRate"] = ival(row, cdix['Sub_SamplePeriod'])
            msg["PortID"] = ival(row, cdix['ComPortRxID'])
            msg["PortName"] = sval(row, cdix['Sub_Name'])
            msg["Vlid"] = ival(row, cdix['VirtualLinkID'])
            if msg["Vlid"] is None:
                logger.error("Message: %s has no vlid, skip" % msg["fullname"])
                continue
            msg["SubVl"] = ival(row, cdix['SubVLID'])
            msg["BAG"] = int(fval(row, cdix['BAG'])*1000)
            msg["MTU"] = ival(row, cdix['MTU'])
            msg["EdeEnabled"] = bval(row, cdix['EdeEnable'])
            msg["EdeSourceId"] = ival(row, cdix['ComPortTxID'])
            msg["DestIP"] = sval(row, cdix['Sub_IpAddress'])
            msg["DestUDP"] = ival(row, cdix['Sub_UdpDstId'])
            msg["SourceMACA"] = sval(row, cdix['Pub_MACAddress'])
            #msg["SourceMACB"] = sval(row, cdix['SourceMACB'])
            msg["SourceIP"] = sval(row, cdix['Pub_IpAddress'])
            msg["SourceUDP"] = ival(row, cdix['Pub_UdpSrcId'])
            msg["MsgDataProtocolType"] = sval(row,cdix['MsgDataProtocolType'])
           
            msg["DestMAC"] = "03:00:00:00:%s:%s" % (hex((msg['Vlid'] >> 8) & 0xFF)[2:],hex(msg['Vlid'] & 0xFF)[2:])  #if excel does not has this para, need to calculate it from vlid

            vl[msg['Vlid']] = Virtuallink(msg['Vlid'],msg,vl,self.hfname,'input')
            #if msg['Lru'] in self.hfnamelist:
            #    continue
            msg['Signals'] = dict()
            Msgdicts[msgname] = msg     
            #msg["ActualPath"]    
            
        return Msgdicts,vl     
    
    def readinputafdxsignal(self,sheet,cdix):
        def sselA664Fsb(sig):
            return sig['sourceSelect'] & VALIDITY_A664FSB

        def sselA429SSM(sig):
            return sig['sourceSelect'] & VALIDITY_A429SSM
        
        Sigdicts = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            #print(111111111111)
            #print(row)
            #print(cdix['ParameterSize'])
            #print(cdix['BitOffsetWithinDS'])
            if sval(row,cdix['Skip']) == '#':
                continue
            sig = dict()
            sig['direct'] = 'Input'     
            sig["Lru"] = sval(row,cdix['HostedFunction'])
            #if sig['Lru'] in self.hfnamelist:
            #    continue
            sig['txport']=sval(row,cdix['PortName'])
            sig["Message"] = sval(row,cdix['A664Message'])
            #print sval(row,cdix['A664Message'])
            msg = self.inputafdxmsg.get(sig['Lru']+'.'+sig['Message'])
            if msg is None:
                logger.error('the signal can not found msg %s siglru: %s'%(sig['Lru']+'.'+sig['Message'],sig['Lru']))
                continue            
            #sig['msg'] = msg
            sig["Pubref"] = sval(row, cdix['Pub_Ref'])
            sig["RpName"] = sval(row, cdix['RP'])
            sig['fullname'] = sig['Lru']+'.'+sig['Message']+"."+sig["RpName"]
            #print sig['fullname']
            #time.sleep(0.1)
            sig["DataSet"] = sval(row, cdix['DS'])
            sig["Signal"] = sval(row, cdix['DP'])
            sig["SSEL"] = sval(row, cdix['Validity'])
            #if sig['Lru']=="RGW05_NonA664_In":
            #if sig["DataSet"]=="DS16":
            ssel = sig['SSEL']
            sourceSelect = 0
            ssellist = [c.strip() for c in ssel.split(',')]
            for p in ssellist:
                if p == "FRESH":
                    sourceSelect |= VALIDITY_FRESHNESS
                elif p == "MASK":
                    sourceSelect |= VALIDITY_MASK
                elif p == "FSB":
                    sourceSelect |= VALIDITY_A664FSB
                elif p == "SSM_BNR":
                    if sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal source selection method: %s" % ssel
                    sourceSelect |= VALIDITY_A429SSM_BNR
                elif p == "SSM_DIS":
                    if sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal source selection method: %s" % ssel
                    sourceSelect |= VALIDITY_A429SSM_DIS
                elif p == "SSM_BCD":
                    if sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal source selection method: %s" % ssel
                    sourceSelect |= VALIDITY_A429SSM_BCD
                elif p == "SSM_CUSTOM":
                    if sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal source selection method: %s" % ssel
                    sourceSelect |= VALIDITY_A429SSM_CUSTOM
                elif p != '':
                    logger.error ('Illegal source selection method: %s %d' % (ssel, id))   
            if sourceSelect & VALIDITY_A664FSB:
                sig["FsbOffset"] = ival(row, cdix['ByteOffsetFSF'])  #661 message do not have fsb
            else:
                sig['FsbOffset'] = None
            sig['sourceSelect'] = sourceSelect
            sig["DSOffset"] = ival(row, cdix['ByteOffsetWithinMsg'])
            sig["DSSize"] = ival(row, cdix['DataSetSize'])
            sig["SigSize"] = ival(row, cdix['ParameterSize'])
            if sval(row, cdix['DataFormatType']) in ['PAD','RESV']:
                #sig['fullname']
                continue
            # change the opaque to UBNR, if parametersize less than 32, for that tool can't
            sigtypetemp = sval(row, cdix['DataFormatType']) 
            if (sigtypetemp == 'OPAQUE'or sigtypetemp=='BLK') and sig['SigSize'] < 32:
                sigtypetemp ='UBNR'
            
            sig["SigType"] = normalizeSigType(sigtypetemp,sig["SigSize"])
            
            
            sig["SigOffset"] = ival(row, cdix['BitOffsetWithinDS'])
            sig["LsbValue"] = fval(row, cdix['LsbRes'])
            
            if sig["SigType"] == 'UINT' and sig["SigOffset"]%8 !=0 and sig["SigSize"] == 8:
                print "******************",
                print sig['RpName']
            if sig['DSOffset'] is None:
                print "eee"
            
            if sig['RpName'] == 'DME4000R_429_CH1.LENGTH':
                pass
            try:
                sig['sigbyteoffset'],sig['sigbitoffset'],sig['sigalign'] = computeSignalAccessAFDX(sig['SigType'],sig['SigSize'], sig['SigOffset'],sig['DSSize'],sig['DSOffset'])
            except:
                with open('erro.txt','a') as f:
                    f.write(sval(row,cdix['A664Message'])+'\n')
                    
            sig['664FSB'] = sselA664Fsb(sig)
            sig['429SSM'] = None#sselA429SSM(sig) 
            #msg['RP'][sig['fullname']] = sig
            try: 
                if sig['sigalign'] is None:
                    continue
            except: 
                print  sval(row,cdix['A664Message'])
                with open('erro.txt','a') as f:
                    f.write(sval(row,cdix['A664Message'])+'\n')  
                continue   

            unikey = sig['Lru']+sig['txport']+sig['Pubref']
            #print unikey
            #add for ADS2 update(add CRC calculate)
            if 'Application_CRC' in sig['Signal']: # the CRC signal
                #print "comt in readinputafdxsignal crc signal"
                sig['crc_signal'] = True
            Sigdicts[unikey] = sig
            #print sig['Pubref']
            
        return Sigdicts
    
    def readoutputafdxmsg(self,sheet,cdix):
        Msgdicts = dict()
        vl = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            #print(22222222222222)
            #print(row)
            #print(cdix['Pub_RefreshPeriod'])
            if sval(row,cdix['Skip']) == '#':
                continue
            msg = dict()     
            msg["Lru"] = sval(row,cdix['HostedFunction'])
            if msg['Lru'] == 'R':
                pass
            msg["Message"] = sval(row,cdix['A664Message'])
            msg['fullname'] = msg['Lru']+'.'+msg['Message']
            msgname = msg['Lru']+'.'+msg['Message']
            msg["TXLength"] = ival(row, cdix['MessageSize'])
            
            
            if msg['TXLength'] < 1 or msg['TXLength'] > 8192:
                logger.error('the xxlength of msg: %s is wrong' % msgname)
                continue
            
            msg["Overhead"] = ival(row, cdix['MessageOverhead'])
            msg["Type"] = sval(row, cdix['PortType'])
            if msg['Type'] == 'QUEUEING':
                msg["QueueLength"] = ival(row, cdix['QueueLength'])
            else:
                msg["QueueLength"] = 1
            #print msg['fullname']
            try:
                msg["TXRate"] = int(fval(row, cdix['Pub_RefreshPeriod']))
            except:
                with open('erro.txt','a') as f:
                    f.write(sval(row,cdix['A664Message'])+'\n')  
                msg["TXRate"]=33              
            #print msg["TXRate"]
            time.sleep(0.1)
            msg["PortID"] = ival(row, cdix['ComPortRxID'])
            msg["PortName"] = sval(row, cdix['Port_Name'])
            msg["Vlid"] = ival(row, cdix['VirtualLinkID'])
            #print msg["Vlid"]
            if msg["Vlid"] is None:
                logger.error("Message: %s has no vlid, skip" % msg["fullname"])
                continue
            msg["SubVl"] = ival(row, cdix['SubVLID'])
            msg["BAG"] = int(fval(row, cdix['BAG'])*1000)
            msg["MTU"] = ival(row, cdix['MTU'])
            msg["EdeEnabled"] = bval(row, cdix['EdeEnable'])
            msg["EdeSourceId"] = ival(row, cdix['ComPortTxID'])
            msg["SourceMACA"] = sval(row, cdix['Pub_MACAddress'])
            #msg["SourceMACB"] = sval(row, cdix['SourceMACB'])
            msg["SourceIP"] = sval(row, cdix['Pub_IpAddress'])
            msg["SourceUDP"] = ival(row, cdix['Pub_UdpSrcId'])
            msg["DestIP"] = sval(row, cdix['Sub_IpAddress'])
            msg["DestUDP"] = ival(row, cdix['Sub_UdpDstId'])
            msg["MsgDataProtocolType"] = sval(row,cdix['MsgDataProtocolType'])
           
            msg["DestMAC"] = "03:00:00:00:%s:%s" % (hex((msg['Vlid'] >> 8) & 0xFF)[2:],hex(msg['Vlid'] & 0xFF)[2:])  #if excel does not has this para, need to calculate it from vlid
          
            vl[msg['Vlid']] = Virtuallink(msg['Vlid'],msg,vl,self.hfname,'output')
            msg['Signals'] = dict()
            Msgdicts[msgname] = msg     
            #msg["ActualPath"]    
            
        return Msgdicts,vl   
    
    def readoutputafdxsignal(self,sheet,cdix):
        def sselA664Fsb(sig):
            return sig['sourceSelect'] & VALIDITY_A664FSB

        def sselA429SSM(sig):
            return sig['sourceSelect'] & VALIDITY_A429SSM
        
        Sigdicts = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            #print(333333333333333)
            #print(row)
            #print(cdix['DataSetSize'])
            if sval(row,cdix['Skip']) == '#':
                continue
            sig = dict()  
            sig['direct'] = 'Output'   
            sig["Lru"] = sval(row,cdix['HostedFunction'])
            sig["Message"] = sval(row,cdix['A664Message'])
            msg = self.outputafdxmsg.get(sig['Lru']+'.'+sig['Message'])
            
            if msg is None:
                logger.error('the signal can not found msg %s'%(sig['Lru']+'.'+sig['Message']))
                continue            
            #sig['msg'] = msg
            ####modify for LRA by zhengchao on 20170217
            #sig["DpName"] = sval(row, cdix['DP'])
            sig['Signal'] = sval(row, cdix['DP'])
            sig['fullname'] = sig['Lru']+'.'+sig['Message']+"."+sig["Signal"]
            sig["DataSet"] = sval(row, cdix['DS'])            
            sig["SSEL"] = sval(row, cdix['Validity'])
            ssel = sig['SSEL']
            sourceSelect = 0
            ssellist = [c.strip() for c in ssel.split(',')]
            for p in ssellist:
                if p == "FRESH":
                    sourceSelect |= VALIDITY_FRESHNESS
                elif p == "MASK":
                    sourceSelect |= VALIDITY_MASK
                elif p == "FSB":
                    sourceSelect |= VALIDITY_A664FSB
                elif p == "SSM_BNR":
                    if sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal source selection method: %s" % ssel
                    sourceSelect |= VALIDITY_A429SSM_BNR
                elif p == "SSM_DIS":
                    if sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal source selection method: %s" % ssel
                    sourceSelect |= VALIDITY_A429SSM_DIS
                elif p == "SSM_BCD":
                    if sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal source selection method: %s" % ssel
                    sourceSelect |= VALIDITY_A429SSM_BCD
                elif p == "SSM_CUSTOM":
                    if sourceSelect & VALIDITY_A429SSM:     # check there is only one SSM mode 
                        raise Exception, "Illegal source selection method: %s" % ssel
                    sourceSelect |= VALIDITY_A429SSM_CUSTOM
                elif p != '':
                    logger.error ('Illegal source selection method: %s ' % ssel)   
            if sourceSelect & VALIDITY_A664FSB:
                sig["FsbOffset"] = ival(row, cdix['ByteOffsetFSF'])  #661 message do not have fsb
            else:
                sig['FsbOffset'] = None
            
            sig['sourceSelect'] = sourceSelect
            sig["DSOffset"] = ival(row, cdix['ByteOffsetWithinMsg'])
            sig["DSSize"] = ival(row, cdix['DataSetSize'])
            sig["SigSize"] = ival(row, cdix['ParameterSize'])
            if sval(row, cdix['DataFormatType']) in ['PAD','RESV']:
                continue
            
            # change the opaque to UBNR, if parametersize less than 32, for that tool can't
            sigtypetemp = sval(row, cdix['DataFormatType']) 
            if (sigtypetemp == 'OPAQUE'or sigtypetemp=='BLK') and sig['SigSize'] < 32:
                sigtypetemp ='UBNR'

            
            sig["SigType"] = normalizeSigType(sigtypetemp,sig["SigSize"])
            sig["SigOffset"] = ival(row, cdix['BitOffsetWithinDS'])            
            sig["LsbValue"] = fval(row, cdix['LsbRes'])
            #if sig['DpName'] == "ABV2_A429Word_51_2.LOAD_CURRENT":
            #    print "&&&&****",
            #    print sig['SigType'],
            #    print sig['SigOffset'],
            #    print sig['SigSize'],
            #    print sig['DSSize']
            if sig["SigType"] == 'UINT' and sig["SigOffset"]%8 !=0 and sig["SigSize"] == 8:
                print "&&&&&&&&&&&&&&&",
                #print sig['DpName']
                
            if sig['DSOffset'] is None:
                print "eee"
            try:
                sig['sigbyteoffset'],sig['sigbitoffset'],sig['sigalign'] = computeSignalAccessAFDX(sig['SigType'],sig['SigSize'], sig['SigOffset'],sig['DSSize'],sig['DSOffset'])
            except:
                with open('erro.txt','a') as f:
                    f.write(sval(row,cdix['A664Message'])+'\n')               
            #if sig['DpName'] == "ABV2_A429Word_51_2.LOAD_CURRENT":
            #    print "&&&&****",
            #    print sig['sigbyteoffset'],
            #    print sig['sigbitoffset'],
            #    print sig['sigalign']
            sig['664FSB'] = sselA664Fsb(sig)
            sig['429SSM'] = None#sselA429SSM(sig)   
            #msg['DP'][sig['fullname']] = sig
            try:
                if sig['sigalign'] is None:
                    continue
            except:
                with open('erro.txt','a') as f:
                    f.write(sval(row,cdix['A664Message'])+'\n')
                continue                
            
            #add for ADS2 update(add CRC calculate)
            if 'Application_CRC' in sig['Signal']: # the CRC signal
                #print "comt in readoutputafdxsignal crc signal"
                sig['crc_signal'] = True
                
            Sigdicts[sig['fullname']+'.'+sig['DataSet'] ] = sig 
            
        return Sigdicts
    
    def readinputcanmsg(self,sheet,cdix):
        Msgdicts = dict()
        vl = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            if sval(row,cdix['Skip']) == '#':
                continue
            msg = dict()     
            msg["Lru"] = sval(row,cdix['Pub_HostedFunction'])
            #if msg['Lru'] in self.hfnamelist:
            #    continue
            msg["Message"] = sval(row,cdix['Pub_CANMessage'])
            msg['fullname'] = msg['Lru']+'.'+msg['Message']
            msgname = msg['Lru']+'.'+msg['Message']
            msg["TXLength"] = ival(row, cdix['MessageSize'])           

            
            if msg['TXLength'] < 1 or msg['TXLength'] > 8:
                logger.error('the Txlength of msg: %s is wrong' % msgname)
                continue
            
            
            msg["TXRate"] = int(fval(row, cdix['Pub_RefreshPeriod']))
            msg["RxRate"] = ival(row, cdix['Sub_SamplePeriod'])
            
            msg["MsgID"] = sval(row, cdix['Pub_MessageID'])
            
            msg["PhysPort"] = sval(row, cdix['Pub_Physical'])
            msg['Signals']= dict()
            Msgdicts[msgname] = msg 
               
            #msg["ActualPath"]    
            
        return Msgdicts     
    
    def readinputcansignal(self,sheet,cdix):
               
        Sigdicts = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            if sval(row,cdix['Skip']) == '#':
                continue
            sig = dict()
            sig['direct'] = 'Input'     
            sig["Lru"] = sval(row,cdix['HostedFunction'])
            #if sig['Lru'] in self.hfnamelist:
            #    continue
            sig["Message"] = sval(row,cdix['CANMessage'])
            msg = self.inputCanMsg.get(sig['Lru']+'.'+sig['Message'])
            
            if msg is None:
                logger.error('the signal can not found msg %s siglru: %s'%(sig['Lru']+'.'+sig['Message'],sig['Lru']))
                continue            
            #sig['msg'] = msg
            sig["Pubref"] = sval(row, cdix['Pub_Ref'])
            sig["RpName"] = sval(row, cdix['RP'])
            sig['fullname'] = sig['Lru']+'.'+sig['Message']+"."+sig["RpName"]
            sig["Signal"] = sval(row, cdix['DP'])
            sig["SSEL"] = sval(row, cdix['Validity'])
            
            sig["SigSize"] = ival(row, cdix['ParameterSize'])
            if sval(row, cdix['DataFormatType']) in ['PAD','RESV']:
                continue
            sigtypetemp = sval(row, cdix['DataFormatType']) 
            if (sigtypetemp == 'OPAQUE' or sigtypetemp=='BLK')and sig['SigSize'] < 32:
                sigtypetemp ='UBNR'
                
            sig["SigType"] = normalizeSigType(sigtypetemp,sig["SigSize"])
            sig["SigOffset"] = ival(row, cdix['BitOffsetWithinDS'])           
            sig["LsbValue"] = fval(row, cdix['LsbRes'])
            
            if sig['SigType'] is None:
                pass
             
            sig['sigbyteoffset'],sig['sigbitoffset'],sig['sigalign'] = computeSignalAccessCAN(sig['SigType'],sig['SigSize'], sig['SigOffset'])
            #msg['RP'][sig['fullname']] = sig
            if sig['sigalign'] is None:
                continue
            unikey = sig['Lru']+sig['Pubref']
            Sigdicts[unikey ] = sig 
            
        return Sigdicts
    
    def readoutputcanmsg(self,sheet,cdix):        
        Msgdicts = dict()
        vl = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            if sval(row,cdix['Skip']) == '#':
                continue
            msg = dict()     
            msg["Lru"] = sval(row,cdix['HostedFunction'])
            msg["Message"] = sval(row,cdix['CANMessage'])
            msg['fullname'] = msg['Lru']+'.'+msg['Message']
            msgname = msg['Lru']+'.'+msg['Message']
            msg["TXLength"] = ival(row, cdix['MessageSize'])
            
            #msg["RxLength"] = fval(row, cdix['MessageSize/RxLength'])
                        #msg["RxLength"] = fval(row, cdix['MessageSize/RxLength'])
            if msg['TXLength'] < 1 or msg['TXLength'] > 8:
                logger.error('the Txlength of msg: %s is wrong' % msgname)
                continue
            msg["TXRate"] = int(fval(row, cdix['RefreshPeriod']))
                        
            msg["MsgID"] = sval(row, cdix['MessageID'])
            
            msg["PhysPort"] = sval(row, cdix['Physical'])
            msg['Signals'] = dict()
            Msgdicts[msgname] = msg  
            #msg["ActualPath"]    
            
        return Msgdicts   
    def readoutputcansignal(self,sheet,cdix):
        Sigdicts = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            if sval(row,cdix['Skip']) == '#':
                continue
            sig = dict()
            sig['direct'] = 'Output'     
            sig["Lru"] = sval(row,cdix['HostedFunction'])
            sig["Message"] = sval(row,cdix['CANMessage'])
            msg = self.outputCanMsg.get(sig['Lru']+'.'+sig['Message'])
            
            if msg is None:
                logger.error('the signal can not found msg %s'%(sig['Lru']+'.'+sig['Message']))
                continue            
            #sig['msg'] = msg
          
            sig["DpName"] = sval(row, cdix['DP'])
            sig['fullname'] = sig['Lru']+'.'+sig['Message']+"."+sig["DpName"]            
            sig["SSEL"] = sval(row, cdix['Validity'])
            
            sig["SigSize"] = ival(row, cdix['ParameterSize'])
            if sval(row, cdix['DataFormatType']) in ['PAD','RESV']:
                continue
            
            sigtypetemp = sval(row, cdix['DataFormatType']) 
            if (sigtypetemp == 'OPAQUE' or sigtypetemp=='BLK') and sig['SigSize'] < 32:
                sigtypetemp ='UBNR'
                
            sig["SigType"] = normalizeSigType(sigtypetemp,sig["SigSize"])
            sig["SigOffset"] = ival(row, cdix['BitOffsetWithinDS'])            
            sig["LsbValue"] = fval(row, cdix['LsbRes'])
            
            if sig['SigType'] is None:
                pass
             
            sig['sigbyteoffset'],sig['sigbitoffset'],sig['sigalign'] = computeSignalAccessCAN(sig['SigType'],sig['SigSize'], sig['SigOffset'])
            #msg['DP'][sig['fullname']] = sig
            Sigdicts[sig['fullname'] ] = sig 
            
        return Sigdicts
    
    
    
    def readinput429chl(self,sheet,cdix):
        Msgdicts = dict()
        #vl = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            if sval(row,cdix['Skip']) == '#':
                continue
            msg = dict()     
            msg["Lru"] = sval(row,cdix['Pub_HostedFunction'])
            #if msg['Lru'] in self.hfnamelist:
            #    continue
            msg["TXPort"] = sval(row,cdix['Pub_A429Port'])

            msg["Channel"] = sval(row, cdix['Pub_A429Channel'])           

            msg["Txrate"] = int(fval(row, cdix['Pub_RefreshPeriod']))  
            msg["Word"] = sval(row, cdix['Pub_A429Word'])
            msg['Label'] = sval(row, cdix['Pub_Label'])
            print '********%s*********'%msg['Label']
            if msg['Label'] == '':
                print "Label is None#########################"
            msg['SDI'] = ival(row,cdix['SDI'])
            if msg['SDI'] is None:
                msg['SDI'] = -1
            msg['fullname'] = msg['Lru']+'.'+msg['Channel']+'.'+msg['Word']
            #msgname = msg['Lru']+'.'+msg['Word'][1:4]
            msg["RXPort"] = sval(row, cdix['Sub_A429Port'])
            
            msg["Protocoltype"] = sval(row, cdix['A429ProtocolType'])
            
            msg["PhysPort"] = sval(row, cdix['Pub_Physical'])
            msg['Signals']= dict()
            Msgdicts[msg['fullname']] = msg
               
            #msg["ActualPath"]    
        #print "################  T  S  Y  #####################"
        #print Msgdicts
        return Msgdicts     
    
    def readinput429signal(self,sheet,cdix):
               
        Sigdicts = dict()
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            if sval(row,cdix['Skip']) == '#':
                continue
            sig = dict()
            sig['direct'] = 'Input'     
            sig["Lru"] = sval(row,cdix['HostedFunction'])
            #print sig["Lru"]
            sig["pub_port"] = sval(row,cdix['Pub_A429Port'])
            sig["pub_channel"] = sval(row,cdix['Pub_A429Channel'])
            sig["msgname"] = sval(row,cdix['A429Message'])
            #if sig['Lru'] in self.hfnamelist:
            #    continue
            
            #labeltem = ival(row,cdix['Sub_Label'])
            #if len(str(labeltem)) ==1:
            #    sig["Label"] = '00'+str(labeltem)
            #elif len(str(labeltem)) == 2:
            #    sig["Label"] = '0'+str(labeltem)
            #else:
            #    sig['Label'] =str(labeltem)
            #print sig['Label']
            Channel= self.input429Chl.get(sig['Lru']+'.'+sig['pub_channel']+'.'+sig['msgname'])
            
            if Channel is None:
                logger.error('the signal can not found channnel %s siglru: %s'%(sig['Lru']+'.'+sig['pub_channel']+'.'+sig['msgname'],sig['Lru']))
                continue            
            #sig['msg'] = msg
            sig["Pubref"] = sval(row, cdix['Pub_Ref'])
            sig["Signal"] = sval(row, cdix['RP'])
            sig['fullname'] = sig['Lru']+'.'+sig['pub_channel']+'.'+sig['msgname']+"."+sig["Signal"]
            sig["DP"] = sval(row, cdix['DP'])
            #sig["SSEL"] = sval(row, cdix['Validity/SSEL'])
            
            sig["SigSize"] = ival(row, cdix['ParameterSize'])
            
            sigtypetemp = sval(row, cdix['DataFormatType']) 
            if (sigtypetemp == 'OPAQUE' or sigtypetemp=='BLK') and sig['SigSize'] < 32:
                sigtypetemp ='UBNR'
            
            sig["SigType"] = normalizeSigType(sigtypetemp,sig["SigSize"])
            sig["SigOffset"] = ival(row, cdix['BitOffsetWithinDS'])           
            sig["LsbValue"] = fval(row, cdix['LsbRes'])
            
            if sig['SigType'] is None:
                pass
             
            sig['sigbyteoffset'],sig['sigbitoffset'],sig['sigalign'] = computeSignalAccess429(sig['SigType'],sig['SigSize'], sig['SigOffset'])
            #msg['RP'][sig['fullname']] = sig
            if sig['sigalign'] is None:
                continue
            Sigdicts[sig['fullname'] ] = sig 
            
        return Sigdicts
    
    def readoutput429chl(self,sheet,cdix):
        Msgdicts = dict()
        
        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            if sval(row,cdix['Skip']) == '#':
                continue
            msg = dict()     
            msg["Lru"] = sval(row,cdix['HostedFunction'])
            #if msg['Lru'] in self.hfnamelist:
            #    continue
            msg["TXPort"] = sval(row,cdix['A429Port'])

            msg["Channel"] = sval(row, cdix['A429Channel'])           

            msg["Txrate"] = int(fval(row, cdix['RefreshPeriod']))  
            msg["Word"] = sval(row, cdix['A429Message'])
            msg['Label'] = sval(row, cdix['Label'])
            print '********%s*********'%msg['Label']
            if msg['Label'] == '':
                print "Label is None#########################"
            msg['SDI'] = ival(row,cdix['SDI'])
            if msg["SDI"] is None:
                msg['SDI'] = -1
            msg['fullname'] = msg['Lru']+'.'+msg['Channel']+'.'+msg['Word']
            #msgname = msg['Lru']+'.'+msg['Word'][1:4]
            
            
            msg["Protocoltype"] = sval(row, cdix['MessageProtocolType'])
            
            msg["PhysPort"] = sval(row, cdix['Physical'])
            msg['Signals']= dict()
            Msgdicts[msg['fullname']] = msg
               
            #msg["ActualPath"]    
            
        return Msgdicts     
    
    def readoutput429signal(self,sheet,cdix):
               
        Sigdicts = dict()

        for rowid in range(1,sheet.nrows): #skip the first row, it the header
            row = sheet.row(rowid)
            if sval(row,cdix['Skip']) == '#':
                continue
            sig = dict()
            sig['direct'] = 'Output'     
            sig["Lru"] = sval(row,cdix['HostedFunction'])
            sig["pub_port"] = sval(row,cdix['A429Port'])
            sig["pub_channel"] = sval(row,cdix['A429Channel'])
            sig['msgname'] = sval(row,cdix['A429Message'])
            #if sig['Lru'] in self.hfnamelist:
            #    continue
            
            #print sig['Label']
            Channel= self.output429Chl.get(sig['Lru']+'.'+sig['pub_channel']+'.'+sig['msgname'])
            
            if Channel is None:
                logger.error('the signal can not found channnel %s siglru: %s'%(sig['Lru']+'.'+sig['pub_channel']+'.'+sig['msgname'],sig['Lru']))
                continue            
            #sig['msg'] = msg
            #sig["Pubref"] = sval(row, cdix['Pub_Ref'])
            #sig["DpName"] = sval(row, cdix['DP'])
            sig["Signal"] = sval(row, cdix['DP'])
            sig['fullname'] = sig['Lru']+'.'+sig['pub_channel']+'.'+sig['msgname']+"."+sig["Signal"]

            #sig["SSEL"] = sval(row, cdix['Validity/SSEL'])
            
            sig["SigSize"] = ival(row, cdix['ParameterSize'])
            
            sigtypetemp = sval(row, cdix['DataFormatType']) 
            if (sigtypetemp == 'OPAQUE' or sigtypetemp=='BLK') and sig['SigSize'] < 32:
                sigtypetemp ='UBNR'
            
            sig["SigType"] = normalizeSigType(sigtypetemp,sig["SigSize"])
            sig["SigOffset"] = ival(row, cdix['BitOffsetWithinDS'])           
            sig["LsbValue"] = fval(row, cdix['LsbRes'])
            
            if sig['SigType'] is None:
                pass
             
            sig['sigbyteoffset'],sig['sigbitoffset'],sig['sigalign'] = computeSignalAccess429(sig['SigType'],sig['SigSize'], sig['SigOffset'])
            #msg['RP'][sig['fullname']] = sig
            if sig['sigalign'] is None:
                continue
            Sigdicts[sig['fullname'] ] = sig 
            
        return Sigdicts
    
    def Merge(self,merge, temp):
        for key, item in temp.items():
            if key not in merge.keys():
                merge[key] = item
                
    def MergeInputVL(self,merge,Temp):
        for key, item in Temp.items():
            if key not in merge.keys():
                merge[key]=item
            else:
                tempitem = merge[key]
                if self.hfname not in tempitem.receivelru:
                    tempitem.receivelru.append(self.hfname)
                for temitem in item.msgport:
                    if temitem not in tempitem.msgport:
                        tempitem.msgport.append(temitem)
                subvlcount = tempitem.suvlid
                if item.suvlid > subvlcount:
                    tempitem.suvlid = item.suvlid
                    
    def MergeOutputVL(self,merge,Temp):
        for key, item in Temp.items():
            if key not in merge.keys():
                merge[key]=item
            else:
                tempitem = merge[key]
                #if self.hfname not in tempitem.receivelru:
                #    tempitem.receivelru.append(self.hfname)
                for temitem in item.msgport:
                    if temitem not in tempitem.msgport:
                        tempitem.msgport.append(temitem)
                subvlcount = tempitem.suvlid
                if item.suvlid > subvlcount:
                    tempitem.suvlid = item.suvlid

    def ConnectSigs(self,sigdict,msgdict):
        #print "come in connectSigs"
        for key,sig in sigdict.items():
            msg = msgdict.get(sig['Lru']+'.'+sig['Message'])   
            if msg is None:
                if sig['direct'] == 'Input':
                    signame = sig['RpName']
                else:
                    signame = sig['Signal']
                logger.error ("There is not exist msgname: %s for sig" %(sig['Lru']+'.'+sig['Message'],signame));   
                continue
            
           
            if 'crc_signal' in  sig and sig['crc_signal']== True:
                #print "***************come int crc process........"
                msg['crcapplication'] = True
                msg['crcsignal'] = sig
                
            if key not in msg['Signals'].keys():
                msg['Signals'][key]= sig  
                
    def Connect429Sigs(self,sigdict,msgdict):
        
        for key,sig in sigdict.items():
            msg = msgdict.get(sig['Lru']+'.'+sig['pub_channel']+'.'+sig['msgname'])
            if msg is None:
                if sig['direct'] == 'Input':
                    signame = sig['RpName']
                else:
                    signame = sig['Signal']
                logger.error ("There is not exist msgname: %s for sig" %(sig['Lru']+'.'+sig['pub_channel']+'.'+sig['msgname'],signame));   
                continue
            if key not in msg['Signals'].keys():
                msg['Signals'][key]= sig
    
    
    #afdx
    def GetAfdxinputMessage(self):                
        inputafdxmsg = self.hfexecl.sheet_by_name('Input664Messages')
        cdix = Get_Column_Index(inputafdxmsg)
        msgtemp,vltemp = self.readinputafdxmsg(inputafdxmsg,cdix)
        self.Merge(self.inputafdxmsg, msgtemp)
        self.MergeInputVL(self.inputvl, vltemp)
        
    def GetAfdxInputSignal(self):
        inputafdxsig = self.hfexecl.sheet_by_name('Input664Signals')
        cdix = Get_Column_Index(inputafdxsig)
        signaltemp = self.readinputafdxsignal(inputafdxsig, cdix)

        self.Merge(self.inputafdxsignal, signaltemp)
        self.ConnectSigs(self.inputafdxsignal, self.inputafdxmsg)



    def GetAfdxoutputMessage(self):        
        outputafdxmsg = self.hfexecl.sheet_by_name('Output664Messages')
        cdix = Get_Column_Index(outputafdxmsg)
        msgtemp,vltemp = self.readoutputafdxmsg(outputafdxmsg,cdix)
        self.Merge(self.outputafdxmsg, msgtemp)
        self.MergeOutputVL(self.outputvl, vltemp)        
        
    def GetAfdxoutputSignal(self):
        outputafdxsig = self.hfexecl.sheet_by_name('Output664Signals')
        cdix = Get_Column_Index(outputafdxsig)
        signaltemp = self.readoutputafdxsignal(outputafdxsig, cdix)
        self.Merge(self.outputafdxsignal, signaltemp)
        self.ConnectSigs(self.outputafdxsignal, self.outputafdxmsg)
    #can    
    def GetCaninputMessage(self):        
        inputcanmsg = self.hfexecl.sheet_by_name('Input825Messages')
        cdix = Get_Column_Index(inputcanmsg)
        msgtemp = self.readinputcanmsg(inputcanmsg,cdix)
        self.Merge(self.inputCanMsg, msgtemp)
        
    def GetCanInputSignal(self):
        inputcansig = self.hfexecl.sheet_by_name('Input825Signals')
        cdix = Get_Column_Index(inputcansig)
        signaltemp = self.readinputcansignal(inputcansig, cdix)
        self.Merge(self.inputCanSignal, signaltemp)
        self.ConnectSigs(self.inputCanSignal, self.inputCanMsg)

    def GetCanoutputMessage(self):        
        outputcanmsg = self.hfexecl.sheet_by_name('Output825Messages')
        cdix = Get_Column_Index(outputcanmsg)
        msgtemp = self.readoutputcanmsg(outputcanmsg,cdix)
        self.Merge(self.outputCanMsg, msgtemp)
        
    def GetCanoutputSignal(self):
        inputafdxsig = self.hfexecl.sheet_by_name('Output825Signals')
        cdix = Get_Column_Index(inputafdxsig)
        signaltemp = self.readoutputcansignal(inputafdxsig, cdix)
        self.Merge(self.outputCanSignal, signaltemp)
        self.ConnectSigs(self.outputCanSignal, self.outputCanMsg)
        
    #a429    
    def Geta429InputChl(self):        
        input429chl = self.hfexecl.sheet_by_name('Input429Messages')
        cdix = Get_Column_Index(input429chl)
        msgtemp = self.readinput429chl(input429chl,cdix)
        self.Merge(self.input429Chl, msgtemp)
        #print "#####################T S Y ###########################"
        #print self.input429Chl
        
    def Geta429InputSignal(self):
        input429sig = self.hfexecl.sheet_by_name('Input429Signals')
        cdix = Get_Column_Index(input429sig)
        signaltemp = self.readinput429signal(input429sig, cdix)
        self.Merge(self.input429Signal, signaltemp)
        self.Connect429Sigs(self.input429Signal, self.input429Chl)

    def Geta429outputMessage(self):        
        output429chl = self.hfexecl.sheet_by_name('Output429Messages')
        cdix = Get_Column_Index(output429chl)
        msgtemp = self.readoutput429chl(output429chl,cdix)
        self.Merge(self.output429Chl, msgtemp)
        
    def Geta429outputSignal(self):
        output429sig = self.hfexecl.sheet_by_name('Output429Signals')
        cdix = Get_Column_Index(output429sig)
        signaltemp = self.readoutput429signal(output429sig, cdix)
        self.Merge(self.output429Signal, signaltemp)
        self.Connect429Sigs(self.output429Signal, self.output429Chl)
    
IDUlist=['HF_IDULEFTINBOARD','HF_IDULEFTOUTBOARD','HF_IDUCENTER','HF_IDURIGHTINBOARD','HF_IDURIGHTOUTBOARD']  

def AnalysisExcel(workdir,hfnamelist):
    print ('Coming in Analysis Excel...')
    gac = GenerateAds2ConfByExcel(hfnamelist)
    
    for hfname in hfnamelist:
        print ('Now Processing %s' %hfname)
        gac.hfname = hfname
        gac.hfexecl = xlrd.open_workbook(os.path.join(workdir,hfname)+'-icd.xlsx')      
        #AFDX INPUT
        gac.GetAfdxinputMessage()
        gac.GetAfdxInputSignal()
        
        #AFDX OUTPUT
        gac.GetAfdxoutputMessage()
        gac.GetAfdxoutputSignal()
        
        #CAN INPUT
        gac.GetCaninputMessage()
        gac.GetCanInputSignal()
        
        #CAN OUTPUT
        gac.GetCanoutputMessage()
        gac.GetCanoutputSignal()
        
        gac.Geta429InputChl()
        gac.Geta429InputSignal()
        
        gac.Geta429outputMessage()
        gac.Geta429outputSignal()
    #for vl in gac.inputvl.values():
    #    print vl.lru
    #for vl in gac.outputvl.values():
    #    print vl.lru
    """
    for hfname in IDUlist:
        #A429 INPUT
        #print hfname
        gac.hfname = hfname
        if os.path.isfile(os.path.join(workdir,hfname)+'-icd-429.xlsx'):
            gac.hfexecl = xlrd.open_workbook(os.path.join(workdir,hfname)+'-icd-429.xlsx')  
            
            gac.Geta429InputChl()
            gac.Geta429InputSignal()
        else:
            logger.error("There is not exist file: %s " %(os.path.join(workdir,hfname)+'-icd-429.xlsx'));
    """   
        #CAN OUTPUT
        #gac.Geta429outputMessage()
        #gac.Geta429outputSignal()
    print ('Leaving Analysis Excel...')
    return gac
    
def main(argv):
    AnalysisExcel(r'D:\C919Tools\GeneExcelICD\Output\bp4.2\BP4.2.0 Process V1.0',['HF_IDUCENTER','FDAS_L1'])

if __name__ == "__main__":
    sys.exit(main(sys.argv))
