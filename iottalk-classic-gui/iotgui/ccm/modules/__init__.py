from .device import Device
from .devicefeature import DeviceFeature
from .devicefeaturecategory import DeviceFeatureCategory
from .devicefeatureobject import DeviceFeatureObject
from .devicefeatureparameter import DeviceFeatureParameter
from .devicemodel import DeviceModel
from .deviceobject import DeviceObject
from .function import Function
from .graph import Graph
from .gui import GUI
from .networkapplication import NetworkApplication
from .other import Other
from .project import Project
from .simulation import Simulation
from .tag import Tag
from .unit import Unit
from .user import User


class CCMModule(Device, DeviceFeature, DeviceFeatureCategory,
                DeviceFeatureObject, DeviceFeatureParameter, DeviceModel,
                DeviceObject, Function, Graph, GUI, NetworkApplication,
                Other, Project, Simulation, Tag, Unit, User):
    ...
