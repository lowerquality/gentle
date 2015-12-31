import logging
import threading
from twisted.internet import reactor
import webbrowser
from PyQt4.QtGui import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout
from gentle.__version__ import __version__

import serve
import sys

def get_open_port(desired=0):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("",desired))
    except socket.error:
        return get_open_port(0)
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port

PORT = get_open_port(8765)

# Start a thread for the web server.
webthread = threading.Thread(target=serve.serve, args=(PORT,))
webthread.start()

def open_browser():
    webbrowser.open("http://localhost:%d/" % (PORT))

def open_about():
    webbrowser.open("https://lowerquality.com/gentle")
    
app = QApplication(sys.argv)
w = QWidget()
w.resize(250, 150)
w.setWindowTitle('Gentle')

def quit_server():
    app.exit()

layout = QVBoxLayout()
w.setLayout(layout)

txt = QLabel('''Gentle v%s

A robust yet lenient forced-aligner built on Kaldi.''' % (__version__))
layout.addWidget(txt)

btn = QPushButton('Open in browser')
btn.setStyleSheet("font-weight: bold;")
layout.addWidget(btn)
btn.clicked.connect(open_browser)

abt = QPushButton('About Gentle')
layout.addWidget(abt)
abt.clicked.connect(open_about)

quitb = QPushButton('Quit')
layout.addWidget(quitb)
quitb.clicked.connect(quit_server)

w.show()

w.raise_()
w.activateWindow()
 
app.exec_()

logging.info("Waiting for server to quit.")
reactor.callFromThread(reactor.stop)
webthread.join()
