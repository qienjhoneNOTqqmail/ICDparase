XmlImport目录：从XML ICD生成Excel
AdsGen目录：从Excel生成iom/cvt/cmp配置文件
DeviceMap目录：定义外系统由哪块板卡发送，即板卡资源分配，同时包含429,825，离散量资源分配


使用
1、生成Excel
进入XmlImport目录，修改Gen-SSDL-Excel-4.3.bat文件中的outdir\hfname\workdir属性值，outdir是生成excel存放路径，hfname列出需要生成excel文件的LRU实例名称，workdir是ICD文件路径

如果icdimport_DS_LRU.py文件存放路径变更，请变更。

2、生成ADS2配置文件
进入AdsGen，可根据需要生成SDIB或SSDL的配置。根据实际情况修改Gen-SDIB-XXX.bat或Gen-SSDL-XXX.bat文件中的outdir（配置文件输出目录），hfname(需要配的LRU实例名称)， workdir(第1步生成的Excel文件路径）,最终会在outdir目录下生成对应的ADS2配置文件