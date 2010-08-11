"""
This module provide GUI for the neutron scattering length density calculator

"""

import wx

import sys,os

from wx.lib.scrolledpanel import ScrolledPanel
from sans.invariant import invariant
from sans.guiframe.utils import format_number, check_float
from sans.guicomm.events import NewPlotEvent, StatusEvent
from invariant_details import InvariantDetailsPanel, InvariantContainer
from invariant_widgets import OutputTextCtrl, InvTextCtrl
from invariant_state import InvariantState as IState
import copy,time
# The minimum q-value to be used when extrapolating
Q_MINIMUM  = 1e-5
# The maximum q-value to be used when extrapolating
Q_MAXIMUM  = 10
# the ratio of maximum q value/(qmax of data) to plot the theory data
Q_MAXIMUM_PLOT = 3
# the number of points to consider during fit
NPTS = 10
#Default value for background
BACKGROUND = 0.0
#default value for the scale
SCALE = 1.0
#default value of the contrast
CONTRAST = 1.0
#default value of the power used for power law
POWER = 4.0
#Invariant panel size 
_BOX_WIDTH = 76


if sys.platform.count("win32")>0:
    _STATICBOX_WIDTH = 450
    PANEL_WIDTH = 500 
    PANEL_HEIGHT = 700
    FONT_VARIANT = 0
else:
    _STATICBOX_WIDTH = 480
    PANEL_WIDTH = 530
    PANEL_HEIGHT = 700
    FONT_VARIANT = 1


