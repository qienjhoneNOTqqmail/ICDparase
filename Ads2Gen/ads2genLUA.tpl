## ----------------------------------------------------------------------------
## ADS2 IOM AFDX Signal Definition Template 
## ----------------------------------------------------------------------------

-- @brief AFDX Protocol dissector plugin
-- @author zhengchao
-- @date 2017.2.17

-- create a new dissector
#set $name="C919_DS-"+$str($udpport)
local NAME = "$name"
local PORT = $udpport
local c919ds = Proto(NAME, "AFDX Protocol $str($udpport)")


-- create fields of c919ds
local fields = c919ds.fields
#set $dslist = []
#set $dslist1 = []

#for $messageName in $inputmodel.keys()
    #set $message=$inputmodel[$messageName]
    #if $udpport is not None and $message['SourceUDP']==$udpport
        ##$print("message name is %s " % ($message['Lru']))
--LRU: $message['Lru']
--MSG NAME: $message['fullname']
        #for $key in $sorted($message['Signalss'].keys())
            #set $sig = $message['Signalss'][$key]
            ##$print("sig name is %s " % ($sig['Signal']))
            #if 'FSS' in $sig['Signal'] or 'FSB' in $sig['Signal'] or 'spare' in $str($sig['Signal']).lower() or 'reserve' in  $str($sig['Signal']).lower():
                #continue
            #end if 
            #if $sig['SigSize'] > ($sig['sigalign'] * 8)
                    #set $endSigByte = $sig['sigbyteoffset']+$sig['SigSize'] / 8 - 1
            #else
                    #set $endSigByte = $sig['sigbyteoffset']+$sig['sigalign'] - 1
            #end if
    #set $mask = (2**$sig['SigSize']-1)<<$sig['sigbitoffset']
    #if $sig['664FSB'] 
    #if $sig['DataSet'] not in $dslist
    $dslist.append($sig['DataSet'])
    #set $dsfsb = $sig['DataSet'].replace(".","_")+'_FSB'
fields.$dsfsb = ProtoField.uint8(NAME .. "$dsfsb", "$dsfsb",base.DEC,{[0]="ND",[3]="NO",[12]="FT",[48]="NCD"},0xFF)
fields.$sig['DataSet'].replace(".","_") = ProtoField.bytes(NAME .. "$sig['DataSet']", "$sig['DataSet']")
    #end if
    #if $endSigByte - $sig['sigbyteoffset'] ==0
fields.$sig['Signal'].replace(".","_") = ProtoField.uint8(NAME .. "$sig['Signal']", "$sig['Signal']",base.DEC,{},$mask)
    #end if
    #if $endSigByte - $sig['sigbyteoffset'] ==1
fields.$sig['Signal'].replace(".","_") = ProtoField.uint16(NAME .. "$sig['Signal']", "$sig['Signal']",base.DEC,{},$mask)
    #end if
    #if $endSigByte - $sig['sigbyteoffset'] ==3
fields.$sig['Signal'].replace(".","_") = ProtoField.uint32(NAME .. "$sig['Signal']", "$sig['Signal']",base.DEC,{},$mask)
    #end if
    #if $endSigByte - $sig['sigbyteoffset'] ==7
fields.$sig['Signal'].replace(".","_") = ProtoField.uint64(NAME .. "$sig['Signal']", "$sig['Signal']",base.DEC,{},$mask)
    #end if
    #else
    ##if $endSigByte - $sig['sigbyteoffset'] >7
fields.$sig['Signal'].replace(".","_") = ProtoField.bytes(NAME .. "$sig['Signal']", "$sig['Signal']",base.HEX)
    #end if
        #end for
    #end if
#end for

-- dissect packet
function c919ds.dissector (tvb, pinfo, tree)
    local subtree = tree:add(c919ds, tvb())
    local baseoffset = 8
    
    -- show protocol name in protocol column
    pinfo.cols.protocol = c919ds.name
    
    -- dissect field one by one, and add to protocol tree
    
#for $messageName in $inputmodel.keys()
    #set $message=$inputmodel[$messageName]
    #if $udpport is not None and $message['SourceUDP']==$udpport
    pinfo.cols.info:set("Msg from $message['fullname']")
        ##$print("message name is %s " % ($message['Lru']))
        #for $key in $sorted($message['Signalss'].keys())
            #set $sig = $message['Signalss'][$key]
            ##$print("sig name is %s " % ($sig['Signal']))
            #if 'FSS' in $sig['Signal'] or 'FSB' in $sig['Signal'] or 'spare' in $str($sig['Signal']).lower() or 'reserve' in  $str($sig['Signal']).lower():
                #continue
            #end if 
            #if $sig['SigSize'] > ($sig['sigalign'] * 8)
                    #set $endSigByte = $sig['sigbyteoffset']+$sig['SigSize'] / 8 - 1
            #else
                    #set $endSigByte = $sig['sigbyteoffset']+$sig['sigalign'] - 1
            #end if
    #set $mask = (2**$sig['SigSize']-1)<<$sig['sigbitoffset']
    #set $bytecount = $endSigByte - $sig['sigbyteoffset']+1
    ##$print("sig startbyte is %s " % ($sig['sigbyteoffset']))
    ##$print("sig endbyte is %s " % ($endSigByte))
    #set $treename = $sig['DataSet'].replace(".","_")+'tree'
    #if $sig['664FSB'] 
    #if $sig['DataSet'] not in $dslist1
    $dslist1.append($sig['DataSet'])
    #set $dsfsb = $sig['DataSet'].replace(".","_")+'_FSB'
    subtree:add(fields.$dsfsb, tvb(baseoffset+$sig['FsbOffset'], 1))
    $treename=subtree:add(fields.$sig['DataSet'].replace(".","_"),tvb(baseoffset+$sig['DSOffset'],$sig['DSSize']))
    ##fields.$dsfsb = ProtoField.uint8(NAME .. "$dsfsb", "$dsfsb",base.DEC,{},0xFF)
    ##fields.$sig['DataSet'] = ProtoField.bytes(NAME .. "$sig['DataSet']", "$sig['DataSet']")
    #end if
    #if $endSigByte - $sig['sigbyteoffset'] ==0
    $treename:add(fields.$sig['Signal'].replace(".","_"), tvb(baseoffset+$sig['sigbyteoffset'], $bytecount))
    #end if
    #if $endSigByte - $sig['sigbyteoffset'] ==1
    $treename:add(fields.$sig['Signal'].replace(".","_"), tvb(baseoffset+$sig['sigbyteoffset'], $bytecount))
    #end if
    #if $endSigByte - $sig['sigbyteoffset'] ==3
    $treename:add(fields.$sig['Signal'].replace(".","_"), tvb(baseoffset+$sig['sigbyteoffset'], $bytecount))
    #end if
    #if $endSigByte - $sig['sigbyteoffset'] ==7
    $treename:add(fields.$sig['Signal'].replace(".","_"), tvb(baseoffset+$sig['sigbyteoffset'], $bytecount))
    #end if
    #else
    ##if $endSigByte - $sig['sigbyteoffset'] >7
    --no FSB
    ##$treename=subtree:add(fields.$sig['DataSet'].replace(".","_"),tvb(baseoffset+$sig['DSOffset'],$sig['DSSize']))
    subtree:add(fields.$sig['Signal'].replace(".","_"), tvb(baseoffset+$sig['sigbyteoffset'], tvb:len()-baseoffset))
    #end if
        #end for
    #end if
#end for    

end

-- register this dissector
DissectorTable.get("udp.port"):add(PORT, c919ds)
