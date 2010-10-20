

################################################################################
#This software was developed by the University of Tennessee as part of the
#Distributed Data Analysis of Neutron Scattering Experiments (DANSE)
#project funded by the US National Science Foundation. 
#
#See the license text in license.txt
#
#copyright 2009, University of Tennessee
################################################################################

import time
import os
import sys
import copy
import logging
import numpy

import xml.dom.minidom
from xml.dom.minidom import parse
from lxml import etree

import DataLoader
from DataLoader.readers.cansas_reader import Reader as CansasReader
from DataLoader.readers.cansas_reader import get_content, write_node
from DataLoader.data_info import Data2D, Detector

#Information to read/write state as xml
FITTING_NODE_NAME = 'fitting_plug_in'
CANSAS_NS = "cansas1d/1.0"

list_of_data_attributes = [["is_data", "is_data", "bool"],
                      ["group_id", "data_group_id", "string"],
                      ["data_name", "data_name", "string"],
                      ["data_id", "data_id", "string"],
                      ["name", "name", "string"],
                      ["data_name", "data_name", "string"]]
list_of_state_attributes = [["engine_type", "engine_type", "string"],
                       ["qmin", "qmin", "float"],
                      ["qmax", "qmax", "float"],
                      ["npts", "npts", "float"],
                      ["shape_rbutton", "shape_rbutton", "bool"],
                      ["shape_indep_rbutton", "shape_indep_rbutton", "bool"],
                      ["plugin_rbutton", "plugin_rbutton","bool"],
                      ["struct_rbutton", "struct_rbutton", "bool"],
                      ["formfactorcombobox", "formfactorcombobox", "float"],
                      ["structurecombobox", "structurecombobox", "float"],
                      ["disp_box", "disp_box", "float"],
                      ["enable_smearer","enable_smearer","bool"],
                      ["disable_smearer","disable_smearer","bool"],
                      ["pinhole_smearer","pinhole_smearer","bool"],
                      ["slit_smearer","slit_smearer","bool"],
                      ["enable_disp","enable_disp","bool"],
                      ["disable_disp","disable_disp","bool"],
                      ["slit_smearer","slit_smearer","bool"],
                      ["enable2D","enable2D","bool"],
                      ["cb1","cb1","bool"],
                      ["tcChi","tcChi","float"],
                     ["smearer", "smearer", "float"],
                     ["smear_type","smear_type", "string"],
                     ["dq_l", "dq_l", "string"],
                     ["dq_r","dq_r", "string"]]

list_of_model_attributes = [["values", "values"],
                            ["weights", "weights"]]

list_of_state_parameters = [["parameters", "parameters"] , 
                            ["str_parameters", "str_parameters"] ,                     
                            ["orientation_parameters", "orientation_params"],
                            ["dispersity_parameters", "orientation_params_disp"],
                            ["fixed_param", "fixed_param"],                      
                            ["fittable_param","fittable_param"]]
list_of_data_2d_attr = [["xmin", "xmin","float"],
                        ["xmax","xmax","float"],
                        ["ymin","ymin","float"],
                        ["ymax","ymax","float"],
                        ["_xaxis","_xaxis", "string"],
                        ["_xunit", "_xunit", "string"],
                        ["_yaxis","_yaxis","string"],
                        ["_yunit","_yunit","string"],
                        ["_zaxis","_zaxis","string"],
                        ["_zunit","_zunit","string"]]
list_of_data2d_values = [["qx_data","qx_data","float"],
                         ["qy_data","qy_data","float"],
                         ["dqx_data","dqx_data","float"],
                         ["dqy_data","dqy_data","float"],
                         ["data","data","float"],
                         ["q_data","q_data","float"],
                         ["err_data","err_data","float"],
                         ["mask","mask","bool"]]

def parse_entry_helper( node, item):
    """
    Create a numpy list from value extrated from the node
    
    :param node: node from each the value is stored
    :param item: list name of three strings.the two first are name of data
        attribute and the third one is the type of the value of that 
        attribute. type can be string, float, bool, etc.
    
    : return: numpy array
    """
    if node is not None:
        if item[2] == "string":
            return str(node.get(item[0]).strip())
        elif item[2] == "bool":
            try:
                return node.get(item[0]).strip() == "True"
                
            except:
                return None
        else:
            try:
                return float(node.get(item[0]))
            except:
                return None
            
            
