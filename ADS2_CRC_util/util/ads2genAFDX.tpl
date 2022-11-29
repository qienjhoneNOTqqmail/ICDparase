#import re

## ----------------------------------------------------------------------------
## ADS2 IOM AFDX Signal Definition Template 
## ----------------------------------------------------------------------------
#def isStatus(p)
    #try
    #if $p.sigName is not None
        #if "FSB" in $p.sigName or ("SSM" in $p.sigName and  $p.msgRef.direction  == 'input')
            #return 1
        #else
            ## inhibit also complete 429 words - are already considered in ICD as signals
            #if $re.match('\AL\d\d\d_', $p.sigName) and $p.sigType=="BYTES" and $p.sigSize==32
                #return 1
            #else
                #return 0
            #end if
        #end if
    #end if
    #except
        #pass
    #end try
    
    #try
    #if $p.DpName is not None
        #if "FSB" in $p.DpName or (".SSM" in $p.DpName and  $p.msgRef.direction  == 'input')
            #return 1
        #else    
            #return 0
        #end if
    #end if
    #except
        #pass
    #end  try
    #return 0
#end def

##Check if MSG shall be treated as RAW message
#def isRaw(vl, message)
	##further filter: 661, ISS, EDE, ...
	#if $message.protocolType.upper() == "PARAMETRIC"
		#return False
	#else
		#return True
	#end if
#end def

