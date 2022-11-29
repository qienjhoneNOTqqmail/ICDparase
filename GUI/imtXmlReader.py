'''
Created on 03.10.2014

@author: dk
'''
from lxml import etree
import sys
import os
import fnmatch

import logger
from bunch import Bunch

global w_exclude
w_exclude = None

# --------------------------------------------------------------------

class IcdNode(object):

    __slots__ = ( 'tag', 'a', 'e', 'text', 'filename', 'parent' )

    def __init__(self, xmltag, filename=None, parent=None):

        if xmltag is None:
            self.tag = "Icd"
            self.a = Bunch()
            self.e = Bunch()
            self.text = ''
        else:
            self.tag = xmltag.tag
            self.a = Bunch(**xmltag.attrib)
            self.e = Bunch()
            for t in xmltag:
                if not t.tag in self.e:
                    self.e[t.tag] = [IcdNode(t, filename, parent=self)]
                else:
                    self.e[t.tag].append(IcdNode(t, filename, parent=self))
            self.text = xmltag.text

        self.parent = parent
        self.filename = filename

    def __str__(self):
        attr = ["%s=%r" % (a, v) for (a, v) in self.e.__dict__.items()]
        return '<ICDNode(' + " ".join(attr) + ')>'
        
    def add(self, t, filename):
        '''
        Add a child object the corresponding entry list
        '''
        node = IcdNode(t, filename, parent=self)
        if not t.tag in self.e:
            self.e[t.tag] = [node]
        else:
            self.e[t.tag].append(node)
            
    def isChildOf(self, parent):
        node = self
        while node.parent is not None:
            if node.parent == parent:
                return True
            else:
                node = node.parent
        return False

    def isParentOf(self, child):
        node = child
        while node.parent is not None:
            if self.parent == self:
                return True
            else:
                node = node.parent
        return False
            
    
# --------------------------------------------------------------------
filecnt = 0 

def icdReadFile(xroot, source):
    '''
    Read an XML file in a IcdNode Tree and add it to the toplevel node provided in xroot
    - xroot: top level node to attach the data
    - source: source file name
    '''
    global filecnt
        
    if w_exclude and fnmatch.fnmatch(source, w_exclude):
        logger.ninfo("Ignoring XML File: %s" % source)
        return

    logger.ninfo("Reading XML File: %s" % source)
    filecnt += 1
    #if filecnt % 20 == 0:
    logger.progress("Reading XML File", 0.05)

    xmltree = etree.parse(source)
    root = xmltree.getroot()
    xroot.add(root, os.path.basename(source))


def icdReadDir(xroot, path, flist):
    '''
    Read all XML file in a directory
    - xroot: top level node to attach the data
    - path: folder path
    - flist: list of file and directries
    Non xml files (not ending with ".xml") and directories are skipped
    '''
    if w_exclude and fnmatch.fnmatch(path, w_exclude):
        logger.ninfo("Ignoring Folder: %s" % path)
        return
    
    for fn in flist:
        if not fn.endswith('.xml'):
            continue
        ffn = os.path.join(path, fn)
        if os.path.isdir(ffn):
            continue
        icdReadFile(xroot, ffn)
    

def icdReadAll(dirOrFileList, exclude=None):
    '''
    Read all ICD files in all directories 
    Glue them all together in a super root
    Return super root to caller
    '''
    global w_exclude
    w_exclude = exclude

    # root for complete XML Tree (including all files)
    xroot = IcdNode(None)
    
    for fn in dirOrFileList:
        if os.path.isdir(fn):
            os.path.walk(fn, icdReadDir, xroot)
        else:
            icdReadFile(xroot, fn)
    
    return xroot

# --------------------------------------------------------------------

if __name__ == "__main__":
    xroot = icdReadAll(sys.argv[1])
    
    for t, l in xroot.e.items():
        print '%6d: %s' % (len(l), t)

    raw_input()

