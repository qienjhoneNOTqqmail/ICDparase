NORMALIZE_SIGTYPES = {
    'SINT'  : 'INT',
    'SHORT' : 'INT',
    'INT'   : 'INT',
    'USHORT': 'UINT',
    'UINT'  : 'UINT',
    'CHAR'  : 'INT',
    'DIS'   : 'BOOL',
    'BOOL'  : 'BOOL',
    'ENUM'  : 'COD',
    'COD'   : 'COD',
    'OPAQUE': 'BYTES',
    'BYTES' : 'BYTES',
    'BLK'   : 'BYTES',
    'STRING': 'STRING',
    'FLOAT' : 'FLOAT',
    'BNR'   : 'BNR',
    'UBNR'  : 'UBNR',
    'BCD'   : 'BCD',
    'UBCD'  : 'UBCD',
    'ISO-5' : 'COD',
    # special purpose types, all can be treated as bitfields alias COD
    'A429OCTLBL'    : 'COD',
    'A429SDI'       : 'COD',
    'A429_SSM_BNR'  : 'COD',
    'A429_SSM_DIS'  : 'COD',
    'A429_SSM_BCD'  : 'COD',
    'A429PARITY'    : 'COD',
    'PAD'           : 'PAD',
    'RESV'          : 'COD',
    'CRC'           : 'UINT',
    'A664_FSB'      : 'UINT',
    # special function sig types
    'UNFRESH'       : 'UNFRESH'
}

def normalizeSigType(sigtype, sigsize):
    if sigtype in ("CHAR", "INT8", "UINT8") and sigsize != 8:
        raise Exception, "Wrong signal size for data type %s" % sigtype

    if sigtype in ("SHORT", "INT16", "UINT16") and sigsize != 16:
        raise Exception, "Wrong signal size for data type %s" % sigtype

    if sigtype in ("UINT", ) and sigsize not in (8,16,32,64):
        sigtype = "COD"
    
    normalizedType = NORMALIZE_SIGTYPES.get(sigtype)
    if normalizedType is None:
        raise Exception, "Unknown signal type %s" % sigtype
    
    return normalizedType


DATATYPES_COMPAT = {
    #Param Type  SignalType 
    'INT':       set(('INT', 'UINT', 'COD', 'FLOAT', 'BNR', 'UBNR', 'BCD', 'UBCD','BOOL',)),
    'COUNT':     set(('INT',)),
    'FLOAT':     set(('INT', 'FLOAT', 'BNR', 'UBNR', 'BCD', 'UBCD')),
    'BOOL':      set(('BOOL','UNFRESH')),
    'ENUM':      set(('COD',)),
    'BYTES':     set(('BYTES','STRING')),
    'CSTRING':   set(('STRING',)),
    'ASTRING':   set(('STRING',)),
}

def compatParamSignal(paramName, paramDatatype, paramDatasize, sigType, sigSize):
    if paramDatatype not in DATATYPES_COMPAT:
        raise Exception, "Illegal parameter data type: %s" % paramDatatype

    if sigType not in DATATYPES_COMPAT[paramDatatype]:
        raise Exception, "Illegal or incompatible signal data type: %s - %s" % (paramDatatype, sigType)
    if paramDatatype != "BYTES":
        if paramDatasize != 32:
            raise Exception, "Illegal parameter data size: %d" % paramDatasize
        if sigSize > 32:
            raise Exception, "Illegal signal size: Only 32 bit values are supported"
    else:
        if (paramDatasize & 0x7): # not multiple of bytes
            raise Exception, "Illegal parameter data size: %d" % paramDatasize
        if paramDatasize != sigSize:
            raise Exception, "Incompatible data size for BYTES signal %s: Parameter: %d,  Signal: %d" % \
                    (paramName, paramDatasize, sigSize)


ONEBIT_TYPES   = set(("BOOL",))
MULTIBYTE_TYPES= set(("BYTES","STRING"))
FULLBYTE_TYPES = set(("INT", "UINT", "CHAR", "FLOAT","BYTES", "STRING"))
BYTE_TYPES     = set(("INT", "UINT"))
HALFWORD_TYPES = set(("INT", "UINT"))
FULLWORD_TYPES = set(("INT", "UINT", "FLOAT"))
LONGWORD_TYPES = set(("INT", "UINT", "FLOAT"))
INTEGER_TYPES  = set(("INT", "UINT"))

        
def computeSignalAccess(msgclass, sigtype, sigsize=0, sigoffset=0, dssize=0, dspos=0):
    if msgclass == "AFDX":
        return computeSignalAccessAFDX(sigtype, sigsize, sigoffset, dssize, dspos)
    elif msgclass == "CAN":
        return computeSignalAccessCAN(sigtype, sigsize, sigoffset, dssize, dspos)
    elif msgclass == "A429":
        return computeSignalAccessA429(sigtype, sigsize, sigoffset, dssize, dspos)
    else:
        raise Exception, "Illegal Message Class %s" % msgclass



