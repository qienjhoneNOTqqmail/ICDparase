## ----------------------------------------------------------------------------
## ADS2 IOM AFDX Signal Definition Template 
## ----------------------------------------------------------------------------

#def gen_signal(m, p)
	
	#if p.get('DpName') is not None
		#if 'FSB' in p['DpName'] or 'spare' in $str($p['DpName']).lower() or 'reserve' in  $str($p['DpName']).lower():
			#return
		#end if
	#end if 
	
	#if p.get('RpName') is not None
		#if 'spare' in $str($p['RpName']).lower() or 'reserve' in  $str($p['RpName']).lower():
			#return		
		#end if
	#end if
	
    #if $p['SigSize'] > ($p['sigalign'] * 8)
       #set $endSigByte = $p['sigbyteoffset']+$p['SigSize'] / 8 - 1 
    #else
       #set $endSigByte = $p['sigbyteoffset']+$p['sigalign'] - 1
    #end if
    #set $endSigBit  = $p['sigbitoffset']+$p['SigSize']-1
                        signal {
                            point = "$cvts.add_664_signal($m,$p)";
                            bytes = "$p['sigbyteoffset']:$endSigByte";
                            bits = "$p['sigbitoffset']:$endSigBit";
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
    #elif $p['SigType'] == "BCD"
                            BCD euconvert = {
                                lsdmagnitude = "$p['LsbValue']";
                                signbits = "0";
                            }
    #else
                            COPY euconvert = {
                            }
    #end if                                
                        }
                        
                        
    #if $p['664FSB']
       #set $fsbname = $cvts.add_664_fsb($m,$p)
       #if $fsbname 
                        signal {
                            point = "$fsbname";
                            bytes = "$p['FsbOffset']:$p['FsbOffset']";
                            bits = "0:7";
                            ppexpr = "";
                            COPY euconvert = {
                            }
                        }
      #end if                                
    #end if                                
    
    #try			
    #if $p['429SSM']
       #set $ssmname = $gac.add_664429_ssm($m,$p)
       #if $ssmname 
                        signal {
                            point = "$ssmname";
                            bytes = "$p['sigbyteoffset']:$endSigByte";
                            bits = "29:30";
                            ppexpr = "";
                            COPY euconvert = {
                            }
                        }

      #end if                                
    #end if
    #except
    	#pass
    #end try                                
#end def

## ----------------------------------------------------------------------------
## ADS2 VL Definition Template 
## ----------------------------------------------------------------------------

#def gen_txvl($model)
                  virtual-links = {
 #for $vl in $model.values()
     #if $LruName is None or  $vl.lru in $LruName
     #if $LruName is None and $vl.lru in ['SYNOPTICEMENUAPP_L','SYNOPTICMENUAPP_R','SYNOPTICPAGEAPP_L','SYNOPTICPAGEAPP_R','VIRTUALCONTROLAPP_L','VIRTUALCONTROLAPP_R','APP_FMS_DATALINK_1','APP_FMS_DATALINK_1','NTM_L1','NTM_L4','NTM_R3','OMSCockpitDisplayApp','HF_ISSPROCESSINGUNIT_L','HF_ISSPROCESSINGUNIT_R']:
            #continue
     #end if ## add for sidb, delete some vl, for that afdx pmc can't support more than 255 vls
                    link {
                        linkname   = "$vl.vlname";
                        macaddress = "$vl.macaddr";
                        bag        = "$vl.bag";
                        mtu        = "$vl.mtu";
                        interfaces = "3";
                        redundancy = "1";
                        #set $subvlcnt = $vl.suvlid
                        #if $subvlcnt == 0
                           #set $subvlcnt = 1
                        #end if
                        subvlcount = "$subvlcnt";
                        enabled    = "1";
                    }
     #end if
 #end for
                    }
#end def


#def gen_rxvl($model)
                  virtual-links = {
 #for $vl in $model.values()
     #if $LruName is  None or  $vl.lru in $LruName
                    link {
                        linkname   = "$vl.vlname";
                        macaddress = "$vl.macaddr";
                        maxskew        = "1000";
                        interfaces = "3";
                        redundancy = "1";
                        integritycheck  = "1";
                    }
     #end if
 #end for
                    }
#end def


