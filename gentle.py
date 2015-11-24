import threading
from twisted.internet import reactor
import wx

from gentle.paths import get_resource, get_datadir
import serve

class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(200,100))

        self.control = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.CreateStatusBar()

        # Setting up the menu.
        filemenu= wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard IDs provided by wxWidgets.
        menuItem = filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        #menuItem = filemenu.Append(102, "&About"," Information about this program")        
        filemenu.AppendSeparator()
        m_close = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        #filemenu.Append(103,"E&xit"," Terminate the program")
        
        self.Bind(wx.EVT_MENU, self.OnClose, m_close)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuItem)
    
        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        self.Show(True)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        print 'about to start a web server...'

        # Start a thread for the web server.
        self.webthread = threading.Thread(target=serve.serve)
        self.webthread.start()

    def OnAbout(self, event):
        print "HI!"

    def OnClose(self, event):
        print "Quitting gentle."
        reactor.callFromThread(reactor.stop)
        print "Waiting for server to quit."
        self.webthread.join()
        print "Done!"
        self.Destroy()

# app = wx.App(False)
# frame = MainWindow(None, "Gentle")
#frame.Show(True)
# app.MainLoop()

serve.serve(installSignalHandlers=1)
