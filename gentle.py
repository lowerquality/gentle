import logging
import threading
from twisted.internet import reactor
import webbrowser
import wx

from gentle.paths import get_resource, get_datadir
import serve

class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(200,100))

        panel = wx.Panel(self)
        self.browse = wx.Button(panel, label="Open in web browser", pos=(0, 0))
        self.Bind(wx.EVT_BUTTON, self.OnBrowseClick, self.browse)

        self.quitb = wx.Button(panel, label="Quit", pos=(0, 30))
        self.Bind(wx.EVT_BUTTON, self.OnClose, self.quitb)

        self.CreateStatusBar()

        # Setting up the menu.
        filemenu= wx.Menu()

        menuItem = filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        filemenu.AppendSeparator()
        m_close = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        
        self.Bind(wx.EVT_MENU, self.OnClose, m_close)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuItem)
    
        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File")
        self.SetMenuBar(menuBar)
        self.Show(True)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        logging.info('about to start a web server...')

        # Start a thread for the web server.
        self.webthread = threading.Thread(target=serve.serve)
        self.webthread.start()

    def OnAbout(self, event):
        logging.info("clicked on ABOUT")

        # Create a little modal dialog box
        dlg = wx.MessageDialog(self, "Robust yet lenient forced aligner", "Gentle", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnClose(self, event):
        logging.info("Quitting gentle.")
        reactor.callFromThread(reactor.stop)
        logging.info("Waiting for server to quit.")
        self.webthread.join()
        self.Destroy()

    def OnBrowseClick(self, event):
        webbrowser.open("http://localhost:8765")

app = wx.App(False)
frame = MainWindow(None, "Gentle")
app.MainLoop()
