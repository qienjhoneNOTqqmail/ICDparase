import os        
import sys


def makePath(path):
    absolutePath = os.path.abspath(path).replace("\\", "/")
    root, dirs   = os.path.splitdrive(absolutePath)
    
    if (dirs[0] == "/"):
        dirs = dirs[1:]
    directories = dirs.split("/")
    
    path = root

    for x in directories:
        path = path + "/" + x
        if not os.path.isdir(path):
            # create
            os.mkdir(path)
        #else:
            # already exists



def main(args):
    
    makePath (args[0])
    


def usage():
    sys.stderr.write('Usage: path to be created\n')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    else:
        sys.exit(main(sys.argv[1:]))
