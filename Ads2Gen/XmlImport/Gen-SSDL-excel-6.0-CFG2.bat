echo "Generate DS excel"
C:\Python27\python D:\ENV\Ads2\C919_ICD_Processor\XmlImport\icdimport_DS_LRU.py -c   --loglevel=INFO --outdir=D:\ENV\Ads2\ICD_output\BP6.0-CFG2\Excel --hfname=FDAS_L1,FDAS_L3,FDAS_R3,IMA_DM_L4,IMA_DM_L5,IMA_DM_R4,SYNOPTICMENUAPP_L,SYNOPTICMENUAPP_R,SYNOPTICPAGEAPP_L,SYNOPTICPAGEAPP_R,HF_IDULEFTINBOARD,HF_IDULEFTOUTBOARD,HF_IDUCENTER,HF_IDURIGHTINBOARD,HF_IDURIGHTOUTBOARD,HF_CCD1,HF_CCD2,HF_DCP1,HF_DCP2,HF_EVS,HF_HCU1,HF_HCU2,HF_HPU1,HF_HPU2,HF_ISIS,HF_MCMW1,HsF_MCMW2,HF_MKB1,HF_MKB2,HF_RCP,HF_RLS1,HF_RLS2,ECL_OPS_APP_L,ECL_OPS_APP_R,VIRTUALCONTROLAPP_L,VIRTUALCONTROLAPP_R,CNSMENUAPP_L,CNSMENUAPP_R,INFOAPP_L,INFOAPP_R --workdir="D:\ENV\Ads2\ICD_XML_6.0-CFG2\Model System Elements"

echo "Generate FMS excel"
C:\Python27\python D:\ENV\Ads2\C919_ICD_Processor\XmlImport\icdimport_DS_LRU.py -c   --loglevel=INFO --outdir=D:\ENV\Ads2\ICD_output\BP6.0-CFG2\Excel --hfname=APP_FMS_TUNE_2,APP_FMS_TUNE_1,APP_FMS_CORE_2,APP_FMS_CORE_1,APP_FMS_NAV_1,APP_FMS_NAV_2,APP_FMS_DATALINK_1,APP_FMS_DATALINK_2,APP_FMS_GUIDANCE_1,APP_FMS_GUIDANCE_2 --workdir="D:\ENV\Ads2\ICD_XML_6.0-CFG2\Model System Elements"

echo "Generate RGW01,02,04,05 input system excel"
C:\Python27\python D:\ENV\Ads2\C919_ICD_Processor\XmlImport\icdimport_DS_LRU.py -c   --loglevel=INFO --outdir=D:\ENV\Ads2\ICD_output\BP6.0-CFG2\Excel --hfname=HF_RIU_1,HF_TCP_3,HF_EMPC_EPS,HF_CARGO_FIRECNTRLPANEL,HF_ENGINEAPU_FIRECNTRLPANEL,HF_FUELOVERHEADPANEL,HF_L_ID,HF_R_ID,HF_L_NAISWITCH,HF_R_NAISWITCH,HF_WHCA,HF_GAGEASSY,HF_MCMW1,HF_MCMW2,HF_LGCU2,HF_AIR_COND_CPA,HF_DIM_CTRL_PWR,HF_ICE_CABIN_LT_CPA,HF_INSTR_CPA_L,HF_INSTR_CPA_R,HF_EMERGENCYLIGHTINGSW,HF_ACU,HF_FUELCONTROLSW_R --workdir="D:\ENV\Ads2\ICD_XML_6.0-CFG2\Model System Elements"

echo "Generate ECL excel"
C:\Python27\python D:\ENV\Ads2\C919_ICD_Processor\XmlImport\icdimport_DS_LRU.py -c   --loglevel=INFO --outdir=D:\ENV\Ads2\ICD_output\BP6.0-CFG2\Excel\ECL --hfname=ECL_OPS_APP_L,ECL_OPS_APP_R --workdir="D:\ENV\Ads2\ICD_XML_6.0-CFG2\Model System Elements"

echo "Generate EDC excel"
C:\Python27\python D:\ENV\Ads2\C919_ICD_Processor\XmlImport\icdimport_DS_LRU.py -c   --loglevel=INFO --outdir=D:\ENV\Ads2\ICD_output\BP6.0-CFG2\Excel\EDC --hfname=HF_EPS_DATA_CONVERT_A,HF_EPS_DATA_CONVERT_B --workdir="D:\ENV\Ads2\ICD_XML_6.0-CFG2\Model System Elements"

echo "Generate GDC excel"
C:\Python27\python D:\ENV\Ads2\C919_ICD_Processor\XmlImport\icdimport_DS_LRU.py -c   --loglevel=INFO --outdir=D:\ENV\Ads2\ICD_output\BP6.0-CFG2\Excel\GDC --hfname=GDC_L,GDC_R --workdir="D:\ENV\Ads2\ICD_XML_6.0-CFG2\Model System Elements"