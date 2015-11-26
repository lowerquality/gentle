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

def open_browser():
    webbrowser.open("http://localhost:%d" % (PORT))
    
# Start a thread for the web server.
webthread = threading.Thread(target=serve.serve, args=(PORT,))
webthread.start()

app = QApplication(sys.argv)
w = QWidget()
w.resize(250, 150)
w.setWindowTitle('Gentle')

btn = QPushButton('Open in browser', w)
btn.clicked.connect(open_browser)

quitb = QPushButton('Quit', w)
quitb.clicked.connect(app.quit)
quitb.move(0,50)

w.show()

app.exec_()

reactor.callFromThread(reactor.stop)
logging.info("Waiting for server to quit.")
webthread.join()