## ----------------------------------------------------------------------------
## Transmit message for stimulation mode
## Constructed from a Input ICD of the LRU
## ----------------------------------------------------------------------------

#def gen_txStimMsg($model)
#for $messageName in $model.keys()   
    #set $message=$model[$messageName]
    #if $LruName is None or $message['Lru'] in $LruName
        $print("message name is %s " % ($message['Lru']))
        #if $LruName is None and $message['Lru'] in ['SYNOPTICEMENUAPP_L','SYNOPTICMENUAPP_R','SYNOPTICPAGEAPP_L','SYNOPTICPAGEAPP_R','VIRTUALCONTROLAPP_L','VIRTUALCONTROLAPP_R','APP_FMS_DATALINK_1','APP_FMS_DATALINK_1','NTM_L1','NTM_L4','NTM_R3','OMSCockpitDisplayApp','HF_ISSPROCESSINGUNIT_L','HF_ISSPROCESSINGUNIT_R']:
            #continue
        #end if ## add for sidb, delete some vl, for that afdx pmc can't support more than 255 vls
        
	    #set $Vlid = $message['Vlid']
	
	    #set $vl=$outputvl[$Vlid]
	    #if $message['SubVl'] > 0
	       #set $subvlId = $message['SubVl'] - 1
	    #else
	       #set $subvlId = 0
	    #end if
	                message $message['Message'] = {
	                    description {
	                        comment = "";
	                        link = "$vl.vlname";
	                        mac_src    = "$message['SourceMACA'].replace('.', ':')";
	                        #set $dstip = $message['DestIP']
	                        #if $dstip == ""
	                            #set $dstip = "224.224.0.0"
	                        #end if
	                        dst_addr   = "$dstip";
	                        dst_port   = "$message['DestUDP']";
	                        src_addr   = "$message['SourceIP']";
	                        src_port   = "$message['SourceUDP']";
	                        pdu_length = "$message['TXLength']";
	                        subvl_id   = "$subvlId";
	                        trigger    = "";
	                        triggermode = "Changed Value";  
	                        MSG_CONTENT signals = {
	                            MESSAGE_TYPE AFDX = { }
	                        }
	
	                        activate = "$cvts.add_664_control($message, '__activate__')";
	                        activatemask = "0xffffffff";
	                        updatemethod = {
	                            tx_rate = "1";
	                            tx_offset = "0";
	                            mode = "Single Msg.";
	                        }
	
		#set $porttype = $message['Type']
		#if "Q" in $porttype and $message['MsgDataProtocolType'].strip() == "Parametric data"
			#set $porttype = "SAMPLING"
		#end if
				
	                        PORT_TYPE $porttype.lower() = {
		#if $porttype.upper() == "SAMPLING"
		                        #set $txrate = $message['TXRate'] / 10 + ($message['TXRate']  % 10 > 0)
		                        #if $txrate == 0
		                           #set $txrate = 1
		                        #end if
	                            tx_rate = "$txrate";
	                            tx_offset = "0";
		#end if
		#if $porttype.upper() == "QUEUEING"
		#set $queuesize = $vl.mtu*$message['QueueLength']
								queuesize = "$queuesize";
		#end if
	                        }
	    #if $message['EdeSourceId'] == 0 
	                        PROT_LAYER udp_layer = {
	                        }
	    #else
	                        PROT_LAYER ede_layer = {
	                            source_id = "$message['EdeSourceId']";
	                            EDE_MGMT not_mgmt_port = {
	                            }
	                        }
	    #end if
	                        sent_msgs = "";
	                        sent_bytes = "";
	                        ALIC no_alic = {
	                        }
	                    }
	                    iomap {    
	 
	                            #for $sig in $message['Signals'].values()
		                             $gen_signal($message, $sig)
		                        #end for
	   
	                    }
	                }
	 #end if
 #end for
#end def

