VERSION_CONTROL {
    FILE_NAME = "\$RCSfile: cvsheader.inc,v \$";
    REVISION = "\$Revision: 1.2 \$";
    AUTHOR = "\$Author: bad \$";
    DATE = "\$Date: 2006/07/27 12:58:00 \$";
}

IOMAP {
    INPUTS {
    }

    OUTPUTS {

    }
    
    TRANSPUTS {
		TECHSAT-FAST {
	    #for $key,$value in $device.items():
	    	FAST-DSO80 $key = {
		    FAST_DSO80_CHAN_CONFIGURATIONS {
			#for $item in $value:
				FAST_DSO_CHANNEL_CONFIGURATION {
					#set $cm = $key+"_CH"+str($item[2])  
					#set ch_num = int($item[2])-1                     
					comment = "$cm";
					CHAN_NUM = "$ch_num";
 
    				CHANNEL_ACTIVATE = {
 						POINT = "";
    					ppexpr = "";
                        
					}

                    		
					OUTPUT = {
                    	POINT = "$cvts.add_Discrete($item[0],$item[1])";                    
						ppexpr = "";                           
						COPY euconvert = {
                    	}                        
					}
                       
					ERROR_STATE = "";
                    
				}
			#end for
			}
		 }
        #end for
		}
       
    }    
	
}