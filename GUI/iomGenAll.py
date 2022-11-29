import iomGenXml
import iomGenVxW
import iomGenBin
import iomGenAds2Data
import sys

if len(sys.argv) != 5:
	print 'Usage: iomGenAll excelfile modelmapfile outputdir appname input/output'
	sys.exit(1)

excelfile = sys.argv[1]
modelfile = sys.argv[2]
outputdir = sys.argv[3]
appname   = sys.argv[4]
inout     = sys.argv[5]

basename = excelfile.rsplit('.',1)[0]
basename = basename.replace("\\","/").rsplit('/',1)[1]
xmlfile  = outputdir+'/'+basename + '.xml'
binfile  = outputdir+'/'+basename + '.bin'
cfile    = outputdir+'/'+basename + '.c'

if iomGenXml.main([excelfile, modelfile, xmlfile]) != 0:
	sys.exit(1)

if iomGenBin.main(['--bigendian', xmlfile]) != 0:
	sys.exit(1)

if iomGenVxW.main([xmlfile, appname]) != 0:
	sys.exit(1)

if iomGenAds2Data.main([excelfile, modelfile, appname, inout]) != 0:
	sys.exit(1)

