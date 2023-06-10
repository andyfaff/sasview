from abc import ABC, abstractmethod
from typing import Tuple

from sas.qtgui.Perspectives.ParticleEditor.datamodel.types import VectorComponents3


class SpatialSample(ABC):
    """ Base class for spatial sampling methods"""
    def __init__(self, n_points_desired, radius):
        self._n_points_desired = n_points_desired
        self.radius = radius

    @abstractmethod
    def _calculate_n_actual(self) -> int:
        """ Calculate the actual number of sample points, based on the desired number of points"""

    @property
    def n_actual(self) -> int:
        """ Actual number of sample points (this might differ from the input number of points)"""
        return self._calculate_n_actual()

    @abstractmethod
    def sampling_details(self) -> str:
        """ A string describing the details of the sample points """

    @abstractmethod
    def pairs(self, size_hint: int) -> Tuple[VectorComponents3, VectorComponents3]:
        """ Pairs of sample points """


    @abstractmethod
    def singles(self, size_hint: int) -> VectorComponents3:
        """ Sample points """

    @abstractmethod
    def boundingSurfaceCheckPoints(self) -> VectorComponents3:
        """ Points that are used to check that the SLD is consistent
        with the solvent SLD at the edge of the sampling space"""

    def __repr__(self):
        return "%s(n=%i,r=%g)" % (self.__class__.__name__, self._n_points_desired, self.radius)

    @abstractmethod
    def start_location(self, size_hint: int) -> VectorComponents3:
        """ Get the sample points """

    @abstractmethod
    def sample_volume(self) -> float:
        """ Volume of sample area """

