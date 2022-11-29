#coding:utf-8
import os,sys,os.path
import xml.etree.ElementTree as ET

#global var
#show log
SHOW_LOG = True
#XML file
XML_PATH = None
All_Nodes = list()
All_Paths = list()
def Get_Child(Parent_Node):
    child= Parent_Node.getchildren()
    if child is not None:
        return child
    return False

def Get_Child1(Parent_Node,inputres):
    inputres = inputres+'.'+ Parent_Node.tag
    children= Parent_Node.getchildren()
    if children in None:
        if inputres not in All_Paths:
            All_Paths.append(inputres)
        return
    else:
        for child in children:
           Get_Child1(child,inputres)


def Get_AllChildName(root):
    #root = tree.getroot()
    print root.tag
    child1_List = Get_Child(root)
    if child1_List == False:
        return
    for child in child1_List:
        #print(child.tag)
        if child.tag not in All_Nodes:
            All_Nodes.append(child.tag)
        Get_AllChildName(child)               
    
def read_xml1(in_path):
    '''读取并解析xml文件
       in_path: xml路径
       return: ElementTree'''
    tree = ET.parse(in_path)
    return tree    

def read_xml(xmlFile,destDir):
    '''
  parse  xml,规则是解析如下格式的xml，root下的2、3级建立目录，第4级建立文件，4级以下以合适的形式写入到文件中
  <?xml version="1.0" ?> 
- <root>
  - <FILE_DIRECTORY NAME="ca002">
   - <FILE_DIRECTORY NAME="RT_CA">
    - <FILE_NAME NAME="0000.obj">
        - <COFF_FILE_HEAD BEGIN="0" END="20">
              <Machine>X86</Machine> 
              <NumberOfSections>2</NumberOfSections> 
              <PointerToSymbolTable>21205</PointerToSymbolTable> 
              <NumberOfSymbols>107</NumberOfSymbols> 
              <SizeOfOptionalHeader>0</SizeOfOptionalHeader> 
              <Characteristics>0</Characteristics> 
          </COFF_FILE_HEAD>
        - <COFF_IMAGE_SECTIONS>
            - <COFF_IMAGE_SECTION INDEX="0">
              <Name>.rdata</Name> 
              <SizeOfRawData>5064</SizeOfRawData> 
              <PointerToRawData>100</PointerToRawData> 
              <PointerToRelocations>0</PointerToRelocations> 
              <PointerToLinenumbers>0</PointerToLinenumbers> 
              <NumberOfRelocations>0</NumberOfRelocations> 
              <NumberOfLinenumbers>0</NumberOfLinenumbers> 
  '''
    # 加载XML文件（2种方法,一是加载指定字符串，二是加载指定文件）
    tree=ET.parse(xmlFile)
    root = tree.getroot()
    #root = ET.fromstring(xmlContent)
    dir1_nodes = root.getchildren()
    #create dir1
    for dir1_node in dir1_nodes:
        dir1=destDir+os.path.sep+dir1_node.attrib['NAME']
        if os.path.exists(dir1)==False:
            os.mkdir(dir1)
        #create dir2
        dir2_nodes = dir1_node.getchildren()
        for dir2_node in dir2_nodes:
            dir2=dir1+os.path.sep+dir2_node.attrib['NAME']
            if os.path.exists(dir2)==False:
                os.mkdir(dir2)
            #create file
            dir3_nodes = dir2_node.getchildren()
            for dir3_node in dir3_nodes:
                dir3=dir2+os.path.sep+dir3_node.attrib['NAME']
                #print dir3
                f=open(dir3,'w')
                #遍历xml标签name=***.obj
                prelen=0
                dir4_nodes = dir3_node.getchildren()
                for dir4_node in dir4_nodes:
                    traversal(dir4_node,f,prelen)
                f.close()