def computeSignalAccessAFDX(sigtype, sigsize=0, sigoffset=0, dssize=0, dspos=0):
    # consistency checks

    # signal must fit in dataset
    # FIXME: if sigoffset + sigsize > dssize * 8:
    #    raise Exception, "Signal does not fit into data set or message"
    
    # for AFDX dataset must be 4 byte aligned and size must be multiple of 4 byte 
    if dssize % 4 != 0 or dspos % 4 != 0:
        raise Exception, "Illegal Data Set Alignment"

    if sigtype in FULLBYTE_TYPES and sigoffset % 8 != 0:
        raise Exception, "Signal offset not aligned to byte boundary"

    if sigtype == "BYTES" and sigoffset % 32 != 0:
        raise Exception, "OPAQUE signal offset not aligned to word boundary"

    if sigtype in ONEBIT_TYPES and sigsize != 1:
        raise Exception, "Illegal signal size for type %s" % sigtype
        
    if sigtype in INTEGER_TYPES and sigsize not in (8, 16, 32, 64):
        raise Exception, "Illegal signal size for type %s" % sigtype

    if sigtype == "FLOAT" and sigsize not in (32, 64):
        raise Exception, "Illegal signal size for type %s" % sigtype
        
    
    if  (sigtype == "BYTES"):
        # Opaque: sigoffset is least significant bit of first word
        # Only works for opaque which have bitoffset multiple of 4 bytes
        sigAccess = 1
        sigByteOffset = dspos + (sigoffset / 8)
        if sigsize < 32:
            sigByteOffset += 4 - sigsize / 8
        sigBitOffset  = 0
    elif  sigtype == "STRING" or (sigtype in BYTE_TYPES  and sigsize == 8):
        # byte aligned data
        sigAccess = 1
        sigByteOffset = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in HALFWORD_TYPES and sigsize == 16:
        # 16 bit aligned data 
        sigAccess = 2
        sigByteOffset = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in  FULLWORD_TYPES and sigsize == 32:
        # 32 bit aligned data 
        sigAccess = 4
        sigByteOffset = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in LONGWORD_TYPES and sigsize == 64:
        # 64 bit aligned data 
        sigAccess = 8
        sigByteOffset = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    else: # COD, BITFIELD, BOOL, DIS, (U)BNR, (U)BCD
        # compute smallest containing access
        startbyte = dspos + (((sigoffset/32 + 1) * 4) - ((sigoffset % 32) + sigsize - 1) / 8 - 1)
        endbyte   = dspos + (((sigoffset/32 + 1) * 4) - (sigoffset % 32) / 8 - 1)
        numbytes     = endbyte - startbyte + 1
        sigAccess = {1: 4, 2: 4, 3: 4, 4: 4, 5: 8, 6: 8, 7:8, 8: 8}.get(numbytes)
        while sigAccess < 8 and startbyte / sigAccess != endbyte / sigAccess:
            sigAccess *= 2

        # access byte offset should now be aligned, 
        # i.e. round down start byte to multiples of sigAccess
        sigByteOffset = (startbyte / sigAccess) * sigAccess 

        lastbyte = (sigByteOffset + sigAccess - 1)
        sigBitOffset = (lastbyte - endbyte) * 8 + sigoffset % 8

    if sigByteOffset % sigAccess != 0:
        raise Exception, "Unaligned signal access: ByteOffset=%d BitOffset=%d Access=%d" % \
            (sigByteOffset, sigBitOffset, sigAccess)
            
    return sigByteOffset, sigBitOffset, sigAccess