#def gen_txSimMsg($model)
#for $messageName in $model.keys()   
    #set $message=$model[$messageName]
    #if $LruName is None or $message['Lru'] in $LruName 
	    #set $Vlid = $message['Vlid']
	
	    #set $vl=$outputvl[$Vlid]
	    #if $message['SubVl'] > 0
	       #set $subvlId = $message['SubVl'] - 1
	    #else
	       #set $subvlId = 0
	    #end if
	                message $message['Message'] = {
	                    description {
	                        comment = "";
	                        link = "$vl.vlname";
	                        mac_src    = "$message['SourceMACA'].replace('.', ':')";
	                        #set $dstip = $message['DestIP']
	                        #if $dstip == ""
	                            #set $dstip = "224.224.0.0"
	                        #end if
	                        dst_addr   = "$dstip";
	                        dst_port   = "$message['DestUDP']";
	                        src_addr   = "$message['SourceIP']";
	                        src_port   = "$message['SourceUDP']";
	                        pdu_length = "$message['TXLength']";
	                        subvl_id   = "$subvlId";
	                        trigger    = "";
	                        triggermode = "Changed Value";  
	                        MSG_CONTENT signals = {
	                            MESSAGE_TYPE AFDX = { }
	                        }
	
	                        activate = "$cvts.add_664_control($message, '__activate__')";
	                        activatemask = "0xffffffff";
	                        updatemethod = {
	                            tx_rate = "1";
	                            tx_offset = "0";
	                            mode = "Single Msg.";
	                        }
	
		#set $porttype = $message['Type']
				
	                        PORT_TYPE $porttype.lower() = {
		#if $porttype.upper() == "SAMPLING"
		                        #set $txrate = $message['TXRate'] / 10 + ($message['TXRate']  % 10 > 0)
		                        #if $txrate == 0
		                           #set $txrate = 1
		                        #end if
	                            tx_rate = "$txrate";
	                            tx_offset = "0";
		#end if
		#if $porttype.upper() == "QUEUEING"
		#set $queuesize = $vl.mtu*$message['QueueLength']
								queuesize = "$queuesize";
		#end if
	                        }
	    #if $message['EdeSourceId'] == 0 
	                        PROT_LAYER udp_layer = {
	                        }
	    #else
	                        PROT_LAYER ede_layer = {
	                            source_id = "$message['EdeSourceId']";
	                            EDE_MGMT not_mgmt_port = {
	                            }
	                        }
	    #end if
	                        sent_msgs = "";
	                        sent_bytes = "";
	                        ALIC no_alic = {
	                        }
	                    }
	                    iomap {    
	 
	                            #for $sig in $message['Signals'].values()
		                             $gen_signal($message, $sig)
		                        #end for
	   
	                    }
	                }
	 #end if
 #end for
#end def


## ----------------------------------------------------------------------------
## receive message for stimulation mode
## Constructed from a output ICD of the LRU
## ----------------------------------------------------------------------------

