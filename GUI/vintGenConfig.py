import iomGenAds2DataV2
import iomGenVI
import sys
import os
import getopt


def usage():
	print 'Usage: iomGenConfig [--steps I] [--sol pseudoPort|hddPort|imaCVT] -o outputdir --app appname excelicd'
	print '       If --steps option includes I (VL), --sol should be specified. Default for --sol is pseudoPort'
	sys.exit(1)

def main():
	# Parse command line arguments
	inputddfile   = None
	outputddfile  = None
	outputdir     = None
	appname       = None
	endian		  = '--bigendian'
	steps 		  = 'I'
	solution      = 'pseudoPort'

	opts, args = getopt.getopt(sys.argv[1:], 'ho:', ['steps=', 'sol=', 'outdir=', 'app=', 'help'])

	for o, a in opts:
		if o in ['-h', '--help']:
		    usage()
		elif o in [ '-o', '--outdir']:
		    outputdir = a
		elif o in [ '--steps']:
		    steps = a
		elif o in [ '--sol']:
		    solution = a
		else:
		    usage()
		    sys.exit(1)

	if len(args) != 1:
		usage()

	excelfile = args[0]
	
	if inputddfile is None and outputddfile is None:
		usage()
	
	if outputdir is None or appname is None:
		usage()
	
	basename = os.path.basename(excelfile).rsplit('.', 1)[0]

	if not os.path.isdir(outputdir):
		os.mkdir(outputdir)

	xmlfile  = os.path.join(outputdir, basename + '.xml')

	if 'I' in steps:
		if iomGenVI.main([excelfile, outputdir, solution]) != 0:
			print "iomGenVI failed"
		else:
			print "iomGenVI OK"
	
	
	
if __name__ == "__main__":
	sys.exit(main())

