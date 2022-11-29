 VERSION_CONTROL {
    FILE_NAME = "\$Id: \$";
    REVISION = "\$Revision: \$";
    AUTHOR = "\$Author: foo \$";
    DATE = "\$Date: 1900/01/01 08:15:00 \$";
}

CVT {
 #for $p in $model.cvtpoints
    POINT $p.name = {
        DOCUMENTATION = "XML ICD";  ##Should be BP Identifier!
        CHANNELMODE = "$p.channelmode";
        DESCRIPTION = "";
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
        #for $a in $p.aliases
                #for $a_ in $a.split(',')
                        { ALIAS = "$a_"; }
                #end for
        #end for
        }
    }
 #end for
}