#def gen_rxStimMsg($model)
#for $messageName in $model.keys()   
    #set $message=$model[$messageName]
    #if $LruName is None or $message['Lru'] in $LruName 
	    #set $Vlid = $message['Vlid']
	
	    #set $vl=$inputvl[$Vlid]
	    #if $message['SubVl'] > 0
	       #set $subvlId = $message['SubVl'] - 1
	    #else
	       #set $subvlId = 0
	    #end if
	                message $message['Message'] = {
	                    description {
	                        comment = "";
	                        link = "$vl.vlname";
	                        mac_src    = "$message['SourceMACA'].replace('.', ':')";
	                        #set $dstip = $message['DestIP']
	                        #if $dstip == ""
	                            #set $dstip = "224.224.0.0"
	                        #end if
	                        dst_addr   = "$dstip";
	                        dst_port   = "$message['DestUDP']";
	                        src_addr   = "$message['SourceIP']";
	                        src_port   = "$message['SourceUDP']";
	                        pdu_length = "$message['TXLength']";
	                        subid_bytes = "0:0";
                            subid_mask = "0";
                            subid_match = "0";
                            trigger    = "";
	                        triggermode = "Changed Value";  
	                        MSG_CONTENT signals = {
	                            MESSAGE_TYPE AFDX = { }
	                        }
	
	                        updatemethod = {
	                            rx_rate = "1";
	                            rx_offset = "0";
	                            mode = "Single Msg.";
	                        }
	
		#set $porttype = $message['Type']
				
	                        PORT_TYPE $porttype.lower() = {
		#if $porttype.upper() == "QUEUEING"
		#set $queuesize = $vl.mtu*$message['QueueLength']
								queuesize = "$queuesize";
		#end if
	                        }
	    #if $message['EdeSourceId'] == 0 
	                        PROT_LAYER udp_layer = {
	                        }
	    #else
	                        PROT_LAYER ede_layer = {
	                            source_id = "$message['EdeSourceId']";
	                            subscriber_idx = "1";
	                            redundancy_enbl = "0";
	                            crc_vldn_enbl = "1";
	                            ord_vldn_enbl = "1";
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
							msg_active = "$cvts.add_664_control($message, '__active__')";
	                        #set $rate = $message['TXRate'] / 10 + ($message['TXRate'] % 10 > 0)
							#if $rate == 0
							    #set $rate=1
							#end if
							EXPECTED_RATE = "$rate";
							rx_timestamp = "";
	                        ALIC no_alic = {
	                        }

	                    }
	                    iomap {    
	 
	                            #for $sig in $message['Signals'].values()
		                             $gen_signal($message, $sig)
		                        #end for
	   
	                    }
	                }
	 #end if
 #end for
#end def


#def gen_rxSimMsg($model)
#for $messageName in $model.keys()   
    #set $message=$model[$messageName]
    #if $LruName is None or $message['Lru'] in $LruName 
	    #set $Vlid = $message['Vlid']
	
	    #set $vl=$inputvl[$Vlid]
	    #if $message['SubVl'] > 0
	       #set $subvlId = $message['SubVl'] - 1
	    #else
	       #set $subvlId = 0
	    #end if
	                message $message['Message'] = {
	                    description {
	                        comment = "";
	                        link = "$vl.vlname";
	                        mac_src    = "ANY"; ##"$message['SourceMACA'].replace('.', ':')";
	                        #set $dstip = $message['DestIP']
	                        #if $dstip == ""
	                            #set $dstip = "ANY"
	                        #end if
	                        dst_addr   = "$dstip";
	                        dst_port   = "$message['DestUDP']";
	                        src_addr   = "$message['SourceIP']";
	                        src_port   = "$message['SourceUDP']";
	                        pdu_length = "$message['TXLength']";
	                        subid_bytes = "0:0";
                            subid_mask = "0";
                            subid_match = "0";
                            trigger    = "";
	                        triggermode = "Changed Value";  
	                        MSG_CONTENT signals = {
	                            MESSAGE_TYPE AFDX = { }
	                        }
	
	                        updatemethod = {
	                            rx_rate = "1";
	                            rx_offset = "0";
	                            mode = "Single Msg.";
	                        }
	
		#set $porttype = $message['Type']
				
	                        PORT_TYPE $porttype.lower() = {
		#if $porttype.upper() == "QUEUEING"
		#set $queuesize = $vl.mtu*$message['QueueLength']
								queuesize = "$queuesize";
		#end if
	                        }
	    #if $message['EdeSourceId'] == 0 
	                        PROT_LAYER udp_layer = {
	                        }
	    #else
	                        PROT_LAYER ede_layer = {
	                            source_id = "$message['EdeSourceId']";
	                            subscriber_idx = "1";
	                            redundancy_enbl = "0";
	                            crc_vldn_enbl = "1";
	                            ord_vldn_enbl = "1";
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
							msg_active = "$cvts.add_664_control($message, '__active__')";
	                        #set $rate = $message['TXRate'] / 10 + ($message['TXRate'] % 10 > 0)
							#if $rate == 0
							    #set $rate=1
							#end if
							EXPECTED_RATE = "$rate";
							rx_timestamp = "";
	                        ALIC no_alic = {
	                        }

	                    }
	                    iomap {    
	 
	                            #for $sig in $message['Signals'].values()
		                             $gen_signal($message, $sig)
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

    TRANSPUTS {
        AFDX $device {
            debug {
            }

            description {
                comment = "";
            }

            receiver {
                vlinks {
                
                	$gen_rxvl($inputvl)
                	               
                }

                messages {
                    #if $mode == 'stim'   
                		$gen_rxStimMsg($inputmodel)
                		
                	#else
                		$gen_rxSimMsg($inputmodel)
                	#end if               
                }
            }

            transmitter {
                vlinks {                      	
                	               
					$gen_txvl($outputvl)
					
                }

                messages {
					#if $mode == 'stim'
						$gen_txStimMsg($outputmodel)
					#else
						$gen_txSimMsg($outputmodel)
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