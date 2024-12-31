'''
A list of events on zope.event bus.
'''

from abc import abstractmethod
from uuid import uuid1

from pony import orm as pony

from iot.config import config


class DevAppEvent(object):
    '''
    The base class of DA related event

    :param id_: the ``UUID`` object

    Attributes:

        :id: the ``UUID`` object
        :timestamp: the time-based uuid (via ``uuid.uuid1``)
            on the event created
        :res: the instance of orm db object
        :type: device application state, (register|online|offline|deregister)
    '''

    def __init__(self, id_):
        self.id = id_
        self.timestamp = uuid1()
        self.res = None

    def __repr__(self):
        return '{} event id: {}, da id: {}'.format(
            self.type, self.timestamp, self.id)

    @property
    @abstractmethod
    def type(self):
        pass


class DevAppRegister(DevAppEvent):
    '''
    The device application ready event
    '''

    @pony.db_session(serializable=True)
    def __init__(self, *args, **kwargs):
        super(DevAppRegister, self).__init__(*args, **kwargs)

        if not getattr(config.db, 'Resource', None):
            self.res = None
            return  # prevent race condition in test cases

        self.res = config.db.Resource.get(id=self.id)

    @property
    def type(self):
        return 'register'


class DevAppOnline(DevAppEvent):
    '''
    The device application ready event
    '''

    @property
    def type(self):
        return 'online'


class DevAppOffline(DevAppEvent):
    '''
    The device application offline event
    '''

    @property
    def type(self):
        return 'offline'


class DevAppDeregister(DevAppEvent):
    '''
    The device application deregister event.
    '''

    @property
    def type(self):
        return 'deregister'
