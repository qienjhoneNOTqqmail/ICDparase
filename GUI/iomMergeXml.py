import sys

def main(args):
    if len(args) != 3:
        print "Usage: iomMergeXml inputfile srcdir outputdir"

    template = args[0]
    srcdir   = args[1]
    output   = args[2]
    
    templateLines = open(template,"r").readlines()
    outputFile    = open(output,"w")
    
    ### very basic operation... copies the template file into the output file 
    ### until a %%% filename %%% line is encoutered. Try to open the file
    ### listed, copy its content into output, then go on copy the content
    ### of the template
    
    for line in templateLines:
    	if line.strip().find("%%%") == 0:
    		fileToInsertName = line.split("%%%")[1].strip()
    		try:
    			linesToInsert = open(srcdir+"/"+fileToInsertName).readlines()
    			for lineToInsert in linesToInsert[1:-1]:
    				outputFile.write(lineToInsert)
    		except:
    			inlineWarning = "<!-- Here should be inserted the data extracted from "+fileToInsertName+" -->\n" 
    			outputFile.write(inlineWarning)
    			print "WARNING: could not find",fileToInsertName,"in",srcdir
    	else:
    		outputFile.write(line)
    outputFile.close()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