class PageState(object):
    """
    Contains information to reconstruct a page of the fitpanel.
    """
    def __init__(self, parent=None, model=None, data=None):
        
        """ 
        Initialize the current state
        
        :param model: a selected model within a page
        :param data: 
        
        """
        self.file = None
        #Time of state creation
        self.timestamp = time.time()
        ## Data member to store the dispersion object created
        self._disp_obj_dict = {}
        #------------------------
        #Data used for fitting 
        self.data = data
        #save additional information on data that dataloader.reader does not read
        self.is_data = None
        self.data_name = ""
        
        if self.data is not None:
            self.data_name = self.data.name
        self.data_id = None
        if self.data is not None and hasattr(self.data, "id"):
            self.data_id = self.data.id
        self.data_group_id = None
        if self.data is not None and hasattr(self.data, "group_id"):
            self.data_group_id = self.data.group_id
        
        ## reset True change the state of exsiting button
        self.reset = False
       
        #engine type
        self.engine_type = None
        # flag to allow data2D plot
        self.enable2D = False
        # model on which the fit would be performed
        self.model = model
       
        #fit page manager 
        self.manager = None
        #Store the parent of this panel parent
        # For this application fitpanel is the parent
        self.parent  = parent
        # Event_owner is the owner of model event
        self.event_owner = None
        ##page name
        self.page_name = ""
        # Contains link between  model ,all its parameters, and panel organization
        self.parameters = []
        # String parameter list that can not be fitted
        self.str_parameters = []
        # Contains list of parameters that cannot be fitted and reference to 
        #panel objects 
        self.fixed_param = []
        # Contains list of parameters with dispersity and reference to 
        #panel objects 
        self.fittable_param = []
        ## orientation parameters
        self.orientation_params = []
        ## orientation parmaters for gaussian dispersity
        self.orientation_params_disp = []
        ## smearer info
        self.smearer = None
        self.smear_type = None
        self.dq_l = None
        self.dq_r = None

        #list of dispersion paramaters
        self.disp_list =[]
        if self.model is not None:
            self.disp_list = self.model.getDispParamList()
        self._disp_obj_dict = {}
        self.disp_cb_dict = {}
        self.values = []
        self.weights = []
                    
        #contains link between a model and selected parameters to fit 
        self.param_toFit = []
        ##dictionary of model type and model class
        self.model_list_box = None
        ## save the state of the context menu
        self.saved_states = {}
        ## save selection of combobox
        self.formfactorcombobox = None
        self.structurecombobox  = None
        ## radio box to select type of model
        self.shape_rbutton = False
        self.shape_indep_rbutton = False
        self.struct_rbutton = False
        self.plugin_rbutton = False
        ## the indice of the current selection
        self.disp_box = 0
        ## Qrange
        ## Q range
        self.qmin = 0.001
        self.qmax = 0.1
        #reset data range
        self.qmax_x = None
        self.qmin_x = None
        
        self.npts = None
        self.name = ""
        self.multi_factor = None
        ## enable smearering state
        self.enable_smearer = False
        self.disable_smearer = True
        self.pinhole_smearer = False
        self.slit_smearer   = False
        ## disperity selection
        self.enable_disp = False
        self.disable_disp = True
       
        ## state of selected all check button
        self.cb1 = False
        ## store value of chisqr
        self.tcChi = None
    
    def clone(self):
        """
        Create a new copy of the current object
        """
        model = None
        if self.model is not None:
            model = self.model.clone()
            model.name = self.model.name
        obj = PageState(self.parent, model=model)
        obj.file = copy.deepcopy(self.file)
        obj.data = copy.deepcopy(self.data)
        if self.data is not None:
            self.data_name = self.data.name
        obj.data_name = self.data_name
        obj.is_data = self.is_data
        obj.model_list_box = copy.deepcopy(self.model_list_box)
        obj.engine_type = copy.deepcopy(self.engine_type)
        
        obj.formfactorcombobox = self.formfactorcombobox
        obj.structurecombobox  = self.structurecombobox  
        
        obj.shape_rbutton = self.shape_rbutton 
        obj.shape_indep_rbutton = self.shape_indep_rbutton
        obj.struct_rbutton = self.struct_rbutton
        obj.plugin_rbutton = self.plugin_rbutton
        
        obj.manager = self.manager
        obj.event_owner = self.event_owner
        obj.disp_list = copy.deepcopy(self.disp_list)
        
        obj.enable2D = copy.deepcopy(self.enable2D)
        obj.parameters = copy.deepcopy(self.parameters)
        obj.str_parameters = copy.deepcopy(self.str_parameters)
        obj.fixed_param = copy.deepcopy(self.fixed_param)
        obj.fittable_param = copy.deepcopy(self.fittable_param)
        obj.orientation_params =  copy.deepcopy(self.orientation_params)
        obj.orientation_params_disp =  copy.deepcopy(self.orientation_params_disp)
        obj.enable_disp = copy.deepcopy(self.enable_disp)
        obj.disable_disp = copy.deepcopy(self.disable_disp)
        obj.tcChi = self.tcChi
  
        if len(self._disp_obj_dict)>0:
            for k , v in self._disp_obj_dict.iteritems():
                obj._disp_obj_dict[k]= v
        if len(self.disp_cb_dict)>0:
            for k , v in self.disp_cb_dict.iteritems():
                obj.disp_cb_dict[k]= v
                
        obj.values = copy.deepcopy(self.values)
        obj.weights = copy.deepcopy(self.weights)
        obj.enable_smearer = copy.deepcopy(self.enable_smearer)
        obj.disable_smearer = copy.deepcopy(self.disable_smearer)
        obj.pinhole_smearer = copy.deepcopy(self.pinhole_smearer)
        obj.slit_smearer = copy.deepcopy(self.slit_smearer)
        obj.smear_type = copy.deepcopy(self.smear_type)
        obj.dq_l = copy.deepcopy(self.dq_l)
        obj.dq_r = copy.deepcopy(self.dq_r)

        obj.disp_box = copy.deepcopy(self.disp_box)
        obj.qmin = copy.deepcopy(self.qmin)
        obj.qmax = copy.deepcopy(self.qmax)
        obj.multi_factor = copy.deepcopy(self.multi_factor)
        obj.npts = copy.deepcopy(self.npts )
        obj.cb1 = copy.deepcopy(self.cb1)
        obj.smearer = copy.deepcopy(self.smearer)
        
        for name, state in self.saved_states.iteritems():
            copy_name = copy.deepcopy(name)
            copy_state = state.clone()
            obj.saved_states[copy_name]= copy_state
        return obj
    
    def _repr_helper(self, list, rep):
        """
        Helper method to print a state
        """
        for item in list:
            rep += "parameter name: %s \n"%str(item[1])
            rep += "value: %s\n"%str(item[2])
            rep += "selected: %s\n"%str(item[0])
            rep += "error displayed : %s \n"%str(item[4][0])
            rep += "error value:%s \n"%str(item[4][1])
            rep += "minimum displayed : %s \n"%str(item[5][0])
            rep += "minimum value : %s \n"%str(item[5][1])
            rep += "maximum displayed : %s \n"%str(item[6][0])
            rep += "maximum value : %s \n"%str(item[6][1])
            rep += "parameter unit: %s\n\n"%str(item[7])
        return rep
    
    def __repr__(self):
        """ 
        output string for printing
        """
        rep = "\nState name: %s\n"%self.file
        t = time.localtime(self.timestamp)
        time_str = time.strftime("%b %d %H:%M", t)
        rep += "State created on : %s\n"%time_str
        rep += "State form factor combobox selection: %s\n"%self.formfactorcombobox
        rep += "State structure factor combobox selection: %s\n"%self.structurecombobox
        rep += "is data : %s\n"%self.is_data
        rep += "data's name : %s\n"%self.data_name
        rep += "data's id : %s\n"%self.data_id
        rep += "model type (form factor) selected: %s\n"%self.shape_rbutton 
        rep += "model type (shape independent) selected: %s\n"%self.shape_indep_rbutton
        rep += "model type (structure factor) selected: %s\n"%self.struct_rbutton
        rep += "model type (plug-in ) selected: %s\n"%self.plugin_rbutton
        rep += "data : %s\n"% str(self.data)
        rep += "Plotting Range: min: %s, max: %s, steps: %s\n"%(str(self.qmin),
                                                str(self.qmax),str(self.npts))
        rep += "Dispersion selection : %s\n"%str(self.disp_box)
        rep += "Smearing enable : %s\n"%str(self.enable_smearer)
        rep += "Smearing disable : %s\n"%str(self.disable_smearer)
        rep += "Pinhole smearer enable : %s\n"%str(self.pinhole_smearer)
        rep += "Slit smearer enable : %s\n"%str(self.slit_smearer)
        rep += "Dispersity enable : %s\n"%str(self.enable_disp)
        rep += "Dispersity disable : %s\n"%str(self.disable_disp)
        rep += "Slit smearer enable: %s\n"%str(self.slit_smearer)
        rep += "2D enable : %s\n"%str(self.enable2D)
        rep += "All parameters checkbox selected: %s\n"%(self.cb1)
        rep += "Value of Chisqr : %s\n"%str(self.tcChi)
        rep += "Smear object : %s\n"%str(self.smearer)
        rep += "Smear type : %s\n"%(self.smear_type)
        rep += "dq_l  : %s\n"%self.dq_l
        rep += "dq_r  : %s\n"%self.dq_r
        
        rep += "model  : %s\n\n"% str(self.model)
        rep += "number parameters(self.parameters): %s\n"%len(self.parameters)
        rep = self._repr_helper( list=self.parameters, rep=rep)
        rep += "number str_parameters(self.str_parameters): %s\n"%len(self.str_parameters)
        rep = self._repr_helper( list=self.str_parameters, rep=rep)
        rep += "number orientation parameters"
        rep += "(self.orientation_params): %s\n"%len(self.orientation_params)
        rep = self._repr_helper( list=self.orientation_params, rep=rep)
        rep += "number dispersity parameters"
        rep += "(self.orientation_params_disp): %s\n"%len(self.orientation_params_disp)
        rep = self._repr_helper( list=self.orientation_params_disp, rep=rep)
        
        return rep
   
    def _toXML_helper(self, list, element, newdoc):
        """
        Helper method to create xml file for saving state
        """
        for item in list:
            sub_element = newdoc.createElement('parameter')
            sub_element.setAttribute('name', str(item[1]))
            sub_element.setAttribute('value', str(item[2]))
            sub_element.setAttribute('selected_to_fit', str(item[0]))
            sub_element.setAttribute('error_displayed', str(item[4][0]))
            sub_element.setAttribute('error_value', str(item[4][1]))
            sub_element.setAttribute('minimum_displayed', str(item[5][0]))
            sub_element.setAttribute('minimum_value', str(item[5][1]))
            sub_element.setAttribute('maximum_displayed', str(item[6][0]))
            sub_element.setAttribute('maximum_value', str(item[6][1]))
            sub_element.setAttribute('unit', str(item[7]))
            element.appendChild(sub_element)
        
    def toXML(self, file="fitting_state.fitv", doc=None, entry_node=None):
        """
        Writes the state of the InversionControl panel to file, as XML.
        
        Compatible with standalone writing, or appending to an
        already existing XML document. In that case, the XML document
        is required. An optional entry node in the XML document may also be given.
        
        :param file: file to write to
        :param doc: XML document object [optional]
        :param entry_node: XML node within the XML document at which we will append the data [optional]
        
        """
        from xml.dom.minidom import getDOMImplementation

        # Check whether we have to write a standalone XML file
        if doc is None:
            impl = getDOMImplementation()
            doc_type = impl.createDocumentType(FITTING_NODE_NAME, "1.0", "1.0")     
            newdoc = impl.createDocument(None, FITTING_NODE_NAME, doc_type)
            top_element = newdoc.documentElement
        else:
            # We are appending to an existing document
            newdoc = doc
            top_element = newdoc.createElement(FITTING_NODE_NAME)
            if entry_node is None:
                newdoc.documentElement.appendChild(top_element)
            else:
                entry_node.appendChild(top_element)
            
        attr = newdoc.createAttribute("version")
        attr.nodeValue = '1.0'
        top_element.setAttributeNode(attr)
        
        # File name
        element = newdoc.createElement("filename")
        if self.file is not None:
            element.appendChild(newdoc.createTextNode(str(self.file)))
        else:
            element.appendChild(newdoc.createTextNode(str(file)))
        top_element.appendChild(element)
        
        element = newdoc.createElement("timestamp")
        element.appendChild(newdoc.createTextNode(time.ctime(self.timestamp)))
        attr = newdoc.createAttribute("epoch")
        attr.nodeValue = str(self.timestamp)
        element.setAttributeNode(attr)
        top_element.appendChild(element)
        # Inputs
        inputs = newdoc.createElement("Attributes")
        top_element.appendChild(inputs)
       

        if self.data is not None and hasattr(self.data, "group_id"):
            self.data_group_id = self.data.group_id
        if self.data is not None and hasattr(self.data, "is_data"):
            self.is_data = self.data.is_data
        if self.data is not None:
            self.data_name = self.data.name
        if self.data is not None and hasattr(self.data, "id"):
            self.data_id = self.data.id
       
        for item in list_of_data_attributes:
            element = newdoc.createElement(item[0])
            exec "element.setAttribute(item[0], str(self.%s))"%(item[1])
            inputs.appendChild(element)   
        
        for item in list_of_state_attributes:
            element = newdoc.createElement(item[0])
            exec "element.setAttribute(item[0], str(self.%s))"%(item[1])
            inputs.appendChild(element)
            
        for item in list_of_model_attributes:
            element = newdoc.createElement(item[0])
            exec "list = self.%s"%item[1]
            for value in list:
                exec "element.appendChild(newdoc.createTextNode(str(%s)))"%value
            inputs.appendChild(element)
            
        for item in list_of_state_parameters:
            element = newdoc.createElement(item[0])
            exec "self._toXML_helper(list=self.%s, element=element, newdoc=newdoc)"%item[1]                       
            inputs.appendChild(element)
       
        # Save the file
        if doc is None:
            fd = open(file, 'w')
            fd.write(newdoc.toprettyxml())
            fd.close()
            return None
        else:
            return newdoc.toprettyxml()
        
    def _fromXML_helper(self, node, list):
        """
        Helper function to write state to xml
        """
        for item in node:
            try:
                name = item.get('name')
            except:
                name = None
            try:
                value = item.get('value')
            except:
                value = None
            try:
                selected_to_fit = (item.get('selected_to_fit') == "True")
            except:
                selected_to_fit = None
            try:
                error_displayed = (item.get('error_displayed') == "True")
            except:
                error_displayed = None
            try:  
                error_value = item.get('error_value')
            except:
                error_value = None
            try:
                minimum_displayed = (item.get('minimum_displayed')== "True")
            except:
                minimum_displayed = None
            try:
                minimum_value = item.get('minimum_value')
            except:
                minimum_value = None
            try:
                maximum_displayed = (item.get('maximum_displayed') == "True")
            except:
                maximum_displayed = None
            try:
                maximum_value = item.get('maximum_value')
            except:
                maximum_value = None
            try:
                unit = item.get('unit')
            except:
                unit = None
            list.append([selected_to_fit, name, value, "+/-",[error_displayed, error_value],
                         [minimum_displayed,minimum_value],[maximum_displayed,maximum_value], unit])
       
    def fromXML(self, file=None, node=None):
        """
        Load fitting state from a file
        
        :param file: .fitv file
        :param node: node of a XML document to read from
        
        """
        if file is not None:
            msg = "PageState no longer supports non-CanSAS"
            msg += " format for fitting files"
            raise RuntimeError, msg
            
        if node.get('version')and node.get('version') == '1.0':
            
            # Get file name
            entry = get_content('ns:filename', node)
            if entry is not None:
                self.file = entry.text.strip()
                
            # Get time stamp
            entry = get_content('ns:timestamp', node)
            if entry is not None and entry.get('epoch'):
                try:
                    self.timestamp = float(entry.get('epoch'))
                except:
                    msg = "PageState.fromXML: Could not"
                    msg += " read timestamp\n %s" % sys.exc_value
                    logging.error(msg)
            
            # Parse fitting attributes
            entry = get_content('ns:Attributes', node)
            for item in list_of_data_attributes:
                node = get_content('ns:%s'%item[0], entry)
                try:
                    exec "self.%s = parse_entry_helper(node, item)"%item[0]
                    
                except:
                    raise
            
            if entry is not None:
                
                for item in list_of_state_attributes:
                    node = get_content('ns:%s'%item[0], entry)
                    try:
                        exec "self.%s = parse_entry_helper(node, item)"%str(item[0])
                    except:
                        raise
                    
                for item in list_of_model_attributes:
                    node = get_content("ns:%s"%item[0], entry)
                    list = []
                    for value in node:
                        try:
                            list.append(float(value)) 
                        except:
                            list.append(None)
                    exec "self.%s = list"%item[1]
                
                for item in list_of_state_parameters:
                    node = get_content("ns:%s"%item[0], entry)
                    exec "self._fromXML_helper(node=node, list=self.%s)"%item[1]
                   

