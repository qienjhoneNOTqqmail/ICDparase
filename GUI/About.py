import sys

import wx                  # This module uses the new wx namespace
import wx.html
import wx.lib.wxpTag

#---------------------------------------------------------------------------

class MyAboutBox(wx.Dialog):
    text = '''
<html>
<body bgcolor="#AC76DE">
<center><table bgcolor="#458154" width="100%%" cellspacing="0"
cellpadding="0" border="1">
<tr>
    <td align="center">
    <h1>ICD Processor Tool %s</h1>
    (%s)<br>
    Running on Python %s<br>
    </td>
</tr>
</table>

<p><b>ICD Processor Tool</b> is a ICD Processing Tool that used to gnenrate the 
Excel ICD from XML file and generate the ADS2 configuration files for SSDL,SDIB....</p>

<p><b>ICD Processor Tool</b> is brought to you by <b>Zheng Chao</b> and<br>
<b>Total Control Software,</b> Copyright (c) 1997-2006.</p>

<p>
<font size="-1">Please see <i>license.txt</i> for licensing information.</font>
</p>

<p><wxp module="wx" class="Button">
    <param name="label" value="Okay">
    <param name="id"    value="ID_OK">
</wxp></p>
</center>
</body>
</html>
'''
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, 'About the ICD Processor Tool',)
        html = wx.html.HtmlWindow(self, -1, size=(420, -1))
        if "gtk2" in wx.PlatformInfo:
            html.SetStandardFonts()
        py_version = sys.version.split()[0]
        html.SetPage(self.text % ("1.0",  #Tool Version
                                  "Windows 7",
                                  "2.7"
                                  ))
        btn = html.FindWindowById(wx.ID_OK)
        ir = html.GetInternalRepresentation()
        html.SetSize( (ir.GetWidth()+25, ir.GetHeight()+25) )
        self.SetClientSize(html.GetSize())
        self.CentreOnParent(wx.BOTH)

#---------------------------------------------------------------------------



if __name__ == '__main__':
    app = wx.PySimpleApp()
    dlg = MyAboutBox(None)
    dlg.ShowModal()
    dlg.Destroy()
    app.MainLoop()