#def gen_signal(m, p)
    #if $isStatus($p)
        #return
    #end if
    #if $p.paramName is not None
       #set $p.paramName = ('.').join($p.paramName.split('.')[1:])
    #end if
    #if $p.sigSize > $p.sigAccess * 8
       #set $endSigByte = $p.sigByteOffset+$p.sigSize / 8 - 1 
    #else
       #set $endSigByte = $p.sigByteOffset+$p.sigAccess - 1
    #end if
    #set $endSigBit  = $p.sigBitOffset+$p.sigSize-1
                        signal {
                            point = "$cvts.add_a664_signal($p)";
                            bytes = "$p.sigByteOffset:$endSigByte";
                            bits = "$p.sigBitOffset:$endSigBit";
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
                        
                        
    #if $p.sselA664Fsb()
       #set $fsbname = $cvts.add_a664_fsb($p)
       #if $fsbname 
                        signal {
                            point = "$fsbname";
                            bytes = "$p.dsFsbOffset:$p.dsFsbOffset";
                            bits = "0:7";
                            ppexpr = "";
                            COPY euconvert = {
                            }
                        }
      #end if                                
    #end if                                
	
    #try
	
	#if $p.sselA429SSM() 
       #set $ssmname = $cvts.add_a664_a429ssm($p)
       #if $ssmname 
                        signal {
                            point = "$ssmname";
                            bytes = "$p.sigByteOffset:$endSigByte";
                            bits = "29:30";
                            ppexpr = "";
                            COPY euconvert = {
                            }
                        }

      #end if                                
	#end if
    #except Exception as e
		$print(e)
    #end try                                
#end def

## ----------------------------------------------------------------------------
## ADS2 VL Definition Template 
## ----------------------------------------------------------------------------

#def gen_txvl($model)
                  virtual-links = {
 #for $vl in $model.afdx.vls.values()
    #if $lruName is not None and vl.lru != $lruName:
        #continue
    #end if
                        link {
                            linkname   = "$vl.vlName";
                            macaddress = "$vl.macAdd";
                            bag        = "$vl.bag";
                            mtu        = "$vl.mtu";
                            interfaces = "3";
                            redundancy = "1";
                            #set $subvlcnt = $vl.nbSubVl
                            #if $subvlcnt == 0
                               #set $subvlcnt = 1
                            #end if
                            subvlcount = "$subvlcnt";
                            enabled    = "1";
                        }
 #end for
                    }
#end def

#def gen_rxvl($model)
                  virtual-links = {
 #for $vl in $model.afdx.vls.values()
   #if $lruName is not None and vl.lru != $lruName:
        #continue
    #end if
                        link {
                            linkname           = "$vl.vlName";
                            macaddress         = "$vl.macAdd";
                            maxskew               = "1000";
                            interfaces         = "3";
                            #if $devmode == True
                            redundancy         = "0";
                            integritycheck  = "0";
                            #else
                            redundancy         = "1";
                            integritycheck  = "1";
                            #end if
                        }
 #end for
                    }
#end def

## ----------------------------------------------------------------------------
## Transmit message for stimulation mode
## Constructed from a Input ICD of the LRU
## ----------------------------------------------------------------------------

#def gen_txStimMsg($model, $msgonly, $devmode)
#for $messageName in $model.afdx.messages.keys()
    #set $message=$model.afdx.messages[$messageName]
    #if $lruName is not None and $message.lruName != $lruName:
        #continue
    #end if
    #set $vl=$model.afdx.vls[$message.vlId]
    #if $message.subVl > 0
       #set $subvlId = $message.subVl - 1
    #else
       #set $subvlId = 0
    #end if
                message $message.msgName = {
                    description {
                        comment = "";
                        link = "$vl.vlName";
                        #set $macsrc    = $message.macSrc.replace('.', ':')
                        #if $devmode
                            #set $macsrc = ""
                        #end if
                        mac_src    = "$macsrc";
                        #set $dstip = $message.dstIp
                        #if $dstip == ""
                            #set $dstip = "224.224.0.0"
                        #end if
                        dst_addr   = "$dstip";
                        dst_port   = "$message.dstPortId";
                        src_addr   = "$message.srcIp";
                        src_port   = "$message.srcPortId";
                        pdu_length = "$message.msgLength";
                        subvl_id   = "$subvlId";
                        trigger    = "";
                        triggermode = "Changed Value";
    #if $msgonly or $isRaw($vl, $message)
                        MSG_CONTENT rawdata = {
                            MESSAGE_TYPE AFDX = { }
                            cvtslot = "$cvts.add_a664_msg($message)";        
                        }
    #else
                        MSG_CONTENT signals = {
                            MESSAGE_TYPE AFDX = { }
                        }
    #end if
                        activate = "$cvts.add_a664_msg_control($message, 'activate')";
                        activatemask = "0xffffffff";
                        updatemethod = {
                            tx_rate = "1";
                            tx_offset = "0";
                            mode = "Single Msg.";
                        }
    #if $devmode
      #set $porttype = "SAMPLING"
    #else
      #set $porttype = $message.portType
	  #if "Q" in $porttype and $message.protocolType.upper() == "PARAMETRIC"
		 #set $porttype = "SAMPLING"
	  #end if
    #end if                    
                        PORT_TYPE $porttype.lower() = {
    #if $porttype == "SAMPLING"
                            #set $txrate = int($message.msgTxInterval) / 10
                            #if $txrate == 0
                               #set $txrate = 1
                            #end if
                            tx_rate = "$txrate";
                            tx_offset = "0";
    #end if
    #if $porttype.upper() == "QUEUEING"
    #set $queuesize = $vl.mtu*$message.queueLength
                            queuesize = "$queuesize";
    #end if
                        }
    #if $message.EdeSource == 0
                        PROT_LAYER udp_layer = {
                        }
    #else
                        PROT_LAYER ede_layer = {
                            source_id = "$message.EdeSource";
                            EDE_MGMT not_mgmt_port = {
                            }
                        }
    #end if
                        sent_msgs = "";
                        sent_bytes = "";
	#if isinstance($message.crcOffset, int) and isinstance($message.crcFsbOffset, int)
						#set $val = $cvts.add_a664_msg_control($message, 'CRC_VAL')
                        #set $fsb = $cvts.add_a664_msg_control($message, 'CRC_FSB')
                        ALIC enable_alic = {
                                alic_fs_offset = "$message.crcFsbOffset";
                                alic_pos = "-1:0";
                                alic_crc_type = "ARINC-665";
                                Mode ei_mask = {
                                    alic_crc_poly = "0x04c11db7";
                                    alic_crc_init = "0xffffffff";
                                    alic_crc_final = "0xffffffff";
                                    alic_fs_value = "$fsb";
                                    alic_value = "$val";
                                }

                            }
	#else
                        ALIC no_alic = {
                        } 
	#end if
                    }
                    iomap {
    #if $msgonly == False and $isRaw($vl, $message) == False
    					#try
    					#for param in $model.afdx.signals[$messageName]
							$gen_signal($message, $param)
                        #end for
						#except
							$print("Exception while proccessing signals for %s"%($messageName))
						#end try
    #end if
                    }
                }
 #end for
#end def

## ----------------------------------------------------------------------------
## Transmit message for simulation mode
## Constructed from a Output ICD of an LRU
## ----------------------------------------------------------------------------

#def gen_txSimMsg($model, $msgonly)
#for $messageName in $model.afdx.messages.keys()
    #set $message=$model.afdx.messages[$messageName]
    #if $lruName is not None and $message.lruName != $lruName:
        #continue
    #end if
    #set $vl=$model.afdx.vls[$message.vlId]
    #if $message.subVl > 0
       #set $subvlId = $message.subVl - 1
    #else
       #set $subvlId = 0
    #end if
                message $message.msgName = {
                    description {
                        comment = "";
                        link = "$vl.vlName";
                       #set $macsrc    = $message.macSrc.replace('.', ':')
                        #if $devmode
                            #set $macsrc = ""
                        #end if
                        mac_src    = "$macsrc";
                        #set $dstip = $message.dstIp
                        #if $dstip == ""
                            #set $dstip = "224.224.0.0"
                        #end if
                        dst_addr   = "$dstip";
                        dst_port   = "$message.dstPortId";
                        src_addr   = "$message.srcIp";
                        src_port   = "$message.srcPortId";
                        pdu_length = "$message.msgLength";
                        subvl_id   = "$subvlId";
                        trigger    = "";
                        triggermode = "Changed Value";
    #if $msgonly or $isRaw($vl, $message)
                        MSG_CONTENT rawdata = {
                            MESSAGE_TYPE AFDX = { }
                            cvtslot = "$cvts.add_a664_msg($message)";        
                        }
    #else
                        MSG_CONTENT signals = {
                            MESSAGE_TYPE AFDX = { }
                        }
    #end if
                        activate = "$cvts.add_a664_msg_control($message, 'activate')";
                        activatemask = "0xffffffff";
                        updatemethod = {
                            tx_rate = "1";
                            tx_offset = "0";
                            mode = "Single Msg.";
                        }
                        
                        PORT_TYPE $message.portType.lower() = {
    #if $message.portType == "SAMPLING"
                            #set $txrate = int($message.msgTxInterval) / 10
                            #if $txrate == 0
                               set $txrate = 1
                            #end if
                            tx_rate = "$txrate";
                            tx_offset = "0";
    #end if
    #if $message.portType.upper() == "QUEUEING"
    #set $queuesize = $vl.mtu*$message.queueLength
                            queuesize = "$queuesize";
    #end if
                        }
    #if $message.EdeSource == 0
                        PROT_LAYER udp_layer = {
                        }
    #else
                        PROT_LAYER ede_layer = {
                            source_id = "$message.EdeSource";
                            EDE_MGMT not_mgmt_port = {
                            }
                        }
    #end if
                        sent_msgs = "";
                        sent_bytes = "";
    #if isinstance($message.crcOffset, int) and isinstance($message.crcFsbOffset, int)
						#set $val = $cvts.add_a664_msg_control($message, 'CRC_VAL')
                        #set $fsb = $cvts.add_a664_msg_control($message, 'CRC_FSB')
                        ALIC enable_alic = {
                                alic_fs_offset = "$message.crcFsbOffset";
                                alic_pos = "-1:0";
                                alic_crc_type = "ARINC-665";
                                Mode ei_mask = {
                                    alic_crc_poly = "0x04c11db7";
                                    alic_crc_init = "0xffffffff";
                                    alic_crc_final = "0xffffffff";
                                    alic_fs_value = "$fsb";
                                    alic_value = "$val";
                                }

                            }
	#else
                        ALIC no_alic = {
                        } 
	#end if
                    }
                    iomap {
    #if $msgonly == False and $isRaw($vl, $message) == False
    					#try
    					#for param in $model.afdx.signals[$messageName]
							$gen_signal($message, $param)
                        #end for
						#except
							$print("Exception while proccessing signals for %s"%($messageName))
						#end try
    #end if
                    }
                }
 #end for
#end def

## ----------------------------------------------------------------------------
## ADS2 Receive message for stimulation mode
## Constructed from the Output ICD of the UUT
## ----------------------------------------------------------------------------

#def gen_rxStimMsg($model, $msgonly)

  #for $messageName in $model.afdx.messages.keys()
    #set $message=$model.afdx.messages[$messageName]
    #if $lruName is not None and $message.lruName != $lruName:
        #continue
    #end if
    #set $vl=$model.afdx.vls[$message.vlId]
                message $message.msgName = {
                    description {
                        comment = "";
                        link = "$vl.vlName";
                        #set $macsrc    = $message.macSrc.replace('.', ':')
                        #if $devmode
                            #set $macsrc = ""
                        #end if
                        mac_src    = "$macsrc";
                        #set $dstip = $message.dstIp
                        #if $dstip == ""
                            #set $dstip = "224.224.0.0"
                        #end if
                        dst_addr   = "$dstip";
                        dst_port   = "$message.dstPortId";
                      #if $devmode
                        src_addr   = "ANY";
                        src_port   = "ANY";
                      #else
                        src_addr   = "$message.srcIp";
                        src_port   = "$message.srcPortId";
                      #end if
                        pdu_length = "$message.msgLength";
                        subid_bytes = "0:0";
                        subid_mask = "0";
                        subid_match = "0";
                        trigger    = "";
                        triggermode = "Changed Value";
    #if $msgonly or $isRaw($vl, $message)
                        MSG_CONTENT rawdata = {
                            MESSAGE_TYPE AFDX = { }
                            cvtslot = "$cvts.add_a664_msg($message)";        
                        }
    #else
                        MSG_CONTENT signals = {
                            MESSAGE_TYPE AFDX = { }
                        }
    #end if
                        updatemethod = {
                            rx_rate = "1";
                            rx_offset = "0";
                            mode = "Single Msg.";
                        }
    #if $message.portType.upper()[0] == "Q"
                        PORT_TYPE queueing = {
       #set $queuesize = $vl.mtu*$message.queueLength
                            queuesize = "$queuesize";
                        }
    #else
                        PORT_TYPE sampling = {
                        }
    #end if

    #if $message.EdeSource == 0
                        PROT_LAYER udp_layer = {
                        }
    #else
                        PROT_LAYER ede_layer = {
                            source_id = "$message.EdeSource";
                            subscriber_idx = "1";
                            redundancy_enbl = "0";
                            crc_vldn_enbl = "$int( not $devmode )";
                            ord_vldn_enbl = "$int( not $devmode )";
                            age_vldn_enbl = "0";
                            protocol_data = "0";
                            rxts_corrected = "0";
                            EDE_MGMT not_mgmt_port = {
                            }
                        }
    #end if
                        received_msgs = "";
                        received_bytes = "";
                        update_rate = "";
                        msg_active = "$cvts.add_a664_msg_control($message, 'active')";
                        #set $rate = int($message.msgTxInterval) / 10
                        #if $rate == 0
                            #set $rate=1
                        #end if
                        EXPECTED_RATE = "$rate";
                        rx_timestamp = "";
	#if isinstance($message.crcOffset, int) and isinstance($message.crcFsbOffset, int)
						#set $val = $cvts.add_a664_msg_control($message, 'CRC_VAL')
                        #set $fsb = $cvts.add_a664_msg_control($message, 'CRC_FSB')
                        ALIC no_alic = {
                        }
	#else
                        ALIC no_alic = {
                        } 
	#end if
                    }
                    iomap {
    #if $msgonly == False and $isRaw($vl, $message) == False
    					#try
    					#for param in $model.afdx.signals[$messageName]
							$gen_signal($message, $param)
                        #end for
						#except
							$print("Exception while proccessing signals for %s"%($messageName))
						#end try
    #end if
                    }
                }
  #end for
#end def

## ----------------------------------------------------------------------------
## ADS2 Receive message for simulation mode
## Constructed from the Input ICD of the UUT
## ----------------------------------------------------------------------------

#def gen_rxSimMsg($model, $msgonly)
  
  #for $messageName in $model.afdx.messages.keys()
    #set $message=$model.afdx.messages[$messageName]
    #if $lruName is not None and $message.lruName != $lruName:
        #continue
    #end if
    #set $vl=$model.afdx.vls[$message.vlId]
                message $message.msgName = {
                    description {
                        comment     = "";
                        link        = "$vl.vlName";
                        #set $macsrc    = $message.macSrc.replace('.', ':')
                        #if $devmode
                            #set $macsrc = ""
                        #end if
                        mac_src    = "$macsrc";
                        #set $dstip = $message.dstIp
                        #if $dstip == "" or $devmode == True
                            #set $dstip = "ANY"
                        #end if
                        dst_addr    = "$dstip";
                        dst_port    = "$message.dstPortId";
                      #if $devmode
                        src_addr   = "ANY";
                        src_port   = "ANY";
                      #else
                        src_addr    = "$message.srcIp";
                        src_port    = "$message.srcPortId";
                      #end if
                        pdu_length  = "$message.msgLength";
                        subid_bytes = "0:0";
                        subid_mask  = "0";
                        subid_match = "0";
                        trigger     = "";
                        triggermode = "Changed Value";
    #if $msgonly or $isRaw($vl, $message)
                        MSG_CONTENT rawdata = {
                            MESSAGE_TYPE AFDX = { }
                            cvtslot = "$cvts.add_a664_msg($message)";        
                        }
    #else
                        MSG_CONTENT signals = {
                            MESSAGE_TYPE AFDX = { }
                        }
    #end if
                        updatemethod = {
                            rx_rate = "1";
                            rx_offset = "0";
                            mode = "Single Msg.";
                        }
                        
                        PORT_TYPE $message.portType.lower() = {
    #if $message.portType.upper() == "QUEUEING"
    #set $queuesize = $vl.mtu*$message.queueLength
                            queuesize = "$queuesize";
    #end if
                        }

    #if $message.EdeSource == 0
                        PROT_LAYER udp_layer = {
                        }
    #else
                        PROT_LAYER ede_layer = {
                            source_id = "$message.EdeSource";
                            subscriber_idx = "1";
                            redundancy_enbl = "0";
                            crc_vldn_enbl = "$int( not $devmode )";
                            ord_vldn_enbl = "$int( not $devmode )";
                            age_vldn_enbl = "0";
                            protocol_data = "0";
                            rxts_corrected = "0";
                            EDE_MGMT mgmt_port = {
                                tm_index = "0";
                                my_subscr_idx = "1";
                                p_type request = {
                                }
                            }
                        }
    #end if
                        received_msgs = "";
                        received_bytes = "";
                        update_rate = "";
                        msg_active = "$cvts.add_a664_msg_control($message, 'active')";
                        #set $rate = int($message.msgTxInterval) / 10
                        #if $rate == 0
                            #set $rate=1
                        #end if
                        EXPECTED_RATE = "$rate";
                        rx_timestamp = "";
    #if isinstance($message.crcOffset, int) and isinstance($message.crcFsbOffset, int)
						#set $val = $cvts.add_a664_msg_control($message, 'CRC_VAL')
                        #set $fsb = $cvts.add_a664_msg_control($message, 'CRC_FSB')
                        ALIC no_alic = {
                        }
	#else
                        ALIC no_alic = {
                        } 
	#end if    
                    }
                    iomap {
    #if $msgonly == False and $isRaw($vl, $message) == False
						#try
    					#for param in $model.afdx.signals[$messageName]
							$gen_signal($message, $param)
                        #end for
						#except
							$print("Exception while proccessing signals for %s"%($messageName))
						#end try
    #end if
                    }
                }
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

    TRANSPUTS {
        AFDX $device {
            debug {
            }

            description {
                comment = "";
            }

            receiver {
                vlinks {
                    $gen_rxvl($inputModel)
                }

                messages {
                    #if $mode == "stim"
                        $gen_rxStimMsg($inputModel, $msgonly)
                    #else
                        $gen_rxSimMsg($inputModel, $msgonly)
                    #end if
                }
            }

            transmitter {
                vlinks {
                    $gen_txvl($outputModel)
                }

                messages {
                    #if $mode == "stim"
                        $gen_txStimMsg($outputModel, $msgonly, $devmode)
                    #else    
                        $gen_txSimMsg($outputModel, $msgonly)
                    #end if
                }
                replay {
                    network_a { }
                    network_b { }
                    network_ab { }
                }
            }
        }
    }
    OUTPUTS {
    }
}                