import json
import requests
import logging
import pytz

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, Text, Boolean, String, DateTime, JSON
from sqlalchemy import asc
from flask_login import UserMixin

from edutalk.exceptions import CCMAPIError
from edutalk.config import config
from edutalk.const import actuatorDm, sensorOptions

db = config.db
log = logging.getLogger('edutalk.models')


class DictMixin:
    def to_dict(self, fields=None):
        if fields is None:
            fields = map(lambda x: x.name, self.__table__.columns)

        return {x: getattr(self, x) for x in fields}


class TimestampMixin():
    # Ref: https://myapollo.com.tw/zh-tw/sqlalchemy-mixin-and-custom-base-classes/
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(pytz.UTC)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.now(pytz.UTC)
    )


class User(db.Model, DictMixin, TimestampMixin, UserMixin):
    __tablename__ = 'User'
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String(255))  # this is a cache stored the result of ccm api query
    approved = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    group_id = Column(Integer, ForeignKey('Group.id'), nullable=False)
    lecture_projects = db.relationship('LectureProject', cascade='all,delete',
                                       backref='user')
    # just a UUID
    _token = Column(String, nullable=False, unique=True, default=lambda: uuid4().hex)

    @property
    def token(self):  # readonly
        return self._token

    _frequency_of_giv = Column(String(), default=json.dumps({}))

    @property
    def frequency_of_giv(self):  # readonly
        return json.loads(self._frequency_of_giv)

    @frequency_of_giv.setter
    def frequency_of_giv(self, val: dict):
        self._frequency_of_giv = json.dumps(val)

    frequency_of_giv = db.synonym('_frequency_of_giv', descriptor=frequency_of_giv)

    _frequency_of_output_var = Column(String(), default=json.dumps({}))

    @property
    def frequency_of_output_var(self):  # readonly
        return json.loads(self._frequency_of_output_var)

    @frequency_of_output_var.setter
    def frequency_of_output_var(self, val: dict):
        self._frequency_of_output_var = json.dumps(val)

    frequency_of_output_var = db.synonym('_frequency_of_output_var',
                                         descriptor=frequency_of_output_var)

    _cookies = Column(String())  # the iottalk ccm cookies

    @property
    def cookies(self):
        return json.loads(self._cookies)

    @cookies.setter
    def cookies(self, val: dict):
        self._cookies = json.dumps(val)

    cookies = db.synonym('_cookies', descriptor=cookies)

    @property
    def ccm_session(self):
        s = getattr(self, '_ccm_session', None)  # cache
        if not s:
            s = self._ccm_session = requests.Session()
            s.cookies.update(self.cookies)
        return s

    @property
    def is_teacher(self):
        return self.group.name == 'teacher'

    @property
    def is_admin(self):
        return self.group.name == 'administrator'

    # for OAuth
    sub = Column(String(255), unique=True)
    email = Column(String(255))

    refresh_token = db.relationship(
        'RefreshToken',
        back_populates='user',
        uselist=False,  # For one-to-one relationship, ref: https://tinyurl.com/jemrw6uf
        cascade='all, delete-orphan',
        passive_deletes=True,
    )
    access_tokens = db.relationship(
        'AccessToken',
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class Group(db.Model):
    __tablename__ = 'Group'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), unique=True)
    users = db.relationship('User', cascade='all,delete', backref='group')

    @classmethod
    def default(cls):
        if len(User.query.all()) == 0:  # assume the first user is admin
            return cls.query.filter_by(name='administrator').first()
        return cls.query.filter_by(name='student').first()


