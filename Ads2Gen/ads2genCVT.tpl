 VERSION_CONTROL {
    FILE_NAME = "\$RCSfile: cvsheader.inc,v \$";
    REVISION = "\$Revision: 1.2 \$";
    AUTHOR = "\$Author: bad \$";
    DATE = "\$Date: 2006/07/27 12:58:00 \$";
}

CVT {
 #for $p in $cvtpoints.values()
    ##$print("message protocal is %s " % ($p.name))
    POINT $p.name = {
        DOCUMENTATION = "$p.name";
        CHANNELMODE = "$p.channelmode";
        DESCRIPTION = "$p.name";
        MESSAGETYPE = "";
        UNIT = "none";
        FORMAT = "";
        DATATYPE = "$p.datatype";
        DATASIZE = "$p.datasize";
        ELEMENTS = "$p.elements";
        VARLENGTH = "$p.varlength";
        FIFOLENGTH = "1";
        DEFAULTVALUE = "$p.defaultvalue";
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
        #for $alias in $p.alias
            { ALIAS = "$alias"; }
        #end for
        }
    }
 #end for
}
