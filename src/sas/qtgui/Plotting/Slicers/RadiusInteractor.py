import numpy as np
from sas.qtgui.Plotting.Slicers.BaseInteractor import BaseInteractor


class RadiusInteractor(BaseInteractor):
    """
     Draw a radial line (centered at [0,0]) at an angle theta from the x-axis
     on a data2D plot from r1 to r2 defined by two arcs (arc1 and arc2). Used
     for example to define a wedge area on the plot.

     param theta: angle of the radial line from the x-axis
     param arc1: inner arc of radius r1 used to define the starting point of
                the radial line
     param arc2: outer arc of radius r2 used to define the ending point of
                the radial line
    """
    def __init__(self, base, axes, color='black', zorder=5, arc1=None,
                 arc2=None, theta=np.pi / 8):
        """
        """
        _BaseInteractor.__init__(self, base, axes, color=color)
        self.markers = []
        self.axes = axes
        self.r1 = arc1.get_radius()
        self.r2 = arc2.get_radius()
        self.theta = theta
        self.save_theta = theta
        self.move_stop = False
        self.theta_left = None
        self.theta_right = None
        self.arc1 = arc1
        self.arc2 = arc2
        x1 = self.r1 * np.cos(self.theta)
        y1 = self.r1 * np.sin(self.theta)
        x2 = self.r2 * np.cos(self.theta)
        y2 = self.r2 * np.sin(self.theta)
        self.line = self.axes.plot([x1, x2], [y1, y2],
                                   linestyle='-', marker='',
                                   color=self.color,
                                   visible=True)[0]
        self.phi = theta
        self.npts = 20
        self.has_move = False
        self.connect_markers([self.line])
        self.update()

    def set_layer(self, n):
        """
        """
        self.layernum = n
        self.update()

    def clear(self):
        """
        """
        self.clear_markers()
        try:
            self.line.remove()
        except:
            # Old version of matplotlib
            for item in range(len(self.axes.lines)):
                del self.axes.lines[0]

    def get_angle(self):
        """
        """
        return self.theta

    def update(self, r1=None, r2=None, theta=None):
        """
        Draw the new roughness on the graph.
        """
        if r1 is not None:
            self.r1 = r1
        if r2 is not None:
            self.r2 = r2
        if theta is not None:
            self.theta = theta
        x1 = self.r1 * np.cos(self.theta)
        y1 = self.r1 * np.sin(self.theta)
        x2 = self.r2 * np.cos(self.theta)
        y2 = self.r2 * np.sin(self.theta)
        self.line.set(xdata=[x1, x2], ydata=[y1, y2])

    def save(self, ev):
        """
        Remember the roughness for this layer and the next so that we
        can restore on Esc.
        """
        self.save_theta = np.arctan2(ev.y, ev.x)
        self.base.freeze_axes()

    def moveend(self, ev):
        """
        """
        self.has_move = False
        self.base.moveend(ev)

    def restore(self, ev):
        """
        Restore the roughness for this layer.
        """
        self.theta = self.save_theta

    def move(self, x, y, ev):
        """
        Process move to a new position, making sure that the move is allowed.
        """
        self.theta = np.arctan2(y, x)
        self.has_move = True
        self.base.update()
        self.base.draw()

    def set_cursor(self, r_min, r_max, theta):
        """
        """
        self.theta = theta
        self.r1 = r_min
        self.r2 = r_max
        self.update()

    def get_params(self):
        """
        """
        params = {}
        params["radius1"] = self.r1
        params["radius2"] = self.r2
        params["theta"] = self.theta
        return params

    def set_params(self, params):
        """
        """
        x1 = params["radius1"]
        x2 = params["radius2"]
        theta = params["theta"]
        self.set_cursor(x1, x2, theta)

