import xlrd
import re
import sys
import os.path
import iomGenCommon

SW_CFG_TMPL = '''
disable edp ports all
disable learning  ports all
disable flooding unicast ports all
disable flooding multicast  ports all
delete fdb all
delete vlan vidu
delete vlan vsdib
delete vlan vima
'''

def getIdxPort(app, vlan_list):

	for i in range(len(vlan_list)):
		if app in vlan_list[i][1]:
			return i
	return -1

def createOutput(outfn, s):
   #os.makedirs(os.path.dirname(outfn))
   open(outfn, "w").write(s)
	
def genSwCfg(data, outfn):
	
	vlan_lst = [[ 1, "HF_IDULEFTOUTBOARD" ],	\
				[ 2, "HF_IDULEFTINBOARD" ],	\
				[ 3, "HF_IDUCENTER" ],	\
				[ 4, "HF_IDURIGHTINBOARD" ],	\
				[ 5, "HF_IDURIGHTOUTBOARD" ],	\
				[ 7, "ac1" ], 	\
				[ 8, "ac2" ], 	\
				[ 10, "FDAS_L1 SYNOPTICPAGEAPP_L SYNOPTICMENU_L IMA_DM_L4" ],	\
				[ 11, "FDAS_R3 SYNOPTICPAGEAPP_R SYNOPTICMENU_R IMA_DM_R4" ],	\
				[ 12, "FDAS_L3 IMA_DM_L5" ], 	\
				[ 16, "net" ]]
	s=SW_CFG_TMPL

	s+= "create vlan vafdx\n"
	s+= "configure vafdx tag 100\n"
	s+= "configure default delete port 1-16\n"
	s+= "configure vafdx add ports 1-16\n"
	s+= "enable learning  port 1-16\n\n"

	vlsPorts = {}
	
	#DS AFDX
	for app in data:
		print "configure sw for %s" % (app[0])
		for vl in app[1].afdx.vls.values(): #!!!!input vl
			print "-check in vl %s" % (vl.vlName)
			port =  vlan_lst[getIdxPort(app[0], vlan_lst )][0]
			if not port:
				continue
			if vl.macAdd not in vlsPorts.keys():
				vlsPorts[vl.macAdd] = []
			if not str(port) in vlsPorts[vl.macAdd]:
				vlsPorts[vl.macAdd].append(str(port))
				
	for vl in vlsPorts.keys():
		print vl + " " + repr(vlsPorts[vl])
		p = ""
		s+="Create fdbentry "+vl+" vlan vafdx ports %s\n"%(( ",".join(vlsPorts[vl])))	
				
	#CAN/A429/DIS-ETH
	s += "Create fdbentry 03:00:00:00:00:01 vlan vafdx ports 1,2,3,4,5\n"
	s += "Create fdbentry 03:00:00:00:00:02 vlan vafdx port 8\n"
	

	createOutput(outfn, s)

def main(args):
	if len(args) <= 2:
		sys.stderr.write("Usage: iomGenSWCfg outputdir inputfile1 inputfile2 ... ")
		sys.exit(1)
	
	outputdir = args[0]
	inputfiles = args[1:]
	
	data = []

	for inputfile in inputfiles:
		class_ = os.path.basename(inputfile).split('.')[0]
		class_ = class_.replace("-icd", "")
		
		modelIn = iomGenCommon.MapReader(inputfile, msgonly=True, direction='input', ignoreSrc=True)
		modelOut = iomGenCommon.MapReader(inputfile, msgonly=True, direction='output', ignoreSrc=True)
		data.append([class_, modelIn, modelOut])
	
	genSwCfg(data, os.path.join(outputdir, "cliListSDIB.xsf"))		
	
	return 0


if __name__ == '__main__':
	sys.exit(main(sys.argv[1:]))