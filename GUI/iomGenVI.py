import xlrd
from lxml import etree
import re
import sys
import os.path


from Cheetah.Template import Template
from lxml import etree
import iomGenCommon

import pdb
def excepthook(ex_cls, ex, tb):
    pdb.post_mortem(tb)
#sys.excepthook = excepthook

#notes/open issues:
# Types A825, A429, DIS, ANA
# Model? Description
# Only Inputs? No Outputs?

TEMPLATE = '''
 <IOMConfiguration HF="$model.identification.application" REV="$model.identification.revision" ICD="$model.identification.icd">

 #for $key in $model.afdx.messageKeys
  #set msg=$model.afdx.messages[$key]
    <Message id="$msg.msgid" messageName="$key" portType="$msg.portType" queueLength="$msg.queueLength" portId="$msg.portId" 
             rate="$msg.msgRate" 
             length="$msg.msgLength"
             dstIp="$msg.dstIp"
             dstUdp="$msg.dstPortId"
             srcUdp="$msg.srcPortId"
             srcIp="$msg.srcIp"
             vlId="$msg.vlId"
             subVl="$msg.subVl"
         />
 #end for

</IOMConfiguration>
'''

PORT_TABLE_TMPL = '''
#set inc = '#include \"hddPortDrv.h\"'
$inc
#set $id = 'const char* PORT_CFG_TABLE_ID=\"XXX '+$tblName+' XXX\";'
$id
#set $brack = '[]'
PORT_TABLE _portTableList$brack =
{
	/* pseudo port name*/
	/* pseudo port id*/
	/* UDP port number*/
	/* in/out device from device */
	/* maximum packet size*/
	/* queueing length ; 0 if sampling*/
	/* ip Src address */
    /* ip Dst address */
	/* socket handle of port*/
	/* MAC dest address for outgoing data - otherwise 00:00:00:00:00:00*/

	/*A664 / ETH */
#for $port in $pCfg
	#set global $found = 0
	#for $model in $model_		
		#for $key in $model.afdx.messageKeys
			#set msg=$model.afdx.messages[$key]
			#if $msg.direction == 'input'
				#set portName = "pseudoport_a664_rx_"+$str($msg.portId)
			#else
				#set portName = "pseudoport_a664_tx_"+$str($msg.portId)
			#end if
			#set$macAddr = "00:00:00:00:00:00"
			#if $portName != $port
				#continue
			#end if
            #set ipSrc = $msg.srcIp
            #set ipDst = $msg.dstIp
			#set udp = $str($msg.dstPortId)
			#if $msg.direction == 'input'
				#set dir = 'IN'				
			#else
				#set dir = 'OUT'
				#set macAddr = "03:00:00:00:"+$hex($msg.vlId>>8)[2:]+":"+$hex($msg.vlId&0xFF)[2:]
				#set ipDst = $ipDst.replace("224.", "10.", 1)
				#if $ipDst == ""
					#set ipDst = "10.224.0.0"
				#end if
			#end if
			#set msgSize = $msg.msgLength
			#if $msg.queueLength > 0
				#set qLen = $msg.queueLength
			#else
				#set qLen = 0
			#end if
			#set global $found = 1
			##$print("SUCC: %s found in ICD %d" % ($port, $found))
	{"/hdd/$portName"	, -1, $udp , $dir, 	$msgSize, $qLen, "$ipSrc", "$ipDst", -1, "$macAddr"},
			#break
		#end for
		#if $found == 1
			#break
		#end if
	#end for
	#if $found != 1
		$print("Error: %s not found in ICD %d" % ($port, $found))
	#end if
#end for
#set $ifdef = "#ifdef A825_SUPPORT"
#set $endif = "#endif"
$ifdef
	/*A825 / ETH not supported yet*/
	/*{"/hdd/A825_TX1", -1, 18251, OUT, 16, 10, "10.31.1.1", "10.224.82.51", -1, "03:00:00:00:00:02"},*/
	/*{"/hdd/A825_TX2", -1, 18252, OUT, 16, 10, "10.31.1.1", "10.224.82.52", -1, "03:00:00:00:00:02"},*/
	{"/hdd/A825_RX1", -1, 18253, IN, 16, 10,  "10.31.1.1", "224.224.82.53", -1, "03:00:00:00:00:01"},
	{"/hdd/A825_RX2", -1, 18254, IN, 16, 10,  "10.31.1.1", "224.224.82.54", -1, "03:00:00:00:00:01"},
$endif	
#set $ifdef = "#ifdef A429_SUPPORT"
$ifdef	
	/*A429 / ETH not supported yet
	{"/hdd/pseudoport_a429_TX1", -1, 14291, OUT, 4, 5, "10.31.1.1", "10.224.42.91", -1, "03:00:00:00:00:02"},
	{"/hdd/pseudoport_a429_TX2", -1, 14292, OUT, 4, 5, "10.31.1.1", "10.224.42.92", -1, "03:00:00:00:00:02"},
	{"/hdd/pseudoport_a429_TX3", -1, 14293, OUT, 4, 5, "10.31.1.1", "10.224.42.93", -1, "03:00:00:00:00:02"},
	{"/hdd/pseudoport_a429_RX1", -1, 14294, IN, 4, 5,  "10.31.1.1", "224.224.42.94", -1, "03:00:00:00:00:01"},
	{"/hdd/pseudoport_a429_RX2", -1, 14295, IN, 4, 5,  "10.31.1.1", "224.224.42.95", -1, "03:00:00:00:00:01"},
	{"/hdd/pseudoport_a429_RX3", -1, 14296, IN, 4, 5,  "10.31.1.1", "224.224.42.96", -1, "03:00:00:00:00:01"},
	{"/hdd/pseudoport_a429_RX4", -1, 14297, IN, 4, 5,  "10.31.1.1", "224.224.42.97", -1, "03:00:00:00:00:01"},
	{"/hdd/pseudoport_a429_RX5", -1, 14298, IN, 4, 5,  "10.31.1.1", 224.224.42.98", -1, "03:00:00:00:00:01"},
	{"/hdd/pseudoport_a429_RX6", -1, 14299, IN, 4, 5,  "10.31.1.1", "224.224.42.99", -1, "03:00:00:00:00:01"},*/
$endif
#set $ifdef = "#ifdef DIS_SUPPORT"	
$ifdef
	/*DIS / ETH 
	{"/hdd/pseudoport_disio_IN", -1, 15000, IN, 2, 2, "10.31.1.1", "224.224.1.1", -1, "03:00:00:00:00:01"},
	{"/hdd/pseudoport_disio_OUT", -1, 15001, OUT, 2, 2, "10.31.1.1", "10.224.1.2", -1, "03:00:00:00:00:02"},*/
 $endif	
	/*EOL do not delete*/
	{""	, -1 , -1, -1, -1, -1, "", "",  -1}

};

'''

