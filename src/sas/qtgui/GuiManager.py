import sys
import os
import subprocess
import logging
import json
import webbrowser

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QtWebKit

from twisted.internet import reactor
# General SAS imports

from sas.sasgui.guiframe.data_manager import DataManager
from sas.sasgui.guiframe.proxy import Connection
from sas.qtgui.SasviewLogger import XStream
import sas.qtgui.LocalConfig as LocalConfig
import sas.qtgui.GuiUtils as GuiUtils
from sas.qtgui.UI.AcknowledgementsUI import Ui_Acknowledgements
from sas.qtgui.AboutBox import AboutBox
from sas.qtgui.IPythonWidget import IPythonWidget
from sas.qtgui.WelcomePanel import WelcomePanel

from sas.qtgui.SldPanel import SldPanel
from sas.qtgui.DensityPanel import DensityPanel

# Perspectives
from sas.qtgui.Perspectives.Invariant.InvariantPerspective import InvariantWindow
from sas.qtgui.DataExplorer import DataExplorerWindow

class Acknowledgements(QtGui.QDialog, Ui_Acknowledgements):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)

class GuiManager(object):
    """
    Main SasView window functionality
    """
    ## TODO: CHANGE FOR SHIPPED PATH IN RELEASE
    HELP_DIRECTORY_LOCATION = "docs/sphinx-docs/build/html"

    def __init__(self, mainWindow=None, reactor=None, parent=None):
        """
        """
        self._workspace = mainWindow
        self._parent = parent

        # Reactor passed from above
        self.setReactor(reactor)

        # Add signal callbacks
        self.addCallbacks()

        # Create the data manager
        # TODO: pull out all required methods from DataManager and reimplement
        self._data_manager = DataManager()

        # Create action triggers
        self.addTriggers()

        # Populate menus with dynamic data
        #
        # Analysis/Perspectives - potentially
        # Window/current windows
        #
        # Widgets
        #
        self.addWidgets()

        # Fork off logging messages to the Log Window
        XStream.stdout().messageWritten.connect(self.listWidget.insertPlainText)
        XStream.stderr().messageWritten.connect(self.listWidget.insertPlainText)

        # Log the start of the session
        logging.info(" --- SasView session started ---")
        # Log the python version
        logging.info("Python: %s" % sys.version)

        # Set up the status bar
        self.statusBarSetup()

        # Show the Welcome panel
        self.welcomePanel = WelcomePanel()
        self._workspace.workspace.addWindow(self.welcomePanel)

        # Current help file
        self._helpView = QtWebKit.QWebView()
        # Needs URL like path, so no path.join() here
        self._helpLocation = self.HELP_DIRECTORY_LOCATION + "/index.html"

        # Current tutorial location
        self._tutorialLocation = os.path.abspath(os.path.join(self.HELP_DIRECTORY_LOCATION,
                                              "_downloads",
                                              "Tutorial.pdf"))

        #==========================================================
        # TEMP PROTOTYPE
        # Add InvariantWindow to the workspace.
        self.invariantWidget = InvariantWindow(self)
        self._workspace.workspace.addWindow(self.invariantWidget)

        # Default perspective
        self._current_perspective = self.invariantWidget

    def addWidgets(self):
        """
        Populate the main window with widgets

        TODO: overwrite close() on Log and DR widgets so they can be hidden/shown
        on request
        """
        # Add FileDialog widget as docked
        self.filesWidget = DataExplorerWindow(self._parent, self, manager=self._data_manager)

        self.dockedFilesWidget = QtGui.QDockWidget("Data Explorer", self._workspace)
        self.dockedFilesWidget.setWidget(self.filesWidget)
        # Disable maximize/minimize and close buttons
        self.dockedFilesWidget.setFeatures(QtGui.QDockWidget.NoDockWidgetFeatures)
        self._workspace.addDockWidget(QtCore.Qt.LeftDockWidgetArea,
                                      self.dockedFilesWidget)

        # Add the console window as another docked widget
        self.logDockWidget = QtGui.QDockWidget("Log Explorer", self._workspace)
        self.logDockWidget.setObjectName("LogDockWidget")
        self.listWidget = QtGui.QTextBrowser()
        self.logDockWidget.setWidget(self.listWidget)
        self._workspace.addDockWidget(QtCore.Qt.BottomDockWidgetArea,
                                      self.logDockWidget)

        # Add other, minor widgets
        self.ackWidget = Acknowledgements()
        self.aboutWidget = AboutBox()

        # Add calculators - floating for usability
        self.SLDCalculator = SldPanel(self)
        self.DVCalculator = DensityPanel(self)

    def statusBarSetup(self):
        """
        Define the status bar.
        | <message label> .... | Progress Bar |

        Progress bar invisible until explicitly shown
        """
        self.progress = QtGui.QProgressBar()
        self._workspace.statusbar.setSizeGripEnabled(False)

        self.statusLabel = QtGui.QLabel()
        self.statusLabel.setText("Welcome to SasView")
        self._workspace.statusbar.addPermanentWidget(self.statusLabel, 1)
        self._workspace.statusbar.addPermanentWidget(self.progress, stretch=0)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setVisible(False)

    def fileRead(self, data):
        """
        Callback for fileDataReceivedSignal
        """
        pass

    def workspace(self):
        """
        Accessor for the main window workspace
        """
        return self._workspace.workspace

    def updatePerspective(self, data):
        """
        """
        assert isinstance(data, list)
        if self._current_perspective is not None:
            self._current_perspective.setData(data.values())
        else:
            msg = "No perspective is currently active."
            logging.info(msg)


    def communicator(self):
        """
        """
        return self.communicate

    def reactor(self):
        """
        """
        return self._reactor

    def setReactor(self, reactor):
        """
        """
        self._reactor = reactor

    def perspective(self):
        """
        """
        return self._current_perspective

    def updateProgressBar(self, value):
        """
        Update progress bar with the required value (0-100)
        """
        assert -1 <= value <= 100
        if value == -1:
            self.progress.setVisible(False)
            return
        if not self.progress.isVisible():
            self.progress.setTextVisible(True)
            self.progress.setVisible(True)

        self.progress.setValue(value)

    def updateStatusBar(self, text):
        """
        """
        #self._workspace.statusbar.showMessage(text)
        self.statusLabel.setText(text)

    def createGuiData(self, item, p_file=None):
        """
        Access the Data1D -> plottable Data1D conversion
        """
        return self._data_manager.create_gui_data(item, p_file)

    def setData(self, data):
        """
        Sends data to current perspective
        """
        if self._current_perspective is not None:
            self._current_perspective.setData(data.values())
        else:
            msg = "Guiframe does not have a current perspective"
            logging.info(msg)

    def quitApplication(self):
        """
        Close the reactor and exit nicely.
        """
        # Display confirmation messagebox
        quit_msg = "Are you sure you want to exit the application?"
        reply = QtGui.QMessageBox.question(
            self._parent,
            'Information',
            quit_msg,
            QtGui.QMessageBox.Yes,
            QtGui.QMessageBox.No)

        # Exit if yes
        if reply == QtGui.QMessageBox.Yes:
            reactor.callFromThread(reactor.stop)
            return True

        return False

    def checkUpdate(self):
        """
        Check with the deployment server whether a new version
        of the application is available.
        A thread is started for the connecting with the server. The thread calls
        a call-back method when the current version number has been obtained.
        """
        version_info = {"version": "0.0.0"}
        c = Connection(LocalConfig.__update_URL__, LocalConfig.UPDATE_TIMEOUT)
        response = c.connect()
        if response is not None:
            try:
                content = response.read().strip()
                logging.info("Connected to www.sasview.org. Latest version: %s"
                             % (content))
                version_info = json.loads(content)
            except ValueError, ex:
                logging.info("Failed to connect to www.sasview.org:", ex)
        self.processVersion(version_info)

    def processVersion(self, version_info):
        """
        Call-back method for the process of checking for updates.
        This methods is called by a VersionThread object once the current
        version number has been obtained. If the check is being done in the
        background, the user will not be notified unless there's an update.

        :param version: version string
        """
        try:
            version = version_info["version"]
            if version == "0.0.0":
                msg = "Could not connect to the application server."
                msg += " Please try again later."
                #self.SetStatusText(msg)
                self.communicate.statusBarUpdateSignal.emit(msg)

            elif cmp(version, LocalConfig.__version__) > 0:
                msg = "Version %s is available! " % str(version)
                if "download_url" in version_info:
                    webbrowser.open(version_info["download_url"])
                else:
                    webbrowser.open(LocalConfig.__download_page__)
                self.communicate.statusBarUpdateSignal.emit(msg)
            else:
                msg = "You have the latest version"
                msg += " of %s" % str(LocalConfig.__appname__)
                self.communicate.statusBarUpdateSignal.emit(msg)
        except:
            msg = "guiframe: could not get latest application"
            msg += " version number\n  %s" % sys.exc_value
            logging.error(msg)
            msg = "Could not connect to the application server."
            msg += " Please try again later."
            self.communicate.statusBarUpdateSignal.emit(msg)

    def addCallbacks(self):
        """
        Method defining all signal connections for the gui manager
        """
        self.communicate = GuiUtils.Communicate()
        self.communicate.fileDataReceivedSignal.connect(self.fileRead)
        self.communicate.statusBarUpdateSignal.connect(self.updateStatusBar)
        self.communicate.updatePerspectiveWithDataSignal.connect(self.updatePerspective)
        self.communicate.progressBarUpdateSignal.connect(self.updateProgressBar)

    def addTriggers(self):
        """
        Trigger definitions for all menu/toolbar actions.
        """
        # File
        self._workspace.actionLoadData.triggered.connect(self.actionLoadData)
        self._workspace.actionLoad_Data_Folder.triggered.connect(self.actionLoad_Data_Folder)
        self._workspace.actionOpen_Project.triggered.connect(self.actionOpen_Project)
        self._workspace.actionOpen_Analysis.triggered.connect(self.actionOpen_Analysis)
        self._workspace.actionSave.triggered.connect(self.actionSave)
        self._workspace.actionSave_Analysis.triggered.connect(self.actionSave_Analysis)
        self._workspace.actionQuit.triggered.connect(self.actionQuit)
        # Edit
        self._workspace.actionUndo.triggered.connect(self.actionUndo)
        self._workspace.actionRedo.triggered.connect(self.actionRedo)
        self._workspace.actionCopy.triggered.connect(self.actionCopy)
        self._workspace.actionPaste.triggered.connect(self.actionPaste)
        self._workspace.actionReport.triggered.connect(self.actionReport)
        self._workspace.actionReset.triggered.connect(self.actionReset)
        self._workspace.actionExcel.triggered.connect(self.actionExcel)
        self._workspace.actionLatex.triggered.connect(self.actionLatex)

        # View
        self._workspace.actionShow_Grid_Window.triggered.connect(self.actionShow_Grid_Window)
        self._workspace.actionHide_Toolbar.triggered.connect(self.actionHide_Toolbar)
        self._workspace.actionStartup_Settings.triggered.connect(self.actionStartup_Settings)
        self._workspace.actionCategry_Manager.triggered.connect(self.actionCategry_Manager)
        # Tools
        self._workspace.actionData_Operation.triggered.connect(self.actionData_Operation)
        self._workspace.actionSLD_Calculator.triggered.connect(self.actionSLD_Calculator)
        self._workspace.actionDensity_Volume_Calculator.triggered.connect(self.actionDensity_Volume_Calculator)
        self._workspace.actionSlit_Size_Calculator.triggered.connect(self.actionSlit_Size_Calculator)
        self._workspace.actionSAS_Resolution_Estimator.triggered.connect(self.actionSAS_Resolution_Estimator)
        self._workspace.actionGeneric_Scattering_Calculator.triggered.connect(self.actionGeneric_Scattering_Calculator)
        self._workspace.actionPython_Shell_Editor.triggered.connect(self.actionPython_Shell_Editor)
        self._workspace.actionImage_Viewer.triggered.connect(self.actionImage_Viewer)
        # Fitting
        self._workspace.actionNew_Fit_Page.triggered.connect(self.actionNew_Fit_Page)
        self._workspace.actionConstrained_Fit.triggered.connect(self.actionConstrained_Fit)
        self._workspace.actionCombine_Batch_Fit.triggered.connect(self.actionCombine_Batch_Fit)
        self._workspace.actionFit_Options.triggered.connect(self.actionFit_Options)
        self._workspace.actionFit_Results.triggered.connect(self.actionFit_Results)
        self._workspace.actionChain_Fitting.triggered.connect(self.actionChain_Fitting)
        self._workspace.actionEdit_Custom_Model.triggered.connect(self.actionEdit_Custom_Model)
        # Window
        self._workspace.actionCascade.triggered.connect(self.actionCascade)
        self._workspace.actionTile.triggered.connect(self.actionTile)
        self._workspace.actionArrange_Icons.triggered.connect(self.actionArrange_Icons)
        self._workspace.actionNext.triggered.connect(self.actionNext)
        self._workspace.actionPrevious.triggered.connect(self.actionPrevious)
        # Analysis
        self._workspace.actionFitting.triggered.connect(self.actionFitting)
        self._workspace.actionInversion.triggered.connect(self.actionInversion)
        self._workspace.actionInvariant.triggered.connect(self.actionInvariant)
        # Help
        self._workspace.actionDocumentation.triggered.connect(self.actionDocumentation)
        self._workspace.actionTutorial.triggered.connect(self.actionTutorial)
        self._workspace.actionAcknowledge.triggered.connect(self.actionAcknowledge)
        self._workspace.actionAbout.triggered.connect(self.actionAbout)
        self._workspace.actionCheck_for_update.triggered.connect(self.actionCheck_for_update)

    #============ FILE =================
    def actionLoadData(self):
        """
        Menu File/Load Data File(s)
        """
        self.filesWidget.loadFile()

    def actionLoad_Data_Folder(self):
        """
        Menu File/Load Data Folder
        """
        self.filesWidget.loadFolder()

    def actionOpen_Project(self):
        """
        Menu Open Project
        """
        self.filesWidget.loadProject()

    def actionOpen_Analysis(self):
        """
        """
        print("actionOpen_Analysis TRIGGERED")
        pass

    def actionSave(self):
        """
        Menu Save Project
        """
        self.filesWidget.saveProject()

    def actionSave_Analysis(self):
        """
        """
        print("actionSave_Analysis TRIGGERED")

        pass

    def actionQuit(self):
        """
        Close the reactor, exit the application.
        """
        self.quitApplication()

    #============ EDIT =================
    def actionUndo(self):
        """
        """
        print("actionUndo TRIGGERED")
        pass

    def actionRedo(self):
        """
        """
        print("actionRedo TRIGGERED")
        pass

    def actionCopy(self):
        """
        """
        print("actionCopy TRIGGERED")
        pass

    def actionPaste(self):
        """
        """
        print("actionPaste TRIGGERED")
        pass

    def actionReport(self):
        """
        """
        print("actionReport TRIGGERED")
        pass

    def actionReset(self):
        """
        """
        logging.warning(" *** actionOpen_Analysis logging *******")
        print("actionReset print TRIGGERED")
        sys.stderr.write("STDERR - TRIGGERED")
        pass

    def actionExcel(self):
        """
        """
        print("actionExcel TRIGGERED")
        pass

    def actionLatex(self):
        """
        """
        print("actionLatex TRIGGERED")
        pass

    #============ VIEW =================
    def actionShow_Grid_Window(self):
        """
        """
        print("actionShow_Grid_Window TRIGGERED")
        pass

    def actionHide_Toolbar(self):
        """
        Toggle toolbar vsibility
        """
        if self._workspace.toolBar.isVisible():
            self._workspace.actionHide_Toolbar.setText("Show Toolbar")
            self._workspace.toolBar.setVisible(False)
        else:
            self._workspace.actionHide_Toolbar.setText("Hide Toolbar")
            self._workspace.toolBar.setVisible(True)
        pass

    def actionStartup_Settings(self):
        """
        """
        print("actionStartup_Settings TRIGGERED")
        pass

    def actionCategry_Manager(self):
        """
        """
        print("actionCategry_Manager TRIGGERED")
        pass

    #============ TOOLS =================
    def actionData_Operation(self):
        """
        """
        print("actionData_Operation TRIGGERED")
        pass

    def actionSLD_Calculator(self):
        """
        """
        self.SLDCalculator.show()

    def actionDensity_Volume_Calculator(self):
        """
        """
        self.DVCalculator.show()

    def actionSlit_Size_Calculator(self):
        """
        """
        print("actionSlit_Size_Calculator TRIGGERED")
        pass

    def actionSAS_Resolution_Estimator(self):
        """
        """
        print("actionSAS_Resolution_Estimator TRIGGERED")
        pass

    def actionGeneric_Scattering_Calculator(self):
        """
        """
        print("actionGeneric_Scattering_Calculator TRIGGERED")
        pass

    def actionPython_Shell_Editor(self):
        """
        Display the Jupyter console as a docked widget.
        """
        terminal = IPythonWidget()

        # Add the console window as another docked widget
        self.ipDockWidget = QtGui.QDockWidget("IPython", self._workspace)
        self.ipDockWidget.setObjectName("IPythonDockWidget")
        self.ipDockWidget.setWidget(terminal)
        self._workspace.addDockWidget(QtCore.Qt.RightDockWidgetArea,
                                      self.ipDockWidget)

    def actionImage_Viewer(self):
        """
        """
        print("actionImage_Viewer TRIGGERED")
        pass

    #============ FITTING =================
    def actionNew_Fit_Page(self):
        """
        """
        print("actionNew_Fit_Page TRIGGERED")
        pass

    def actionConstrained_Fit(self):
        """
        """
        print("actionConstrained_Fit TRIGGERED")
        pass

    def actionCombine_Batch_Fit(self):
        """
        """
        print("actionCombine_Batch_Fit TRIGGERED")
        pass

    def actionFit_Options(self):
        """
        """
        print("actionFit_Options TRIGGERED")
        pass

    def actionFit_Results(self):
        """
        """
        print("actionFit_Results TRIGGERED")
        pass

    def actionChain_Fitting(self):
        """
        """
        print("actionChain_Fitting TRIGGERED")
        pass

    def actionEdit_Custom_Model(self):
        """
        """
        print("actionEdit_Custom_Model TRIGGERED")
        pass

    #============ ANALYSIS =================
    def actionFitting(self):
        """
        """
        print("actionFitting TRIGGERED")
        pass

    def actionInversion(self):
        """
        """
        print("actionInversion TRIGGERED")
        pass

    def actionInvariant(self):
        """
        """
        print("actionInvariant TRIGGERED")
        pass

    #============ WINDOW =================
    def actionCascade(self):
        """
        Arranges all the child windows in a cascade pattern.
        """
        self._workspace.workspace.cascade()

    def actionTile(self):
        """
        Tile workspace windows
        """
        self._workspace.workspace.tile()

    def actionArrange_Icons(self):
        """
        Arranges all iconified windows at the bottom of the workspace
        """
        self._workspace.workspace.arrangeIcons()

    def actionNext(self):
        """
        Gives the input focus to the next window in the list of child windows.
        """
        self._workspace.workspace.activateNextWindow()

    def actionPrevious(self):
        """
        Gives the input focus to the previous window in the list of child windows.
        """
        self._workspace.workspace.activatePreviousWindow()

    #============ HELP =================
    def actionDocumentation(self):
        """
        Display the documentation

        TODO: use QNetworkAccessManager to assure _helpLocation is valid
        """
        self._helpView.load(QtCore.QUrl(self._helpLocation))
        self._helpView.show()

    def actionTutorial(self):
        """
        Open the tutorial PDF file with default PDF renderer
        """
        # Not terribly safe here. Shell injection warning.
        # isfile() helps but this probably needs a better solution.
        if os.path.isfile(self._tutorialLocation):
            result = subprocess.Popen([self._tutorialLocation], shell=True)

    def actionAcknowledge(self):
        """
        Open the Acknowledgements widget
        """
        self.ackWidget.show()

    def actionAbout(self):
        """
        Open the About box
        """
        # Update the about box with current version and stuff

        # TODO: proper sizing
        self.aboutWidget.show()

    def actionCheck_for_update(self):
        """
        Menu Help/Check for Update
        """
        self.checkUpdate()

        pass
