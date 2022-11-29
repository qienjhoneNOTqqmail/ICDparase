#def exclude_sig(sigName)
	#set $excl= ("sign_status_matrix", "label", "parity", "source_destination_id", "sign_bit", "ssm", "sdi")
	#for $n in $excl
		#if $sigName.lower().endswith($n)
			#return True
		#end if
	#end for
	#return False
#end def

#def gen_signal(msg, p)
	
	#if $exclude_sig($p.sigName)
		#return
    #else
        
        #set $startSigBit  = $p.sigBitOffset+1  ##sigBitOffset starts with 0
        #set $endSigBit = $startSigBit + $p.sigSize-1 
                            signal {
                                point = "$cvts.add_a429_signal($p)";
                                bits = "$startSigBit:$endSigBit";
                                ppexpr = "";
                                
		#if $p.sigType == "BNR"
								LINEAR euconvert = {
									signed = "1";
									factor = "$p.sigLsbValue";
									offset = "0.0";
								}
		#elif $p.sigType == "UBNR"
								LINEAR euconvert = {
									signed = "0";
									factor = "$p.sigLsbValue";
									offset = "0.0";
								}
		#elif $p.sigType == "BCD"
								BCD euconvert = {
									lsdmagnitude = "1"; ##Multiplier attribute, specifies the subscribers preferred multiplier of the parameter (Date, Time, Fequency).
									signbits = "0";
								}
		#else
								COPY euconvert = {
								}
		#end if
                            }
    #end if
#end def

#def gen_label($model, $dir, $dev)
    #for $labelName in $model.a429.messages.keys()
        #set $label=$model.a429.messages[$labelName]
        #if $lruName is not None and $label.lruName != $lruName:
            #continue
        #end if
        #if $type($device) == $type('str')
            #set $skip = False
        #else
            #set $skip = not ($dev ==  $device.getAdsDevice(label.msgPhysPort))
        #end if
        #if not $skip
            #if -1 == $label.msgSDI
                #set $sdi = "*"
            #else
                #set $sdi = $label.msgSDI
            #end if

        label $label.msgName = {
            description {
                label = "$label.msgLabel";
                sdi = "$sdi";
                #if $dir == "TX"
                txrate = "$label.msgRate";    
                update_policy = "Rate-Conform";
                activate_point = "$cvts.add_a429_msg_control($label, 'activate')";
                activate_mask = "0xffffffff";
                label_errors = "";
                #else
                rxrate = "$label.msgRate";
                update_rate = "10";
                label_active = "$cvts.add_a429_msg_control($label, 'active')";
                label_errors = "";
                rx_timestamp = "";
                #end if
            }
            iomap {

			#try
            #for $param in $model.a429.signals[$labelName]
                $gen_signal($label, $param)
            #end for
			#except
				$print("Exception while processing signals for %s"%($labelName))
			#end try
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
		#if $type('str') == $type($device)
            #set $devList = [$device]
        #else
            #set $devList = $device.getAdsDeviceList($lruName)
        #end if
        #for $dev in  $devList
		A429-PMC $dev {
			RECEIVER {
				channel {
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
			
					labels {
					$gen_label($inputModel, "RX", $dev)
					}
				}
			}
			
		TRANSMITTER {
				channel {
					description {
						comment = "";
						speed = "LOW";
						parity = "ODD";
						label_count = "";
					}

					labels {
					$gen_label($outputModel, "TX", $dev)
					}
				}
		
			}
		#end for
		}
	}
}