class InvariantPanel(ScrolledPanel):
    """
    Provides the Invariant GUI.
    """
    ## Internal nickname for the window, used by the AUI manager
    window_name = "Invariant"
    ## Name to appear on the window title bar
    window_caption = "Invariant"
    ## Flag to tell the AUI manager to put this panel in the center pane
    CENTER_PANE = True
    def __init__(self, parent, data=None, manager=None,*args, **kwds):
        kwds["size"]= (PANEL_WIDTH, PANEL_HEIGHT)
        kwds["style"]= wx.FULL_REPAINT_ON_RESIZE
        ScrolledPanel.__init__(self, parent=parent, *args, **kwds)
        self.SetupScrolling()
        #Font size 
        self.SetWindowVariant(variant=FONT_VARIANT)
        #Object that receive status event
        self.parent = parent
        #plug-in using this panel
        self._manager = manager 
        #Data uses for computation
        self._data = data
        self._scale = SCALE 
        self._background = BACKGROUND
        self._bmark = None
        self.bookmark_num = 0
        
        self._set_bookmark_menu()
        #Init state
        self.set_state()
        # default flags for state
        self.new_state = False
        self.is_state_data = False
        self.is_power_out = False

        #container of invariant value
        self.inv_container = None
        #Draw the panel
        self._do_layout()
        self.reset_panel()
        self._reset_state_list()
        
        if self.parent is not None:
            msg = ""
            wx.PostEvent(self.parent,StatusEvent(status=msg, info="info"))
            
        ## Default file location for save
        self._default_save_location = os.getcwd()
        
    def err_check_on_data(self):
        """
        Check if data is valid for further computation
        """
        flag = False
        self.hint_msg_txt.SetLabel('')
        #edit the panel
        if self._data is not None:
            if len(self._data.x[self._data.x==0]) > 0:
                flag = True
                msg = "Invariant: one of your q-values is zero. Delete that entry before proceeding"
                self.hint_msg_txt.SetLabel(msg)
                wx.PostEvent(self.parent, StatusEvent(status=msg,
                                                      info="warning",
                                                      type="stop")) 
        return flag
    
    def set_data(self, data):
        """
        Set the data
        """
        self._data = data
        #edit the panel
        if self._data is not None:
            self.err_check_on_data()
            self.get_state_by_num(0)
            data_name = self._data.name
            data_qmin = min (self._data.x)
            data_qmax = max (self._data.x)
            self.data_name_tcl.SetValue(str(data_name))
            self.data_min_tcl.SetLabel(str(data_qmin))
            self.data_max_tcl.SetLabel(str(data_qmax))
            self.reset_panel()
            self.compute_invariant(event=None)
            self.state.file = self._data.name
            #Reset the list of states
            self.state.data = copy.deepcopy(data)
            self._reset_state_list()
        return True  
    def set_message(self):
        """
        Display warning message if available
        """
        if self.inv_container is not None:
            if self.inv_container.existing_warning:
                msg = "Warning! Computations on invariant require your "
                msg += "attention.\n Please click on Details button."
                self.hint_msg_txt.SetForegroundColour("red")
    
                wx.PostEvent(self.parent,StatusEvent(status=msg,info="warning"))
            else:
                msg = "For more information, click on Details button."
                self.hint_msg_txt.SetForegroundColour("black")
                wx.PostEvent(self.parent,StatusEvent(status=msg,info="info"))
            self.hint_msg_txt.SetLabel(msg)
            
       
    def set_manager(self, manager):
        """
        set value for the manager
        """
        self._manager = manager 
        
    def set_state(self,state=None,data=None):
        """
        set state when loading it from a .inv/.svs file
        """
        if state == None or data == None:
            self.state = IState()
        else:
            self.new_state = True
            if not self.set_data(data):
                return
            self.state = state 
            self.state.file = data.name   
            num = self.state.saved_state['state_num']
            
            if num > 0 :
                self._undo_enable()
            if num < len(state.state_list)-1:
                self._redo_enable()
                
            # get bookmarks
            self.bookmark_num = len(self.state.bookmark_list)

            total_bookmark_num = self.bookmark_num+1
            for ind in range(1,total_bookmark_num):
                #bookmark_num = ind
                value = self.state.bookmark_list[ind]
                name = "%d] bookmarked at %s on %s"% (ind,value[0], value[1])
                # append it to menu
                id = wx.NewId()
                self.popUpMenu.Append(id,name,str(''))
                wx.EVT_MENU(self, id, self._back_to_bookmark) 

            self.get_state_by_num(state_num=str(num))
            
            self._get_input_list() 
            #make sure that the data is reset (especially when loaded from a inv file)
            self.state.data = self._data
            self.new_state = False 
            self.is_state_data = False

    def clear_panel(self, format='.svs'):
        """
        Clear panel to defaults, used by set_state of manager
        """
        if format == '.svs':
            self._data = None
            # default data testctrl
            self.hint_msg_txt.SetLabel('')
            data_name = ''
            data_qmin = ''
            data_qmax = ''
            self.data_name_tcl.SetValue(str(data_name))
            self.data_min_tcl.SetLabel(str(data_qmin))
            self.data_max_tcl.SetLabel(str(data_qmax))
            #reset output textctrl
            self._reset_output()
            #reset panel
            self.reset_panel()
            #reset state w/o data
            self.set_state()
            # default flags for state
            self.new_state = False
            self.is_state_data = False
            self.is_power_out = False

    def get_background(self):
        """
        return the background textcrtl value as a float
        """
        background = self.background_tcl.GetValue().lstrip().rstrip()
        if background == "":
            raise ValueError, "Need a background"
        if check_float(self.background_tcl):
            return float(background)
        else:
            raise ValueError, "Receive invalid value for background : %s"%(background)
    
    def get_scale(self):
        """
        return the scale textcrtl value as a float
        """
        scale = self.scale_tcl.GetValue().lstrip().rstrip()
        if scale == "":
            raise ValueError, "Need a background"
        if check_float(self.scale_tcl):
            if float(scale)<= 0.0:
                self.scale_tcl.SetBackgroundColour("pink")
                self.scale_tcl.Refresh()
                raise ValueError, "Receive invalid value for scale: %s"%(scale)
            return float(scale)
        else:
            raise ValueError, "Receive invalid value for scale : %s"%(scale)
        
    def get_contrast(self):
        """
        return the contrast textcrtl value as a float
        """
        par_str = self.contrast_tcl.GetValue().strip()
        contrast = None
        if par_str !="" and check_float(self.contrast_tcl):
            contrast = float(par_str)
        return contrast
    
    def get_extrapolation_type(self, low_q, high_q):
        """
        """
        extrapolation = None
        if low_q  and not high_q:
            extrapolation = "low"
        elif not low_q  and high_q:
            extrapolation = "high"
        elif low_q and high_q:
            extrapolation = "both"
        return extrapolation
            
    def get_porod_const(self):
        """
        return the porod constant textcrtl value as a float
        """
        par_str = self.porod_constant_tcl.GetValue().strip()
        porod_const = None
        if par_str !="" and check_float(self.porod_constant_tcl):
            porod_const = float(par_str)
        return porod_const
    
    def get_volume(self, inv, contrast, extrapolation):
        """
        """
        if contrast is not None:
            try:
                v, dv = inv.get_volume_fraction_with_error(contrast=contrast, 
                                                           extrapolation=extrapolation)
                self.volume_tcl.SetValue(format_number(v))
                self.volume_err_tcl.SetValue(format_number(dv))
            except:
                self.volume_tcl.SetValue(format_number(None))
                self.volume_err_tcl.SetValue(format_number(None))
                msg= "Error occurred computing volume fraction: %s"%sys.exc_value
                wx.PostEvent(self.parent, StatusEvent(status=msg,
                                                      info="error",
                                                      type="stop"))
               
    def get_surface(self, inv, contrast, porod_const, extrapolation):
        """
        """
        if contrast is not None and porod_const is not None:
            try:
                s, ds = inv.get_surface_with_error(contrast=contrast,
                                        porod_const=porod_const,
                                        extrapolation=extrapolation)
                self.surface_tcl.SetValue(format_number(s))
                self.surface_err_tcl.SetValue(format_number(ds))
            except:
                self.surface_tcl.SetValue(format_number(None))
                self.surface_err_tcl.SetValue(format_number(None))
                msg = "Error occurred computing specific surface: %s"%sys.exc_value
                wx.PostEvent(self.parent, StatusEvent(status=msg, info="error",
                                                       type="stop"))
                
    def get_total_qstar(self, inv, extrapolation):
        """
        """
        try:
            qstar_total, qstar_total_err = inv.get_qstar_with_error(extrapolation)
            
            self.invariant_total_tcl.SetValue(format_number(qstar_total))
            self.invariant_total_err_tcl.SetValue(format_number(qstar_total_err))
            self.inv_container.qstar_total = qstar_total
            self.inv_container.qstar_total_err = qstar_total_err
         
        except:
            self.inv_container.qstar_total = "Error"
            self.inv_container.qstar_total_err = "Error"
            self.invariant_total_tcl.SetValue(format_number(None))
            self.invariant_total_err_tcl.SetValue(format_number(None))
            msg= "Error occurred computing invariant using extrapolation: %s"%sys.exc_value
            wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))  
            
    def get_low_qstar(self, inv, npts_low, low_q=False):
        """
        """
        if low_q:
            try: 
                qstar_low, qstar_low_err = inv.get_qstar_low()
                self.inv_container.qstar_low = qstar_low
                self.inv_container.qstar_low_err = qstar_low_err
                extrapolated_data = inv.get_extra_data_low(npts_in=npts_low) 
                power_low = inv.get_extrapolation_power(range='low')  
                if self.power_law_low.GetValue():
                    self.power_low_tcl.SetValue(format_number(power_low))
                self._manager.plot_theory(data=extrapolated_data,
                                           name="Low-Q extrapolation")
            except:
                self.inv_container.qstar_low = "ERROR"
                self.inv_container.qstar_low_err = "ERROR"
                self._manager.plot_theory(name="Low-Q extrapolation")
                msg= "Error occurred computing low-Q invariant: %s"%sys.exc_value
                wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
        else:
            try:
                self._manager.plot_theory(name="Low-Q extrapolation")
            except: pass
            
    def get_high_qstar(self, inv, high_q=False):
        """
        """
        if high_q:
            try: 
                qmax_plot = Q_MAXIMUM_PLOT * max(self._data.x)
                if qmax_plot > Q_MAXIMUM: qmax_plot = Q_MAXIMUM
                qstar_high, qstar_high_err = inv.get_qstar_high()
                self.inv_container.qstar_high = qstar_high
                self.inv_container.qstar_high_err = qstar_high_err
                power_high = inv.get_extrapolation_power(range='high') 
                self.power_high_tcl.SetValue(format_number(power_high))
                high_out_data = inv.get_extra_data_high(q_end=qmax_plot,npts=500)
                self._manager.plot_theory(data=high_out_data,
                                           name="High-Q extrapolation")
            except:
                self.inv_container.qstar_high = "ERROR"
                self.inv_container.qstar_high_err = "ERROR"
                self._manager.plot_theory(name="High-Q extrapolation")
                msg= "Error occurred computing high-Q invariant: %s"%sys.exc_value
                wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
        else:
            try:
                self._manager.plot_theory(name="High-Q extrapolation")
            except: pass

    def get_qstar(self, inv):
        """
        """
        qstar, qstar_err = inv.get_qstar_with_error()
        self.inv_container.qstar = qstar
        self.inv_container.qstar_err = qstar_err
             
    def set_extrapolation_low(self, inv, low_q=False):
        """
        return float value necessary to compute invariant a low q
        """
        #get funtion
        if self.guinier.GetValue():
            function_low = "guinier"
        # get the function
        power_low = None #2.0/3.0
        if self.power_law_low.GetValue():
            function_low = "power_law"
            if self.fit_enable_low.GetValue():
                #set value of power_low to none to allow fitting
                power_low = None
            else:
                power_low = self.power_low_tcl.GetValue().lstrip().rstrip()
                if check_float(self.power_low_tcl):
                    power_low = float(power_low)
                else:
                    if low_q :
                        #Raise error only when qstar at low q is requested
                        msg = "Expect float for power at low q , got %s"%(power_low)
                        raise ValueError, msg
       
        #Get the number of points to extrapolated
        npts_low = self.npts_low_tcl.GetValue().lstrip().rstrip()   
        if check_float(self.npts_low_tcl):
            npts_low = float(npts_low)
        else:
            if low_q:
                msg = "Expect float for number of points at low q , got %s"%(npts_low)
                raise ValueError, msg
        #Set the invariant calculator
        inv.set_extrapolation(range="low", npts=npts_low,
                                   function=function_low, power=power_low)    
        return inv, npts_low  
    

    def set_extrapolation_high(self, inv, high_q=False):
        """
        return float value necessary to compute invariant a high q
        """
        power_high = None
        #if self.power_law_high.GetValue():
        function_high = "power_law"
        if self.fit_enable_high.GetValue():
            #set value of power_high to none to allow fitting
            power_high = None
        else:
            power_high = self.power_high_tcl.GetValue().lstrip().rstrip()
            if check_float(self.power_high_tcl):
                power_high = float(power_high)
            else:
                if high_q :
                    #Raise error only when qstar at high q is requested
                    msg = "Expect float for power at high q , got %s"%(power_high)
                    raise ValueError, msg
                          
        npts_high = self.npts_high_tcl.GetValue().lstrip().rstrip()   
        if check_float(self.npts_high_tcl):
            npts_high = float(npts_high)
        else:
            if high_q:
                msg = "Expect float for number of points at high q , got %s"%(npts_high)
                raise ValueError, msg
        inv.set_extrapolation(range="high", npts=npts_high,
                                   function=function_high, power=power_high)
        return inv, npts_high
    
    def display_details(self, event):
        """
        open another panel for more details on invariant calculation
        """
        panel = InvariantDetailsPanel(parent=self, 
                                           qstar_container=self.inv_container)
        panel.ShowModal()
        panel.Destroy()
        self.button_calculate.SetFocus()
        
    def compute_invariant(self, event=None):
        """
        compute invariant 
        """
        if self._data == None:
            msg = "\n\nData must be loaded first in order to perform a compution..."
            wx.PostEvent(self.parent, StatusEvent(status=msg))
        # set a state for this computation for saving
        elif event != None: 
            self._set_compute_state(state='compute')
            self.button_bookmark.Enable(True)
            msg= "\n\nStarting a new invariant computation..."            
            wx.PostEvent(self.parent, StatusEvent(status=msg))
            

        if self._data is None or self.err_check_on_data():
            return
        
        #clear outputs textctrl 
        self._reset_output()
        try:
            background = self.get_background()
            scale = self.get_scale()
        except:
            msg= "Invariant Error: %s"%(sys.exc_value)
            wx.PostEvent(self.parent, StatusEvent(status= msg, type="stop"))
            return
        
        low_q = self.enable_low_cbox.GetValue()
        high_q = self.enable_high_cbox.GetValue()  
        #set invariant calculator 
        inv = invariant.InvariantCalculator(data=self._data,
                                            background=background,
                                            scale=scale)
        try:
            inv, npts_low = self.set_extrapolation_low(inv=inv, low_q=low_q)
            inv, npts_high = self.set_extrapolation_high(inv=inv, high_q=high_q)
        except:
            msg = "Error occurred computing invariant: %s"%sys.exc_value
            wx.PostEvent(self.parent, StatusEvent(status=msg,
                                                 info="warning",type="stop"))
            return
        #check the type of extrapolation
        extrapolation = self.get_extrapolation_type(low_q=low_q, high_q=high_q)
       
        #Compute invariant
        bkg_changed = False
        scale_changed = False
        try:
            self.get_qstar(inv=inv)
            #if scale_changed or bkg_changed:
            #self._manager.plot_data(data=inv.get_data())
            
        except:
            msg= "Error occurred computing invariant: %s"%sys.exc_value
            wx.PostEvent(self.parent, StatusEvent(status=msg, 
                                                  info="warning",type="stop"))
            return
       
        #Compute qstar extrapolated to low q range 
        self.get_low_qstar(inv=inv, npts_low=npts_low, low_q=low_q)
        #Compute qstar extrapolated to high q range 
        self.get_high_qstar(inv=inv, high_q=high_q)
        #Compute qstar extrapolated to total q range and set value to txtcrtl
        self.get_total_qstar(inv=inv, extrapolation=extrapolation)
        # Parse additional parameters
        porod_const = self.get_porod_const()        
        contrast = self.get_contrast()
        
        try:
            #Compute volume and set value to txtcrtl
            self.get_volume(inv=inv, contrast=contrast, extrapolation=extrapolation)
            #compute surface and set value to txtcrtl
        except:
            msg = "Error occurred computing invariant: %s"%sys.exc_value
            wx.PostEvent(self.parent, StatusEvent(status=msg,
                                                  info="warning",type="stop"))
        try:
            self.get_surface(inv=inv, contrast=contrast, porod_const=porod_const, 
                                    extrapolation=extrapolation)
            
        except:
            msg = "Error occurred computing invariant: %s"%sys.exc_value
            wx.PostEvent(self.parent, StatusEvent(status=msg,
                                                  info="warning",type="stop"))
            
        #compute percentage of each invariant
        self.inv_container.compute_percentage()
        
        #display a message
        self.set_message()
        
        # reset power_out to default to get ready for another '_on_text'
        if self.is_power_out == True:
            self.state.container = copy.deepcopy(self.inv_container)
            self.state.timestamp= self._get_time_stamp()
            msg = self.state.__str__()
            self.state.set_report_string()
            self.is_power_out = False
            wx.PostEvent(self.parent, StatusEvent(status = msg ))

        #enable the button_ok for more details
        self.button_details.Enable()

        if event != None: 
            if not self.button_report.IsEnabled(): self.button_report.Enable(True)
            if not self.button_save.IsEnabled(): self.button_save.Enable(True)
            wx.PostEvent(self.parent, StatusEvent(status = '\nFinished invariant computation...'))
        
    def undo(self,event=None):
        """
        Go back to the previous state
        
        : param event: undo button event
        """
        if event != None: event.Skip()
        if self.state.state_num <0: return
        self.is_power_out = True
        # get the previous state_num
        pre_state_num = int(self.state.saved_state['state_num']) - 1
        self.get_state_by_num(state_num=str(pre_state_num))
        
        if float(pre_state_num) <=0:
            self._undo_disable()
        else:
            self._undo_enable()

        self._redo_enable()
        self.is_power_out = False  
        self._info_state_num()
        
        
    def redo(self,event=None):
        """
        Go forward to the previous state
        
        : param event: redo button event
        """
        if event != None: event.Skip()
        self.is_power_out = True
        # get the next state_num
        next_state_num = int(self.state.saved_state['state_num']) + 1

        self.get_state_by_num(state_num=str(next_state_num))
        
        if float(next_state_num)+2 > len(self.state.state_list):
            self._redo_disable()
        else:
            self._redo_enable()
        
        self._undo_enable()
        self.is_power_out = False
        self._info_state_num()
        
    def report(self, event=None):
        """
        Invoke report dialog panel
        
        : param event: report button event
        """
        from report_dialog import ReportDialog

        self.state.set_report_string()
        report_html_str = self.state.report_str
        report_text_str = self.state.__str__()
        report_img = self.state.image
        report_list = [report_html_str,report_text_str,report_img]
        dialog = ReportDialog(report_list, None, -1, "")
        dialog.ShowModal()
        
    def get_state_by_num(self,state_num=None):
        """
        Get the state given by number
        
        : param state_num: the given state number
        """     
        if state_num == None:
            return

        backup_state_list = copy.deepcopy(self.state.state_list)
        
        # get the previous state
        try:
            current_state = copy.deepcopy(self.state.state_list[str(state_num)])
            # get the previously computed state number (computation before the state changes happened)
            current_compute_num = str(current_state['compute_num'])
        except :
            raise
            #raise ValueError,  "No such state exists in history"
        
        # get the state at pre_compute_num
        comp_state = copy.deepcopy(self.state.state_list[current_compute_num])

        # set the parameters
        for key in comp_state:
            value = comp_state[key]
            try:
                exec "self.%s.SetValue(str(%s))" % (key, value)
            except TypeError:
                exec "self.%s.SetValue(%s)" % (key, value)
            except:
                pass
          
        self.compute_invariant(event=None)
        # set the input params at the state at pre_state_num
        for key in current_state:
            # set the inputs and boxes
            value = current_state[key]
            try:
                exec 'self.%s.SetValue(str(%s))' % (key, value)
            except TypeError:
                exec 'self.%s.SetValue(%s)' % (key, value)
            except:
                pass

        self._enable_high_q_section(event=None)
        self._enable_low_q_section(event=None)
        self.state.state_list = backup_state_list
        self.state.saved_state = current_state
        self.state.state_num = state_num
           
        
    def get_bookmark_by_num(self, num=None):
        """
        Get the bookmark state given by number
        
        : param num: the given bookmark number
        
        """
        current_state = {}
        comp_state = {}
        backup_state_list = copy.deepcopy(self.state.state_list)

        # get the previous state
        try:
            time,date,current_state,comp_state = self.state.bookmark_list[int(num)] 
        except :
            raise ValueError,  "No such bookmark exists"

        # set the parameters
        for key in comp_state:
            value = comp_state[key]
            try:
                exec "self.%s.SetValue(str(%s))" % (key, value)
            except TypeError:
                exec "self.%s.SetValue(%s)" % (key, value)
            except:
                pass

        self.compute_invariant(event=None)
        # set the input params at the state of pre_state_num
        for key in current_state:
            value = current_state[key]
            try:
                exec 'self.%s.SetValue(str(%s))' % (key, value)
            except TypeError:
                exec 'self.%s.SetValue(%s)' % (key, value)
            except:
                pass
        self.state.saved_state = copy.deepcopy(current_state)
       
        self._enable_high_q_section(event=None)
        self._enable_low_q_section(event=None)
        self.state.state_list = backup_state_list
        #self.state.saved_state = current_state
        #self.state.state_num = state_num

    def reset_panel(self):
        """
        set the panel at its initial state.
        """
        self.background_tcl.SetValue(str(BACKGROUND))
        self.scale_tcl.SetValue(str(SCALE)) 
        self.contrast_tcl.SetValue(str(CONTRAST))
        self.porod_constant_tcl.SetValue('') 
        self.npts_low_tcl.SetValue(str(NPTS))
        self.enable_low_cbox.SetValue(False)
        self.fix_enable_low.SetValue(True)
        self.power_low_tcl.SetValue(str(POWER))
        self.guinier.SetValue(True)
        self.power_low_tcl.Disable()
        self.enable_high_cbox.SetValue(False)
        self.fix_enable_high.SetValue(True)
        self.power_high_tcl.SetValue(str(POWER))
        self.npts_high_tcl.SetValue(str(NPTS))
        self.button_details.Disable()
        #Change the state of txtcrtl to enable/disable
        self._enable_low_q_section()
        #Change the state of txtcrtl to enable/disable
        self._enable_high_q_section()
        self._reset_output()
        self.button_undo.Disable()
        self.button_redo.Disable()
        self.button_bookmark.Disable()
        self.button_report.Disable()
        self.button_save.Disable() 
        self.button_calculate.SetFocus()
        #self.SetupScrolling()
        
    def _set_state(self, event):
        """
        Set the state list
        
        :param event: rb/cb event
        """
        if event == None:
            return
        obj = event.GetEventObject()
        name = str(obj.GetName())
        value = str(obj.GetValue())
        rb_list = [['power_law_low','guinier'],['fit_enable_low','fix_enable_low'],['fit_enable_high','fix_enable_high']]

        try:
            if value == None or value.lstrip().rstrip() =='':
                value = 'None'
            exec 'self.state.%s = %s' % (name, value)
            exec "self.state.saved_state['%s'] = %s" %  (name, value)
            
            # set the count part of radio button clicked False for the saved_state
            for title,content in rb_list:
                if name ==  title:
                    name = content 
                    value = False     
                elif name == content:
                    name = title
                    value = False 
            exec "self.state.saved_state['%s'] = %s" %  (name, value)     
            
            # Instead of changing the future, create a new future.
            max_state_num = len(self.state.state_list)-1   
            self.state.saved_state['state_num'] = max_state_num   
            
            self.state.saved_state['state_num'] +=1
            self.state.state_num = self.state.saved_state['state_num']
            self.state.state_list[str(self.state.state_num)] = self.state.clone_state()#copy.deepcopy(self.state.saved_state)
        except:           
            pass

        event.Skip()
        self._undo_enable()
        self._redo_disable()
            
    def _set_compute_state(self,state=None):
        """
        Notify the compute_invariant state to self.state
        
        : param state: set 'compute' when the computation is activated by the 'compute' button, else None
        
        """
        # reset the default
        if state != 'compute':
            self.new_state = False
            self.is_power_out = False
        else:
            self.is_power_out = True
        # Instead of changing the future, create a new future.
        max_state_num = len(self.state.state_list)-1   
        self.state.saved_state['state_num'] = max_state_num        
        # A new computation is also A state
        temp_saved_states = self.state.clone_state()#copy.deepcopy(self.state.saved_state)
        temp_saved_states['state_num'] +=1
        self.state.state_num = temp_saved_states['state_num']

                
        # set the state number of the computation 
        if state == 'compute':
            temp_saved_states['compute_num'] = self.state.state_num
        self.state.saved_state= copy.deepcopy(temp_saved_states)
        self.state.state_list[str(self.state.state_num)] = self.state.clone_state()#copy.deepcopy(self.state.saved_state)
        
        # A computation is a new state, so delete the states with any higher state numbers
        for i in range(self.state.state_num+1,len(self.state.state_list)):
            try:
                del (self.state.state_list[str(i)])
            except: 
                pass
        # Enable the undo button if it was not
        self._undo_enable()
        self._redo_disable()
        
        
    def _reset_state_list(self,data=None):
        """
        Reset the state_list just before data was loading: Used in 'set_current_data()'
        """
        #if data == None: return
        #temp_state = self.state.clone_state()#copy.deepcopy(self.state.saved_state)
        # Clear the list 
        self.state.state_list.clear()
        self.state.bookmark_list.clear()
        # Set defaults
        self.state.saved_state['state_num'] = 0
        self.state.saved_state['compute_num'] = 0
        if self._data != None:
            self.state.saved_state['file'] = str(self._data.name)
        else:
            self.state.saved_state['file'] = 'None'
        self.state.file = self.state.saved_state['file']

        self.state.state_num = self.state.saved_state['state_num']
        self.state.timestamp = "('00:00:00', '00/00/0000')"

        # Put only the current state in the list
        self.state.state_list[str(self.state.state_num)] = self.state.clone_state()#copy.deepcopy(self.state.saved_state)
        self._undo_disable()
        
    def _on_text(self, event):
        """
        Catch text change event to add the state to the state_list
        
        :param event: txtctr event ; assumes not None
        
        """
        if self._data == None: 
            return
        # check if this event is from do/undo button
        if self.state.saved_state['is_time_machine'] or self.new_state:
            event.Skip()
            return
        
        # get the object
        obj = event.GetEventObject()
        name = str(obj.GetName())
        value = str(obj.GetValue())
        state_num = self.state.saved_state['state_num']

        # text event is a new state, so delete the states with higher state_num
        # i.e., change the future
        for i in range(int(state_num)+1,len(self.state.state_list)):
            try:
                del (self.state.state_list[str(i)])
            except: 
                pass
        
        # Instead of changing the future, create a new future.
        #max_state_num = len(self.state.state_list)-1   
        #self.state.saved_state['state_num'] = max_state_num

        # try to add new state of the text changes in the state_list
        try:
            if value.strip() == None: value = ''
            exec "self.state.%s = '%s'" % (name, value)
            exec "self.state.saved_state['%s'] = '%s'" %  (name, value)
            exec "self.state.input_list['%s'] = '%s'" % (name, value)
            if not self.is_power_out:
                if name != 'power_low_tcl' and name !='power_high_tcl':
                    self.state.saved_state['state_num'] += 1
            self.state.state_num = self.state.saved_state['state_num']
            self.state.state_list[str(self.state.state_num)] = self.state.clone_state()#copy.deepcopy(self.state.saved_state)
        except:
            pass

        event.Skip()
        self._undo_enable()
        self._redo_disable()
        self.button_bookmark.Enable(True)
        self.button_report.Disable()
       
        
    def _on_out_text(self, event):     
        """
        Catch ouput text change to add the state 
        
        :param event: txtctr event ; assumes not None
        
        """    
        # get the object
        obj = event.GetEventObject()
        name = str(obj.GetName())
        value = str(obj.GetValue())
        try:
            exec "self.state.saved_state['%s'] = '%s'" %  (name, value)
            self.state.state_list[str(self.state.state_num)] = self.state.clone_state()
        except:
            pass
        if event != None: event.Skip()\

    def _get_input_list(self):     
        """
        get input_list; called by set_state
        """    
        # get state num of the last compute state
        compute_num = self.state.saved_state['compute_num']
        # find values and put into the input list
        for key1,value1 in self.state.state_list[str(compute_num)].iteritems(): 
            for key,value in self.state.input_list.iteritems(): 
                if key == key1:
                    self.state.input_list[key]=value1
                    break
        
    def _set_bookmark_menu(self):
        """
        Setup 'bookmark' context menu
        """
        ## Create context menu for page
        self.popUpMenu = wx.Menu()
        id = wx.NewId()
        self._bmark = wx.MenuItem(self.popUpMenu,id,"BookMark"," Bookmark the panel to recall it later")
        self.popUpMenu.AppendItem(self._bmark)
        self._bmark.Enable(True)
        wx.EVT_MENU(self, id, self._on_bookmark)
        self.popUpMenu.AppendSeparator()
        self.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        
    def _on_bookmark(self,event):
        """
        Save the panel state in memory and add the list on the popup menu on bookmark context menu event
        """ 
        if self._data == None: return
        if event == None: return
        self.bookmark_num += 1
        # date and time of the event
        #year, month, day,hour,minute,second,tda,ty,tm_isdst= time.localtime()
        #my_time= str(hour)+" : "+str(minute)+" : "+str(second)+" "
        #date= str( month)+"/"+str(day)+"/"+str(year)
        my_time, date = self._get_time_stamp()
        state_num = self.state.state_num
        compute_num = self.state.saved_state['compute_num']
        # name and message of the bookmark list
        msg=  "State saved at %s on %s"%(my_time, date)
         ## post help message for the selected model 
        msg +=" Right click on the panel to retrieve this state"
        #wx.PostEvent(self.parent.parent, StatusEvent(status = msg ))
        name = "%d] bookmarked at %s on %s"%(self.bookmark_num,my_time, date)
        
        # append it to menu
        id = wx.NewId()
        self.popUpMenu.Append(id,name,str(msg))
        wx.EVT_MENU(self, id, self._back_to_bookmark )
        state = self.state.clone_state()
        comp_state = copy.deepcopy(self.state.state_list[str(compute_num)])
        self.state.bookmark_list[self.bookmark_num] = [my_time,date,state,comp_state]
        self.state.toXML(self, doc=None, entry_node=None)
        
        wx.PostEvent(self.parent,StatusEvent(status=msg,info="info"))

    def _back_to_bookmark(self,event):
        """
        Bring the panel back to the state of bookmarked requested by context menu event
        and set it as a new state
        """
        ## post help message for the selected model 
        msg = self.popUpMenu.GetHelpString(event.GetId())
        msg +=" reloaded"
        wx.PostEvent(self.parent, StatusEvent(status = msg ))
        
        name= self.popUpMenu.GetLabel(event.GetId())
        num,time = name.split(']')
        current_state_num = self.state.state_num  
        self.get_bookmark_by_num(num)
        state_num = int(current_state_num)+1
        
        self.state.saved_state['state_num'] = state_num
        self.state.state_list[str(state_num)] = self.state.clone_state()#copy.deepcopy(self.state.saved_state)
        self.state.state_num = state_num
        self._undo_enable()
        self._info_bookmark_num(event)
        
    def _info_bookmark_num(self,event=None):
        """
        print the bookmark number in info
        
        : event: popUpMenu event
        """
        if event == None: return
        # get the object
        item = self.popUpMenu.FindItemById(event.GetId())
        text = item.GetText()
        num = text.split(']')[0]
        msg = "bookmark num = %s "% num
        
        wx.PostEvent(self.parent, StatusEvent(status = msg ))
        
    def _info_state_num(self):
        """
        print the current state number in info
        """
        msg = "state num = "
        msg += self.state.state_num
        
        wx.PostEvent(self.parent, StatusEvent(status = msg))
                         
    def _get_time_stamp(self):
        """
        return time and date stings
        """
        # date and time 
        year, month, day,hour,minute,second,tda,ty,tm_isdst= time.localtime()
        my_time= str(hour)+":"+str(minute)+":"+str(second)
        date= str( month)+"/"+str(day)+"/"+str(year)
        return my_time, date
    
    def _undo_enable(self):
        """
        Enable undo button
        """
        if not self.button_undo.IsEnabled():
            self.button_undo.Enable(True)

    def _undo_disable(self):
        """
        Disable undo button
        """
        if self.button_undo.IsEnabled():
            self.button_undo.Disable()

    def _redo_enable(self):
        """
        Enable redo button
        """
        if not self.button_redo.IsEnabled():
            self.button_redo.Enable(True)

    def _redo_disable(self):
        """
        Disable redo button
        """
        if self.button_redo.IsEnabled():
            self.button_redo.Disable()
            
    def _on_save_button(self, evt=None): 
        """
        Save invariant state into a file
        """
        # Ask the user the location of the file to write to.
        path = None
        dlg = wx.FileDialog(self, "Choose a file", self._default_save_location, "", "*.inv", wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self._default_save_location = os.path.dirname(path)
        else:
            return None
        
        dlg.Destroy()
        
        self._manager.save_file(filepath=path, state=self.state)
        
    def _show_message(self, mssg='',msg='Warning'):
        """
        Show warning message when resetting data
        """
        # no message for now
        return True
        count_bf = self.data_cbbox.GetCount()
        if count_bf > 1:
            mssg += 'Loading a new data set will reset all the work done in this panel. \n\r'
            mssg += 'Please make sure to save it first... \n\r'
            answer = wx.MessageBox(mssg, msg, wx.CANCEL|wx.OK|wx.ICON_EXCLAMATION)
    
            if answer == wx.OK:
                return True
            else:
                return False
        else: True
        
    def _reset_output(self):
        """
        clear outputs textcrtl
        """
        self.invariant_total_tcl.Clear()
        self.invariant_total_err_tcl.Clear()
        self.volume_tcl.Clear()
        self.volume_err_tcl.Clear()
        self.surface_tcl.Clear()
        self.surface_err_tcl.Clear()
        #prepare a new container to put result of invariant
        self.inv_container = InvariantContainer()

    
    def _on_context_menu(self,event):
        
        pos = event.GetPosition()
        pos = self.ScreenToClient(pos)
       
        self.PopupMenu(self.popUpMenu, pos) 
      
    def _define_structure(self):
        """
        Define main sizers needed for this panel
        """
        ## Box sizers must be defined first before defining buttons/textctrls (MAC).
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        #Sizer related to outputs
        outputs_box = wx.StaticBox(self, -1, "Outputs")
        self.outputs_sizer = wx.StaticBoxSizer(outputs_box, wx.VERTICAL)
        self.outputs_sizer.SetMinSize((PANEL_WIDTH,-1))
        #Sizer related to data
        data_name_box = wx.StaticBox(self, -1, "I(q) Data Source")
        self.data_name_boxsizer = wx.StaticBoxSizer(data_name_box, wx.VERTICAL)
        self.data_name_boxsizer.SetMinSize((PANEL_WIDTH,-1))
        self.hint_msg_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.data_name_sizer = wx.BoxSizer(wx.HORIZONTAL)
       
        self.data_range_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #Sizer related to background and scale
        self.bkg_scale_sizer = wx.BoxSizer(wx.HORIZONTAL) 
        #Sizer related to contrast and porod constant
        self.contrast_porod_sizer = wx.BoxSizer(wx.HORIZONTAL) 
        #Sizer related to inputs
        inputs_box = wx.StaticBox(self, -1, "Customized Inputs")
        self.inputs_sizer = wx.StaticBoxSizer(inputs_box, wx.VERTICAL)
        #Sizer related to extrapolation
        extrapolation_box = wx.StaticBox(self, -1, "Extrapolation")
        self.extrapolation_sizer = wx.StaticBoxSizer(extrapolation_box,
                                                        wx.VERTICAL)
        self.extrapolation_sizer.SetMinSize((PANEL_WIDTH,-1))
        self.extrapolation_range_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.extrapolation_low_high_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #Sizer related to extrapolation at low q range
        low_q_box = wx.StaticBox(self, -1, "Low Q")
        self.low_extrapolation_sizer = wx.StaticBoxSizer(low_q_box, wx.VERTICAL)
        self.low_q_sizer = wx.GridBagSizer(5,5)
        #Sizer related to extrapolation at low q range
        high_q_box = wx.StaticBox(self, -1, "High Q")
        self.high_extrapolation_sizer = wx.StaticBoxSizer(high_q_box, wx.VERTICAL)
        self.high_q_sizer = wx.GridBagSizer(5,5)
        #sizer to define outputs
        self.volume_surface_sizer = wx.GridBagSizer(5,5)
        #Sizer related to invariant output
        self.invariant_sizer = wx.GridBagSizer(5, 5)
        #Sizer related to button
        self.button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #Sizer related to save button
        self.save_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
    def _layout_data_name(self):
        """
        Draw widgets related to data's name
        """
        #Sizer hint 
        hint_msg = "First open data file from 'File' menu.  Then Highlight and right click on the data plot. \n"
        hint_msg += "Finally, select 'Compute Invariant'."
        self.hint_msg_txt = wx.StaticText(self, -1, hint_msg)  
        self.hint_msg_txt.SetForegroundColour("red")
        msg = "Highlight = mouse the mouse's cursor on the data until the plot's color changes to yellow"
        self.hint_msg_txt.SetToolTipString(msg)
        self.hint_msg_sizer.Add(self.hint_msg_txt)
        #Data name [string]
        data_name_txt = wx.StaticText(self, -1, 'Data : ')  
       
        self.data_name_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH*5, 20), style=0) 
        self.data_name_tcl.SetToolTipString("Data's name.")
        self.data_name_sizer.AddMany([(data_name_txt, 0, wx.LEFT|wx.RIGHT, 10),
                                       (self.data_name_tcl, 0, wx.EXPAND)])
        #Data range [string]
        data_range_txt = wx.StaticText(self, -1, 'Total Q Range (1/A): ') 
        data_min_txt = wx.StaticText(self, -1, 'Min : ')  
        self.data_min_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0, name='data_min_tcl')
        self.data_min_tcl.SetToolTipString("The minimum value of q range.")
        data_max_txt = wx.StaticText(self, -1, 'Max : ') 
        self.data_max_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0, name='data_max_tcl') 
        self.data_max_tcl.SetToolTipString("The maximum value of q range.")
        self.data_range_sizer.AddMany([(data_range_txt, 0, wx.RIGHT, 10),
                                       (data_min_txt, 0, wx.RIGHT, 10),
                                       (self.data_min_tcl, 0, wx.RIGHT, 10),
                                       (data_max_txt, 0, wx.RIGHT, 10),
                                       (self.data_max_tcl, 0, wx.RIGHT, 10)])
        self.data_name_boxsizer.AddMany([(self.hint_msg_sizer, 0 , wx.ALL, 5),
                            (self.data_name_sizer, 0 , wx.ALL, 10),
                                     (self.data_range_sizer, 0 , wx.ALL, 10)])
    
    def _layout_bkg_scale(self):
        """
        Draw widgets related to background and scale
        """
        background_txt = wx.StaticText(self, -1, 'Background : ')  
        self.background_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0, name='background_tcl') 
        wx.EVT_TEXT(self, self.background_tcl.GetId(), self._on_text)
        background_hint_txt = "Background"
        self.background_tcl.SetToolTipString(background_hint_txt)
        background_unit_txt = wx.StaticText(self, -1, '[1/cm]')  
        scale_txt = wx.StaticText(self, -1, 'Scale : ')  
        self.scale_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0, name='scale_tcl')
        wx.EVT_TEXT(self, self.scale_tcl.GetId(), self._on_text)
        scale_hint_txt = "Scale"
        self.scale_tcl.SetToolTipString(scale_hint_txt)
        self.bkg_scale_sizer.AddMany([(background_txt, 0, wx.LEFT, 10),
                                       (self.background_tcl, 0, wx.LEFT, 5),
                                       (background_unit_txt, 0, wx.LEFT, 10),
                                       (scale_txt, 0, wx.LEFT, 70),
                                       (self.scale_tcl, 0, wx.LEFT, 40)])
 
    def _layout_contrast_porod(self):
        """
        Draw widgets related to porod constant and contrast
        """
        contrast_txt = wx.StaticText(self, -1, 'Contrast : ')  
        self.contrast_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH, 20), style=0,name='contrast_tcl')
        wx.EVT_TEXT(self, self.contrast_tcl.GetId(), self._on_text)
        contrast_hint_txt = "Contrast"
        self.contrast_tcl.SetToolTipString(contrast_hint_txt)
        contrast_unit_txt = wx.StaticText(self, -1, '[1/A^(2)]')  
        porod_const_txt = wx.StaticText(self, -1, 'Porod Constant:')  
        self.porod_constant_tcl = InvTextCtrl(self, -1, 
                                              size=(_BOX_WIDTH, 20), style=0,name='porod_constant_tcl') 
        wx.EVT_TEXT(self, self.porod_constant_tcl.GetId(), self._on_text)
        porod_const_hint_txt = "Porod Constant"
        self.porod_constant_tcl.SetToolTipString(porod_const_hint_txt)
        optional_txt = wx.StaticText(self, -1, '(Optional)')  
        self.contrast_porod_sizer.AddMany([(contrast_txt, 0, wx.LEFT, 10),
                                           (self.contrast_tcl, 0, wx.LEFT, 20),
                                           (contrast_unit_txt, 0, wx.LEFT, 10),
                                           (porod_const_txt, 0, wx.LEFT, 50),
                                       (self.porod_constant_tcl, 0, wx.LEFT, 0),
                                       (optional_txt, 0, wx.LEFT, 10)])
        
    def _enable_fit_power_law_low(self, event=None):
        """
        Enable and disable the power value editing
        """
        if event != None: 
            self.button_bookmark.Enable(True)
            self.button_report.Disable()
            print "enable fit==>event!=None"

        if self.fix_enable_low.IsEnabled():
            
            if self.fix_enable_low.GetValue():
                self.fit_enable_low.SetValue(False)
                self.power_low_tcl.Enable()
            else:
                self.fit_enable_low.SetValue(True)
                self.power_low_tcl.Disable()
        self._set_state(event=event)
           
    def _enable_low_q_section(self, event=None):
        """
        Disable or enable some button if the user enable low q extrapolation
        """
        if event != None: 
            self.button_bookmark.Enable(True)
            self.button_report.Disable()
            
        if self.enable_low_cbox.GetValue():
            self.npts_low_tcl.Enable()
            self.fix_enable_low.Enable()
            self.fit_enable_low.Enable()
            self.guinier.Enable()
            self.power_law_low.Enable()

        else:
            self.npts_low_tcl.Disable()
            self.fix_enable_low.Disable()
            self.fit_enable_low.Disable()
            self.guinier.Disable()
            self.power_law_low.Disable()
        
        self._enable_power_law_low()
        self._enable_fit_power_law_low()
        self._set_state(event=event)
        self.button_calculate.SetFocus()
        
    def _enable_power_law_low(self, event=None):
        """
        Enable editing power law section at low q range
        """
        if event != None: 
            self.button_bookmark.Enable(True)
            self.button_report.Disable()
        if self.guinier.GetValue():
            self.power_law_low.SetValue(False)
            self.fix_enable_low.Disable()
            self.fit_enable_low.Disable()
            self.power_low_tcl.Disable()
        else:
            self.power_law_low.SetValue(True)
            self.fix_enable_low.Enable()
            self.fit_enable_low.Enable()
            self.power_low_tcl.Enable()
        self._enable_fit_power_law_low()
        self._set_state(event=event)
            
    def _layout_extrapolation_low(self):
        """
        Draw widgets related to extrapolation at low q range
        """
        self.enable_low_cbox = wx.CheckBox(self, -1, "Enable Extrapolate Low Q",name='enable_low_cbox')
        wx.EVT_CHECKBOX(self, self.enable_low_cbox.GetId(),
                                         self._enable_low_q_section)
        self.fix_enable_low = wx.RadioButton(self, -1, 'Fix',
                                         (10, 10),style=wx.RB_GROUP,name='fix_enable_low')
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_fit_power_law_low,
                                     id=self.fix_enable_low.GetId())
        self.fit_enable_low = wx.RadioButton(self, -1, 'Fit', (10, 10),name='fit_enable_low')
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_fit_power_law_low, 
                                        id=self.fit_enable_low.GetId())
        self.guinier = wx.RadioButton(self, -1, 'Guinier',
                                         (10, 10),style=wx.RB_GROUP, name='guinier')
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_power_law_low,
                                     id=self.guinier.GetId())        
        self.power_law_low = wx.RadioButton(self, -1, 'Power Law', (10, 10),name='power_law_low')
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_power_law_low, 
                                        id=self.power_law_low.GetId())
        
        npts_low_txt = wx.StaticText(self, -1, 'Npts')
        self.npts_low_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH*2/3, -1),name='npts_low_tcl')
        wx.EVT_TEXT(self, self.npts_low_tcl.GetId(), self._on_text)
        msg_hint = "Number of Q points to consider"
        msg_hint +="while extrapolating the low-Q region"
        self.npts_low_tcl.SetToolTipString(msg_hint)
        power_txt = wx.StaticText(self, -1, 'Power')
        self.power_low_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH*2/3, -1),name='power_low_tcl')
        wx.EVT_TEXT(self, self.power_low_tcl.GetId(), self._on_text)
       
        power_hint_txt = "Exponent to apply to the Power_law function."
        self.power_low_tcl.SetToolTipString(power_hint_txt)
        iy = 0
        ix = 0
        self.low_q_sizer.Add(self.enable_low_cbox,(iy, ix),(1,5),
                            wx.TOP|wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        iy += 1
        ix = 0
        self.low_q_sizer.Add(npts_low_txt,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.low_q_sizer.Add(self.npts_low_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        iy += 1
        ix = 0
        self.low_q_sizer.Add(self.guinier,(iy, ix),(1,2),
                             wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        iy += 1
        ix = 0
        self.low_q_sizer.Add(self.power_law_low,(iy, ix),(1,2),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
       
        # Parameter controls for power law
        ix = 1
        iy += 1
        self.low_q_sizer.Add(self.fix_enable_low,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix += 1
        self.low_q_sizer.Add(self.fit_enable_low,(iy, ix),(1,1),
                           wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix = 1
        iy += 1
        self.low_q_sizer.Add(power_txt,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix += 1
        self.low_q_sizer.Add(self.power_low_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        self.low_extrapolation_sizer.AddMany([(self.low_q_sizer, 0,
                                                wx.BOTTOM|wx.RIGHT, 15)])
        
    def _enable_fit_power_law_high(self, event=None):
        """
        Enable and disable the power value editing
        """
        if event != None: 
            self.button_bookmark.Enable(True)
            self.button_report.Disable()
        if self.fix_enable_high.IsEnabled():
            if self.fix_enable_high.GetValue():
                self.fit_enable_high.SetValue(False)
                self.power_high_tcl.Enable()
            else:
                self.fit_enable_high.SetValue(True)
                self.power_high_tcl.Disable()
        self._set_state(event=event)
        
    def _enable_high_q_section(self, event=None):
        """
        Disable or enable some button if the user enable high q extrapolation
        """
        if event != None: 
            self.button_bookmark.Enable(True)
            self.button_report.Disable()
        if self.enable_high_cbox.GetValue():
            self.npts_high_tcl.Enable()
            self.power_law_high.Enable()
            self.power_high_tcl.Enable()
            self.fix_enable_high.Enable()
            self.fit_enable_high.Enable()
        else:
            self.npts_high_tcl.Disable()
            self.power_law_high.Disable()
            self.power_high_tcl.Disable()
            self.fix_enable_high.Disable()
            self.fit_enable_high.Disable()
        self._enable_fit_power_law_high()
        self._set_state(event=event)
        self.button_calculate.SetFocus()
 
    def _layout_extrapolation_high(self):
        """
        Draw widgets related to extrapolation at high q range
        """
        self.enable_high_cbox = wx.CheckBox(self, -1, "Enable Extrapolate high-Q", name='enable_high_cbox')
        wx.EVT_CHECKBOX(self, self.enable_high_cbox.GetId(),
                                         self._enable_high_q_section)
        self.fix_enable_high = wx.RadioButton(self, -1, 'Fix',
                                         (10, 10),style=wx.RB_GROUP,name='fix_enable_high')
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_fit_power_law_high,
                                     id=self.fix_enable_high.GetId())
        self.fit_enable_high = wx.RadioButton(self, -1, 'Fit', (10, 10),name='fit_enable_high')     
        self.Bind(wx.EVT_RADIOBUTTON, self._enable_fit_power_law_high, 
                                        id=self.fit_enable_high.GetId())
        
        self.power_law_high = wx.StaticText(self, -1, 'Power Law')
        msg_hint ="Check to extrapolate data at high-Q"
        self.power_law_high.SetToolTipString(msg_hint)
        npts_high_txt = wx.StaticText(self, -1, 'Npts')
        self.npts_high_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH*2/3, -1),name='npts_high_tcl')
        wx.EVT_TEXT(self, self.npts_high_tcl.GetId(), self._on_text)
        msg_hint = "Number of Q points to consider"
        msg_hint += "while extrapolating the high-Q region"
        self.npts_high_tcl.SetToolTipString(msg_hint)
        power_txt = wx.StaticText(self, -1, 'Power')
        self.power_high_tcl = InvTextCtrl(self, -1, size=(_BOX_WIDTH*2/3, -1),name='power_high_tcl')
        wx.EVT_TEXT(self, self.power_high_tcl.GetId(), self._on_text)
        power_hint_txt = "Exponent to apply to the Power_law function."
        self.power_high_tcl.SetToolTipString(power_hint_txt)
        iy = 0
        ix = 0
        self.high_q_sizer.Add(self.enable_high_cbox,(iy, ix),(1,5),
                            wx.TOP|wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        iy += 1
        ix = 0
        self.high_q_sizer.Add(npts_high_txt,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.high_q_sizer.Add(self.npts_high_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        iy += 2
        ix = 0
        self.high_q_sizer.Add(self.power_law_high,(iy, ix),(1,2),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
       
        # Parameter controls for power law
        ix = 1
        iy += 1
        self.high_q_sizer.Add(self.fix_enable_high,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix += 1
        self.high_q_sizer.Add(self.fit_enable_high,(iy, ix),(1,1),
                           wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix = 1
        iy += 1
        self.high_q_sizer.Add(power_txt,(iy, ix),(1,1),
                            wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.high_q_sizer.Add(self.power_high_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        self.high_extrapolation_sizer.AddMany([(self.high_q_sizer, 0, 
                                                wx.BOTTOM|wx.RIGHT, 10)])
        
    def _layout_extrapolation(self):
        """
        Draw widgets related to extrapolation
        """
        extra_hint = "Extrapolation Maximum Q Range [1/A]: "
        extra_hint_txt = wx.StaticText(self, -1, extra_hint)
        #Extrapolation range [string]
        extrapolation_min_txt = wx.StaticText(self, -1, 'Min :')  
        self.extrapolation_min_tcl = OutputTextCtrl(self, -1, 
                                                size=(_BOX_WIDTH, 20), style=0,name='extrapolation_min_tcl')
        self.extrapolation_min_tcl.SetValue(str(Q_MINIMUM))
        self.extrapolation_min_tcl.SetToolTipString("The minimum extrapolated q value.")
        extrapolation_max_txt = wx.StaticText(self, -1, 'Max :') 
        self.extrapolation_max_tcl = OutputTextCtrl(self, -1,
                                                  size=(_BOX_WIDTH, 20), style=0,name='extrapolation_max_tcl') 
        self.extrapolation_max_tcl.SetValue(str(Q_MAXIMUM))
        self.extrapolation_max_tcl.SetToolTipString("The maximum extrapolated q value.")
        self.extrapolation_range_sizer.AddMany([(extra_hint_txt, 0, wx.LEFT, 10),
                                                (extrapolation_min_txt, 0, wx.LEFT, 10),
                                                (self.extrapolation_min_tcl,
                                                            0, wx.LEFT, 10),
                                                (extrapolation_max_txt, 0, wx.LEFT, 10),
                                                (self.extrapolation_max_tcl,
                                                            0, wx.LEFT, 10),
                                                ])
        self._layout_extrapolation_low()
        self._layout_extrapolation_high()
        self.extrapolation_low_high_sizer.AddMany([(self.low_extrapolation_sizer,
                                                     0, wx.ALL, 5),
                                                   (self.high_extrapolation_sizer,
                                                    0, wx.ALL, 5)])
        self.extrapolation_sizer.AddMany([(self.extrapolation_range_sizer, 0,
                                            wx.RIGHT, 5),
                                        (self.extrapolation_low_high_sizer, 0,
                                           wx.ALL, 5)])
        
    def _layout_volume_surface_sizer(self):
        """
        Draw widgets related to volume and surface
        """
        unit_volume = ''
        unit_surface = ''
        uncertainty = "+/-" 
        volume_txt = wx.StaticText(self, -1, 'Volume Fraction      ')
        self.volume_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1),name='volume_tcl')
        wx.EVT_TEXT(self, self.volume_tcl.GetId(), self._on_out_text)
        self.volume_tcl.SetToolTipString("Volume fraction.")
        self.volume_err_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1),name='volume_err_tcl')
        wx.EVT_TEXT(self, self.volume_err_tcl.GetId(), self._on_out_text)
        self.volume_err_tcl.SetToolTipString("Uncertainty on the volume fraction.")
        volume_units_txt = wx.StaticText(self, -1, unit_volume)
        
        surface_txt = wx.StaticText(self, -1, 'Specific Surface')
        self.surface_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1),name='surface_tcl')
        wx.EVT_TEXT(self, self.surface_tcl.GetId(), self._on_out_text)
        self.surface_tcl.SetToolTipString("Specific surface value.")
        self.surface_err_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1),name='surface_err_tcl')
        wx.EVT_TEXT(self, self.surface_err_tcl.GetId(), self._on_out_text)
        self.surface_err_tcl.SetToolTipString("Uncertainty on the specific surface.")
        surface_units_txt = wx.StaticText(self, -1, unit_surface)
        iy = 0
        ix = 0
        self.volume_surface_sizer.Add(volume_txt, (iy, ix), (1,1),
                             wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.volume_surface_sizer.Add(self.volume_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 10)
        ix += 1
        self.volume_surface_sizer.Add(wx.StaticText(self, -1, uncertainty),
                         (iy, ix),(1,1),wx.EXPAND|wx.ADJUST_MINSIZE, 10) 
        ix += 1
        self.volume_surface_sizer.Add(self.volume_err_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 10) 
        ix += 1
        self.volume_surface_sizer.Add(volume_units_txt, (iy, ix), (1,1),
                             wx.EXPAND|wx.ADJUST_MINSIZE, 10)
        iy += 1
        ix = 0
        self.volume_surface_sizer.Add(surface_txt, (iy, ix), (1,1),
                             wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.volume_surface_sizer.Add(self.surface_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0)
        ix += 1
        self.volume_surface_sizer.Add(wx.StaticText(self, -1, uncertainty),
                         (iy, ix),(1,1),wx.EXPAND|wx.ADJUST_MINSIZE, 0) 
        ix += 1
        self.volume_surface_sizer.Add(self.surface_err_tcl, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 0) 
        ix += 1
        self.volume_surface_sizer.Add(surface_units_txt, (iy, ix), (1,1),
                            wx.EXPAND|wx.ADJUST_MINSIZE, 10)
        
    def _layout_invariant_sizer(self):
        """
        Draw widgets related to invariant
        """
        uncertainty = "+/-" 
        unit_invariant = '[1/(cm * A)]'
        invariant_total_txt = wx.StaticText(self, -1, 'Invariant Total [Q*]')
        self.invariant_total_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1),name='invariant_total_tcl')
        msg_hint = "Total invariant [Q*], including extrapolated regions."
        self.invariant_total_tcl.SetToolTipString(msg_hint)
        self.invariant_total_err_tcl = OutputTextCtrl(self, -1, size=(_BOX_WIDTH,-1),name='invariant_total_err_tcl')
        self.invariant_total_err_tcl.SetToolTipString("Uncertainty on invariant.")
        invariant_total_units_txt = wx.StaticText(self, -1, unit_invariant)
    
        #Invariant total
        iy = 0
        ix = 0
        self.invariant_sizer.Add(invariant_total_txt, (iy, ix), (1,1),
                             wx.LEFT|wx.EXPAND|wx.ADJUST_MINSIZE, 15)
        ix += 1
        self.invariant_sizer.Add(self.invariant_total_tcl, (iy, ix), (1,1),
                          wx.EXPAND|wx.ADJUST_MINSIZE, 10)
        ix += 1
        self.invariant_sizer.Add( wx.StaticText(self, -1, uncertainty),
                         (iy, ix),(1,1),wx.EXPAND|wx.ADJUST_MINSIZE, 10) 
        ix += 1
        self.invariant_sizer.Add(self.invariant_total_err_tcl, (iy, ix), (1,1),
                             wx.EXPAND|wx.ADJUST_MINSIZE, 10)
        ix += 1
        self.invariant_sizer.Add(invariant_total_units_txt,(iy, ix), (1,1),
                          wx.EXPAND|wx.ADJUST_MINSIZE, 10)
 
    def _layout_inputs_sizer(self):
        """
        Draw widgets related to inputs
        """
        self._layout_bkg_scale()
        self._layout_contrast_porod()
        self.inputs_sizer.AddMany([(self.bkg_scale_sizer, 0, wx.ALL, 5),
                                    (self.contrast_porod_sizer, 0, wx.ALL, 5)])
        
    def _layout_outputs_sizer(self):
        """
        Draw widgets related to outputs
        """
        self._layout_volume_surface_sizer()
        self._layout_invariant_sizer()
        static_line = wx.StaticLine(self, -1)
        self.outputs_sizer.AddMany([(self.volume_surface_sizer, 0, wx.ALL, 10),
                                    (static_line, 0, wx.EXPAND, 0),
                                    (self.invariant_sizer, 0, wx.ALL, 10)])
    def _layout_button(self):  
        """
        Do the layout for the button widgets
        """ 
        #compute button
        id = wx.NewId()
        self.button_calculate = wx.Button(self, id, "Compute", name ='compute_invariant' )
        self.button_calculate.SetToolTipString("Compute invariant")
        self.Bind(wx.EVT_BUTTON, self.compute_invariant, id=id)   
        #detail button
        id = wx.NewId()
        self.button_details = wx.Button(self, id, "Details?")
        self.button_details.SetToolTipString("Details about the results of the computation")
        self.Bind(wx.EVT_BUTTON, self.display_details, id=id)
        details = "Details on Invariant Total Calculations"
        details_txt = wx.StaticText(self, -1, details)
        self.button_sizer.AddMany([((50,10), 0 , wx.LEFT,0),
                                   (details_txt, 0 , 
                                    wx.RIGHT|wx.BOTTOM|wx.TOP, 10),
                                   (self.button_details, 0 , wx.ALL, 10),
                        (self.button_calculate, 0 , wx.RIGHT|wx.TOP|wx.BOTTOM, 10)])#,
                                   #(self.button_undo, 0 , wx.ALL, 10),
                                   #(self.button_redo, 0 , wx.ALL, 10)])
    def _layout_save_button(self):  
        """
        Do the layout for the save button widgets
        """ 
        import sans.perspectives.invariant as inv

        path = inv.get_data_path(media='media')
        self.undo_png = os.path.join(path,"undo.png")
        self.redo_png = os.path.join(path,"redo.png")
        self.bookmark_png = os.path.join(path,"bookmark.png")
        self.report_png = os.path.join(path,"report.png")
        self.save_png = os.path.join(path,"save.png")
        #undo button
        id = wx.NewId()
        self.button_undo = wx.BitmapButton(self, id,wx.Bitmap(self.undo_png))#wx.Button(self, id, "Undo",size=(50,20))
        self.button_undo.SetToolTipString("Undo")
        
        #self.button_undo.SetBackgroundColour('#c2e6f8')
        self.Bind(wx.EVT_BUTTON, self.undo, id=id)
        self._undo_disable()
        #redo button
        id = wx.NewId()
        self.button_redo = wx.BitmapButton(self, id,wx.Bitmap(self.redo_png))#wx.Button(self, id, "Redo",size=(50,20))
        self.button_redo.SetToolTipString("Redo")
        self.Bind(wx.EVT_BUTTON, self.redo, id=id)
        self._redo_disable()   
        #bookmark button
        id = wx.NewId()
        self.button_bookmark = wx.BitmapButton(self, id,wx.Bitmap(self.bookmark_png))#wx.Button(self, id, "Undo",size=(50,20))
        self.button_bookmark.SetToolTipString("Bookmark: right-click on the panel to retrieve it")
        self.Bind(wx.EVT_BUTTON, self._on_bookmark, id=id)
        #report button
        id = wx.NewId()
        self.button_report = wx.BitmapButton(self, id,wx.Bitmap(self.report_png))#wx.Button(self, id, "Redo",size=(50,20))
        self.button_report.SetToolTipString("Report the result of the computation")
        self.Bind(wx.EVT_BUTTON, self.report, id=id)
        #self.button_report.Disable()   
        #save button
        id = wx.NewId()
        self.button_save = wx.BitmapButton(self, id,wx.Bitmap(self.save_png), name ='Save_invariant')#wx.Button(self, id, "Save", name ='Save_invariant' )
        self.button_save.SetToolTipString("Save as a file")
        self.Bind(wx.EVT_BUTTON, self._on_save_button, id=id)   
        self.button_save.Disable()  
        self.save_button_sizer.AddMany([((PANEL_WIDTH/2,20), 1 , wx.EXPAND|wx.ADJUST_MINSIZE,0),
                                   (self.button_undo, 0 ,wx.LEFT|wx.ADJUST_MINSIZE, 10),
                                   (self.button_redo, 0 ,wx.LEFT|wx.ADJUST_MINSIZE, 10),
                                   (self.button_bookmark, 0 ,wx.LEFT|wx.ADJUST_MINSIZE, 10),
                                   (self.button_report, 0 ,wx.LEFT|wx.ADJUST_MINSIZE, 10),
                                   (self.button_save, 0 ,wx.LEFT|wx.ADJUST_MINSIZE, 10)])        
    def _do_layout(self):
        """
        Draw window content
        """
        self._define_structure()
        self._layout_data_name()
        self._layout_extrapolation()
        self._layout_inputs_sizer()
        self._layout_outputs_sizer()
        self._layout_button()
        self._layout_save_button()
        self.main_sizer.AddMany([(self.data_name_boxsizer,0, wx.ALL, 10),
                                  (self.outputs_sizer, 0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),
                                  (self.button_sizer,0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),
                                 (self.inputs_sizer, 0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),
                                  (self.extrapolation_sizer, 0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10),\
                                  (self.save_button_sizer,0,
                                  wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)])
        self.SetSizer(self.main_sizer)
        self.SetAutoLayout(True)
        
        
class InvariantDialog(wx.Dialog):
    """
    """
    def __init__(self, parent=None, id=1,graph=None,
                 data=None, title="Invariant",base=None):
        wx.Dialog.__init__(self, parent, id, title, size=(PANEL_WIDTH,
                                                             PANEL_HEIGHT))
        self.panel = InvariantPanel(self)
        self.Centre()
        self.Show(True)
        
class InvariantWindow(wx.Frame):
    """
    """
    def __init__(self, parent=None, id=1,graph=None, 
                 data=None, title="Invariant",base=None):
        
        wx.Frame.__init__(self, parent, id, title, size=(PANEL_WIDTH +100,
                                                             PANEL_HEIGHT+100))
        from DataLoader.loader import  Loader
        self.loader = Loader()
        import invariant

        data= self.loader.load("C:/ECLPS/workspace/trunk/DataLoader/test/ascii_test_3.txt")
        self.panel = InvariantPanel(self)

        data.name = data.filename
        self.panel.set_data(data)
        self.Centre()
        self.Show(True)
        
class MyApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        frame = InvariantWindow()
        frame.Show(True)
        self.SetTopWindow(frame)
        
        return True
      
# end of class MyApp

if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()