class Reader(CansasReader):
    """
    Class to load a .fitv fitting file
    """
    ## File type
    type_name = "Fitting"
    
    ## Wildcards
    type = ["Fitting files (*.fitv)|*.fitv"
            "SANSView file (*.svs)|*.svs"]
    ## List of allowed extensions
    ext=['.fitv', '.FITV', '.svs', 'SVS']   
    
    def __init__(self, call_back=None, cansas=True):
        CansasReader.__init__(self)
        """
        Initialize the call-back method to be called
        after we load a file
        
        :param call_back: call-back method
        :param cansas:  True = files will be written/read in CanSAS format
                        False = write CanSAS format
            
        """
        ## Call back method to be executed after a file is read
        self.call_back = call_back
        ## CanSAS format flag
        self.cansas = cansas
        
    def read(self, path):
        """ 
        Load a new P(r) inversion state from file
        
        :param path: file path
        
        """
        if self.cansas == True:
            return self._read_cansas(path)
     
    def _data2d_to_xml_doc(self, datainfo):
        """
        Create an XML document to contain the content of a Data2D
        
        :param datainfo: Data2D object
        
        """
        if not issubclass(datainfo.__class__, Data2D):
            raise RuntimeError, "The cansas writer expects a Data2D instance"
        
        doc = xml.dom.minidom.Document()
        main_node = doc.createElement("SASroot")
        main_node.setAttribute("version", self.version)
        main_node.setAttribute("xmlns", "cansas1d/%s" % self.version)
        main_node.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        main_node.setAttribute("xsi:schemaLocation", "cansas1d/%s http://svn.smallangles.net/svn/canSAS/1dwg/trunk/cansas1d.xsd" % self.version)
        
        doc.appendChild(main_node)
        
        entry_node = doc.createElement("SASentry")
        main_node.appendChild(entry_node)
       
        write_node(doc, entry_node, "Title", datainfo.title)
        if datainfo is not None:
            write_node(doc, entry_node, "data_class", datainfo.__class__.__name__)
        for item in datainfo.run:
            runname = {}
            if datainfo.run_name.has_key(item) and len(str(datainfo.run_name[item]))>1:
                runname = {'name': datainfo.run_name[item] }
            write_node(doc, entry_node, "Run", item, runname)
        # Data info
        new_node = doc.createElement("SASdata")
        entry_node.appendChild(new_node)
        for item in list_of_data_2d_attr:
            element = doc.createElement(item[0])
            exec "element.setAttribute(item[0], str(datainfo.%s))"%(item[1])
            new_node.appendChild(element)
            
        for item in list_of_data2d_values:
            root_node = doc.createElement(item[0])
            new_node.appendChild(root_node)
            
            exec "temp_list = datainfo.%s"%item[1]

            if temp_list is None or len(temp_list)== 0:
                element = doc.createElement(item[0])
                exec "element.appendChild(doc.createTextNode(str(%s)))"%temp_list
                root_node.appendChild(element)
            else:
                for value in temp_list:
                    element = doc.createElement(item[0])
                    exec "element.setAttribute(item[0], str(%s))"%value
                    root_node.appendChild(element)
       
        # Sample info
        sample = doc.createElement("SASsample")
        if datainfo.sample.name is not None:
            sample.setAttribute("name", str(datainfo.sample.name))
        entry_node.appendChild(sample)
        write_node(doc, sample, "ID", str(datainfo.sample.ID))
        write_node(doc, sample, "thickness", datainfo.sample.thickness, {"unit":datainfo.sample.thickness_unit})
        write_node(doc, sample, "transmission", datainfo.sample.transmission)
        write_node(doc, sample, "temperature", datainfo.sample.temperature, {"unit":datainfo.sample.temperature_unit})
        
        for item in datainfo.sample.details:
            write_node(doc, sample, "details", item)
        
        pos = doc.createElement("position")
        written = write_node(doc, pos, "x", datainfo.sample.position.x, {"unit":datainfo.sample.position_unit})
        written = written | write_node(doc, pos, "y", datainfo.sample.position.y, {"unit":datainfo.sample.position_unit})
        written = written | write_node(doc, pos, "z", datainfo.sample.position.z, {"unit":datainfo.sample.position_unit})
        if written == True:
            sample.appendChild(pos)
        
        ori = doc.createElement("orientation")
        written = write_node(doc, ori, "roll",  datainfo.sample.orientation.x, {"unit":datainfo.sample.orientation_unit})
        written = written | write_node(doc, ori, "pitch", datainfo.sample.orientation.y, {"unit":datainfo.sample.orientation_unit})
        written = written | write_node(doc, ori, "yaw",   datainfo.sample.orientation.z, {"unit":datainfo.sample.orientation_unit})
        if written == True:
            sample.appendChild(ori)
        
        # Instrument info
        instr = doc.createElement("SASinstrument")
        entry_node.appendChild(instr)
        
        write_node(doc, instr, "name", datainfo.instrument)
        
        #   Source
        source = doc.createElement("SASsource")
        if datainfo.source.name is not None:
            source.setAttribute("name", str(datainfo.source.name))
        instr.appendChild(source)
        
        write_node(doc, source, "radiation", datainfo.source.radiation)
        write_node(doc, source, "beam_shape", datainfo.source.beam_shape)
        size = doc.createElement("beam_size")
        if datainfo.source.beam_size_name is not None:
            size.setAttribute("name", str(datainfo.source.beam_size_name))
        written = write_node(doc, size, "x", datainfo.source.beam_size.x, {"unit":datainfo.source.beam_size_unit})
        written = written | write_node(doc, size, "y", datainfo.source.beam_size.y, {"unit":datainfo.source.beam_size_unit})
        written = written | write_node(doc, size, "z", datainfo.source.beam_size.z, {"unit":datainfo.source.beam_size_unit})
        if written == True:
            source.appendChild(size)
            
        write_node(doc, source, "wavelength", datainfo.source.wavelength, {"unit":datainfo.source.wavelength_unit})
        write_node(doc, source, "wavelength_min", datainfo.source.wavelength_min, {"unit":datainfo.source.wavelength_min_unit})
        write_node(doc, source, "wavelength_max", datainfo.source.wavelength_max, {"unit":datainfo.source.wavelength_max_unit})
        write_node(doc, source, "wavelength_spread", datainfo.source.wavelength_spread, {"unit":datainfo.source.wavelength_spread_unit})
        
        #   Collimation
        for item in datainfo.collimation:
            coll = doc.createElement("SAScollimation")
            if item.name is not None:
                coll.setAttribute("name", str(item.name))
            instr.appendChild(coll)
            
            write_node(doc, coll, "length", item.length, {"unit":item.length_unit})
            
            for apert in item.aperture:
                ap = doc.createElement("aperture")
                if apert.name is not None:
                    ap.setAttribute("name", str(apert.name))
                if apert.type is not None:
                    ap.setAttribute("type", str(apert.type))
                coll.appendChild(ap)
                
                write_node(doc, ap, "distance", apert.distance, {"unit":apert.distance_unit})
                
                size = doc.createElement("size")
                if apert.size_name is not None:
                    size.setAttribute("name", str(apert.size_name))
                written = write_node(doc, size, "x", apert.size.x, {"unit":apert.size_unit})
                written = written | write_node(doc, size, "y", apert.size.y, {"unit":apert.size_unit})
                written = written | write_node(doc, size, "z", apert.size.z, {"unit":apert.size_unit})
                if written == True:
                    ap.appendChild(size)

        #   Detectors
        for item in datainfo.detector:
            det = doc.createElement("SASdetector")
            written = write_node(doc, det, "name", item.name)
            written = written | write_node(doc, det, "SDD", item.distance, {"unit":item.distance_unit})
            written = written | write_node(doc, det, "slit_length", item.slit_length, {"unit":item.slit_length_unit})
            if written == True:
                instr.appendChild(det)
            
            off = doc.createElement("offset")
            written = write_node(doc, off, "x", item.offset.x, {"unit":item.offset_unit})
            written = written | write_node(doc, off, "y", item.offset.y, {"unit":item.offset_unit})
            written = written | write_node(doc, off, "z", item.offset.z, {"unit":item.offset_unit})
            if written == True:
                det.appendChild(off)
            
            center = doc.createElement("beam_center")
            written = write_node(doc, center, "x", item.beam_center.x, {"unit":item.beam_center_unit})
            written = written | write_node(doc, center, "y", item.beam_center.y, {"unit":item.beam_center_unit})
            written = written | write_node(doc, center, "z", item.beam_center.z, {"unit":item.beam_center_unit})
            if written == True:
                det.appendChild(center)
                
            pix = doc.createElement("pixel_size")
            written = write_node(doc, pix, "x", item.pixel_size.x, {"unit":item.pixel_size_unit})
            written = written | write_node(doc, pix, "y", item.pixel_size.y, {"unit":item.pixel_size_unit})
            written = written | write_node(doc, pix, "z", item.pixel_size.z, {"unit":item.pixel_size_unit})
            if written == True:
                det.appendChild(pix)
                
            ori = doc.createElement("orientation")
            written = write_node(doc, ori, "roll",  item.orientation.x, {"unit":item.orientation_unit})
            written = written | write_node(doc, ori, "pitch", item.orientation.y, {"unit":item.orientation_unit})
            written = written | write_node(doc, ori, "yaw",   item.orientation.z, {"unit":item.orientation_unit})
            if written == True:
                det.appendChild(ori)
                
        # Processes info
        for item in datainfo.process:
            node = doc.createElement("SASprocess")
            entry_node.appendChild(node)

            write_node(doc, node, "name", item.name)
            write_node(doc, node, "date", item.date)
            write_node(doc, node, "description", item.description)
            for term in item.term:
                value = term['value']
                del term['value']
                write_node(doc, node, "term", value, term)
            for note in item.notes:
                write_node(doc, node, "SASprocessnote", note)
        # Return the document, and the SASentry node associated with
        # the data we just wrote
        return doc, entry_node
   
    def _parse_state(self, entry):
        """
        Read a fit result from an XML node
        
        :param entry: XML node to read from 
        
        :return: PageState object
        """
        # Create an empty state
        state = None   
        # Locate the P(r) node
        try:
            nodes = entry.xpath('ns:%s' % FITTING_NODE_NAME, namespaces={'ns': CANSAS_NS})
            if nodes !=[]:
                # Create an empty state
                state =  PageState()
                state.fromXML(node=nodes[0])
        except:
            logging.info("XML document does not contain fitting information.\n %s" % sys.exc_value)
            
        return state
    
   
                    
    def _parse_entry(self, dom):
        """
        Parse a SASentry
        
        :param node: SASentry node
        
        :return: Data1D/Data2D object
        
        """
        node = dom.xpath('ns:data_class', namespaces={'ns': CANSAS_NS})
        if not node or node[0].text.lstrip().rstrip() != "Data2D":
            return CansasReader._parse_entry(self, dom)
        
        #Parse 2D
        data_info = Data2D()
        
        # Look up title      
        self._store_content('ns:Title', dom, 'title', data_info)
        
        # Look up run number   
        nodes = dom.xpath('ns:Run', namespaces={'ns': CANSAS_NS})
        for item in nodes:    
            if item.text is not None:
                value = item.text.strip()
                if len(value) > 0:
                    data_info.run.append(value)
                    if item.get('name') is not None:
                        data_info.run_name[value] = item.get('name')
                           
        # Look up instrument name              
        self._store_content('ns:SASinstrument/ns:name', dom, 'instrument', data_info)

        # Notes
        note_list = dom.xpath('ns:SASnote', namespaces={'ns': CANSAS_NS})
        for note in note_list:
            try:
                if note.text is not None:
                    note_value = note.text.strip()
                    if len(note_value) > 0:
                        data_info.notes.append(note_value)
            except:
                err_mess = "cansas_reader.read: error processing entry notes\n  %s" % sys.exc_value
                self.errors.append(err_mess)
                logging.error(err_mess)
        
        # Sample info ###################
        entry = get_content('ns:SASsample', dom)
        if entry is not None:
            data_info.sample.name = entry.get('name')
            
        self._store_content('ns:SASsample/ns:ID', 
                     dom, 'ID', data_info.sample)                    
        self._store_float('ns:SASsample/ns:thickness', 
                     dom, 'thickness', data_info.sample)
        self._store_float('ns:SASsample/ns:transmission', 
                     dom, 'transmission', data_info.sample)
        self._store_float('ns:SASsample/ns:temperature', 
                     dom, 'temperature', data_info.sample)
        
        nodes = dom.xpath('ns:SASsample/ns:details', namespaces={'ns': CANSAS_NS})
        for item in nodes:
            try:
                if item.text is not None:
                    detail_value = item.text.strip()
                    if len(detail_value) > 0:
                        data_info.sample.details.append(detail_value)
            except:
                err_mess = "cansas_reader.read: error processing sample details\n  %s" % sys.exc_value
                self.errors.append(err_mess)
                logging.error(err_mess)
        
        # Position (as a vector)
        self._store_float('ns:SASsample/ns:position/ns:x', 
                     dom, 'position.x', data_info.sample)          
        self._store_float('ns:SASsample/ns:position/ns:y', 
                     dom, 'position.y', data_info.sample)          
        self._store_float('ns:SASsample/ns:position/ns:z', 
                     dom, 'position.z', data_info.sample)          
        
        # Orientation (as a vector)
        self._store_float('ns:SASsample/ns:orientation/ns:roll', 
                     dom, 'orientation.x', data_info.sample)          
        self._store_float('ns:SASsample/ns:orientation/ns:pitch', 
                     dom, 'orientation.y', data_info.sample)          
        self._store_float('ns:SASsample/ns:orientation/ns:yaw', 
                     dom, 'orientation.z', data_info.sample)          
       
        # Source info ###################
        entry = get_content('ns:SASinstrument/ns:SASsource', dom)
        if entry is not None:
            data_info.source.name = entry.get('name')
        
        self._store_content('ns:SASinstrument/ns:SASsource/ns:radiation', 
                     dom, 'radiation', data_info.source)                    
        self._store_content('ns:SASinstrument/ns:SASsource/ns:beam_shape', 
                     dom, 'beam_shape', data_info.source)                    
        self._store_float('ns:SASinstrument/ns:SASsource/ns:wavelength', 
                     dom, 'wavelength', data_info.source)          
        self._store_float('ns:SASinstrument/ns:SASsource/ns:wavelength_min', 
                     dom, 'wavelength_min', data_info.source)          
        self._store_float('ns:SASinstrument/ns:SASsource/ns:wavelength_max', 
                     dom, 'wavelength_max', data_info.source)          
        self._store_float('ns:SASinstrument/ns:SASsource/ns:wavelength_spread', 
                     dom, 'wavelength_spread', data_info.source)    
        
        # Beam size (as a vector)   
        entry = get_content('ns:SASinstrument/ns:SASsource/ns:beam_size', dom)
        if entry is not None:
            data_info.source.beam_size_name = entry.get('name')
            
        self._store_float('ns:SASinstrument/ns:SASsource/ns:beam_size/ns:x', 
                     dom, 'beam_size.x', data_info.source)    
        self._store_float('ns:SASinstrument/ns:SASsource/ns:beam_size/ns:y', 
                     dom, 'beam_size.y', data_info.source)    
        self._store_float('ns:SASinstrument/ns:SASsource/ns:beam_size/ns:z', 
                     dom, 'beam_size.z', data_info.source)    
        
        # Collimation info ###################
        nodes = dom.xpath('ns:SASinstrument/ns:SAScollimation', namespaces={'ns': CANSAS_NS})
        for item in nodes:
            collim = Collimation()
            if item.get('name') is not None:
                collim.name = item.get('name')
            self._store_float('ns:length', item, 'length', collim)  
            
            # Look for apertures
            apert_list = item.xpath('ns:aperture', namespaces={'ns': CANSAS_NS})
            for apert in apert_list:
                aperture =  Aperture()
                
                # Get the name and type of the aperture
                aperture.name = apert.get('name')
                aperture.type = apert.get('type')
                    
                self._store_float('ns:distance', apert, 'distance', aperture)    
                
                entry = get_content('ns:size', apert)
                if entry is not None:
                    aperture.size_name = entry.get('name')
                
                self._store_float('ns:size/ns:x', apert, 'size.x', aperture)    
                self._store_float('ns:size/ns:y', apert, 'size.y', aperture)    
                self._store_float('ns:size/ns:z', apert, 'size.z', aperture)
                
                collim.aperture.append(aperture)
                
            data_info.collimation.append(collim)
        
        # Detector info ######################
        nodes = dom.xpath('ns:SASinstrument/ns:SASdetector', namespaces={'ns': CANSAS_NS})
        for item in nodes:
            
            detector = Detector()
            
            self._store_content('ns:name', item, 'name', detector)
            self._store_float('ns:SDD', item, 'distance', detector)    
            
            # Detector offset (as a vector)
            self._store_float('ns:offset/ns:x', item, 'offset.x', detector)    
            self._store_float('ns:offset/ns:y', item, 'offset.y', detector)    
            self._store_float('ns:offset/ns:z', item, 'offset.z', detector)    
            
            # Detector orientation (as a vector)
            self._store_float('ns:orientation/ns:roll',  item, 'orientation.x', detector)    
            self._store_float('ns:orientation/ns:pitch', item, 'orientation.y', detector)    
            self._store_float('ns:orientation/ns:yaw',   item, 'orientation.z', detector)    
            
            # Beam center (as a vector)
            self._store_float('ns:beam_center/ns:x', item, 'beam_center.x', detector)    
            self._store_float('ns:beam_center/ns:y', item, 'beam_center.y', detector)    
            self._store_float('ns:beam_center/ns:z', item, 'beam_center.z', detector)    
            
            # Pixel size (as a vector)
            self._store_float('ns:pixel_size/ns:x', item, 'pixel_size.x', detector)    
            self._store_float('ns:pixel_size/ns:y', item, 'pixel_size.y', detector)    
            self._store_float('ns:pixel_size/ns:z', item, 'pixel_size.z', detector)    
            
            self._store_float('ns:slit_length', item, 'slit_length', detector)
            
            data_info.detector.append(detector)    

        # Processes info ######################
        nodes = dom.xpath('ns:SASprocess', namespaces={'ns': CANSAS_NS})
        for item in nodes:
            process = Process()
            self._store_content('ns:name', item, 'name', process)
            self._store_content('ns:date', item, 'date', process)
            self._store_content('ns:description', item, 'description', process)
            
            term_list = item.xpath('ns:term', namespaces={'ns': CANSAS_NS})
            for term in term_list:
                try:
                    term_attr = {}
                    for attr in term.keys():
                        term_attr[attr] = term.get(attr).strip()
                    if term.text is not None:
                        term_attr['value'] = term.text.strip()
                        process.term.append(term_attr)
                except:
                    err_mess = "cansas_reader.read: error processing process term\n  %s" % sys.exc_value
                    self.errors.append(err_mess)
                    logging.error(err_mess)
            
            note_list = item.xpath('ns:SASprocessnote', namespaces={'ns': CANSAS_NS})
            for note in note_list:
                if note.text is not None:
                    process.notes.append(note.text.strip())
            
            data_info.process.append(process)
            
            
        # Data info ######################
        nodes = dom.xpath('ns:SASdata', namespaces={'ns': CANSAS_NS})
        if len(nodes)>1:
            raise RuntimeError, "CanSAS reader is not compatible with multiple SASdata entries"
       
        for entry in nodes:
            for item in list_of_data_2d_attr:
                #get node
                node = get_content('ns:%s'%item[0], entry)
                exec "data_info.%s = parse_entry_helper(node, item)"%(item[1])
                    
            for item in list_of_data2d_values:
                field = get_content('ns:%s'%item[0], entry)
                list = []
                if field is not None:
                    list = [parse_entry_helper(node, item) for node in field]
                exec "data_info.%s = numpy.array(list)"%item[0]
        
        return data_info

    def _read_cansas(self, path):
        """ 
        Load data and P(r) information from a CanSAS XML file.
        
        :param path: file path
        
        :return: Data1D object if a single SASentry was found, 
                    or a list of Data1D objects if multiple entries were found,
                    or None of nothing was found
                    
        :raise RuntimeError: when the file can't be opened
        :raise ValueError: when the length of the data vectors are inconsistent
        
        """
        output = []
        basename  = os.path.basename(path)
        root, extension = os.path.splitext(basename)
        ext = extension.lower()
        try:
            if os.path.isfile(path):
                
                #TODO: eventually remove the check for .xml once
                # the P(r) writer/reader is truly complete.
                if  ext in self.ext or \
                    ext == '.xml':
                    
                    tree = etree.parse(path, parser=etree.ETCompatXMLParser())
                    # Check the format version number
                    # Specifying the namespace will take care of the file format version 
                    root = tree.getroot()
                    entry_list = root.xpath('ns:SASentry', namespaces={'ns': CANSAS_NS})
                    for entry in entry_list:   
                        try:
                            sas_entry = self._parse_entry(entry)
                        except:
                            raise
                        fitstate = self._parse_state(entry)
                        
                        #state could be None when .svs file is loaded
                        #in this case, skip appending to output
                        if fitstate != None:
                            sas_entry.meta_data['fitstate'] = fitstate
                            sas_entry.filename = fitstate.file
                            output.append(sas_entry)
            else:
                self.call_back(format=ext)
                raise RuntimeError, "%s is not a file" % path

            # Return output consistent with the loader's api
            if len(output)==0:
                self.call_back(state=None, datainfo=None,format=ext)
                return None
            else:
                for ind in range(len(output)):
                    # Call back to post the new state
                    state = output[ind].meta_data['fitstate']
                    t = time.localtime(state.timestamp)
                    time_str = time.strftime("%b %d %H:%M", t)
                    # Check that no time stamp is already appended
                    max_char = state.file.find("[")
                    if max_char < 0:
                        max_char = len(state.file)
                    original_fname = state.file[0:max_char]
                    state.file = original_fname +' [' + time_str + ']'
                   
                        
                    if state is not None and state.is_data is not None:
                        exec 'output[%d].is_data = state.is_data'% ind 
                     
                    output[ind].filename = state.file
                    state.data = output[ind]
                    state.data.name = output[ind].filename #state.data_name
                    state.data.id = state.data_id
                    if state.is_data is not None:
                        state.data.is_data = state.is_data
                    if output[ind].run_name is not None and len(output[ind].run_name) != 0 :
                        name = output[ind].run_name
                    else: 
                        name=original_fname
                    state.data.group_id = name
                    #store state in fitting
                    self.call_back(state=state, datainfo=output[ind],format=ext)
                return output
              
        except:
            self.call_back(format=ext)
            raise
           
    def write(self, filename, datainfo=None, fitstate=None):
        """
        Write the content of a Data1D as a CanSAS XML file only for standalone
        
        :param filename: name of the file to write
        :param datainfo: Data1D object
        :param fitstate: PageState object
        
        """
        # Sanity check
        if self.cansas == True:
            
            # Add fitting information to the XML document
            doc = self.write_toXML(datainfo, fitstate)
            # Write the XML document
            fd = open(filename, 'w')
            fd.write(doc.toprettyxml())
            fd.close()
        else:
            fitstate.toXML(file=filename)
        
    def write_toXML(self, datainfo=None, state=None):
        """
        Write toXML, a helper for write() , could be used by guimanager._on_save()
        
        : return: xml doc
        """

        if state.data is None:
            data = DataLoader.data_info.Data1D(x=[], y=[])  
        else:  
            #make sure title and data run is filled up.
            if state.data.title == None or state.data.title=='': state.data.title = state.data.name
            if state.data.run_name == None or state.data.run_name=={}: 
                state.data.run = [str(state.data.name)]
                state.data.run_name[0] = state.data.name
   
            if issubclass(state.data.__class__, DataLoader.data_info.Data1D):

                data = state.data
                doc, sasentry = self._to_xml_doc(data)
            else:
                data = state.data
                doc, sasentry = self._data2d_to_xml_doc(data)
            

        if state is not None:
            state.toXML(doc=doc, file=data.name, entry_node=sasentry)
            
        return doc 
  
if __name__ == "__main__":
    state = PageState(parent=None)
    #state.toXML()
    """
    
    file = open("test_state", "w")
    pickle.dump(state, file)
    print pickle.dumps(state)
    state.data_name = "hello---->"
    pickle.dump(state, file)
    file = open("test_state", "r")
    new_state= pickle.load(file)
    print "new state", new_state
    new_state= pickle.load(file)
    print "new state", new_state
    #print "state", state
    """
    import bsddb
    import pickle
    db= bsddb.btopen('file_state.db', 'c')
    val = (pickle.dumps(state), "hello", "hi")
    db['state1']= pickle.dumps(val)
    print pickle.loads(db['state1'])
    state.data_name = "hello---->22"
    db['state2']= pickle.dumps(state)
    state.data_name = "hello---->2"
    db['state3']= pickle.dumps(state)
    del db['state3']
    state.data_name = "hello---->3"
    db['state4']= pickle.dumps(state)
    new_state = pickle.loads(db['state1'])
    #print db.last()
    db.set_location('state2')
    state.data_name = "hello---->5"
    db['aastate5']= pickle.dumps(state)
    db.keys().sort()
    print pickle.loads(db['state2'])
  
    db.close()