def computeSignalAccessCAN(sigtype, sigsize=0, sigoffset=0, dssize=0, dspos=0):
    # consistency checks
    # signal must fit in dataset
    if sigoffset + sigsize > dssize * 8:
        raise Exception, "Signal does not fit into data set or message"
    
    # dataset must fit in message
    if dssize > 8:
        raise Exception, "Illegal Data Set Size"
    
    if sigtype in FULLBYTE_TYPES and sigoffset % 8 != 0:
        raise Exception, "Signal offset not aligned to byte boundary"

    if sigtype in ONEBIT_TYPES and sigsize != 1:
        raise Exception, "Illegal signal size for type %s" % sigtype
        
    if sigtype in INTEGER_TYPES and sigsize not in (8, 16, 32, 64):
        raise Exception, "Illegal signal size for type %s" % sigtype

    if sigtype == "FLOAT" and sigsize not in (32, 64):
        raise Exception, "Illegal signal size for type %s" % sigtype
    
    if sigtype in MULTIBYTE_TYPES and sigsize % 8 != 0:
        raise Exception, "Illegal signal size for type %s" % sigtype
    
    if  sigtype in MULTIBYTE_TYPES or \
       (sigtype in BYTE_TYPES  and sigsize == 8):
        # byte aligned data
        sigAccess = 1
        sigByteOffset = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in HALFWORD_TYPES and sigsize == 16:
        # 16 bit aligned data 
        sigAccess = 2
        sigByteOffset = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in  FULLWORD_TYPES and sigsize == 32:
        # 32 bit aligned data 
        sigAccess = 4
        sigByteOffset = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    elif sigtype in LONGWORD_TYPES and sigsize == 64:
        # 64 bit aligned data 
        sigAccess = 8
        sigByteOffset = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        sigBitOffset  = 0
    else: # COD, BITFIELD, BOOL, DIS, (U)BNR, (U)BCD
        # compute smallest containing access
        startbyte = dspos + (dssize - (sigoffset + sigsize - 1) / 8 - 1)
        endbyte   = dspos + (dssize - sigoffset/8 - 1)
        numbytes  = endbyte - startbyte + 1
        sigAccess = {1: 1, 2: 2, 3: 4, 4: 4, 5: 8, 6: 8, 7:8, 8: 8}.get(numbytes)

        if sigAccess is None:
            raise Exception, "Illegal signal size for type %s" % sigtype

        while sigAccess < 8 and startbyte / sigAccess != endbyte / sigAccess:
            sigAccess *= 2

        # access byte offset should now be aligned, 
        # i.e. round down start byte to multiples of sigAccess
        sigByteOffset = (startbyte / sigAccess) * sigAccess 

        lastbyte = (sigByteOffset + sigAccess - 1)
        sigBitOffset = (lastbyte - endbyte) * 8 + sigoffset % 8

    if sigByteOffset % sigAccess != 0:
        raise Exception, "Unaligned signal access: ByteOffset=%d BitOffset=%d Access=%d" % \
            (sigByteOffset, sigBitOffset, sigAccess)
            
    return sigByteOffset, sigBitOffset, sigAccess

def computeSignalAccessA429(sigtype, sigsize=0, sigoffset=0, dssize=0, dspos=0):
    # consistency checks
    
    # dataset must fit in message
    if int(dssize)*8 != 32:
        raise Exception, "Illegal Label Size"

    # signal must fit in dataset
    if sigoffset + sigsize > 32:
        raise Exception, "Signal does not fit into label"
    
    if sigtype in FULLBYTE_TYPES and sigoffset % 8 != 0:
        raise Exception, "Signal offset not aligned to byte boundary"

    if sigtype in ONEBIT_TYPES and sigsize != 1:
        raise Exception, "Illegal signal size for type %s" % sigtype
        
    if sigtype in INTEGER_TYPES and sigsize > 21:
        raise Exception, "Illegal signal size for type %s" % sigtype

    if sigtype == "FLOAT" and sigsize > 21:
        raise Exception, "Illegal signal size for type %s" % sigtype
    
    if sigtype in MULTIBYTE_TYPES and sigsize % 8 != 0:
        raise Exception, "Illegal signal size for type %s" % sigtype

    sigByteOffset = sigoffset / 32 * 4 + dspos
    sigBitOffset  = sigoffset % 32
    sigAccess     = 4

    return sigByteOffset, sigBitOffset, sigAccess

# ---------------------------------------------------------------------------------------
# embedded test code
# ---------------------------------------------------------------------------------------

