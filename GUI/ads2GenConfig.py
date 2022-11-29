import iomGenXml
import iomGenVxW
import iomGenBin
import iomGenAds2Data
import iomGenVI
import sys
import os
import getopt


def usage():
    print 'Usage: ads2GenConfig --msgmode raw|signals|params --simmode sim|stim -o outputdir excelicd'

def main():
    # Parse command line arguments
    outputdir     = None
    steps         = 'A'
    simmode       = 'stim'        # other value "sim"
    msgmode       = 'signals'    # other value "raw"
    target        = 'SWTESTS'      # other values: SSDL, MDVS
    splitiom      = 'False'
    prefix        = None
    deviceMap     = None
    
    opts, args = getopt.getopt(sys.argv[1:], 'hm:s:p:o:x:X:', ['splitiom=','simmode=', 'msgmode=', 'outdir=', 'prefix=', 'target=', 'help','deviceMap='])
    
    for o, a in opts:
        if o in ['-h', '--help']:
            usage()
        elif o in ['-o', '--outdir']:
            outputdir = a
        elif o in ['-p', '--prefix']:
            prefix = a
        elif o in ['-s', '--simmode']:
            simmode = a
        elif o in ['-m', '--msgmode']:
            msgmode = a
        elif o in ['-t', '--target']:
            target = a
        elif o in ['-x', '--splitiom']:
            splitiom = a
        elif o in ['-X', '--deviceMap']:
            deviceMap = a
        else:
            usage()
            return -1
    
    if simmode not in ("sim", "stim"):
        usage()
        return -1
    
    if msgmode not in ('raw', 'signals', 'params'):
        usage()
        return -1
    
    if len(args) != 1:
        usage()
        return -1
    
    excelfile = args[0]
    
    if outputdir is None: 
        usage()
        return -1
    
    
    basename = os.path.basename(excelfile).rsplit('.', 1)[0]
    
    if not os.path.isdir(outputdir):
        os.mkdir(outputdir)
    
    # FIXME: Add merging of multiple ICDs 

    if 'A' in steps:
        if iomGenAds2Data.main([excelfile, outputdir, prefix, simmode, msgmode, target, splitiom, deviceMap]) != 0:
            print "iomGenADS2 failed"
        else:
            print "iomGenADS2 OK"
    
if __name__ == "__main__":
    sys.exit(main())

