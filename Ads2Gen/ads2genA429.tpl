#def gen_signal(msg, p)
	#if "label" in $str($p['Signal']).lower() or "parity" in $str($p['Signal']).lower()
		#return
	#else
		#set $endSigBit  = $p['sigbitoffset']+$p['SigSize']
		#set $startSigBit = $p['sigbitoffset']+1
							signal {
								point = "$cvts.add_a429_signal($msg,$p)";
								bits = "$startSigBit:$endSigBit";
								ppexpr = "";
		#if "BNR" in $p['SigType'] ##FIXME X $p['SigType'] -> COD 
								LINEAR euconvert = {
									signed = "1";
									factor = "$p['LsbValue']";
									offset = "0.0";
								}
								
								
		#elif "BCD" in $p['SigType'] 
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
	#end if
#end def

#def gen_label($model, $dir, $dev)
    #for $labelName in $model.keys()
		#set label=$model[$labelName]
		##$print("label physPort is %s lru channel is %s -- %s" % ($label['PhysPort'],$dev['Lru_Channel'],$labelName))
		#if $LruName is None or ($label['Lru'] in $LruName and $label['PhysPort'] in $dev['Lru_Channel'])
		    #if -1 == $label['SDI']
                #set $sdi = "*"
            #else
                #set $sdi = $label['SDI']
            #end if
		
			label $label['Word'] = {
				description {				    
					label = "$int($str($label['Label']),8)";	
					sdi = "$sdi";				
					#if $dir == "TX"
					txrate = "$label['Txrate']";	
					update_policy = "Rate-Conform";
					activate_point = "$cvts.add_a429_msg_control($label, '__activate__')";
					activate_mask = "0xffffffff";
					label_errors = "";
					#else
					rxrate = "$label['Txrate']";
					update_rate = "10";
					label_active = "";
					label_errors = "";
					rx_timestamp = "";
					#end if
				}
				iomap {
	            #for $param in $label['Signals'].values()
	                        $gen_signal($label, $param)
	            #end for
	                    }
			}
		#end if
    #end for
#end def

VERSION_CONTROL {
    FILE_NAME = "\$RCSfile: cvsheader.inc,v \$";
    REVISION = "\$Revision: 0.1a \$";
    AUTHOR = "\$Author: lgs \$";
    DATE = "\$Date: 2006/07/27 12:58:00 \$";
}

IOMAP {
    INPUTS {
    }

    OUTPUTS {
    }

    TRANSPUTS {
		#set $devList = []
		#if $type('str') == $type($device)
        	#set $devList = [{'SSDL_Device':$device}]
    	#else  
			#for $key,$item in $device.items()
			   #for $item1 in $item
				#if $LruName in $key and $item1['DeviceType']=='A429 Board'
				    $print("come int###########")
					$devList.append($item1)
				#end if
				#end for
			#end for
		#end if
		$print('LRU: %s len of devlist is %d'% ($LruName, $len($devList)))	
		#for $dev in  $devList		
		#set $board = $dev['SSDL_Device'].split(',')[0]
		#set $chl = $dev['SSDL_Device'].split(',')[1]
		#if $chl.startswith('TX')
			#set $rxchl = ''
			#set $txchl = $chl
		#else
		    #set $rxchl = $chl
			#set $txchl = ''
		#end if
        A429-PMC $board {
            RECEIVER {
                channel $rxchl{
                    description {
                        comment = "";
                        speed = "AUTO-DETECT";
                        parity = "ODD";
                        label_count = "";
                        parity_error_count = "";
                        long_word_error_count = "";
                        short_word_error_count = "";
                        gap_error_count = "";
                    }
            
					labels{
					$gen_label($inputmodel, "RX", $dev)
					}
				}
			}
            
           TRANSMITTER {
                channel $txchl {
                    description {
                        comment = "";
                        speed = "HIGH";
                        parity = "ODD";
                        label_count = "";
                    }

                    labels {
					$gen_label($outputmodel, "TX", $dev)
					}
				}
           
			}		
		}
		#end for
	}
}