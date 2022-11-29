'''
Created on 06.09.2014

@author: dk

global constants, to be synchronized with C implementation

'''
from bunch import Bunch

ALERTDB_MAGIC_NUMBER = 0xC919FDAF

MIN_ALERT_ID       = 1
MAX_ALERT_ID       = 2000
MAX_ALERT_PRIORITY = 2000

ALERT_PARAMETER_BASE_ADDRESS = 4096


SynopticPages = Bunch(
    encode = {
        "none":            0,       # No synoptic Page
        "status":          1,       # Avionics Page
        "air":             2,       # Air Conditioning System
        "door":            3,       # Doors and Slides
        "elec":            4,       # Electric System
        "fltctrl":         5,       # Flight Controls
        "fuel":            6,       # Fuel System
        "hyd":             7,       # Hydraulic System
        "cbic":            8,       # Circuit Breaker App
    },
    
    normalize = {
        "":                "none",
        "tbd":             "none",
        "none":            "none",
        "no":              "none",
        "n/a":             "none",
        "status":          "status",
        "air":             "air",
        "door":            "door",
        "elec":            "elec",
        "fltctrl":         "fltctrl",
        "fuel":            "fuel",
        "hyd":             "hyd",
        "cbic":            "cbic",
        'avionics':        "status",
     }
  )

FlightPhases = Bunch(
    encode = {
        "powerup":          1,       #Power Up
        "taxiout":          2,       #Taxi-out
        "to1":              3,       #Take Off 1"
        "to2":              4,       #Take Off 2"
        "to3":              5,       #Take Off 3-ground"
        "to3climb":         6,       #Take Off 3-climb"
        "cruise":           7,       #Cruise
        "approach":         8,       #Approach
        "landing":          9,       #Landing
        "taxiin":           10,      #TaxiIn
        "shutdown":         11,      #Shutdown
    },

    normalize = {
        "powerup":          "powerup",
        "power up":         "powerup",
        "power-up":         "powerup",
        "taxiout":          "taxiout",
        "taxi-out":         "taxiout",
        "taxi out":         "taxiout",
        "to1":              "to1",
        "to2":              "to2",
        "to3":              "to3",
        "cruise":           "cruise",
        "approach":         "approach",
        "landing":          "landing",
        "taxiin":           "taxiin",
        "taxi-in":          "taxiin",
        "taxi in":          "taxiin",
        "shutdown":         "shutdown",
    }
)


AuralAlertClass = Bunch(
    encode = {
        "none":                         0, # No acoustic signal
        "singleplay":                   1, # Once
        "continuous":                   2, # Repeated until reason disappear or cancel
        "contnocancel":                 3, # Repeat until reason disappear, no cancel
    },
    normalize = {
        "":                             "none",
        "n/a":                          "none",
        "none":                         "none",
        "tbd":                          "none",
        "singleplay":                   "singleplay",
        "continuous":                   "continuous",
        "continuouscancellable":        "continuous",
        "continuous cancellable":       "continuous",
        "continuousnon-cancellable":    "contnocancel",
        "continuous non-cancellable":   "contnocancel",
        "contnocancel":                 "contnocancel",
    }
)


OtherDisplayEffects = Bunch(
    encode = {
        "none":         0,       # None
        "terrain":      1,       # Display Terrain Map Layer
        "windshear":    2,       # Display Windshear Map Layer
        "collaps":      3,       # Disable Menus and Collapse Dropdowns
    },

    normalize = {
        "":                 'none',
        "none":             'none',
        "tbd":              "none",
        "n/a":              "none",
        "terrain":          "terrain",
        "windshear":        "windshear",
        "collaps":          "collaps",
    }
)

AlertTypes = Bunch(
    encode = {
        "tc":              0,       #Time Critial Message
        "cas":             1,       #CAS Message
        "cpa":             2,       #CPA only Alert
    },
    normalize = {
        "tc":              "tc",
        "cas":             "cas",
        "cpa":             "cpa",
        "cpaonly":         "cpa",
        "cpa only":        "cpa"
    }
)

AlertClasses = Bunch(
    encode = {
        "warning":         0,       # Warning message
        "caution":         1,       # Caution message
        "advisory":        2,       # Advisory message
        "status":          3,       # Status message
        "none":            4,       # No message, CPA Effect Only"
    },
    normalize = {
        "warning":         "warning",
        "caution":         "caution",
        "advisory":        "advisory",
        "status":          "status",
        "n/a":             "none",
        "none":            "none",
    }
)


# opcodes
OPCODE_CONST    = 0
OPCODE_PARAM    = 1

OPCODES = {
    '.prev':    2,
    '.valid':   5,
    '.invalid': 6,
    '.if' :     7,
    '.select':  8,

    '.and':     9,
    '.or':      10,
    '.xor':     11,
    '.not':     12,

    '.iadd':    13,
    '.isub':    14,
    '.imul':    15,
    '.idiv':    16,
    '.fadd':    17,
    '.fsub':    18,
    '.fmul':    19,
    '.fdiv':    20,

    '.eq':      21,

    '.igt':     22,
    '.ige':     23,
    '.ilt':     24,
    '.ile':     25,
    
    '.fgt':     26,
    '.fge':     27,
    '.flt':     28,
    '.fle':     29,
    

    '.tdr':     30,
    '.active':  31,
    '.tdf':     32
}

BOOLCONST = {
    '.false':   0,
    '.true':    1,
}
