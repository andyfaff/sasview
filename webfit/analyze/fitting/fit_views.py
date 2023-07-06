import json
from logging import getLogger

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view

from sasmodels.core import load_model
from sas.sascalc.fit.models import ModelManager
from sasdata.dataloader.loader import Loader
from bumps import fitters
from bumps.formatnum import format_uncertainty
#TODO categoryinstallers should belong in SasView.Systen rather than in QTGUI
from sas.qtgui.Utilities.CategoryInstaller import CategoryInstaller

from serializers import FitSerializers
from data.models import Data
from .models import (
    Fit,
    FitModel,
    FitParameter,
)


fit_logger = getLogger(__name__)

@api_view(["PUT"])
def start(request, version = None):
    serializer = FitSerializers()
    fit = get_object_or_404(Fit)
    fit_model = get_object_or_404(FitModel)

    if request.method == "PUT":
        if request.file_id:
            if not fit.opt_in and not request.user.is_authenticated:
                return HttpResponseBadRequest("user isn't logged in")
            """
            do I even need this? I think I need this to make sure the serializer goes to the right place
            fit(username = request.username)
            fit_model(id = fit.fit_model_id)
            serializer(fit)
            (do i need a FitModelSerializers)
            """
            data_obj = get_object_or_404(Data, id = request.file_id)
            loaded_data = Loader.load(data_obj.file)
        
        if not request.data["MODEL_CHOICES"] in fit_model: 
            return HttpResponseBadRequest("No model selected for fitting")
        
        kernel = load_model(request.model)
        #TODO figure out how to load parameters

    return HttpResponseBadRequest()


@api_view(["GET"])
def fit_status(request, fit_id, version = None):
    fit_obj = get_object_or_404(Fit, id = fit_id)
    if request.method == "GET":
        #TODO figure out private later <- probs write in Fit model
        if not fit_obj.opt_in and not request.user.is_authenticated:
            return HttpResponseBadRequest("user isn't logged in")
        return_info = {"fit_id" : fit_id, "status" : Fit.status}
        if Fit.results:
            return_info+={"results" : Fit.results}
        return return_info
    
    return HttpResponseBadRequest()


@api_view(["GET"])
def list_optimizers(request, version = None):
    if request.method == "GET":
        return_info = {"optimizers" : [fitters.FIT_ACTIVE_IDS]}
        return return_info
    return HttpResponseBadRequest()


@api_view(["GET"])
def list_models(request, version = None):
    model_manager = ModelManager()
    if request.method == "GET":
        unique_models = {"models": []}
        if request.kind:
            unique_models["models"] += [{request.kind : ADDLATER}]
        elif request.categories:
            user_file = CategoryInstaller.get_user_file()
            with open(user_file) as cat_file:
                file_contents = cat_file.read()
            spec_cat = file_contents[request.categories]
            unique_models["models"] += [spec_cat]
        else:
            unique_models["models"] = [model_manager.get_model_list()]
        return unique_models
        """TODO requires discussion:
        if request.username:
            if request.user.is_authenticated:
                user_models = 
                listed_models += {"plugin_models": user_models}
        """
    return HttpResponseBadRequest()

#takes DataInfo and saves it into to specified file location
