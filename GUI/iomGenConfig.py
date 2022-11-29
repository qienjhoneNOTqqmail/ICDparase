import iomGenXml
import iomGenVxW
import iomGenBin
import sys
import os
import getopt


def usage():
    print 'Usage: iomGenConfig [--littleendian|--bigendian] [--steps XBV] [--sol pseudoPort|hddPort|imaCVT] [--indd modelinputdd] [--outdd modeloutputdd] -o outputdir --app appname excelicd'
    sys.exit(1)

def main():
    # Parse command line arguments
    inputddfiles  = []
    outputddfiles = []
    outputdir     = None
    appname       = None
    endian          = '--xxendian'
    steps           = 'XBV'

    opts, args = getopt.getopt(sys.argv[1:], 'ho:', \
                            ['littleendian', 'bigendian', 'xxendian', 'steps=', 'indd=', 'outdd=', 'outdir=', 'app=', 'help'])

    for o, a in opts:
        if o in ['-h', '--help']:
            usage()
        elif o in ['--littleendian', '--bigendian']:
            endian = o
        elif o in [ '--indd']:
            inputddfiles.append(a)
        elif o in [ '--outdd']:
            outputddfiles.append(a)
        elif o in [ '-o', '--outdir']:
            outputdir = a
        elif o in [ '-a', '--app']:
            appname = a
        elif o in [ '--steps']:
            steps = a
        else:
            usage()
            sys.exit(1)

    if len(args) != 1:
        usage()

    excelfile = args[0]
    
    if inputddfiles is [] and outputddfiles is []:
        usage()
    
    if outputdir is None or appname is None:
        usage()
    
    basename = os.path.basename(excelfile).rsplit('.', 1)[0]

    if not os.path.isdir(outputdir):
        os.mkdir(outputdir)

    xmlfile  = os.path.join(outputdir, basename + '.xml')

    if 'X' in steps:
        arglist = []
        for x in inputddfiles:
            arglist += ['--indd', x] 
        for x in outputddfiles:
            arglist += ['--outdd', x] 
        if iomGenXml.main(arglist + ['-o', xmlfile, '-a', appname, excelfile]) != 0:
            print "iomGenXml failed"
        else:
            print "iomGenXml OK"
    
    if 'B' in steps:
        if iomGenBin.main(['--littleendian', xmlfile, outputdir]) != 0:
            print "iomGenBIN --littleendian failed"
        else:
            print "iomGenBIN --littleendian OK"

        if iomGenBin.main(['--bigendian', xmlfile, outputdir]) != 0:
            print "iomGenBIN --bigendian failed"
        else:
            print "iomGenBIN --bigendian OK"
    
    if 'V' in steps:
        if iomGenVxW.main([xmlfile, appname, outputdir]) != 0:
            print "iomGenVXW failed"
        else:
            print "iomGenVXW OK"
    
if __name__ == "__main__":
    sys.exit(main())