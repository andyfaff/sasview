"""
   This software was developed by the University of Tennessee as part of the
Distributed Data Analysis of Neutron Scattering Experiments (DANSE)
project funded by the US National Science Foundation. 

See the license text in license.txt

copyright 2008, 2009, University of Tennessee
"""

import wx
import sys
#import os

#from sans.guicomm.events import StatusEvent  
from sans.calculator.kiessig_calculator import KiessigThicknessCalculator 
from calculator_widgets import OutputTextCtrl
from calculator_widgets import InputTextCtrl

_BOX_WIDTH = 77
#Slit length panel size 
if sys.platform.count("win32") > 0:
    PANEL_WIDTH = 500
    PANEL_HEIGHT = 210
    FONT_VARIANT = 0
else:
    PANEL_WIDTH = 560
    PANEL_HEIGHT = 230
    FONT_VARIANT = 1
 
class KiessigThicknessCalculatorPanel(wx.Panel):
    """
    Provides the Kiessig thickness calculator GUI.
    """
    ## Internal nickname for the window, used by the AUI manager
    window_name = "Kiessig Thickness Calculator"
    ## Name to appear on the window title bar
    window_caption = "Kiessig Thickness Calculator"
    ## Flag to tell the AUI manager to put this panel in the center pane
    CENTER_PANE = True
    
    def __init__(self, parent, *args, **kwds):
        wx.Panel.__init__(self, parent, *args, **kwds)
        #Font size 
        self.SetWindowVariant(variant=FONT_VARIANT)  
        # Object that receive status event
        self.parent = parent
        self.kiessig = KiessigThicknessCalculator()
        #layout attribute
        self.hint_sizer = None
        self._do_layout()
       
    def _define_structure(self):
        """
        Define the main sizers building to build this application.
        """
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.box_source = wx.StaticBox(self, -1,
                                str("Kiessig Thickness Calculator"))
        self.boxsizer_source = wx.StaticBoxSizer(self.box_source,
                                                    wx.VERTICAL)
        self.dq_name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.thickness_size_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hint_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
       
    def _layout_dq_name(self):
        """
        Fill the sizer containing dq name
        """
        # get the default dq
        dq_value = str(self.kiessig.get_deltaq())
        dq_unit_txt = wx.StaticText(self, -1, '[1/A]')
        dq_name_txt = wx.StaticText(self, -1, 
                                'Kiessig Fringe Width (Delta Q): ')
        self.dq_name_tcl = InputTextCtrl(self, -1, 
                                         size=(_BOX_WIDTH,-1))
        dq_hint = "Type the Kiessig Fringe Width (Delta Q)"
        self.dq_name_tcl.SetValue(dq_value)
        self.dq_name_tcl.SetToolTipString(dq_hint)
        #control that triggers importing data
        id = wx.NewId()
        self.compute_button = wx.Button(self, id, "Compute")
        hint_on_compute = "Compute the diameter/thickness in the real space."
        self.compute_button.SetToolTipString(hint_on_compute)
        self.Bind(wx.EVT_BUTTON, self.on_compute, id=id)
        self.dq_name_sizer.AddMany([(dq_name_txt, 0, wx.LEFT, 15),
                                    (self.dq_name_tcl, 0, wx.LEFT, 15),
                                    (dq_unit_txt,0, wx.LEFT, 10),
                                (self.compute_button, 0, wx.LEFT, 30)])
    def _layout_thickness_size(self):
        """
        Fill the sizer containing thickness information
        """
        thick_unit = '['+self.kiessig.get_thickness_unit() +']'
        thickness_size_txt = wx.StaticText(self, -1, 
                                           'Thickness (or Diameter): ')
        self.thickness_size_tcl = OutputTextCtrl(self, -1, 
                                                 size=(_BOX_WIDTH,-1))
        thickness_size_hint = " Estimated Size in Real Space"
        self.thickness_size_tcl.SetToolTipString(thickness_size_hint)
        thickness_size_unit_txt = wx.StaticText(self, -1, thick_unit)
        
        self.thickness_size_sizer.AddMany([(thickness_size_txt, 0, wx.LEFT, 15),
                                    (self.thickness_size_tcl, 0, wx.LEFT, 15),
                                    (thickness_size_unit_txt, 0, wx.LEFT, 10)])
    
    def _layout_hint(self):
        """
        Fill the sizer containing hint 
        """
        hint_msg = "This tool is to approximately estimate "
        hint_msg += "the thickness of a layer"
        hint_msg += " or the diameter of particles\n "
        hint_msg += "from the Kiessig fringe width in SANS/NR data."
        hint_msg += ""
        self.hint_txt = wx.StaticText(self, -1, hint_msg)
        self.hint_sizer.AddMany([(self.hint_txt, 0, wx.LEFT, 15)])
    
    def _layout_button(self):  
        """
        Do the layout for the button widgets
        """ 
        self.bt_close = wx.Button(self, wx.ID_CANCEL,'Close')
        self.bt_close.Bind(wx.EVT_BUTTON, self.on_close)
        self.bt_close.SetToolTipString("Close this window.")
        self.button_sizer.AddMany([(self.bt_close, 0, wx.LEFT, 390)])
        
    def _do_layout(self):
        """
            Draw window content
        """
        self._define_structure()
        self._layout_dq_name()
        self._layout_thickness_size()
        self._layout_hint()
        self._layout_button()
        self.boxsizer_source.AddMany([(self.dq_name_sizer, 0,
                                          wx.EXPAND|wx.TOP|wx.BOTTOM, 5),
                                   (self.thickness_size_sizer, 0,
                                     wx.EXPAND|wx.TOP|wx.BOTTOM, 5),
                                     (self.hint_sizer, 0,
                                     wx.EXPAND|wx.TOP|wx.BOTTOM, 5)])
        self.main_sizer.AddMany([(self.boxsizer_source, 0, wx.ALL, 10),
                                  (self.button_sizer, 0,
                                    wx.EXPAND|wx.TOP|wx.BOTTOM, 5)])
        self.SetSizer(self.main_sizer)
        self.SetAutoLayout(True)

    def on_close(self, event):
        """
        close the window containing this panel
        """
        self.parent.Close()
        if event is not None:
            event.Skip()
        
    def on_compute(self, event):
        """
        Execute the computation of thickness
        """
        # skip for another event
        if event != None:
            event.Skip()
        dq = self.dq_name_tcl.GetValue()
        self.kiessig.set_deltaq(dq)
        # calculate the thickness 
        output = self.kiessig.compute_thickness()
        thickness = self.format_number(output)
        # set tcl
        self.thickness_size_tcl.SetValue(str(thickness))
        
    def format_number(self, value=None):
        """
        Return a float in a standardized, human-readable formatted string 
        """
        try: 
            value = float(value)
        except:
            output = None
            return output

        output = "%-7.4g" % value
        return output.lstrip().rstrip()   
     
class KiessigWindow(wx.Frame):
    def __init__(self, parent=None, title="Kiessig Thickness Calculator",
                  size=(PANEL_WIDTH,PANEL_HEIGHT), *args, **kwds):
        kwds['title'] = title
        kwds['size'] = size
        wx.Frame.__init__(self, parent, *args, **kwds)
        self.parent = parent
        self.panel = KiessigThicknessCalculatorPanel(parent=self)
        self.Centre()
        self.Show(True)
        
if __name__ == "__main__": 
    app = wx.PySimpleApp()
    frame = KiessigWindow()    
    frame.Show(True)
    app.MainLoop()     