class Lecture(db.Model, DictMixin):
    __tablename__ = 'Lecture'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False, unique=True)
    idx = Column(Integer, nullable=False)  # lecture orders
    idm = Column(String(255))  # the input device model name
    odm = Column(String(255), nullable=False, unique=True)  # the output device model name
    joins = Column(JSON)
    lecture_projects = db.relationship('LectureProject', cascade='all,delete',
                                       backref='lecture')
    code = Column(String)  # the vpython program
    iv_list = Column(JSON, nullable=False)  # input variable list
    output_variables = Column(JSON, nullable=False, default=[])
    odf_to_idf_mapping = Column(JSON, nullable=False, default={})

    _url_history = Column(JSON)
    _video_history = Column(JSON, nullable=False, default='[]')

    @property
    def url_history(self):
        if self._url_history is None:
            return []
        return json.loads(self._url_history)

    @url_history.setter
    def url_history(self, val: list):
        self._url_history = json.dumps(val)

    url_history = db.synonym('_url_history', descriptor=url_history)

    @property
    def url(self):  # HackMD url
        histories = self.url_history
        if histories and len(histories) > 0:
            return histories[0]
        return ''

    @property
    def video_history(self):
        return json.loads(self._video_history)

    @video_history.setter
    def video_history(self, val: list):
        self._video_history = json.dumps(val)

    video_history = db.synonym('_video_history', descriptor=video_history)

    @property
    def video(self):  # video stream url
        if len(self.video_history) > 0:
            return self.video_history[0]
        return ''

    def __init__(self, **kwargs):
        if 'code_path' in kwargs:
            p = kwargs.pop('code_path')
            with open(p) as f:
                kwargs['code'] = f.read()

        return super().__init__(**kwargs)

    @classmethod
    def list_(cls):
        return tuple(map(
            lambda x: x.to_dict(['id', 'name', 'url', 'idm', 'odm']),
            cls.query.order_by(asc(cls.idx)).all()))

    @property
    def da_name(self):  # readonly
        return self.odm

    @classmethod
    def isexist(cls, name):
        return cls.query.filter_by(name=name).first() is not None


class Template(db.Model, DictMixin):
    __tablename__ = 'Template'
    id = Column(Integer, primary_key=True, nullable=False)
    dm = Column(String(255), nullable=False, unique=True)
    code = Column(String)  # the vpython program template
    iv_list = Column(JSON, nullable=False)  # input variable list

    def __init__(self, **kwargs):
        if 'code_path' in kwargs:
            p = kwargs.pop('code_path')
            with open(p) as f:
                kwargs['code'] = f.read()

        return super().__init__(**kwargs)

    @classmethod
    def isexist(cls, **kwargs):
        return cls.query.filter_by(**kwargs).first() is not None


class InputVariable(db.Model, DictMixin):
    __tablename__ = 'InputVariable'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False, unique=True)


class OutputVariable(db.Model, DictMixin):
    __tablename__ = 'OutputVariable'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False, unique=True)


class Unit(db.Model, DictMixin):
    __tablename__ = 'Unit'
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False, unique=True)