PORT_CFG_TMPL = '''
<PseudoPartitionDescription>
	<Ports>
#for $model in $model_
#for $key in $model.afdx.messageKeys
  #set msg=$model.afdx.messages[$key]
  #if $msg.direction == 'input'
	#set dir = "SOURCE"
    #set refreshRate="$msg.msgRate"
  #else
    #set dir = "DESTINATION"
    #set refreshRate="$msg.msgValidityPeriod"
  #end if
  #if $msg.queueLength > 0
	 #if $msg.direction == 'input'
		#set proto = "RECEIVER_DISCARD"
	 #else
		#set proto = "NOT_APPLICABLE"
	 #end if
        <QueuingPort Name="pseudoport_a664_$str($msg.portId)" Attribute="PSEUDO_PORT" Direction="$dir" MessageSize="$msg.msgLength" QueueLength="$msg.queueLength" DriverName="hddPortDrv" Protocol="$proto"/>
  #else
        <SamplingPort Name="pseudoport_a664_$str($msg.portId)" Attribute="PSEUDO_PORT" Direction="$dir" MessageSize="$msg.msgLength" RefreshRate="$refreshRate" DriverName="hddPortDrv" />
  #end if
#end for
#end for
		 <!--<QueuingPort Name="pseudoport_a825_TX1"  Attribute="PSEUDO_PORT" Direction="DESTINATION" MessageSize="16" QueueLength="2" DriverName="hddPortDrv" Protocol="NOT_APPLICABLE" />
		 <QueuingPort Name="pseudoport_a825_TX2" Attribute="PSEUDO_PORT" Direction="DESTINATION" MessageSize="16" QueueLength="2" DriverName="hddPortDrv" Protocol="NOT_APPLICABLE" /> -->
		 <QueuingPort Name="A825_RX1" Attribute="PSEUDO_PORT" Direction="SOURCE" MessageSize="12" QueueLength="1" DriverName="hddPortDrv" Protocol="RECEIVER_DISCARD" />
		 <QueuingPort Name="A825_RX2" Attribute="PSEUDO_PORT" Direction="SOURCE" MessageSize="12" QueueLength="1" DriverName="hddPortDrv" Protocol="RECEIVER_DISCARD" />
		 <!--<QueuingPort Name="pseudoport_a429_TX1" Attribute="PSEUDO_PORT" Direction="DESTINATION" MessageSize="4" QueueLength="5" DriverName="hddPortDrv" Protocol="NOT_APPLICABLE" />
		 <QueuingPort Name="pseudoport_a429_TX2" Attribute="PSEUDO_PORT" Direction="DESTINATION" MessageSize="4" QueueLength="5" DriverName="hddPortDrv" Protocol="NOT_APPLICABLE" />
		 <QueuingPort Name="pseudoport_a429_TX3" Attribute="PSEUDO_PORT" Direction="DESTINATION" MessageSize="4" QueueLength="5" DriverName="hddPortDrv" Protocol="NOT_APPLICABLE" />
		 <QueuingPort Name="pseudoport_a429_RX1" Attribute="PSEUDO_PORT" Direction="SOURCE" MessageSize="4" QueueLength="5" DriverName="hddPortDrv" Protocol="RECEIVER_DISCARD" />
		 <QueuingPort Name="pseudoport_a429_RX2" Attribute="PSEUDO_PORT" Direction="SOURCE" MessageSize="4" QueueLength="5" DriverName="hddPortDrv" Protocol="RECEIVER_DISCARD" />
		 <QueuingPort Name="pseudoport_a429_RX3" Attribute="PSEUDO_PORT" Direction="SOURCE" MessageSize="4" QueueLength="5" DriverName="hddPortDrv" Protocol="RECEIVER_DISCARD" />
		 <QueuingPort Name="pseudoport_a429_RX4" Attribute="PSEUDO_PORT" Direction="SOURCE" MessageSize="4" QueueLength="5" DriverName="hddPortDrv" Protocol="RECEIVER_DISCARD" />
		 <QueuingPort Name="pseudoport_a429_RX5" Attribute="PSEUDO_PORT" Direction="SOURCE" MessageSize="4" QueueLength="5" DriverName="hddPortDrv" Protocol="RECEIVER_DISCARD" />
		 <QueuingPort Name="pseudoport_a429_RX6" Attribute="PSEUDO_PORT" Direction="SOURCE" MessageSize="4" QueueLength="5" DriverName="hddPortDrv" Protocol="RECEIVER_DISCARD" />
		 <QueuingPort Name="pseudoport_disio_IN" Attribute="PSEUDO_PORT" Direction="SOURCE" MessageSize="2" QueueLength="2" DriverName="hddPortDrv" Protocol="RECEIVER_DISCARD" />
		 <QueuingPort Name="pseudoport_disio_OUT" Attribute="PSEUDO_PORT" Direction="DESTINATION" MessageSize="2" QueueLength="2" DriverName="hddPortDrv" Protocol="NOT_APPLICABLE" />
	</Ports>
</PseudoPartitionDescription>
'''

