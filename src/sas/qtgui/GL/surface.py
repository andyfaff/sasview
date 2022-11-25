import logging
from typing import Optional, Tuple
import numpy as np

import matplotlib as mpl

from sas.qtgui.GL.models import FullModel, WireModel
from sas.qtgui.GL.color import Color, ColorMap

logger = logging.getLogger("GL.Surface")

class Surface(FullModel):


    @staticmethod
    def calculate_edge_indices(nx, ny, gap=1):
        all_edges = []
        for i in range(nx-1):
            for j in range(0, ny, gap):
                all_edges.append((j*nx + i, j*nx + i + 1))

        for i in range(0, nx, gap):
            for j in range(ny-1):
                all_edges.append((j*nx + i, (j+1)*nx + i))

        return all_edges

    @staticmethod
    def calculate_triangles(nx, ny):
        triangles = []
        for i in range(nx-1):
            for j in range(ny-1):
                triangles.append((j*nx + i, (j+1)*nx+(i+1), j*nx + (i + 1)))
                triangles.append((j*nx + i, (j+1)*nx + i, (j+1)*nx + (i+1)))
        return triangles

    def __init__(self,
                 x_values: np.ndarray,
                 y_values: np.ndarray,
                 z_data: np.ndarray,
                 colormap: str= ColorMap._default_colormap,
                 edge_skip: int=1):

        """ Surface plot


        :param x_values: 1D array of x values
        :param y_values: 1D array of y values
        :param z_data: 2D array of z values
        :param colormap: name of a matplotlib colour map
        :param edge_skip: skip every `edge_skip` index when drawing wireframe
        """


        self.x_data, self.y_data = np.meshgrid(x_values, y_values)
        self.z_data = z_data

        self.n_x = len(x_values)
        self.n_y = len(y_values)

        self.colormap = ColorMap(colormap)

        verts = [(float(x), float(y), float(z)) for x, y, z in zip(np.nditer(self.x_data), np.nditer(self.y_data), np.nditer(self.z_data))]

        super().__init__(
            vertices=verts,
            edges=Surface.calculate_edge_indices(self.n_x, self.n_y, edge_skip),
            triangle_meshes=[Surface.calculate_triangles(self.n_x, self.n_y)],
            edge_colors=Color(1.0,1.0,1.0),
            vertex_colors=self.colormap.color_array([z for _, _, z in verts])
            )

        self.wireframe_render_enabled = True
        self.solid_render_enabled = True


    # def _get_colors(self, z_values, colormap) -> Sequence[Color]:
    #     return []
    #
    # def set_z_data(self, z_data):
    #     pass