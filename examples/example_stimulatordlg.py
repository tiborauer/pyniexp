import sys
from PyQt5.QtWidgets import QApplication
from pyniexp.stimulatordlg import Stimulator

app = QApplication(sys.argv)
app.setApplicationName('Stimulator')
app.setOrganizationName('PyNIExp')
app.setApplicationVersion('1.0')

stimdlg = Stimulator()

app.exec_()