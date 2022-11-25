""" As close a thing as there are to tests for GL"""

import numpy as np

from PyQt5 import QtWidgets

from sas.qtgui.GL.scene import GraphWidget
from sas.qtgui.GL.models import ModelBase
from sas.qtgui.GL.color import Color
from sas.qtgui.GL.surface import Surface
from sas.qtgui.GL.cone import Cone
from sas.qtgui.GL.cube import Cube
from sas.qtgui.GL.cylinder import Cylinder
from sas.qtgui.GL.icosahedron import Icosahedron
from sas.qtgui.GL.sphere import Sphere


def mesh_example():
    x = np.linspace(-1, 1, 101)
    y = np.linspace(-1, 1, 101)
    x_grid, y_grid = np.meshgrid(x, y)

    r_sq = x_grid**2 + y_grid**2
    z = np.cos(np.sqrt(r_sq))/(r_sq+1)

    return Surface(x, y, z, edge_skip=4)


def primative_library():
    """ Shows all the existing primitives that can be rendered, press a key to go through them"""

    import os

    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    app = QtWidgets.QApplication([])


    item_list = [
        mesh_example(),
        Cube(edge_colors=Color(1, 1, 1), face_colors=Color(0.7, 0.2, 0)),
        Cube(edge_colors=Color(1, 1, 1), face_colors=[
            Color(1,0,0),
            Color(0,1,0),
            Color(0,0,1),
            Color(1,1,0),
            Color(0,1,1),
            Color(1,0,1)
        ], color_by_mesh=True),
        Cone(edge_colors=Color(1, 1, 1), vertex_colors=Color(0, 0.7, 0.2)),
        Cylinder(edge_colors=Color(1, 1, 1), vertex_colors=Color(0, 0.2, 0.7)),
        Icosahedron(edge_colors=Color(1, 1, 1), vertex_colors=Color(0.7, 0, 0.7)),
        Sphere(edge_colors=Color(1, 1, 1), vertex_colors=Color(0.7, 0.7, 0.0)),
        Sphere(edge_colors=Color(1, 1, 1), vertex_colors=Color(0.7, 0.4, 0.0), grid_gap=4)
    ]

    # Turn off all of them
    for item in item_list:
        item.solid_render_enabled = False
        item.wireframe_render_enabled = False


    # Thing for going through each of the draw types of the primatives

    def item_states(item: ModelBase):

        item.solid_render_enabled = True
        item.wireframe_render_enabled = True

        yield None

        item.solid_render_enabled = False
        item.wireframe_render_enabled = True

        yield None

        item.solid_render_enabled = True
        item.wireframe_render_enabled = False

        yield None

        item.solid_render_enabled = False
        item.wireframe_render_enabled = False

    def scan_states():
        while True:
            for item in item_list:
                for _ in item_states(item):
                    yield None

    state = scan_states()
    next(state)


    mainWindow = QtWidgets.QMainWindow()
    viewer = GraphWidget(parent=mainWindow)

    # Keyboard callback
    def enable_disable(key):
        next(state)
        viewer.update()

    viewer.on_key = enable_disable

    for item in item_list:
        viewer.add(item)

    mainWindow.setCentralWidget(viewer)

    mainWindow.show()

    mainWindow.resize(600, 600)
    app.exec_()


if __name__ == "__main__":
    primative_library()