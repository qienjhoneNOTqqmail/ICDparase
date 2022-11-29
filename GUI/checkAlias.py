import sys
import os.path

SL_HEADER = '''VERSION_CONTROL {
	FILE_NAME = \"$Id:$\";
	REVISION = \"$Revision:$\";
	AUTHOR = \"$Author:$\";
	DATE = \"$Date:$\";
}
SETLIST {
	LINKLIST {
		LINKS {
'''
SL_FOOTER = '''
        }

    }
}
'''
SL_LINK = '''
            LINK %s = {
                SOURCE = \"%s\";
                FILTER = "";
            }
		'''
def writeSetList(aliases, fn):
	fn_ = fn.replace(".cvt", ".set", 1)
	f = open(fn_, "w")
	f.write(SL_HEADER) 
	for a in aliases.keys():
		f.write(SL_LINK%(a, aliases[a]))
	f.write(SL_FOOTER) 
	f.close()
	print ">> " + fn_ + " written"

def checkAlias(check_only, dir, files):
	aliases = dict()
	for fn  in files:
		fn_ = dir + "/" + fn
		if(fn.endswith(".cvt")):
			print "Process " + fn
			f = open(fn_, "r")
			nc = ""			
			aliases_=dict()
			for l in f.readlines():
				if "ALIAS =" in l:
					alias = l.split("\"")[1]
					if alias in aliases.keys():
						nalias = "%s_%d"%(alias, len(aliases_.keys()))
						aliases_[nalias] = alias
						print ">> " + alias + " multiple defined"
						nc+=(l.replace(alias, nalias , 1 ))
					else:
						aliases[alias] = alias
						nc+=l
				else:
					nc+=l
			f.close()
			if(len(aliases_) and not check_only):
				print ">> " + fn + " written"
				f = open(fn_, "w")
				f.write(nc)
				f.close()
				writeSetList(aliases_, fn_)
			else:
				pass #do nothing
			
			
			
		else:
			pass #don't case
		
# --------------------------------------------------------------------
if __name__ == "__main__":
	
	try:
		fd = sys.argv[1]
		check_only = int(sys.argv[2])
	except:
		fd = "./"
		check_only = False
		
	if os.path.exists(fd) and os.path.isdir(fd):
		os.path.walk(fd, checkAlias, check_only)
	else:
		print "Can't read " + fd + " exiting"
		exit(1)
