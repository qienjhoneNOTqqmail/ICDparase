@echo off
if "%*" == ""     ( goto :usage  )
if "%1" == "help" ( goto :usage  )
if "%1" == "?" ( goto :usage  )
if "%1" == "-h" ( goto :usage  )
if "%1" == "/h" ( goto :usage  )
if "%1" == "/?" ( goto :usage  )
if "%1" == "--help" ( goto :usage  )
rem ---------------------------------------------------------------------------------------

rem set PYLIBDIR=%~d0%~p0../lib/python
echo off
set ICD_PATH=%1
set OUT_DIR_ROOT=%2

echo Generate ADS2 L3 CFG for %ICD_PATH%

set MERGED_ICD=%OUT_DIR_ROOT%\DS_SDIBL3.X_ICD.xlsx
set FUN_LIST=HF_IDUCENTER HF_IDULEFTINBOARD HF_IDULEFTOUTBOARD HF_IDURIGHTINBOARD HF_IDURIGHTOUTBOARD
set OUT_DIR=%OUT_DIR_ROOT%\SDIBL3.X
C:\Python\Python27\python iomGenExcel.py --merge --loglevel=ERROR --output=%MERGED_ICD% %FUN_LIST% -- "%ICD_PATH%"
C:\Python\Python27\python ads2GenConfig.py --outdir %OUT_DIR% --target SWTESTS --prefix SDIB --simmode stim --msgmode signals %MERGED_ICD% 
set MERGED_ICD=%OUT_DIR_ROOT%\DS_SDIBL3.2_ICD.xlsx
set FUN_LIST=FDAS_L1 FDAS_L3 FDAS_R3 IMA_DM_L4 IMA_DM_L5 IMA_DM_R4 SYNOPTICMENUAPP_L SYNOPTICMENUAPP_R SYNOPTICPAGEAPP_L SYNOPTICPAGEAPP_R HF_MCMW1
set OUT_DIR=%OUT_DIR_ROOT%\SDIBL3.2
C:\Python\Python27\python iomGenExcel.py --merge --loglevel=ERROR --output=%MERGED_ICD% %FUN_LIST% -- "%ICD_PATH%"
C:\Python\Python27\python ads2GenConfig.py --outdir %OUT_DIR% --target SWTESTS --prefix SDIB --simmode stim --msgmode signals %MERGED_ICD% 


goto :eof

:usage 
echo ADS2 IO Config Generation Tools
echo Generation of ADS2 Test System Configuration for Integration Level 3.X(3.1, 3.4, 3.3) and 3.2
echo Usage: genAdsCfgL3 XML_ICD_PATH OUT_DIR_ROOT
echo Where: XML_ICD_PATH is the path of the XML ICDs of a specific BP
echo        OUT_DIR_ROOT is the name of a directory where all generated files shall be saved
echo Example: genAdsCfgL3  C:\PATH_TO_XML_ICD_DIR C:\PATH_TO_OUTPUTDIR
