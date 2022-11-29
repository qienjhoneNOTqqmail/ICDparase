from Cheetah.Template import Template
from lxml  import etree
import sys
import os

PseudoPortTemplate = '''

#def genDriverName(platform, portid)
  #if $platform =="idu"
      DriverName="a664_driver"
  #elif $platform == "ima"
      DriverName="/dev/afdx/0/$portid"
  #else
      DriverName="UNKNOWN"
  #end if
#end def
  

 #for $key in $model.messageKeys
  #set map=$model.messages[$key]
    #if $map.isQueuing
        <QueuingPort
          Attribute="DIRECT_ACCESS_PORT"
      #if $direction == "input"
          Name="pseudoport_a664_rx_$map.portId"
          Direction="SOURCE"
          Protocol="RECEIVER_DISCARD"          
      #else
          Name="pseudoport_a664_tx_$map.portId"
          Direction="DESTINATION"
          Protocol="NOT_APPLICABLE"          
      #end if
          MessageSize="$map.msgLength"
          QueueLength="$map.queueLength"
          $genDriverName($platform, $map.portId)/>
    #else
        <SamplingPort 
          Attribute="PSEUDO_PORT"
      #if $direction == "input"
          Name="pseudoport_a664_rx_$map.portId"
          Direction="SOURCE"
      #else
          Name="pseudoport_a664_tx_$map.portId"
          Direction="DESTINATION"
      #end if
          MessageSize="$map.msgLength"
          RefreshRate="$map.ratesec"
          $genDriverName($platform, $map.portId)
          />
    #end if
 #end for
'''

ApexPortTemplate = '''
 #for $key in $model.messageKeys
  #set map=$model.messages[$key]
    #if len($map.portName) > 30:
        <!-- port name truncated by tool. Original name: $map.portName -->
    #end if
    #if $map.isQueuing
        <QueuingPort 
            Name="$map.portName[0:30]"  
            QueueLength="$map.queueLength"
            MessageSize="$map.msgLength" 
#if $direction == "input"
            Direction="DESTINATION"
            Protocol="NOT_APPLICABLE"             
#else
            Direction="SOURCE"
            Protocol="RECEIVER_DISCARD"
#end if
            Attribute="LOCAL_PORT"/>

    #else
        <SamplingPort 
            Name="$map.portName[0:30]"  
            Attribute="LOCAL_PORT"
#if $direction == "input"
            Direction="DESTINATION"
#else
            Direction="SOURCE"
#end if
            MessageSize="$map.msgLength"
            RefreshRate="$map.ratesec"/>
        
    #end if
 #end for
'''

ConnectionTemplate = '''
#def genDriverPartName(platform)
    #if $platform =="ima"
        PartitionNameRef = "AfdxDriver"
    #elif $platform == "idu"
        PartitionNameRef = "pseudo_part"
    #else
        PartitionNameRef = "UNKNOWN"
    #end if
#end def

 #for $key in $model.messageKeys
  #set map=$model.messages[$key]
  #if len($map.portName) > 30:
        <!-- port name truncated by tool. Original name: $map.portName -->     
  #end if
  #if $direction == "input"
        <Channel    Id="1$map.portId">
            <Source 
                $genDriverPartName($platform)
                PortNameRef="pseudoport_a664_rx_$map.portId"/>
            <Destination 
                PartitionNameRef="$model.appPartitionName" 
                PortNameRef="$map.portName[0:30]"/>
        </Channel>    
  #else
        <Channel    Id="2$map.portId">
            <Destination 
                $genDriverPartName($platform)
                PortNameRef="pseudoport_a664_tx_$map.portId"/>
            <Source 
                PartitionNameRef="$model.appPartitionName" 
                PortNameRef="$map.portName[0:30]"/>
        </Channel>    
  #end if
 #end for
'''


class Bunch(object):
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

