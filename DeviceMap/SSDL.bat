echo off
rem --- to configure ---
set ICD_PATH=D:\BP4.2formal
set OUT_DIR_ROOT=C:\Data\BP4.2
set PYTHONPATH=C:\Data\PE\1000_C919DS\Dev\CDS_SW\09_Tools\head\IOMGen\src
rem --- to configure ---

echo Generate ADS2 CFG for %ICD_PATH%

echo BUILD ADS2 CFG for SSDL CFG L5.1
rem --- our UUTs ---
set FUN_LIST=FDAS_L1 FDAS_L3 FDAS_R3 HF_IDUCENTER HF_IDULEFTINBOARD HF_IDULEFTOUTBOARD HF_IDURIGHTINBOARD HF_IDURIGHTOUTBOARD IMA_DM_L4 IMA_DM_L5 IMA_DM_R4 SYNOPTICMENUAPP_L SYNOPTICMENUAPP_R SYNOPTICPAGEAPP_L SYNOPTICPAGEAPP_R VIRTUALCONTROLAPP_L VIRTUALCONTROLAPP_R HF_MCMW1 HF_EVS HF_ISIS HF_CCD1 HF_CCD2 HF_DCP1 HF_DCP2 HF_MKB1 HF_MKB2 HF_RCP HF_DIM_CTRL_PWR
set OUT_DIR=%OUT_DIR_ROOT%\SSDL5.1
set MERGED_ICD=%OUT_DIR%\DS_SSDL_ICD.xlsx
set DEVMAP=D:\DeviceMap\SSDL_DEVMAP-4.2-5.1.xlsx

rem below command used to generate separate HF ICD excel file at current folder.
rem C:\Python27\python iomGenExcel.py  --loglevel=TRACE %FUN_LIST% -- "%ICD_PATH%"

rem below two command to generate all HF ICD into one excel file.
C:\Python27\python iomGenExcel.py --merge --loglevel=TRACE --output=%MERGED_ICD% %FUN_LIST% -- "%ICD_PATH%"
C:\Python27\python ads2GenConfig.py --deviceMap=%DEVMAP% --splitiom=True --outdir=%OUT_DIR% --target=SSDL --simmode=stim --msgmode=signals %MERGED_ICD%
