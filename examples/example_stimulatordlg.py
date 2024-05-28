import sys
from PyQt6.QtWidgets import QApplication
from pyniexp.stimulator import StimulatorApp

app = QApplication(sys.argv)
app.setApplicationName('Stimulator')
app.setOrganizationName('PyNIExp')
app.setApplicationVersion('1.0')

stimdlg = StimulatorApp()

app.exec()