
import  wx
import subprocess
import threading
#---------------------------------------------------------------------------

class MyFrame(wx.Frame):
    def __init__(
            self, parent, ID, title, pos=wx.DefaultPosition,
            size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE
            ):

        wx.Frame.__init__(self, parent, ID, title, pos, size, style)
        panel = wx.Panel(self, -1)

        button = wx.Button(panel, 1003, "Close Me")
        button.SetPosition((15, 15))
        self.Bind(wx.EVT_BUTTON, self.OnCloseMe, button)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)


    def OnCloseMe(self, event):
        self.Close(True)

    def OnCloseWindow(self, event):
        self.Destroy()

#---------------------------------------------------------------------------

class TestPanel(wx.Panel):
    def __init__(self, parent, log, frame):
        self.log = log
        self.frame = frame
        wx.Panel.__init__(self, parent, -1, name='SSDL_CFG_Gen')
        
            
        labelICDPath = wx.StaticText(self, -1, "Excel ICD Path", (10,10))
        labelICDPath.SetHelpText("Input the ICD file path for tool")

        
        self.icdpathtext = wx.TextCtrl(self, -1, frame.genConfigData['excelpath'], pos=(150,10), size=(500,-1))
        self.icdpathtext.SetHelpText("Here's some help text for path")
        
        labelOutdir = wx.StaticText(self, -1, "Ads2 CFG Output Dir", (10,40))
        labelOutdir.SetHelpText("Output diectory the ICD file path for tool")

        
        self.outputtext = wx.TextCtrl(self, -1, frame.genConfigData['ads2outdir'], pos=(150,40), size=(500,-1))
        self.outputtext.SetHelpText("Here's some help text for path")
        
        labelhflist = wx.StaticText(self, -1, "Hosted Functions", (10,70))
        labelhflist.SetHelpText("Output diectory the ICD file path for tool")

        
        self.hflisttext = wx.TextCtrl(self, -1, frame.genConfigData['hfnames'], pos=(150,70), size=(500,100), style=wx.TE_MULTILINE)
        self.hflisttext.SetHelpText("Here's some help text for path")
        
        labeldevmap = wx.StaticText(self, -1, "Device Map", (10,200))
        labeldevmap.SetHelpText("Output diectory the ICD file path for tool")

        
        self.devmaptext = wx.TextCtrl(self, -1, frame.genConfigData['devicemap'], pos=(150,200), size=(500,-1))
        self.devmaptext.SetHelpText("Here's some help text for path")
        
        modeList = ['Simulation', 'Stimulation']

   
        rb_mode = wx.RadioBox(
                self, -1, "Mode", (10,230), wx.DefaultSize,
                modeList, 2, wx.RA_SPECIFY_COLS
                )
        
        self.Bind(wx.EVT_RADIOBOX, self.EvtModeRadioBox, rb_mode)
        
        self.smode = 'sim'
        
        b = wx.Button(self, -1, "Generate ADS2 CFG", (10,300))
        self.Bind(wx.EVT_BUTTON, self.OnButton, b)

        self.PYTHON = "C:\Python27\python" 
#iomGenExcel.py --merge --loglevel=ERROR --output=%MERGED_ICD% %FUN_LIST% -- "%ICD_PATH%"
    def OnButton(self, evt):
        self.log.WriteText(self.PYTHON + ' ' + 'D:\C919Tools\C919_ICD_Processor\Ads2Gen\ADS2CONFIG.py' + ' -c -m --loglevel=INFO --inputtype=Excel --outdir=' + self.outputtext.GetValue()+ ' --mode=' + self.smode+ ' --devmap='+ self.devmaptext.GetValue()+ ' --hfname=' +self.hflisttext.GetValue()+ ' --workdir='+ self.icdpathtext.GetValue())
        try:
            self.compile = subprocess.Popen(
                               self.PYTHON + ' ' + 'D:\C919Tools\C919_ICD_Processor\Ads2Gen\ADS2CONFIG.py' + ' -c -m --loglevel=INFO --inputtype=Excel --outdir=' + self.outputtext.GetValue()+ ' --mode=' + self.smode+ ' --devmap='+ self.devmaptext.GetValue()+ ' --hfname=' +self.hflisttext.GetValue()+ ' --workdir='+ self.icdpathtext.GetValue(),
                               shell=False,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
            print "Created process with PID %d" % self.compile.pid

            self.StdErrThread = threading.Thread(target=self.frame.readStdErr,args=(self.compile,))
            self.StdErrThread.daemon = True
            self.StdErrThread.start()
            self.frame.waitStdErr()

        except Exception as e:
            print e
            if hasattr(e, "child_traceback"):
                print e.child_traceback
    
    def EvtModeRadioBox(self,evt):
        mode = ['sim','stim']
        self.log.WriteText('EvtRadioBox: %d\n' % evt.GetInt())
        self.smode=mode[evt.GetInt()]
        
#--------------------------------------------------------------------------


def runTest(frame, nb, log):
    win = TestPanel(nb, log, frame)
    return win


#---------------------------------------------------------------------------


overview = """\
A Frame is a window whose size and position can (usually) be changed by 
the user. It usually has thick borders and a title bar, and can optionally 
contain a menu bar, toolbar and status bar. A frame can contain any window 
that is not a Frame or Dialog. It is one of the most fundamental of the 
wxWindows components. 

A Frame that has a status bar and toolbar created via the 
<code>CreateStatusBar</code> / <code>CreateToolBar</code> functions manages 
these windows, and adjusts the value returned by <code>GetClientSize</code>
to reflect the remaining size available to application windows.

By itself, a Frame is not too useful, but with the addition of Panels and
other child objects, it encompasses the framework around which most user
interfaces are constructed.

If you plan on using Sizers and auto-layout features, be aware that the Frame
class lacks the ability to handle these features unless it contains a Panel.
The Panel has all the necessary functionality to both control the size of
child components, and also communicate that information in a useful way to
the Frame itself.
"""


if __name__ == '__main__':
    import sys,os
    import run
    run.main(['', os.path.basename(sys.argv[0])] + sys.argv[1:])

