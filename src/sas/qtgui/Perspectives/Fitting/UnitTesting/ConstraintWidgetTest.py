import sys
import unittest
import numpy as np

from unittest.mock import MagicMock

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtTest import QTest

# set up import paths
import path_prepare

import sas.qtgui.Utilities.ObjectLibrary as ObjectLibrary
import sas.qtgui.Utilities.GuiUtils as GuiUtils
from sas.qtgui.Plotting.PlotterData import Data1D

# Local
from sas.qtgui.Perspectives.Fitting.ConstraintWidget import ConstraintWidget
from sas.qtgui.Perspectives.Fitting.Constraint import Constraint
from sas.qtgui.Perspectives.Fitting.FittingPerspective import FittingWindow
from sas.qtgui.Perspectives.Fitting.FittingWidget import FittingWidget

if not QtWidgets.QApplication.instance():
    app = QtWidgets.QApplication(sys.argv)

class ConstraintWidgetTest(unittest.TestCase):
    '''Test the ConstraintWidget dialog'''
    def setUp(self):
        '''Create ConstraintWidget dialog'''
        class dummy_manager(object):
            def communicator(self):
                return GuiUtils.Communicate()
            communicate = GuiUtils.Communicate()

        '''Create the perspective'''
        self.perspective = FittingWindow(dummy_manager())
        ConstraintWidget.updateSignalsFromTab = MagicMock()

        self.widget = ConstraintWidget(parent=self.perspective)

        # Example constraint object
        self.constraint1 = Constraint(parent=None, param="test", value="7.0", min="0.0", max="inf", func="M1:sld")
        self.constraint2 = Constraint(parent=None, param="poop", value="7.0", min="0.0", max="inf", func="7.0")

    def tearDown(self):
        '''Destroy the GUI'''
        self.widget.close()
        self.widget = None

    def testDefaults(self):
        '''Test the GUI in its default state'''
        self.assertIsInstance(self.widget, QtWidgets.QWidget)
        # Default title
        self.assertEqual(self.widget.windowTitle(), "Constrained and Simultaneous Fit")
        # Dicts
        self.assertIsInstance(self.widget.available_constraints, dict)
        self.assertIsInstance(self.widget.available_tabs, dict)
        # TableWidgets
        self.assertEqual(self.widget.tblTabList.columnCount(), 4)
        self.assertEqual(self.widget.tblConstraints.columnCount(), 1)
        # Data accept 
        self.assertFalse(self.widget.acceptsData())
        # By default, the constraint table is disabled
        self.assertFalse(self.widget.tblConstraints.isEnabled())

    def testOnFitTypeChange(self):
        ''' test the single/batch fit switch '''
        self.widget.initializeFitList = MagicMock()
        # Assure current type is Single
        self.assertEqual(self.widget.currentType, "FitPage")
        # click on "batch"
        QTest.mouseClick(self.widget.btnBatch, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        # See what the current type is now
        self.assertEqual(self.widget.currentType, "BatchPage")
        # See if the list is getting initialized
        self.assertTrue(self.widget.initializeFitList.called)
        # Go back to single fit
        QTest.mouseClick(self.widget.btnSingle, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()
        # See what the current type is now
        self.assertEqual(self.widget.currentType, "FitPage")

    def testGetTabsForFit(self):
        ''' Test the fitting tab list '''
        self.assertEqual(self.widget.getTabsForFit(), [])
        # add one tab
        self.widget.tabs_for_fitting = {"foo": True}
        self.assertEqual(self.widget.getTabsForFit(), ['foo'])
        # add two tabs
        self.widget.tabs_for_fitting = {"foo": True, "bar": True}
        self.assertEqual(self.widget.getTabsForFit(), ['foo', 'bar'])
        # disable one tab
        self.widget.tabs_for_fitting = {"foo": False, "bar": True}
        self.assertEqual(self.widget.getTabsForFit(), ['bar'])

    def testIsTabImportable(self):
        ''' tab checks for consistency '''
        test_tab = MagicMock(spec=FittingWidget)
        test_tab.data_is_loaded = False
        test_tab.kernel_module = None
        test_tab.data = self.constraint1
        ObjectLibrary.getObject = MagicMock(return_value=test_tab)

        self.assertFalse(self.widget.isTabImportable(None))
        self.assertFalse(self.widget.isTabImportable("BatchTab1"))
        self.widget.currentType = "Batch"
        self.assertFalse(self.widget.isTabImportable("BatchTab"))
        self.widget.currentType = "test"
        self.assertFalse(self.widget.isTabImportable("test_tab"))
        test_tab.data_is_loaded = True
        self.assertTrue(self.widget.isTabImportable("test_tab"))

    def testOnTabCellEdit(self):
        ''' test what happens on monicker edit '''
        # Mock a tab
        test_tab = MagicMock(spec=FittingWidget)
        test_tab.data_is_loaded = False
        test_tab.kernel_module = MagicMock()
        test_tab.kernel_module.id = "foo"
        test_tab.kernel_module.name = "bar"
        test_tab.data.filename = "baz"
        ObjectLibrary.getObject = MagicMock(return_value=test_tab)
        self.widget.updateFitLine("test_tab")

        # disable the tab
        self.widget.tblTabList.item(0, 0).setCheckState(0)
        self.assertEqual(self.widget.tabs_for_fitting["test_tab"], False)
        self.assertFalse(self.widget.cmdFit.isEnabled())
        # enable the tab
        self.widget.tblTabList.item(0, 0).setCheckState(2)
        self.assertEqual(self.widget.tabs_for_fitting["test_tab"], True)
        self.assertTrue(self.widget.cmdFit.isEnabled())

    def testUpdateFitLine(self):
        ''' See if the fit table row can be updated '''
        pass

    def testUpdateFitList(self):
        ''' see if the fit table can be updated '''
        pass

    def testUpdateConstraintList(self):
        ''' see if the constraint table can be updated '''
        pass

    def testFindNameErrorInConstraint(self):
        ''' test if we get get a faulty constraint'''
        constraint = "M1.scale = M2.scal + M2.background"
        name_error = "M2"
        expression = "P1.scale = M2.scal + M2.background"
        name = self.widget.findNameErrorInConstraint(constraint, expression, name_error)
        self.assertEqual("M2.scal", name)
