#def gen_signal(msg, p)
    #set sigbytes = $int($p['SigSize'] / 8) + $int($p['SigSize']%8 > 0)
	#set $endSigByte = ( $p['sigbitoffset'])/8 + $sigbytes - 1
	#set $startSigByte 	= ( $p['sigbitoffset'])/8
	#set $startSigBit 	= ( $p['sigbitoffset']) - $startSigByte*8 
	#set $endSigBit 	= ( $p['sigbitoffset']) + $p['SigSize'] - $startSigByte*8 -1
	#set $temstart = $startSigByte
	#set $startSigByte 	= $int($msg['TXLength']-1 - $endSigByte)	
	#set $endSigByte 	= $int($msg['TXLength']-1 - $temstart)
                        signal {
                            point = "$cvts.add_a825_signal($msg,$p)";
                            bytes = "$startSigByte:$endSigByte";
                            bits = "$startSigBit:$endSigBit";
                            ppexpr = "";
    #if $p['SigType'] == "BNR"
                            LINEAR euconvert = {
                                signed = "1";
                                factor = "$p['LsbValue']";
                                offset = "0.0";
                            }
    #elif $p['SigType'] == "UBNR"
                            LINEAR euconvert = {
                                signed = "0";
                                factor = "$p['LsbValue']";
                                offset = "0.0";
                            }
    #else
                            COPY euconvert = {
                            }
    #end if                                
                        }
#end def

#def gen_inputmsg(model, dev)
	#for $messageName in $model.keys()
		#set $message=$model[$messageName]
		#if $message['Lru'] in $LruName and $message['PhysPort'] in $dev['Lru_Channel']
	        
	        INPUT-MESSAGE $message['Message'] = {
                    CONFIGURATION {
                        comment = "";
                        canidtype = "EXT";
                        canid = "$int($str($message['MsgID']),16)";
						
                        DMODE = {
                            SAMPLING DATA_MODE = {
                            }
                        }				

                        UPDATE_INFO = {
                            update_rate = "";
                            label_active = "";
                            EXPECTED_RATE = "$message['TXRate']";
                            rx_timestamp = "";
                        }
                    }

                    iomap {
				
                #for $param in $message['Signals'].values()
                        $gen_signal($message, $param)
                #end for
				
                    }
                }

       #end if
    #end for
#end def

#def gen_outputmsg(model, dev)
	#for $messageName in $model.keys()
		#set $message=$model[$messageName]
		#if $message['Lru'] in $LruName and $message['PhysPort'] in $dev['Lru_Channel']
		
            OUTPUT-MESSAGE $message['Message']= {
                CONFIGURATION {
                    comment = "";
                    canidtype = "EXT";
                    canid = "$int($str($message['MsgID']),16)";
                    msgtype = "DATA";
                    BYTECOUNT = "$message['TXLength']";
                    activate = {
                        point = "$cvts.add_a825_msg_control($message, '__activate__')";
                        mask = "0xffffffff";
                    }
				
                    DMODE = {
                        TX_SAMPLING DATA_MODE = {
                            rate = "$message['TXRate']";
                            offset = "0";
                        }

                    }
					
                }

                    iomap {
		
            #for $param in $message['Signals'].values()
                        $gen_signal($message, $param)
            #end for
	
                    }
                }
        #end if
    #end for
#end def

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
	#set $devList = []
	#for $key,$item in $device.items()
	   #for $item1 in $item
			#if $LruName in $key and $item1['DeviceType']=='A825 Board'
				$devList.append($item1)
			#end if
	   #end for
	#end for
	
	#for $dev in  $devList
        TECHSAT-CAN $dev['SSDL_Device'] = {
            GLOBAL_CONFIG {
                comment = "";
                speed = "500K";
                mode = "Normal";
                TXECHO = "0";
            }
            
            INPUT_MESSAGES {
                $gen_inputmsg($inputmodel, $dev)
            }
            
            OUTPUT_MESSAGES {
                $gen_outputmsg($outputmodel, $dev)
            }
           
        }
	#end for
    }
}