def Prase_ICD_xml(xmlFile,destDir):
    '''
  parse  xml,规则是解析如下格式的xml，root下的2、3级建立目录，第4级建立文件，4级以下以合适的形式写入到文件中
  <?xml version="1.0" ?> 
- <root>
  - <FILE_DIRECTORY NAME="ca002">
   - <FILE_DIRECTORY NAME="RT_CA">
    - <FILE_NAME NAME="0000.obj">
        - <COFF_FILE_HEAD BEGIN="0" END="20">
              <Machine>X86</Machine> 
              <NumberOfSections>2</NumberOfSections> 
              <PointerToSymbolTable>21205</PointerToSymbolTable> 
              <NumberOfSymbols>107</NumberOfSymbols> 
              <SizeOfOptionalHeader>0</SizeOfOptionalHeader> 
              <Characteristics>0</Characteristics> 
          </COFF_FILE_HEAD>
        - <COFF_IMAGE_SECTIONS>
            - <COFF_IMAGE_SECTION INDEX="0">
              <Name>.rdata</Name> 
              <SizeOfRawData>5064</SizeOfRawData> 
              <PointerToRawData>100</PointerToRawData> 
              <PointerToRelocations>0</PointerToRelocations> 
              <PointerToLinenumbers>0</PointerToLinenumbers> 
              <NumberOfRelocations>0</NumberOfRelocations> 
              <NumberOfLinenumbers>0</NumberOfLinenumbers> 
  '''
    # 加载XML文件（2种方法,一是加载指定字符串，二是加载指定文件）
    tree=ET.parse(xmlFile)
    root = tree.getroot()
    #root = ET.fromstring(xmlContent)
    dir1_nodes = root.getchildren()
    dir1 = root.attrib['Name']
    print dir1
    #create dir1
    for dir1_node in dir1_nodes:
        if dir1_node is None:
            continue
        dir1=dir1_node.attrib['Name']
        #if os.path.exists(dir1)==False:
        print dir1  
            #os.mkdir(dir1)
        #create dir2
        dir2_nodes = dir1_node.getchildren()
        for dir2_node in dir2_nodes:
            if dir2_node is None:
                continue
            if dir2_node.attrib.has_key('Name'):
                dir2=dir2_node.attrib['Name']
                print 'Name - ' +dir2
            elif dir2_node.attrib.has_key('SrcName'):
                dir2=dir2_node.attrib['SrcName']
                print 'SrcName - '+dir2
            #if os.path.exists(dir2)==False:
                          #os.mkdir(dir2)
            #create file
            dir3_nodes = dir2_node.getchildren()
            for dir3_node in dir3_nodes:
                if dir3_node is None:
                    continue
                if dir3_node.attrib.has_key('Name'):
                    dir3=dir3_node.attrib['Name']
                    print 'Name -' + dir3
                elif dir3_node.attrib.has_key('SrcName'):
                    dir3=dir3_node.attrib['SrcName']
                    print 'SrcName - '+dir3
                
def traversal(node,f,prelen):
    '''recursively traversal the rest of xml's content'''
    length=node.getchildren()
    attrs=''
    texts=''
    if len(node.attrib)>0:
        for key in node.attrib:
            attrs+=str(key)+":"+str(node.attrib[key])+" "
        attrs=attrs[:-1]
        f.write('-'*prelen+node.tag+'('+attrs+')')
    else:
        f.write('-'*prelen+node.tag)
    if node.text!=None:
        f.write(':'+node.text)
    f.write('\n')
    if length!=0:
        nodes = node.getchildren()
        prelen+=4
        for node1 in nodes:           
            traversal(node1,f,prelen)           
def parseXmls(filePath,destDir):
    '''traversal xmls directory'''
    if os.path.isfile(filePath)and os.path.basename(filePath).endswith('.xml'):
        #print filePath
        read_xml(filePath,destDir)
    else:
        for item in os.listdir(filePath):
            #print item
            subpath = filePath+os.path.sep+item
            parseXmls(subpath,destDir)
def main():
    "Main function."
    #input xml dir
    while True:
        dir=raw_input("input the dir:")
        if not os.path.exists(dir):
            print("you input dir is not existed!")
            continue
        else:
            break
    #create the dir of dest path that using to store the parsing xmls 
    '''destDir = os.path.split(dir)[0]+os.sep+time.strftime('%Y%m%d')
        if not os.path.exists(destDir):
            os.mkdir(destDir) '''
    
    destDir = os.path.split(dir)[0]+os.path.sep+os.path.basename(dir)+'xml'
    if os.path.exists(destDir)==False:
                os.mkdir(destDir)  
    #recall the function of parse the xmls
    #parseXmls(dir,destDir)
    tree = read_xml1(dir)
    root=tree.getroot()
    Get_Child1(root,'')
    Get_AllChildName(root)
    print(All_Nodes)
    
    Prase_ICD_xml(dir,destDir)    
if __name__ == '__main__':
     main()
