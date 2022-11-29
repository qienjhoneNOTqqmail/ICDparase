import os
import sys
import getopt

#DSB_ROOT = os.environ.get('DSB_ROOT')
TFG_ROOT = os.path.join('C:', '\\TechSAT', 'TestFrameGen', 'lib', 'python')

sys.path.append(TFG_ROOT)

from ScadeImport.importScadeType import XscadeReader


def usage():
    print 'iomGenDDOffset generates the offset xml file from SCADE DD'
    print 'args: -m --model       SCADE operator name. e.g. PFDTopLevel'
    print '      -r --rootdir     Root Directory from where SCADS shall search for xscade files.'
    print '      [-o --outputdir] Directory where the generated files will be stored. Current directory per default'
    print '      [-c --cvt]       Generate CVT in outputdir directory.'
    print '      [-s --struct]    Name of C Structure. Name of CVT if not set.'

def main(argv):
    try:
        opts, args = getopt.getopt(argv[1:], 'hm:r:o:c:s:', ['help', 'model=', 'rootdir=', 'outputdir=', 'cvt=', 'struct='])
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    modelname = None
    modelrootdir = None
    cvt = None
    cstruct = None
    workpath = '.'

    for opt, arg in opts:
        if opt in ('-m', '--model'):
            modelname = arg
        elif opt in ('-r', '--rootdir'):
            modelrootdir = arg
        elif opt in ('-o', '--outputdir'):
            workpath = arg
        elif opt in ('-c', '--cvt'):
            cvt = arg
        elif opt in ('-s', '--struct'):
            cstruct = arg
    
    if not modelname or not modelrootdir:
        usage()
        sys.exit(2)
        
    if not cstruct:
        cstruct = cvt

    searchlist = [modelrootdir + '/' + modelname, modelrootdir + '/Common', modelrootdir ] 
        
    try:
        # The names of input model and output model must be "ModelInput" and "ModelOutput"
        reader = XscadeReader('%s.xscade' % modelname, searchlist)
        reader.processNode()
    except Exception as e:
        print "Error: XscadeReader initialize failed. Abort." + str(e)
        sys.exit(2)

    # create variable list with attributes
    namelist = []
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
        
    from ScadeSimGen.genAds2ScadeSim import genDDMap, genAds2Cvt, genCStruct
    genDDMap(inputNamelist, outputNamelist, modelname, workpath)
    curDir = os.getcwd()
    os.chdir(workpath)
    print ("DD offset generated under %s" % os.getcwd())

    if cvt is not None:
        genAds2Cvt(inputNamelist, cvt)
        print ("ADS2 CVT generated under %s" % os.getcwd())
        genCStruct(inputNamelist, cvt, cvt, cstruct)

    os.chdir(curDir)
    
if __name__ == '__main__':
    main(sys.argv)
