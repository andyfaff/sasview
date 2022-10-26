from typing import NamedTuple

from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal



from sas.qtgui.Utilities.UI.OrientationViewerControllerUI import Ui_OrientationViewierControllerUI

class Orientation(NamedTuple):
    """ Data sent when updating the plot"""
    theta: int
    phi: int
    psi: int
    dtheta: int
    dphi: int
    dpsi: int

class OrientationViewierController(QtWidgets.QDialog, Ui_OrientationViewierControllerUI):

    """ Widget that controls the orientation viewer"""

    valueEdited = pyqtSignal(Orientation, name='valueEdited')

    def __init__(self, parent=None):
        super().__init__()

        self.setupUi(self)

        # All sliders emit the same signal - the angular coordinates in degrees
        self.thetaSlider.valueChanged.connect(self.onAngleChange)
        self.phiSlider.valueChanged.connect(self.onAngleChange)
        self.psiSlider.valueChanged.connect(self.onAngleChange)
        self.deltaTheta.valueChanged.connect(self.onAngleChange)
        self.deltaPhi.valueChanged.connect(self.onAngleChange)
        self.deltaPsi.valueChanged.connect(self.onAngleChange)

    def onAngleChange(self):
        theta = self.thetaSlider.value()
        phi = self.phiSlider.value()
        psi = self.psiSlider.value()

        dtheta = self.deltaTheta.value()
        dphi = self.deltaPhi.value()
        dpsi = self.deltaPsi.value()

        self.valueEdited.emit(Orientation(theta, phi, psi, dtheta, dphi, dpsi))



def main():
    """ Show a demo of the slider """
    app = QtWidgets.QApplication([])

    mainWindow = QtWidgets.QMainWindow()
    viewer = OrientationViewierController(mainWindow)

    mainWindow.setCentralWidget(viewer)

    mainWindow.show()

    mainWindow.resize(700, 100)
    app.exec_()


if __name__ == "__main__":
    main()