def testComputeSignalAccess():
    tc = (
          #,msgclass, sigtype  , sigsize, sigoffset,   dssize,  dspos  Expected Result
         (1, ("AFDX",   "INT"  ,   16,         32,          8,      0), ( 6,  0, 2)),
         (2, ('AFDX',   'COD'  ,   16,          8,          8,      0), ( 0,  8, 4)),
         (3, ('CAN' ,   'COD'  ,   16,         40,          8,      0), ( 0,  8, 4)),
         (4, ('CAN' ,   'COD'  ,   16,         40,          5,      0), "Exception"),
         (5, ('CAN' ,   'INT'  ,   17,          8,          4,      0), "Exception"),
         (6, ('CAN' ,   'INT'  ,   16,          8,          8,      0), "Exception"),
         (7, ('CAN' ,   'INT'  ,   16,          8,          5,      0), ( 2,  0, 2)),
         (8, ('CAN' ,   'INT'  ,   16,          8,          3,      0), ( 0,  0, 2)),
         (9, ('CAN' ,   'BOOL' ,    2,          8,          3,      0), "Exception"),
         (10,('CAN' ,   'INT'  ,   33,          8,          4,      0), "Exception"),
         (11,('CAN' ,   'INT'  ,   33,          8,          16,     0), "Exception"),
         (12,('CAN' ,   'INT'  ,   33,          8,           8,     0), "Exception"),
         (13,('CAN' ,   'INT'  ,   64,          8,           8,     0), "Exception"),
         (14,('CAN' ,   'INT'  ,   64,          0,           8,     0), ( 0,  0, 8)),
         (15,('CAN' ,   'BOOL' ,    1,          8,           3,     0), ( 0, 16, 4)),
         (16,("AFDX",   "INT"  ,    8,         39,           8,     0), "Exception"),
         (17,("AFDX",   "INT"  ,    8,         40,           8,     0), ( 6,  0, 1)),
         (18,("AFDX",   "INT"  ,   16,         40,           8,     0), "Exception"),
         (19,("AFDX",   "INT"  ,   16,         48,           8,     0), ( 4,  0, 2)),
         (20,("AFDX",   "INT"  ,   16,         56,           8,     0), "Exception"),
         (21,("AFDX",   "INT"  ,   16,          0,           8,     0), ( 2,  0, 2)),
         (22,("AFDX",   "INT"  ,   16,         16,           8,     0), ( 0,  0, 2)),
         (23,("AFDX",   "INT"  ,   24,         16,           8,     0), "Exception"),
         (24,("AFDX",   "INT"  ,   32,         16,           8,     0), "Exception"),
         (25,("AFDX",   "INT"  ,   32,          0,           8,     0), ( 0,  0, 4)),
         (26,("AFDX",   "INT"  ,   32,         32,           8,     0), ( 4,  0, 4)),
         (27,("AFDX",   "COD"  ,    5,         36,           8,     0), ( 4,  4, 4)),
         (28,("AFDX",   "COD"  ,    5,         44,           8,     0), ( 4, 12, 4)),
         (29,("AFDX",   "COD"  ,    5,         50,           8,     0), ( 4, 18, 4)),
         (30,("AFDX",   "COD"  ,    5,         62,           8,     0), ( 0, 30, 8)),
         (31,("AFDX",   "COD"  ,    5,          1,           8,     0), ( 0,  1, 4)),
         (32,("AFDX",   "FLOAT",   16,          0,           4,     0), "Exception"),
         (33,("AFDX",   "FLOAT",   32,         48,           8,     0), "Exception"),
         (34,("AFDX",   "FLOAT",   32,         32,           8,     0), ( 4,  0, 4)),
         (35,("AFDX",   "INT"  ,   24,         32,           8,     0), "Exception"),
         (36,("AFDX",   "BYTES",   24,         32,           8,     0), ( 5,  0, 1)),
         (37,("AFDX",   "COD"  ,    7,        424,         148,     8), (60,  8, 4)),
         (38,("AFDX",   "COD"  ,    7,        431,         148,     8), (60, 15, 4)),
         (39,("AFDX",   "BYTES", 4000,          0,        1020,     8), ( 8,  0, 1)),
         (40,("AFDX",   "INT"  ,    8,         48,          28,     8), (13,  0, 1)),
         (41,("AFDX",   "INT"  ,   16,         32,          28,     8), (14,  0, 2)),
         (42,("AFDX",   "INT"  ,   64,        160,          28,     8), (24,  0, 8)),
         (43,("AFDX",   "COD"  ,   35,         96,          16,     8), (16,  0, 8)),
         (44,("AFDX",   "COD"  ,   19,         32,          12,     8), (12,  0, 4)),
         (45,("AFDX",   "COD"  ,    3,          9,           8,     8), ( 8,  9, 4)),
         (46,("AFDX",   "FLOAT",   64,         32,          16,     8), ( 8,  0, 8)),
         (47,("AFDX",   "FLOAT",   64,         96,          16,     8), (16,  0, 8)),
         (48,("AFDX",   "INT"  ,    8,         24,           8,     8), ( 8,  0, 1)),
         (49,("AFDX",   "INT"  ,    8,         16,           8,     8), ( 9,  0, 1)),
         (50,("AFDX",   "INT"  ,    8,          8,           8,     8), (10,  0, 1)),
         (51,("AFDX",   "INT"  ,    8,          0,           8,     8), (11,  0, 1)),
         (52,("AFDX",   "INT"  ,    8,         32,           8,     8), (15,  0, 1)),
         (53,("AFDX",   "INT"  ,   16,          0,           4,     8), (10,  0, 2)),
         (54,("AFDX",   "INT"  ,   16,          0,           4,    12), (14,  0, 2)),
         (55,("AFDX",   "INT"  ,   16,          0,           4,    16), (18,  0, 2)),
         (56,("AFDX",   "INT"  ,   16,          0,           4,    20), (22,  0, 2)),
         (57,("AFDX",   "INT"  ,   16,          0,           4,    28), (30,  0, 2)), 
         (58,("AFDX",   "INT"  ,   32,          0,          12,     8), ( 8,  0, 4)),
         (59,("AFDX",   "FLOAT",   32,         32,          12,     8), (12,  0, 4)),
         (60,("AFDX",   "FLOAT",   32,         64,          12,     8), (16,  0, 4)),
         (61,("AFDX",   "INT"  ,   32,          0,          12,    20), (20,  0, 4)),
         (62,("AFDX",   "FLOAT",   32,         32,          12,    20), (24,  0, 4)),
         (63,("AFDX",   "FLOAT",   32,         32,          12,    20), (24,  0, 4)),
         (64,("AFDX",   "COD"  ,    3,         12,           8,     8), ( 8, 12, 4)),
         (65,("AFDX",   "COD"  ,    3,          9,           8,     8), ( 8,  9, 4)),
         (66,("AFDX",   "COD"  ,    3,          6,           8,     8), ( 8,  6, 4)),
         (67,("AFDX",   "COD"  ,    3,          3,           8,     8), ( 8,  3, 4)),
         (68,("AFDX",   "COD"  ,    3,          0,           8,     8), ( 8,  0, 4)),
         (69,("AFDX",   "COD"  ,   19,          0,          12,     8), ( 8,  0, 4)),
         (70,("AFDX",   "COD"  ,   19,         32,          12,     8), (12,  0, 4)),
         (71,("AFDX",   "COD"  ,   19,         64,          12,     8), (16,  0, 4)),
         (72,("AFDX",   "COD"  ,   19,          0,          12,    20), (20,  0, 4)),
         (73,("AFDX",   "COD"  ,   19,         64,          12,    20), (28,  0, 4)),
         (74,("AFDX",   "COD"  ,   35,         32,          16,     8), ( 8,  0, 8)),
         (75,("AFDX",   "COD"  ,   35,         96,          16,     8), (16,  0, 8)),
         (76,("AFDX",   "COD"  ,    3,          0,          28,     8), ( 8,  0, 4)),
         (77,("AFDX",   "BNR"  ,   16,         16,          28,     8), ( 8, 16, 4)),
         (78,("AFDX",   "BNR"  ,   16,         32,          28,     8), (12,  0, 4)),
         (79,("AFDX",   "BNR"  ,    8,         48,          28,     8), (12, 16, 4)),
         (80,("AFDX",   "BNR"  ,    8,         56,          28,     8), (12, 24, 4)),
         (81,("AFDX",   "COD"  ,    6,         64,          28,     8), (16,  0, 4)),
         (82,("AFDX",   "COD"  ,    8,         72,          28,     8), (16,  8, 4)),
         (83,("AFDX",   "COD"  ,   64,        160,          28,     8), (24,  0, 8)),
         (84,("AFDX",   "COD"  ,   18,        192,          28,     8), (32,  0, 4)),
         (85,("AFDX",   "BYTES"  , 64,        0,            28,     8), (8,  0, 1)),
         (86,("AFDX",   "BYTES"  , 24,        0,            28,     8), (9,  0, 1)),
         (87,("AFDX",   "BYTES"  , 24,        8,            28,     8), "Exception"),
         (88,("A429",   "BNR"   , 12,         12,            4,     0), (0, 12, 4)),

          #,msgclass, sigtype  , sigsize, sigoffset,   dssize,  dspos  Expected Result
    )

    okcount = 0
    failedcount = 0

    for x in tc:
        try:
            res = computeSignalAccess(*x[1])
            if cmp(x[2], res) != 0:
                print "Error: TC ", x[0], ": Expected: ", x[2], "Got: ", res 
                failedcount += 1
            else:
                okcount += 1
        except Exception, e:
            if x[2] != "Exception":
                print "Error: TC ", x[0], ": Expected: ", x[2], "Got: ", str(e)
                failedcount += 1
            else:
                okcount += 1
    print "OK: %d, FAILED: %d" % (okcount, failedcount)

if __name__ == "__main__":
    testComputeSignalAccess()