class PortConfigGenerator():
    def __init__(self, filename):
        self.filename = filename
        self.inputMessages     = {}
        self.inputMessageKeys  = []
        self.outputMessages    = {}
        self.outputMessageKeys = []
        
        xmlfile = open(filename, "r")
        xmltree = etree.parse(xmlfile)
        root = xmltree.getroot()
        

        section = root.find("AfdxInput")
        if section is not None:
            for xm in section.iterfind("AfdxMessage"):
                message = self.readMessage(xm)
                self.inputMessageKeys.append(message.msgName)
                self.inputMessages[message.msgName] = message

        section = root.find("AfdxOutput")
        if section is not None:
            for xm in section.iterfind("AfdxMessage"):
                message = self.readMessage(xm)
                self.outputMessageKeys.append(message.msgName)
                self.outputMessages[message.msgName] = message
            
    def readMessage(self, xm):
        message = Bunch(
            msgName     = xm.attrib["messageName"],
            portName    = xm.attrib["portName"],
            portId      = xm.attrib["portId"],
            rate        = xm.attrib["rate"],
            ratesec     = float(xm.attrib["rate"]) / 1000.0,
            msgLength   = xm.attrib["length"],
            isQueuing   = False,
            queueLength = 0
        )
        porttype = xm.attrib['portType'].upper()
        if porttype.startswith('Q'):
            message.isQueuing = True
            message.queueLength = int(xm.attrib["queueLength"])
        elif porttype.startswith('S'):
            message.isQueuing = False
            message.queueLength = 0
        else:
            sys.stderr.write("Bad port type (%s) for message %s\n" %(porttype, message.messageName))
            return None
        
        return message
        

    def genPseudoPorts(self, appname, platform, outdir):
        outfn = os.path.join(outdir, appname + '-pseudoports.xml')
        f = open(outfn, "w")

        model = Bunch(messages = self.inputMessages, messageKeys=self.inputMessageKeys, appPartitionName=appname + "_part")
        tmpl = Template(PseudoPortTemplate, searchList=[{ "platform": platform, "model"  : model, "direction": "input"}])
        f.write("<A664PseudoPorts>")
        f.write(tmpl.respond())

        model = Bunch(messages = self.outputMessages, messageKeys=self.outputMessageKeys, appPartitionName=appname + "_part")
        tmpl = Template(PseudoPortTemplate, searchList=[{ "platform": platform, "model"  : model, "direction": "output"}])
        f.write(tmpl.respond())
        f.write("<A664PseudoPorts>")

    def genApexPorts(self, appname, platform, outdir):
        outfn = os.path.join(outdir, appname + '-apexports.xml')
        f = open(outfn, "w")

        model = Bunch(messages = self.inputMessages, messageKeys=self.inputMessageKeys, appPartitionName=appname + "_part")
        tmpl = Template(ApexPortTemplate, searchList=[{ "platform": platform, "model"  : model, "direction":"input"}])
        f.write("<A664ApplicationPorts>")
        f.write(tmpl.respond())

        model = Bunch(messages = self.outputMessages, messageKeys=self.outputMessageKeys, appPartitionName=appname + "_part")
        tmpl = Template(ApexPortTemplate, searchList=[{ "platform": platform, "model"  : model, "direction":"output"}])
        f.write(tmpl.respond())
        f.write("</A664ApplicationPorts>")

    def genConnections(self, appname, platform, outdir):
        outfn = os.path.join(outdir, appname + '-connections.xml')
        f = open(outfn, "w")

        model = Bunch(messages = self.inputMessages, messageKeys=self.inputMessageKeys, appPartitionName=appname + "_part")
        tmpl = Template(ConnectionTemplate, searchList=[{ "platform": platform, "model"  : model, "direction": "input"}])
        f.write("<A664PortConnections>")
        f.write(tmpl.respond())

        model = Bunch(messages = self.outputMessages, messageKeys=self.outputMessageKeys, appPartitionName=appname + "_part")
        tmpl = Template(ConnectionTemplate, searchList=[{ "platform": platform, "model"  : model, "direction": "output"}])
        f.write(tmpl.respond())
        f.write("</A664PortConnections>")

def main(args):
    if len(args) != 3:
        print "Usage: iomGenVxWConfig inputfile appname outdir platform"
        return -1

    filename = args[0]
    appname  = args[1]
    outdir   = args[2]
    if len(args) > 3:
        platform = args[3]
    else:
        # let's determine ourself
        if appname[0:3].lower() in ('syn', 'fda', 'dmi'):
            platform = "ima"
        else:
            platform = "idu"

    msgreader = PortConfigGenerator(filename)
    msgreader.genPseudoPorts(appname, platform, outdir)
    msgreader.genApexPorts(appname, platform, outdir)
    msgreader.genConnections(appname, platform, outdir)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
