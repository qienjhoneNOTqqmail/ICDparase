#def gen_signal(msg, p)
    #set sigbytes = $int($p.sigSize / 8) + $int($p.sigSize%8 > 0)
    #set $endSigByte = ( $p.sigBitOffset)/8 + $sigbytes - 1
    #set $startSigByte     = ( $p.sigBitOffset)/8
    #set $startSigBit     = ( $p.sigBitOffset) - $startSigByte*8 
    #set $endSigBit     = ( $p.sigBitOffset) + $p.sigSize - $startSigByte*8 -1
    #set $startSigByte     = $msg.msgLength-1 - $startSigByte
    #set $endSigByte     = $msg.msgLength-1 - $endSigByte
                        signal {
                            point = "$cvts.add_a825_signal($p)";
                            bytes = "$startSigByte:$endSigByte";
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
    #else
                            COPY euconvert = {
                            }
    #end if                                
                        }
#end def

#def gen_inputmsg(model, dev)
    #for $messageName in $model.can.messages.keys()
        #set $message=$model.can.messages[$messageName]
        #if $lruName is not None and $message.lruName != $lruName:
            #continue
        #end if
        #if $type($device) == $type('str')
            #set $skip = False
        #else
            #set $skip = not ($dev ==  $device.getAdsDevice($message.msgPhysPort))
        #end if
            #if not $skip
                INPUT-MESSAGE $message.msgName = {
                    CONFIGURATION {
                        comment = "";
                        canidtype = "EXT";
                        canid = "$message.msgCanID";
                        #if not $msgonly
                        DMODE = {
                            SAMPLING DATA_MODE = {
                            }
                        }
                        #else
                        DMODE = {
                            QUEUEING DATA_MODE = {
                                fifo = "$cvts.add_a825_msg($message)";
                            }
                        }    
                        #end if 

                        UPDATE_INFO = {
                            update_rate = "";
                            label_active = "";
                            EXPECTED_RATE = "$message.msgRate";
                            rx_timestamp = "";
                        }
                    }

                    iomap {
                #if not $msgonly
                #for $param in $model.can.signals[$messageName]
                     $gen_signal($message, $param)
                #end for
                #end if
                    }
                }
        #end if
    #end for
#end def

#def gen_outputmsg(model, dev)
    #for $messageName in $model.can.messages.keys()
        #set $message=$model.can.messages[$messageName]
        #if $lruName is not None and $message.lruName != $lruName:
            #continue
        #end if
        #if $type($device) == $type('str')
            #set $skip = False
        #else
            #set $skip = not ($dev ==  $device.getAdsDevice($message.msgPhysPort))
        #end if
            #if not $skip
                OUTPUT-MESSAGE $message.msgName = {
                    CONFIGURATION {
                        comment = "";
                        canidtype = "EXT";
                        canid = "$message.msgCanID";
                        msgtype = "DATA";
                        BYTECOUNT = "$message.msgLength";
                        activate = {
                            point = "$cvts.add_a825_msg_control($message, 'activate')";
                            mask = "0xffffffff";
                        }
                        #if not $msgonly
                        DMODE = {
                            TX_SAMPLING DATA_MODE = {
                                rate = "$message.msgRate";
                                offset = "0";
                            }

                        }
                        #else
                        DMODE = {
                            QUEUEING DATA_MODE = {
                                fifo = "$cvts.add_a825_msg($message)";
                            }

                        }    
                        #end if 
                    }

                    iomap {
            #if not $msgonly
            #for $param in $model.can.signals[$messageName]
                        $gen_signal($message, $param)
            #end for
            #end if
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
    #if $type('str') == $type($device)
        #set $devList = [$device]
    #else
        #set $devList = $device.getAdsDeviceList($lruName)
    #end if
    #for $dev in  $devList
        TECHSAT-CAN $dev = {
            GLOBAL_CONFIG {
                comment = "";
                speed = "500K";
                mode = "Normal";
                TXECHO = "0";
            }
            
            INPUT_MESSAGES {
                $gen_inputmsg($inputModel, $dev)
            }
            
            OUTPUT_MESSAGES {
                $gen_outputmsg($outputModel, $dev)
            }
           
        }
    #end for
    }
}