ALIAS_CVT_TMPL = '''
VERSION_CONTROL {
	FILE_NAME = "\$RCSfile: \$";
	REVISION = "\$Revision: \$";
	AUTHOR = "\$Author: \$";
	DATE = "\$Date: \$";
}

CVT {
#for $model in $model_
#for $key in $model.afdx.messageKeys
	#set msg=$model.afdx.messages[$key]
	#set name = $msg.fullname
	#if $msg.queueLength > 0
		#set mode = "MUXFIFO"
		#set qlen = $msg.queueLength
	#else
		#set mode = "SAMPLING"
		#set qlen = 1
	#end if
	#set len = $msg.msgLength
	#set portName = "apexport_a664_"+$str($msg.portId)
	POINT $name = {
		DOCUMENTATION = "$model.identification.icd";
		CHANNELMODE = "$mode";
		DESCRIPTION = "";
		UNIT = "opaque";
		FORMAT = "%x";
		DATATYPE = "byte";
		DATASIZE = "0";
		#set $len_ = $len+32
		ELEMENTS = "$len_";
		VARLENGTH = "1";
		FIFOLENGTH = "$qlen";
		DEFAULTVALUE = "";
		MINVALUE = "0";
		MAXVALUE = "255";
		ERRINJECT_PUT = "0";
		ERRINJECT_GET = "0";
		SAMPLE_ON_REQUEST ="0";
		EXTID = "0";
		DISCARD_OOR = "0";
		ATOMIC ="0";
		GETHANDLER = "0";
		PUTHANDLER = "0";
		VALUEMAP = {}
		ALIASLIST = {
			{ ALIAS = "$portName"; }
			{ ALIAS = "$msg.portName"; }
		}
	}
#end for
#end for
}	
'''
class Bunch(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

def createOutput(outfn, s):
   #os.makedirs(os.path.dirname(outfn))
   open(outfn, "w").write(s)
	
def genHddPortCfg(mapping, outfn): #obsolete: use IDU IOM pseudoPort def instead
    tmpl = Template(PORT_CFG_TMPL, searchList=[{ "model_": mapping}])
    s = tmpl.respond()
    createOutput(outfn, s)

def genHddPortTblCheck(el, mapping):
	try: 
		drv 			= el.get('DriverName')	
		assert drv == "hddPortDrv", "Driver Name"
		name	 		= el.get('Name')
		if ("825" in name) or ("429" in name):
			print "Review manually " + name 
			return 1 
		direction		= el.get('Direction')
		mode			= el.tag
		msgsize		= int(el.get('MessageSize'))
		pid			= int(name.split("_")[3])
		if direction == "SOURCE" :	# Input Message
			map = mapping[0]
		else:
			map = mapping[1]	
			
		for key in map.afdx.messageKeys:
			msg = map.afdx.messages[key]
			if msg.portId == pid:
				assert msgsize == msg.msgLength, "Message Size"
				assert (msg.direction == 'input' and direction == 'SOURCE') or \
						(msg.direction == 'output' and direction == 'DESTINATION') , "Direction"
				assert (msg.queueLength > 0 and mode.find("QueuingPort") > -1 ) or \
						(msg.queueLength == 0 and mode.find("SamplingPort") > -1 ), "Mode"
				if mode.find("QueuingPort") > -1:
					assert msg.queueLength == int(el.get('QueueLength')), "Queue Length"
				return 1
		print "Error: CFG on %s (%s)" % (el.get('Name'), "not found")
	except AssertionError, args:
		print "Error: CFG on %s (%s)" % (el.get('Name'), args)
		return False
	
def genHddPortTbl(mapping, outfn, tblName, pseudoPortsXml):
	pCfg = []
	err = 0
	# for el in pseudoPortsXml.iter(tag=etree.Element):
		# if el.tag.endswith('QueuingPort') or el.tag.endswith('SamplingPort'):
			# pCfg.append(el.get('Name'))
			# if (el.get('Name') == "pseudoport_a664_66225"):
				# print el#
	try:
		ns = pseudoPortsXml.nsmap[None]
		tag = "{"+ns+"}QueuingPort"
	except:
		tag = "QueuingPort"
		
	for el in pseudoPortsXml.findall("*//"+tag):
		if  el is not None:
			if genHddPortTblCheck(el, mapping):
				print el.get('Name')
				pCfg.append(el.get('Name'))
			else:
				err += 1

	try:
		tag = "{"+ns+"}SamplingPort"
	except:
		tag = "SamplingPort"
	for el in pseudoPortsXml.findall("*//"+tag):
		if  el is not None:
			if genHddPortTblCheck(el, mapping):
				print el.get('Name')
				pCfg.append(el.get('Name'))
			else:
				err += 1
	if err:
		return
		
	tmpl = Template(PORT_TABLE_TMPL, searchList=[{ "model_": mapping}, {"tblName":tblName}, {"pCfg":pCfg}])
	s = tmpl.respond()
	createOutput(outfn, s)
	
def genGpmPortAliasCvt(mapping, outfn):  #obsolete: function will be provided by genAds2 tools
    tmpl = Template(ALIAS_CVT_TMPL, searchList=[{ "model_": mapping}])
    s = tmpl.respond()
    createOutput(outfn, s)


def main(args):
	if len(args) != 3:
		sys.stderr.write("Usage: iomGenVIHdd inputfile pseudoPortDef outputdir")
		return 1
		
		
	inputfile = args[0]
	pseudoPortDef = args[1]
	outputdir = args[2]
	solution = "hddPort" #imaCVT|pseudoPort obsolete
	
	modelIn = iomGenCommon.MapReader(inputfile, msgonly=True, direction='input', ignoreSrc=True)
	modelOut = iomGenCommon.MapReader(inputfile, msgonly=True, direction='output', ignoreSrc=True)
	#if model.errorCount > 0: 
	#    return 1
	
	#if solution == "pseudoPort":
	#	genHddPortCfg([modelIn, modelOut], os.path.join(outputdir, "pseudoCfg.xml"))
	
	
	if solution == "hddPort":
		class_ = os.path.basename(inputfile).split('.')[0]
		class_ = class_.replace("-icd", "")
		fn = "hddPortTbl.c"
		
		xmltree = etree.parse(pseudoPortDef)
		pseudoPortsXml = xmltree.getroot()

		genHddPortTbl([modelIn, modelOut], os.path.join(outputdir, fn), class_, pseudoPortsXml )		
	
	#if solution == "imaCVT":  
	#	class_ = os.path.basename(inputfile).split('.')[0]
	#	class_ = class_.replace("-icd", "")
	#	fn = "gpmPortAlias_" + class_ + ".cvt"	
	#	genGpmPortAliasCvt([modelIn, modelOut], os.path.join(outputdir, fn))		
	return 0


if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))