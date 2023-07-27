"""
Creates documentation from .py files
"""
import os
import sys
from os.path import join, abspath, dirname, basename
import subprocess

FILE_ABS_SOURCE = abspath(dirname(__file__))
MAIN_PY_SRC = FILE_ABS_SOURCE + "/../source-temp/user/models/src/"
if os.path.exists(MAIN_PY_SRC):
    ABSOLUTE_TARGET_MAIN = abspath(join(dirname(__file__), MAIN_PY_SRC))
    PLUGIN_PY_SRC = abspath(dirname(__file__)) + "/../../../../.sasview/plugin_models/"
    ABSOLUTE_TARGET_PLUGINS = abspath(join(dirname(__file__), PLUGIN_PY_SRC))
else:
    pass

def get_py(directory):
    for root, dirs, files in os.walk(directory):
        # Only include python files not starting in '_' (pycache not included)
        PY_FILES = [join(directory, string) for string in files if not string.startswith("_") and string.endswith(".py")]
        return PY_FILES

def get_main_docs():
    """
Generates string of .py files to be passed into compiling functions
Future reference: move to main() function?
    """
    # The order in which these are added is important. if ABSOLUTE_TARGET_PLUGINS goes first, then we're not compiling the .py file stored in .sasview/plugin_models
    TARGETS = get_py(ABSOLUTE_TARGET_MAIN) + get_py(ABSOLUTE_TARGET_PLUGINS)
    print(get_py(ABSOLUTE_TARGET_PLUGINS))
    base_targets = [basename(string) for string in TARGETS]
    # Removes duplicate instances of the same file copied from plugins folder to source-temp/user/models/src/
    for file in TARGETS:
        if base_targets.count(basename(file)) >= 2:
            TARGETS.remove(file)
            base_targets.remove(basename(file))
    return TARGETS

def call_regenmodel(filepath, regen_py):
    """
    Runs regenmodel.py/regentoc.py (specified in parameter regen_py) with all found PY_FILES
    """
    REGENMODEL = abspath(dirname(__file__)) + "/" + regen_py
    # Initialize command to be executed
    command = [
        sys.executable,
        REGENMODEL,
    ]
    # Append each filepath to command individually if passed in many files
    if type(filepath) == list:
        for string in filepath:
            command.append(string)
    else:
        command.append(filepath)
    subprocess.run(command)

def generate_html(single_file="", rst=False):
    """
    Generates HTML from an RST using a subprocess. Based off of syntax provided in Makefile found under /sasmodels/doc/
    """
    DOCTREES = "../build/doctrees/"
    SPHINX_SOURCE = "../source-temp/"
    HTML_TARGET = "../build/html/"
    if rst is False:
        single_rst = SPHINX_SOURCE + "user/models/" + single_file.replace('.py', '.rst')
    else:
        single_rst = single_file
    if single_rst.endswith("models/") or single_rst.endswith("user/"):
        # (re)sets value to empty string if nothing was entered
        single_rst = ""
    command = [
        sys.executable,
        "-m",
        "sphinx",
        "-d",
        DOCTREES,
        "-D",
        "latex_elements.papersize=letter",
        SPHINX_SOURCE,
        HTML_TARGET,
        single_rst,
    ]
    try:
        # Try removing empty arguments
        command.remove("")
    except:
        pass
    subprocess.check_call(command)

def call_all_files():
    TARGETS = get_main_docs()
    for file in TARGETS:
        #  easiest for regenmodel.py if files are passed in individually
        call_regenmodel(file, "regenmodel.py")
    # regentoc.py requires files to be passed in bulk or else LOTS of unexpected behavior
    call_regenmodel(TARGETS, "regentoc.py")

def call_one_file(file):
    TARGETS = get_main_docs()
    NORM_TARGET = join(ABSOLUTE_TARGET_MAIN, file)
    MODEL_TARGET =  join(ABSOLUTE_TARGET_PLUGINS, file)
    # Determines if a model's source .py file from /user/models/src/ should be used or if the file from /plugin-models/ should be used
    if os.path.exists(NORM_TARGET) and os.path.exists(MODEL_TARGET):
        if os.path.getmtime(NORM_TARGET) < os.path.getmtime(MODEL_TARGET):
            file_call_path = NORM_TARGET
        else:
            file_call_path = MODEL_TARGET
    elif not os.path.exists(NORM_TARGET):
        file_call_path = MODEL_TARGET
    else:
        file_call_path = NORM_TARGET
    call_regenmodel(file_call_path, "regenmodel.py") # There might be a cleaner way to do this but this approach seems to work and is fairly minimal
    call_regenmodel(TARGETS, "regentoc.py")

def main():
    try:
        if ".rst" in sys.argv[1]:
            # Generate only HTML if passed in file is an RST
            generate_html(sys.argv[1], rst=True)
        else:
            call_one_file(sys.argv[1]) # Tries to generate reST file for only one doc, if no doc is specified then will try to regenerate all reST files. Timesaving measure.
            generate_html(sys.argv[1])
    except:
        call_all_files() # Regenerate all RSTs
        generate_html() # Regenerate all HTML

if __name__ == "__main__":
    main()