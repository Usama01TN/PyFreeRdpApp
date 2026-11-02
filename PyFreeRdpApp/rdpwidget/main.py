# coding=utf-8
"""
RDPWidget demo entry point: python main.py
"""
from ManyQt.QtWidgets import QApplication
from sys import path, argv, exit
from os.path import dirname

if dirname(__file__) not in path:
    path.append(dirname(__file__))
if dirname(dirname(dirname(__file__))) not in path:
    path.append(dirname(dirname(dirname(__file__))))

try:
    from .rdpwidget import qtExec, appIcon
    from .mainwindow import MainWindow
except:
    from rdpwidget import qtExec, appIcon
    from mainwindow import MainWindow

if __name__ == u'__main__':
    a = QApplication(argv)  # type: QApplication
    a.setWindowIcon(appIcon())
    w = MainWindow()  # type: MainWindow
    w.show()
    exit(qtExec(a))
