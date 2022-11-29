'''
Created on 30.11.2014

@author: dk

Common constants for IO Manager binary configuration
To be harmonized with IO Manager C Header File
'''

class IOM:
    MAX_VALUE_UTINT32    = 0xFFFFFFFF
    MAX_VALUE_FLOAT32    = 3.4028234E38   # 0x7F7F FFFF
    MIN_VALUE_FLOAT32    = 1.17549435E-38
    MAX_VALUE_SINT32     = 2147483647
    MIN_VALUE_SINT32     = -2147483648
    

    SIGINTYPE_UINT32     = 0
    SIGINTYPE_SIG64      = 1
    SIGINTYPE_OPAQUE     = 2
    SIGINTYPE_BOOL       = 3
    SIGINTYPE_CODED32    = 4
    SIGINTYPE_CODED64    = 5
    SIGINTYPE_SIG32_I2F  = 6
    SIGINTYPE_SIG32_F2I  = 7
    SIGINTYPE_BNR        = 8
    SIGINTYPE_UBNR       = 9
    SIGINTYPE_BCD        = 10
    SIGINTYPE_UBCD       = 11
    SIGINTYPE_BNR_F2I    = 12
    SIGINTYPE_UBNR_F2I   = 13
    SIGINTYPE_BCD_F2I    = 14
    SIGINTYPE_UBCD_F2I   = 15
    SIGINTYPE_INT8       = 16
    SIGINTYPE_INT16      = 17
    SIGINTYPE_UINT8      = 18
    SIGINTYPE_UINT16     = 19
    SIGINTYPE_INT8_ADD   = 20
    SIGINTYPE_STRINGS    = 21                # not implemented yet
    SIGINTYPE_FLOATS     = 22
    SIGINTYPE_DOUBLE     = 23
    SIGINTYPE_INT32      = 24
    SIGINTYPE_UNFRESH    = 25
    SIGINTYPE_BOOL_8BIT  = 26
    SIGINTYPE_CODED8     = 27

    SIGOUTTYPE_SIG8               = 0        # Output Mapping Type: 8bits word
    SIGOUTTYPE_SIG16              = 1        # Output Mapping Type: 16bits word
    SIGOUTTYPE_SIG32              = 2        # Output Mapping Type: 32bits word
    SIGOUTTYPE_SIG64              = 3        # Output Mapping Type: 64bits word
    SIGOUTTYPE_MULTIPLE_BYTES     = 4        # Output Mapping Type: Multiple Bytes
    SIGOUTTYPE_A664_BOOLEAN       = 5        # Output Mapping Type: A664 Boolean
    SIGOUTTYPE_BITFIELD32         = 6        # Output Mapping Type: A664 Boolean
    SIGOUTTYPE_A429BNR_FLOAT      = 7        # A429 BNR conversion from Float
    SIGOUTTYPE_A429UBNR_FLOAT     = 8        # A429 UBNR conversion from Float
    SIGOUTTYPE_A429BNR_INTEGER    = 9        # A429 BNR conversion from Integer
    SIGOUTTYPE_A429UBNR_INTEGER   = 10       # A429 UBNR conversion from Integer
    SIGOUTTYPE_A429BCD_FLOAT      = 11       # A429 BCD conversion from Float
    SIGOUTTYPE_A429BCD_INTEGER    = 12       # A429 BCD conversion from Integer
    SIGOUTTYPE_VALIDITY_STATUS    = 13       # Special function Output validity status (CAN only)

    CONDTYPE_FRESHNESS      = 0
    CONDTYPE_A664FS         = 1
    CONDTYPE_A429SSM_BNR    = 2
    CONDTYPE_A429SSM_BCD    = 3
    CONDTYPE_A429SSM_DIS    = 4
    CONDTYPE_VALIDITY_PARAM = 5
    CONDTYPE_RANGE_INT      = 6
    CONDTYPE_RANGE_UINT     = 7
    CONDTYPE_RANGE_FLOAT    = 8
    CONDTYPE_RANGE_FLOATBNR = 9
    CONDTYPE_INVALID        = 10

    A664_MESSAGE_PADDING                 = 64
    A664_MESSAGE_HEADER_LENGTH           = 64
    A664_MESSAGE_HEADER_FRESHNESS_OFFSET = 0

    TRANSPORT_A664 = 0
    TRANSPORT_A429 = 1
    TRANSPORT_A825 = 2

    PARAMETER_VALUE_SIZE = 4

    IOM_CONFIG_HEADER_SIZE               = 28 * 4 # 28 32 bit words
    
    A429_MESSAGE_LENGTH                  = 8      # 32 bit validity and 32 bit A429 Label data
    A429_FRESHNESS_OFFSET                = 8      # 32 bit validity 
    A429_DATA_OFFSET                     = 4      # 32 bit A429 Label data
    A429_NOF_SDI                         = 4      # Two bit field for Source Destination Identifier

    SET_HEADER_SIZE                      = (6*4) # 6 32 bit words
    LIC_PARAM_SOURCE_SIZE                = (20*4) # 20 32 bit words
    SET_MAX_SOURCES                      = 12
    SET_SOURCE_LIC_PARAMETER             = 1
    SET_SOURCE_HEALTH_SCORE              = 2
    SET_SOURCE_OBJECT_VALID              = 3
                                        
    SET_SOURCE_HEALTH_NO_LOCK            = 0
    SET_SOURCE_HEALTH_LOCK               = 1
    SET_SOURCE_HEALTH_LOCK_PERMANENT     = 2
                                        
    SET_SOURCE_PARAM_VALUE_ANY           = 0
    SET_SOURCE_PARAM_VALUE_EXACT         = 1