class LectureProject(db.Model, DictMixin):
    __tablename__ = 'LectureProject'
    id = Column(Integer, primary_key=True, nullable=False)
    u_id = Column(Integer, ForeignKey('User.id'), nullable=False)
    lec_id = Column(Integer, ForeignKey('Lecture.id'), nullable=False)
    p_id = Column(Integer, nullable=False)  # iottalk project id
    code = Column(String)  # the vpython program
    comment = db.relationship('Comment', uselist=False, cascade='all,delete',
                              backref='project')
    # ``user`` is available via backref
    # ``lecture`` is available via backref
    historical_data = db.relationship('HistoricalData', cascade='all,delete',
                                      backref='project')
    last_bind = Column(Boolean, nullable=False, default=False)

    # cache project.get because it takes 2.x seconds
    project_cache = None

    def get_project(self):
        if not self.project_cache:
            from edutalk.utils import ag_ccmapi
            self.project_cache = ag_ccmapi(self.u_id, 'project.get', {'key': self.p_id})
        return self.project_cache

    @property
    def ido(self):
        from edutalk.utils import ag_ccmapi
        do_id = next(x['do_id']
                     for x in self.get_project()['ido']
                     if x['dm_name'] == self.lecture.idm)
        return ag_ccmapi(self.u_id, 'deviceobject.get', {'p_id': self.p_id, 'do_id': do_id})

    @property
    def odo(self):
        from edutalk.utils import ag_ccmapi
        do_id = next(x['do_id']
                     for x in self.get_project()['odo']
                     if x['dm_name'] == self.lecture.odm)
        return ag_ccmapi(self.u_id, 'deviceobject.get', {'p_id': self.p_id, 'do_id': do_id})

    @property
    def logger_do(self):
        from edutalk.utils import ag_ccmapi
        do_id = next(x['do_id']
                     for x in self.get_project()['odo']
                     if x['dm_name'] == 'SimpleLogger')
        return ag_ccmapi(self.u_id, 'deviceobject.get', {'p_id': self.p_id, 'do_id': do_id})

    @property
    def m2_ido(self):
        from edutalk.utils import ag_ccmapi
        do_id = next(x['do_id']
                     for x in self.get_project()['ido']
                     if x['dm_name'] == 'M2')
        return ag_ccmapi(self.u_id, 'deviceobject.get', {'p_id': self.p_id, 'do_id': do_id})

    @property
    def available_actuators_device(self):
        from edutalk.utils import ag_ccmapi
        devices = {}
        for do in self.actuators_do:
            if do['dm_name'] not in devices:
                devices[do['dm_name']] = \
                    [x for x in ag_ccmapi(self.u_id, 'device.get',
                                          {'p_id': self.p_id, 'do_id': do['do_id']})
                     if x['status'] == "online"]
        return devices

    @property
    def available_sensors_device(self):
        from edutalk.utils import ag_ccmapi
        devices = {}
        for do in self.sensors_do:
            if do['dm_name'] not in devices:
                if do['dm_name'] == self.lecture.idm:
                    devices['Smartphone'] = [{'d_name': 'Smartphone', 'mac_addr': ''}]
                elif do['dm_name'] in sensorOptions:
                    devices[do['dm_name']] = \
                        [x for x in ag_ccmapi(self.u_id, 'device.get',
                                              {'p_id': self.p_id, 'do_id': do['do_id']})
                         if x['status'] == "online"]
        return devices

    @property
    def sensors_do(self):
        return [x
                for x in self.get_project()['ido']
                if x['dm_name'] != self.lecture.odm]

    def clear_sensors_do(self):
        from edutalk.utils import ag_ccmapi
        for do in self.sensors_do:
            ag_ccmapi(self.u_id, 'deviceobject.delete',
                      {'p_id': self.p_id, 'do_id': do['do_id']})

    @property
    def actuators_do(self):
        return [x
                for x in self.get_project()['odo']
                if x['dm_name'] != self.lecture.odm and x['dm_name'] != 'SimpleLogger']

    def clear_actuators_do(self):
        from edutalk.utils import ag_ccmapi
        for do in self.actuators_do:
            ag_ccmapi(self.u_id, 'deviceobject.delete',
                      {'p_id': self.p_id, 'do_id': do['do_id']})

    def unbind_actuators(self):
        from edutalk.utils import ag_ccmapi
        if len(self.lecture.output_variables) > 0:
            try:
                ag_ccmapi(self.u_id, 'device.unbind',
                          {'p_id': self.p_id, 'do_id': do['do_id']})
            except CCMAPIError as e:
                log.error(f"Error unbinding actuator: {str(e)}")

    @classmethod
    def get_by_lec_user(cls, lecture, user):
        return cls.query.filter(cls.lecture == lecture, cls.user == user).first()

    @classmethod
    def get_by_lec_user_last_bind(cls, lecture, user):
        return cls.query. \
            filter(cls.lecture == lecture, cls.user == user,
                   cls.last_bind is True).first()

    @classmethod
    def create(cls, lecture, user):
        from edutalk.utils import ag_ccmapi
        try:
            project = ag_ccmapi(user.id, 'project.get', {'key': f'edu_{lecture.name}'})
        except CCMAPIError:
            pass
        else:
            ag_ccmapi(user.id, 'project.delete', {'p_id': project['p_id']})

        try:
            p_id = ag_ccmapi(user.id, 'project.create', {'p_name': f'edu_{lecture.name}'})
            ag_ccmapi(user.id, 'project.on', {'p_id': p_id})
            ag_ccmapi(user.id, 'deviceobject.create',
                      {'p_id': p_id, 'dm_name': 'SimpleLogger'})
            x = cls(user=user, lecture=lecture, p_id=p_id, code=lecture.code)
            x.create_na(user.id)
        except Exception as e:
            db.session.rollback()
            import traceback
            log.error(traceback.format_exc())
        else:
            x.comment = Comment()
            db.session.add(x)
            db.session.commit()
    def create_na(self, u_id):  # create device objects
        try:
            from edutalk.utils import ag_ccmapi

            ido_id = ag_ccmapi(u_id, 'deviceobject.create',
                            {'p_id': self.p_id, 'dm_name': self.lecture.idm})
            non_rc_do_id = {}
            non_rc_idfs = {}
            for device in sensorOptions:
                if device not in ('Input Box', 'Range Slider', 'Smartphone', 'Morsensor',):
                    do_id = ag_ccmapi(u_id, 'deviceobject.create', {'p_id': self.p_id, 'dm_name': device})
                    non_rc_do_id[device] = do_id
                    non_rc_idfs[device] = [x['df_name'] for x in
                                        ag_ccmapi(u_id, 'devicemodel.get', {'key': device})['df_list']]

            odo_id = ag_ccmapi(u_id, 'deviceobject.create',
                            {'p_id': self.p_id, 'dm_name': self.lecture.odm})
            fn_list = ag_ccmapi(u_id, 'function.list')

            ido = ag_ccmapi(u_id, 'deviceobject.get',
                            {'p_id': self.p_id, 'do_id': ido_id})['do']
            logger_do = self.logger_do['do']

            rc_idfs = set()
            skip = set()
            for k in non_rc_idfs:
                for item in non_rc_idfs[k]:
                    skip.add(item)
            for idf in ido['dfo']:
                if idf not in skip:
                    rc_idfs.add(idf)

            for idf in ido['dfo']:
                odf = '{}-O'.format(idf.split('-')[0])
                if (odf not in logger_do['dfo']):
                    odf = 'OneDimLogger-O'
                if idf in rc_idfs:
                    try:
                        ag_ccmapi(u_id, 'networkapplication.create',
                                {'p_id': self.p_id,
                                'joins': [(ido['do_id'], idf), [logger_do['do_id'], odf]]})
                    except CCMAPIError as e:
                        log.error(f"Error creating network application for RC IDF {idf}: {str(e)}")
                elif idf in non_rc_idfs['M2']:
                    try:
                        ag_ccmapi(u_id, 'networkapplication.create',
                                {'p_id': self.p_id,
                                'joins': [(non_rc_do_id['M2'], idf), [logger_do['do_id'], odf]]})
                    except CCMAPIError as e:
                        log.error(f"Error creating network application for M2 IDF {idf}: {str(e)}")

            joins = json.loads(self.lecture.joins) if isinstance(self.lecture.joins, str) else self.lecture.joins
            for odf in joins:
                na_joins = [(odo_id, odf)]
                for idf in joins[odf]:
                    # join rc
                    if idf[0] in rc_idfs:
                        na_joins.append((ido_id, idf[0]))
                    # join m2
                    elif idf[0] in non_rc_idfs.get('M2', []):
                        na_joins.append((non_rc_do_id.get('M2'), idf[0]))

                if not na_joins:
                    log.warning(f"No valid joins found for ODF {odf}")
                    continue

                try:
                    na_id = ag_ccmapi(u_id, 'networkapplication.create',
                                    {'p_id': self.p_id, 'joins': na_joins})
                    na_info = ag_ccmapi(u_id, 'networkapplication.get',
                                        {'p_id': self.p_id, 'na_id': na_id})
                    idf_order = {info['df_name']: f'x{index + 1}'
                                for index, info in enumerate(na_info['input'])}
                    dfm_list = [{'dfo_id': info['dfo_id'], 'dfmp_list': info['dfmp']}
                                for info in na_info['input']]
                    dfmp_list = []
                    for index, dfmp in enumerate(na_info['output'][0]['dfmp']):
                        idf = joins[odf][index]
                        if len(idf_order) == 1:
                            fn_name = 'x1' if idf[1] == '' else idf[1]
                        else:
                            fn_name = idf_order[idf[0]]
                            fn_name += '1' if idf[1] == '' else idf[1][1]

                        fn_id = next(fn for fn in fn_list if fn['fn_name'] == fn_name)['fn_id']
                        ag_ccmapi(u_id, 'function.create_sdf',
                                {'fn_id': fn_id, 'df_id': na_info['output'][0]['df_id']})
                        dfmp['fn_id'] = fn_id
                        dfmp_list.append(dfmp)
                    dfm_list.append({'dfo_id': na_info['output'][0]['dfo_id'],
                                    'dfmp_list': dfmp_list})
                    ag_ccmapi(u_id, 'networkapplication.update',
                            {'p_id': self.p_id, 'na_id': na_id, 'dfm_list': dfm_list})
                except CCMAPIError as e:
                    log.error(f"Error creating or updating network application for ODF {odf}: {str(e)}")

            # create actuator device objects and join
            actuator_odf_id = {}
            used_actuators = set()
            output_variables = json.loads(self.lecture.output_variables) if isinstance(self.lecture.output_variables, str) else self.lecture.output_variables
            for actuator_var in output_variables:
                if isinstance(actuator_var, dict):
                    dm = actuator_var.get('actuator')
                    odf = actuator_var.get('odf')
                    if not dm or not odf:
                        continue
                    if odf not in actuator_odf_id:
                        actuator_odf_id[odf] = ag_ccmapi(u_id, 'devicefeature.get',
                                                        {'key': odf})['df_id']
                    used_actuators.add(dm)
                    # create device object
                    try:
                        actuator_do_id = ag_ccmapi(u_id, 'deviceobject.create',
                                                {'p_id': self.p_id, 'dm_name': dm,
                                                    'dfs': [actuator_odf_id[odf]]})
                        # join
                        na_joins = [(actuator_do_id, odf), (odo_id, actuator_var['idf'][0])]
                        ag_ccmapi(u_id, 'networkapplication.create',
                                {'p_id': self.p_id, 'joins': na_joins})
                    except CCMAPIError as e:
                        log.error(f"Error creating actuator device object or network application for {dm}: {str(e)}")
                else:
                    log.warning(f"Invalid actuator_var format: {actuator_var}")

            for dm in actuatorDm:
            # create placeholder device object for checking available actuators device
                odfs = [ag_ccmapi(u_id, 'devicefeature.get', {'key': df})['df_id']
                        for df in actuatorDm[dm]['odfs']]
                if dm not in used_actuators:
                    try:
                        ag_ccmapi(u_id, 'deviceobject.create',
                                {'p_id': self.p_id, 'dm_name': dm,
                                'dfs': odfs})  # 确保这里的 'dfs' 没有多余的空格
                    except CCMAPIError as e:
                        log.error(f"Error creating placeholder device object for {dm}: {str(e)}")

        except Exception as e:
            log.error(f"Unexpected error in create_na for LectureProject {self.id}: {str(e)}")
            log.error(traceback.format_exc())
            raise

    '''def create_na(self, u_id):  # create device objects
        from edutalk.utils import ag_ccmapi

        ido_id = ag_ccmapi(u_id, 'deviceobject.create',
                           {'p_id': self.p_id, 'dm_name': self.lecture.idm})
        non_rc_do_id = {}
        non_rc_idfs = {}
        for device in sensorOptions:
            if device not in ('Input Box', 'Range Slider', 'Smartphone', 'Morsensor',):
                do_id = ag_ccmapi(u_id, 'deviceobject.create', {'p_id': self.p_id, 'dm_name': device})
                non_rc_do_id[device] = do_id
                non_rc_idfs[device] = [x['df_name'] for x in
                                       ag_ccmapi(u_id, 'devicemodel.get', {'key': device})['df_list']]

        odo_id = ag_ccmapi(u_id, 'deviceobject.create',
                           {'p_id': self.p_id, 'dm_name': self.lecture.odm})
        fn_list = ag_ccmapi(u_id, 'function.list')

        ido = ag_ccmapi(u_id, 'deviceobject.get',
                        {'p_id': self.p_id, 'do_id': ido_id})['do']
        logger_do = self.logger_do['do']

        rc_idfs = set()
        skip = set()
        for k in non_rc_idfs:
            for item in non_rc_idfs[k]:
                skip.add(item)
        for idf in ido['dfo']:
            if idf not in skip:
                rc_idfs.add(idf)
        # todo: we must redesign replay/logger to frontend/variable based !!!
        # because it is expensive to add new senor devices in current impl
        # 1. sensor data format differs from any existing device model
        # in iottalk in order to support replay/logger
        # 2. we have to manually join like below in current impl
        for idf in ido['dfo']:
            odf = '{}-O'.format(idf.split('-')[0])
            if (odf not in logger_do['dfo']):
                odf = 'OneDimLogger-O'
            if idf in rc_idfs:
                ag_ccmapi(u_id, 'networkapplication.create',
                          {'p_id': self.p_id,
                           'joins': [(ido['do_id'], idf), [logger_do['do_id'], odf]]})
            elif idf in non_rc_idfs['M2']:
                ag_ccmapi(u_id, 'networkapplication.create',
                          {'p_id': self.p_id,
                           'joins': [(non_rc_do_id['M2'], idf), [logger_do['do_id'], odf]]})

        for odf in self.lecture.joins:
            na_joins = [(odo_id, odf)]
            for idf in self.lecture.joins[odf]:
                # join rc
                if idf[0] in rc_idfs:
                    na_joins.append((ido_id, idf[0]))
            for idf in self.lecture.joins[odf]:
                # join m2
                if idf[0] in non_rc_idfs['M2']:
                    na_joins.append((non_rc_do_id['M2'], idf[0]))

            na_id = ag_ccmapi(u_id, 'networkapplication.create',
                              {'p_id': self.p_id, 'joins': na_joins})
            na_info = ag_ccmapi(u_id, 'networkapplication.get',
                                {'p_id': self.p_id, 'na_id': na_id})
            idf_order = {info['df_name']: f'x{index + 1}'
                         for index, info in enumerate(na_info['input'])}
            dfm_list = [{'dfo_id': info['dfo_id'], 'dfmp_list': info['dfmp']}
                        for info in na_info['input']]
            dfmp_list = []
            for index, dfmp in enumerate(na_info['output'][0]['dfmp']):
                idf = self.lecture.joins[odf][index]
                if len(idf_order) == 1:
                    fn_name = 'x1' if idf[1] == '' else idf[1]
                else:
                    fn_name = idf_order[idf[0]]
                    fn_name += '1' if idf[1] == '' else idf[1][1]

                fn_id = next(fn for fn in fn_list if fn['fn_name'] == fn_name)['fn_id']
                ag_ccmapi(u_id, 'function.create_sdf',
                          {'fn_id': fn_id, 'df_id': na_info['output'][0]['df_id']})
                dfmp['fn_id'] = fn_id
                dfmp_list.append(dfmp)
            dfm_list.append({'dfo_id': na_info['output'][0]['dfo_id'],
                             'dfmp_list': dfmp_list})
            ag_ccmapi(u_id, 'networkapplication.update',
                      {'p_id': self.p_id, 'na_id': na_id, 'dfm_list': dfm_list})

        # create actuator device objects and join
        actuator_odf_id = {}
        used_actuators = set()
        for actuator_var in self.lecture.output_variables:
            dm = actuator_var['actuator']
            odf = actuator_var['odf']
            if not dm or not odf:
                continue
            if odf not in actuator_odf_id:
                actuator_odf_id[odf] = ag_ccmapi(u_id, 'devicefeature.get',
                                                 {'key': odf})['df_id']
            used_actuators.add(dm)
            # create device object
            actuator_do_id = ag_ccmapi(u_id, 'deviceobject.create',
                                       {'p_id': self.p_id, 'dm_name': dm,
                                        'dfs': [actuator_odf_id[odf]]})
            # join
            na_joins = [(actuator_do_id, odf), (odo_id, actuator_var['idf'][0])]
            ag_ccmapi(u_id, 'networkapplication.create',
                      {'p_id': self.p_id, 'joins': na_joins})

        for dm in actuatorDm:
            # create placeholder device object for checking available actuators device
            odfs = [ag_ccmapi(u_id, 'devicefeature.get', {'key': df})['df_id']
                    for df in actuatorDm[dm]['odfs']]
            if dm not in used_actuators:
                ag_ccmapi(u_id, 'deviceobject.create',
                          {'p_id': self.p_id, 'dm_name': dm,
                           'dfs': odfs})'''
    
    
    def delete(self):
        from edutalk.utils import ag_ccmapi
        try:
            ag_ccmapi(self.u_id, 'device.unbind',
                      {'p_id': self.p_id, 'do_id': self.ido['do']['do_id']})
            ag_ccmapi(self.u_id, 'device.unbind',
                      {'p_id': self.p_id, 'do_id': self.odo['do']['do_id']})
            ag_ccmapi(self.u_id, 'device.unbind',
                      {'p_id': self.p_id, 'do_id': self.logger_do['do']['do_id']})
            ag_ccmapi(self.u_id, 'project.delete', {'p_id': self.p_id})
        except CCMAPIError:
            log.warning('user %s project %s delete failed',
                        self.user.username, self.p_id)
        db.session.delete(self)
        db.session.commit()


