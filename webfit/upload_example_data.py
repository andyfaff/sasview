import os
import re
import sys
import json
import logging
import django
from glob import glob

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from data.models import Data

# Initialise the Django environment. This must be done before importing anything
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sasmarket.settings")
django.setup()

EXAMPLE_DATA_DIR = os.environ.get("EXAMPLE_DATA_DIR", "../src/sas/example_data")

def parse_1D():
    dir_1d = os.path.join(EXAMPLE_DATA_DIR, "example_data", "1d_data")
    if not os.path.isdir(dir_1d):
        logging.error("1D Data directory not found at: {}".format(dir_1d))
        return
    for file_path in glob(os.path.join(dir_1d)):
        upload_file(file_path)

def parse_2D():
    dir_2d = os.path.join(EXAMPLE_DATA_DIR, "example_data", "2d_data")
    if not os.path.isdir(dir_2d):
        logging.error("2D Data directory not found at: {}".format(dir_2d))
        return
    for file_path in glob(os.path.join(dir_2d)):
        upload_file(file_path)


"""def upload_file(file):
    file_content = [
        {
            "model": "data.Data",
            "fields": {
                "file" : file,
                "is_public" : True
            }
        }
    ]
    json_obj = json.dumps(file_content, indent=4)
    with open("/data/fixtures/{file}.js", "w") as f:
        f.write(json_obj)"""

def upload_file(file_path):
    # Upload the file at file_path to the model
    file_name = os.path.split(file_path)[-1]

    file_obj = None
    with open(file_path, 'rb') as file_handle:
        file_obj = SimpleUploadedFile(file_name, file_handle.read())

    if file_obj is None:
        raise Exception("Unable to upload file: {}".format(file_path))
    
    data_file = Data(file_name=file_name, file=file_obj, is_public=True)
    data_file.save()
    