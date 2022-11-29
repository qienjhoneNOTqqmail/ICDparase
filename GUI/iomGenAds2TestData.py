import xlrd
import re
import sys
from Cheetah.Template import Template
from lxml import etree

import iomGenCommon


CVTConfigTemplate = '''
 VERSION_CONTROL {
    FILE_NAME = "\$RCSfile: cvsheader.inc,v \$";
    REVISION = "\$Revision: 1.2 \$";
    AUTHOR = "\$Author: bad \$";
    DATE = "\$Date: 2006/07/27 12:58:00 \$";
}

CVT {
 #for $key in $model.cvtpoints.keys()
	#set $p = $model.cvtpoints[$key]
	#set $type = 'int32'
	#if $p.type == 'FLOAT'
		#set $type = 'real32'
	#end if	
    POINT $key = {
        DOCUMENTATION = "$key";
        CHANNELMODE = "SAMPLING";
        DESCRIPTION = "$key";
        MESSAGETYPE = "";
        UNIT = "none";
        FORMAT = "";
        DATATYPE = "$type";
        DATASIZE = "4";
        ELEMENTS = "1";
        VARLENGTH = "0";
        FIFOLENGTH = "1";
        DEFAULTVALUE = "";
        MINVALUE = "0";
        MAXVALUE = "0";
        VALUEMAP = {
        }

        ERRINJECT_PUT = "0";
        ERRINJECT_GET = "0";
        SAMPLE_ON_REQUEST = "0";
        EXTID = "0";
        DISCARD_OOR = "0";
        ATOMIC = "0";
        GETHANDLER = "";
        PUTHANDLER = "";
        ALIASLIST = {
        }
    }
 #end for
}
'''


IOMAds2Template = '''
VERSION_CONTROL {
    FILE_NAME = "\$RCSfile: cvsheader.inc,v \$";
    REVISION = "\$Revision: 1.2 \$";
    AUTHOR = "\$Author: bad \$";
    DATE = "\$Date: 2006/07/27 12:58:00 \$";
}

IOMAP {
    INPUTS {
    }

    TRANSPUTS {
        TCP-UDP ETH-3 = {
            description {
                comment = "TBD";
            }
			#set $modelname = $model.modelname+"Ouput"
            UDP-RX-Socket $modelname = {
                CONFIGURATION {
                    comment = "";
                    address = "0.0.0.0";
                    port = "15001";
                    raw = "0";
                    buffer = {
                        size = "8192";
                        count = "8";
                    }

                    received_msgs = "";
                    received_bytes = "";
                    discarded_bytes = "";
                }

                rxmsgs = {
                    Message CMD_RSP = {
                        FILTER {
                            comment = "";
                            NONE msgident = {
                            }

                            sequence = {
                                type = "NONE";
                                bytes = "0:0";
                                add = "0";
                                counter = "";
                                error_count = "";
                            }

                            NONE checksum = {
                            }

                            disabled = "0";
                            activate = {
                                point = "";
                                mask = "0xffffffff";
                            }

                            received_msgs = "";
                            received_bytes = "";
                        }

                        signals = {
                          #for $key in $model.cvtpoints.keys()
                            #set $p = $model.cvtpoints[$key]
							#set bytesStart = $p.offset
							#set bytesEnd = $p.offset+3
							#set name = $p.name.split(".")[1]
                            Sample {
                                point = "$model.cvtname::$name";
                                bytes = "$bytesStart:$bytesEnd";
                                bits = "0:31";
                                ppexpr = "";
                                COPY euconvert = {
                                }                                
                            }
							
                          #end for

                        }

                    }

                }

            }

        }

    }

    OUTPUTS {
    }
}
'''

class Bunch(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)
        

def genIpAds2TestData(mapping, outfn):
    model = Bunch(cvtpoints=mapping.params, modelname=mapping.modelname, cvtname=outfn)
    tmpl = Template(IOMAds2Template, searchList=[{ "model"  : model}])
    
    s = tmpl.respond()
    open(outfn+".iom", "w").write(s)

    model = Bunch(cvtpoints=mapping.params)
    tmpl = Template(CVTConfigTemplate, searchList=[{ "model"  : model}])
    s = tmpl.respond()
    open(outfn+".cvt", "w").write(s)

def main(args):
    if len(args) < 1:
        sys.stderr.write("Usage: iomGenAds2Data ddmap [outputfile]")
        sys.exit(1)

    ddmapfile = args[0]

    if len(sys.argv) > 1:
        outputfile = args[1]
    else:
        outputfile = inputfile.rsplit(".", 1)[0]

    # read DD Map file (generated from SCADE Model)
    ddmap  = iomGenCommon.DDMapReader(ddmapfile)
        
    # Generate Test System (SDIB) configuration (CVT and IOM)
    genIpAds2TestData(ddmap, outputfile)

if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
