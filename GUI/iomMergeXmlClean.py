import sys
from lxml import etree
from copy import deepcopy


def cleanConnections(duplicates,namespace):
    # go through the duplicates, collect destination of each channel,
    # and append it to the first channel, then remove the duplicates            
    for channel in duplicates[1:]:
        DestinationTag = "{"+namespace+"}Destination"
        duplicates[0].append(deepcopy(channel.find(DestinationTag)))
        channel.getparent().remove(channel)        
        
def cleanPorts(duplicates,namespace):
    # go through the duplicates, set the Attribute of the first occurence
    # to PSEUDO_PORT and delete the other entries
    duplicates[0].attrib["Attribute"] = "PSEUDO_PORT"
    for port in duplicates[1:]:
        port.getparent().remove(port) 

        
def cleanFile(xmlFile, section, attr, callback):
    print "Opening and cleaning "+xmlFile
    xmltree = etree.parse(xmlFile)
    xmlroot = xmltree.getroot()
        
    # extracting the section to be looked at from the main document.
    ns = xmlroot.nsmap[None]
    SectionTag  = "{"+ns+"}"+section
    SectionElts = xmlroot.find(SectionTag)

    # for each element in the section, check for duplicate according to the "main"
    # attribute (primary key equivalent)
    for sectionElt in SectionElts:
        currAttr = sectionElt.get(attr)
        if currAttr == None:
            # Could not find the desired attribute on the current section element.
            # it is very likely a comment... Uncomment the following line if necessary.
            # print "Check Issue on "+etree.tostring(sectionElt.pretty_print=True)
            continue
        # get all the section elements that matches the primary key:
        key = "[@"+attr+"='"+currAttr+"']"
        matching = SectionElts.findall(".//*"+key)
        
        # if "matching" length is more than one, we have duplicated element in the section
        if len(matching) != 1:
            print "Found duplicated port:"+currAttr
            
            # call the "registered" function to deal with duplicates in this file/section
            callback(matching,ns)
    
    file = open(xmlFile ,"w")
    file.write(etree.tostring(xmlroot,pretty_print=True))
    file.close()    
    

    
def main(args):
    mainCfgXml    = args[0]
    pseudoPortXml = args[1]
    
    cleanFile(mainCfgXml   ,"Connections","Id"  ,cleanConnections)
    cleanFile(pseudoPortXml,"Ports"      ,"Name",cleanPorts)

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
