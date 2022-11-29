VERSION_CONTROL {
    FILE_NAME = "\$RCSfile: cvsheader.inc,v \$";
    REVISION = "\$Revision: 1.2 \$";
    AUTHOR = "\$Author: bad \$";
    DATE = "\$Date: 2006/07/27 12:58:00 \$";
}

CVTS {
    CVTLIST = {
        #for $lru in $lrus
	        {
	            CVT = "$lru";
	        }
	    #end for

    }

}

IFREAL {
    LOADLIST = "";
    UNLOADLIST = "";
    IOMAPLIST = {
        #for $lru in $lrus
	        {
	            IOMAP = "$lru";
	        }
	    #end for

    }

}

IFSIM {
    LOADLIST = "";
    UNLOADLIST = "";
    SIMULATIONS = {
    }

}

