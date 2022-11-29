import dsb_scriptrun
s=dsb_scriptrun.PySim("crc")
s.add_output("AFDX-01::RAW-TX3")
s.add_output("AFDX-01::RAW-TX2-FS")
s.add_output("AFDX-01::RAW-TX2-CRC")
s.test_start(mode="foreground")
s.outputs["AFDX-01::RAW-TX2-FS"] = 0x03
s.outputs["AFDX-01::RAW-TX2-CRC"] = 0xFFFFFFFF
s.sync()
s.outputs["AFDX-01::RAW-TX3"] = range(256) + 4*[0]
s.sync()
s.loginfo("CHECK VALID CRC VAL")

