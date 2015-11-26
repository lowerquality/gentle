import logging
import threading
from twisted.internet import reactor
import webbrowser
from PyQt4.QtGui import QApplication, QWidget, QPushButton

import serve
import sys

def get_open_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("",0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port

PORT = get_open_port()

# Start a thread for the web server.
webthread = threading.Thread(target=serve.serve, args=(PORT,))
webthread.start()

def open_browser():
    webbrowser.open("http://localhost:%d/" % (PORT))
    
app = QApplication(sys.argv)
w = QWidget()
w.resize(250, 150)
w.setWindowTitle('Gentle')

def quit_server():
    app.exit()

btn = QPushButton('Open in browser', w)
btn.clicked.connect(open_browser)

quitb = QPushButton('Quit', w)
quitb.clicked.connect(quit_server)
quitb.move(0,50)

w.show()

w.raise_()
w.activateWindow()
 
app.exec_()

logging.info("Waiting for server to quit.")
reactor.callFromThread(reactor.stop)
webthread.join()
