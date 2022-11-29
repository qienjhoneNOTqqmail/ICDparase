
import  wx
import subprocess
import threading
import Queue

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
    
        wx.Panel.__init__(self, parent, -1,name='XML_ICD_Import')
        
            
        labelICDPath = wx.StaticText(self, -1, "ICD Path", (10,10))
        labelICDPath.SetHelpText("Input the ICD file path for tool")

        
        self.icdpathtext = wx.TextCtrl(self, -1, frame.genConfigData['xmlICDpath'], pos=(150,10), size=(500,-1))
        self.icdpathtext.SetHelpText("Here's some help text for path")
        
        labelOutdir = wx.StaticText(self, -1, "Output Dir", (10,40))
        labelOutdir.SetHelpText("Output diectory the ICD file path for tool")

        
        self.outputtext = wx.TextCtrl(self, -1, frame.genConfigData['outputdir'], pos=(150,40), size=(500,-1))
        self.outputtext.SetHelpText("Here's some help text for path")
        
        labelhflist = wx.StaticText(self, -1, "Hosted Functions", (10,70))
        labelhflist.SetHelpText("Output diectory the ICD file path for tool")

        
        self.hflisttext = wx.TextCtrl(self, -1, frame.genConfigData['hflist'], pos=(150,70), size=(500,100), style=wx.TE_MULTILINE)
        self.hflisttext.SetHelpText("Here's some help text for path")
        
        b = wx.Button(self, -1, "Generate Excel ICD", (10,200))
        self.Bind(wx.EVT_BUTTON, self.OnButton, b)

        self.PYTHON = "C:\Python27\python" 
#iomGenExcel.py --merge --loglevel=ERROR --output=%MERGED_ICD% %FUN_LIST% -- "%ICD_PATH%"
    def OnButton(self, evt):
        self.log.WriteText(self.PYTHON + ' ' + 'D:\C919Tools\C919_ICD_Processor\XmlImport\icdimport_DS_LRU.py' + ' -c  --loglevel=INFO --outdir=' + self.outputtext.GetValue()+' --hfname='+self.hflisttext.GetValue()+ ' --workdir='+ self.icdpathtext.GetValue())
        try:
            self.compile = subprocess.Popen(
                               self.PYTHON + ' ' + 'D:\C919Tools\C919_ICD_Processor\XmlImport\icdimport_DS_LRU.py' + ' -c --loglevel=INFO --outdir=' + self.outputtext.GetValue()+' --hfname='+self.hflisttext.GetValue()+ ' --workdir='+ self.icdpathtext.GetValue(),
                               shell=False,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
            self.log.WriteText( "Created process with PID %d" % self.compile.pid)
            #print self.compile.stdout.readline()
            '''
            returncode = self.compile.poll()
            while returncode is None:
                    line = self.compile.stdout.readline()
                    returncode = self.compile.poll()
                    line = line.strip()
                    self.log.WriteText(line)
            print returncode
            '''
            self.StdErrThread = threading.Thread(target=self.frame.readStdErr,args=(self.compile,))
            self.StdErrThread.daemon = True
            self.StdErrThread.start()

            self.frame.waitStdErr()
        except Exception as e:
            print e
            if hasattr(e, "child_traceback"):
                print e.child_traceback
    '''
    def readStdErr(self):
        try:
            self.log.WriteText('coming in readstderr')
            #s=self.compile.stderr.read()
            #self.frame.StdErrQueue.put(s)       
            while self.compile.poll() is None:
                    line = self.compile.stdout.readline()
                    line = line.strip()
                    #self.log.WriteText(line)
                    self.frame.StdErrQueue.put(line)

            line = self.compile.stdout.read()
            self.frame.StdErrQueue.put(line)
            #self.log.WriteText(line)    
        except:
            pass
        
    def waitStdErr(self):
        try:
            #self.log.WriteText('coming in waitstderr')
            s = self.frame.StdErrQueue.get_nowait()
            if s:
                self.log.WriteText("ERROR: %s" % s)
        except Queue.Empty:
            pass
            
        wx.FutureCall(100, self.waitStdErr)
    '''
#---------------------------------------------------------------------------


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

