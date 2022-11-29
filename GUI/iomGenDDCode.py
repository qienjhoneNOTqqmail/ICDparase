import struct
import zlib
import sys

from exceptions import Exception
from lxml import etree



def buildDDCode(xmlroot):
	class par_t:
		def __init__(self):
			self.offset = 0
			self.size = 0
			self.type = ""
			self.name = ""

	def getKey(item):
		return item.offset
		
	parList = []
	# Read the XML file
	for x in xmlroot.iterfind("parameter"):
		param = par_t()
		param.offset = int(x.attrib["offset"])
		param.size = int(x.attrib["size"])
		param.type = x.attrib["type"]		
		param.name = x.attrib["name"].split(".")[-1]
		parList.append(param)
	
	# Sort per offset
	parList.sort(key=getKey)

	output = "typedef struct\n{\n"
	offset = 0
	padId = 1
	for x in parList:
		if x.offset > offset:
			# Add padding
			gap = x.offset - offset
			strOffset = "/*\tOffset= " + ("%0.6i" % offset) + " */\t"
			output = output + strOffset + "Byte_t\t\t" + "padding" + str(padId) + "[" + str(gap) + "];\n"
			offset = x.offset
			padId = padId + 1
	
		type = x.type 
		
		strOffset = "/*\tOffset= " + ("%0.6i" % offset) + " */\t"
		if type == "BOOL":
			output = output + strOffset + "UInt32_t\t" + x.name + ";\n"
		elif type == "INT":
			output = output + strOffset + "SInt32_t\t" + x.name + ";\n"
		elif type == "FLOAT":
			output = output + strOffset + "Float32_t\t" + x.name + ";\n"
		elif type == "ENUM":
			output = output + strOffset + "SInt32_t\t" + x.name + ";\n"
		else:
			output = output + strOffset + "Byte_t\t\t" + x.name + "[" + str(x.size) + "];\n"
			
		offset = offset + x.size
	
	output = output + "} FDASAlertInputDD_t;\n"
	return output
	

def main(args):
    
    input_filename  = args[1]
    output_filename = args[0]
    xmlfile = open(input_filename, "r")
    xmltree = etree.parse(xmlfile)
    root = xmltree.getroot()
    output = buildDDCode(root)
    outfile = open(output_filename, "w");
    outfile.write(output)
    outfile.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