class Comment(db.Model, DictMixin):
    __tablename__ = 'Comment'
    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('LectureProject.id'), nullable=False)
    # ``project`` is avialable via backref
    content = Column(String, nullable=False, default="")


class HistoricalData(db.Model, DictMixin):
    __tablename__ = 'HistoricalData'
    id = Column(Integer, primary_key=True, nullable=False)
    project_id = Column(Integer, ForeignKey('LectureProject.id'), nullable=False)
    # ``project`` is avialable via backref
    name = Column(String, nullable=False)
    _data = Column(JSON)

    @property
    def data(self):
        return json.loads(self._data)

    @data.setter
    def data(self, val: list):
        self._data = json.dumps(val)

    data = db.synonym('_data', descriptor=data)

    @classmethod
    def get_by_project_user(cls, project, name):
        return cls.query.filter(cls.project == project, cls.name == name).first()

    @classmethod
    def query_all(cls, project):
        return [name[0] for name in
                cls.query.with_entities(cls.name).filter(cls.project == project).all()]

    @classmethod
    def query_file(cls, name):
        return cls.query.filter(cls.name == name).first()


class RefreshToken(db.Model, TimestampMixin):
    id = Column(Integer, primary_key=True)
    token = Column(Text)

    user_id = Column(Integer, ForeignKey('User.id'))

    user = db.relationship('User', back_populates='refresh_token')
    access_tokens = db.relationship(
        'AccessToken',
        back_populates='refresh_token',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class AccessToken(db.Model, TimestampMixin):
    id = Column(Integer, primary_key=True)
    token = Column(Text)
    expires_at = Column(db.DateTime())

    user_id = Column(Integer, ForeignKey('User.id'))
    refresh_token_id = Column(Integer, ForeignKey('refresh_token.id'))

    user = db.relationship('User', back_populates='access_tokens')
    refresh_token = db.relationship('RefreshToken', back_populates='access_tokens')

    def refresh(self):
        from authlib.integrations.requests_client import OAuth2Session

        try:
            oauth2_client = OAuth2Session(
                client_id=config.client_id,
                client_secret=config.client_secret,
                scope='openid'
            )

            token_response = oauth2_client.refresh_token(
                url=config.token_endpoint,
                refresh_token=self.refresh_token.token)

            if token_response.get('refresh_token'):
                self.refresh_token.token = token_response.get('refresh_token')

            # Create a new access token record
            access_token_record = AccessToken(
                token=token_response.get('access_token'),
                expires_at=(
                        datetime.utcnow().replace(tzinfo=pytz.UTC)
                        + timedelta(seconds=token_response.get('expires_in', 0))
                ),
                user=self.user,
                refresh_token=self.refresh_token
            )
            db.session.add(access_token_record)
        except Exception as e:
            db.session.rollback()
            log.error(e)
        else:
            db.session.commit()
