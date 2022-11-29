HARDWARE {
    #for $hwcmp in $hwcmps 
	    COMPONENT {
	        name = "$hwcmp";
	    } 
	#end for   
}

DISPLAYS {
    DISPLAY main@$DPC = {
        COMPUTER = "$DPC";
        DISPLAY = "main";
        ITEMS {
            #for $pnl in $pnls
	            PANEL {
	                name = "$pnl";
	            }
	        #end for

        }

    }

}

RT-HOSTS {
    RT-HOST $DPC = {
	    #for $simcmp in $simcmps 
		    COMPONENT {
		        name = "$simcmp";
		    } 
		#end for
    }

}