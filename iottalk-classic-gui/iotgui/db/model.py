"""
The Database Model.

contains:
    User
    RefreshToken
    AccessToken
    DeviceFeatureCategory
    DeviceFeature
    DeviceModel
    DM_DF
    Unit
    DF_Parameter
    Tag
    Tag_Parameter
    DM_DF_Tag
    Device
    Function
    FunctionVersion
    FunctionSDF
    Project
    NetworkApplication
    DeviceObject
    DFObject
    DF_Module
    MultipleJoin_Module
"""
import datetime

import pytz

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum,
    Float, ForeignKey, Integer, String, Text, UniqueConstraint, schema)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import functions as sql_funcs

from iotgui.config import TYPE_LIST

base = declarative_base()


class ExportMixin:
    def _getattr_r(self, obj, key: str, default=None):
        '''
        ``getattr`` with recursive resolving.
        '''
        x, d, y = key.partition('.')

        val = getattr(obj, x, default)

        if not d:  # without '.'
            return x, val
        if val is None:
            return y.rpartition('.')[-1], default

        return self._getattr_r(val, y, default)

    def to_dict(self, keys) -> dict:
        '''
        >>> x.to_dict(('a', 'b.c'))
        {
            'a': 42,
            'c': 24,
        }
        '''
        return dict(self._getattr_r(self, k, None) for k in keys)

    def export(self):
        '''
        For the ``export_project`` endpoint.
        '''
        raise NotImplementedError


class TimestampMixin():
    # Ref: https://myapollo.com.tw/zh-tw/sqlalchemy-mixin-and-custom-base-classes/
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(pytz.UTC),
        server_default=sql_funcs.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.datetime.now(pytz.UTC)
    )


class User(base, TimestampMixin, ExportMixin):
    """User."""

    __tablename__ = 'User'
    __table_args__ = {'sqlite_autoincrement': True}
    u_id = Column(Integer,
                  primary_key=True,
                  nullable=False)
    u_name = Column(String(255),
                    nullable=False,
                    unique=True)
    passwd = Column(String(255),
                    nullable=False)  # Legacy when using the account subsystem
    is_active = Column(Boolean,
                       server_default=schema.DefaultClause("1"),
                       nullable=False)
    is_deleted = Column(Boolean,
                        server_default=schema.DefaultClause("0"),
                        nullable=False)
    is_authenticated = Column(Boolean,  # only for flask-login use
                              server_default=schema.DefaultClause("1"),
                              nullable=False)
    is_anonymous = Column(Boolean,  # only for flask-login use
                          server_default=schema.DefaultClause("0"),
                          nullable=False)
    is_admin = Column(Boolean,  # only for flask-login use
                      server_default=schema.DefaultClause("0"),
                      nullable=False)
    projects = relationship('Project', backref='user')

    def get_id(self):
        """For flask-login authentication."""
        return self.u_id

    # V2.4.0 support Account Subsystem
    sub = Column(String(255), unique=True, nullable=True)
    email = Column(String(255), default='', nullable=False)
    refresh_token = relationship(
        'RefreshToken',
        back_populates='user',
        uselist=False,  # For one-to-one relationship, ref: https://tinyurl.com/jemrw6uf
        cascade='all, delete-orphan',
        passive_deletes=True,
    )
    access_tokens = relationship(
        'AccessToken',
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


# V2.4.0: Add RefreshToken Table to support Account Subsystem
class RefreshToken(base, TimestampMixin):
    """RefreshToken."""

    __tablename__ = 'RefreshToken'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True)
    token = Column(Text)

    u_id = Column(Integer, ForeignKey('User.u_id'))

    user = relationship('User', back_populates='refresh_token')
    access_tokens = relationship(
        'AccessToken',
        back_populates='refresh_token',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


# V2.4.0: Add AccessToken Table to support Account Subsystem
class AccessToken(base, TimestampMixin):
    """AccessToken."""

    __tablename__ = 'AccessToken'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, primary_key=True)
    token = Column(Text)
    expires_at = Column(DateTime())

    u_id = Column(Integer, ForeignKey('User.u_id'))
    refresh_token_id = Column(Integer, ForeignKey('RefreshToken.id'))

    user = relationship('User', back_populates='access_tokens')
    refresh_token = relationship('RefreshToken', back_populates='access_tokens')


class DeviceFeatureCategory(base):
    """DeviceFeatureCategory."""

    __tablename__ = 'DeviceFeatureCategory'
    __table_args__ = {'sqlite_autoincrement': True}
    dfc_id = Column(Integer,
                    primary_key=True,
                    nullable=False)
    dfc_name = Column(String(255),
                      nullable=False,
                      unique=True)


class DeviceFeature(base):
    """DeviceFeature."""

    __tablename__ = 'DeviceFeature'
    __table_args__ = {'sqlite_autoincrement': True}
    df_id = Column(Integer,
                   primary_key=True,
                   nullable=False)
    df_name = Column(String(255),
                     nullable=False,
                     unique=True)
    df_type = Column(Enum('input', 'output'),
                     nullable=False)
    df_category = Column(String(255),
                         ForeignKey('DeviceFeatureCategory.dfc_name'),
                         nullable=False,
                         default='None')
    # legacy
    param_no = Column(Integer,
                      nullable=False,
                      default=0)
    comment = Column(Text,
                     nullable=False)

    # DFObject is the 'many' side
    # DeviceFeatre is the 'one' side
    dfos = relationship('DFObject', back_populates='df')


class DeviceModel(base):
    """DeviceModel."""

    __tablename__ = 'DeviceModel'
    __table_args__ = {'sqlite_autoincrement': True}
    dm_id = Column(Integer,
                   primary_key=True,
                   nullable=False)
    dm_name = Column(String(255),
                     nullable=False,
                     unique=True)
    # legacy
    dm_type = Column(Enum('smartphone', 'wearable', 'other'),
                     nullable=False,
                     default='other')

    # Instead of V1 plural_DF_list
    # If True, select DF number using the drop-down menu on the GUI
    plural = Column(Boolean,
                    nullable=False,
                    default=False)
    # Instead of V1 create_model_without_select_feature_list
    # If True, select register device instead of DF
    device_only = Column(Boolean,
                         nullable=False,
                         default=False)

    # DeviceObject is the 'many' side
    # DeviceModel is the 'one' side
    dos = relationship('DeviceObject', back_populates='dm')


class DM_DF(base):
    """DM_DF."""

    __tablename__ = 'DM_DF'
    __table_args__ = (UniqueConstraint('dm_id', 'df_id', name='dm_df'),
                      {'sqlite_autoincrement': True})
    mf_id = Column(Integer,
                   primary_key=True,
                   nullable=False)
    dm_id = Column(Integer,
                   ForeignKey('DeviceModel.dm_id'),
                   nullable=False)
    df_id = Column(Integer,
                   ForeignKey('DeviceFeature.df_id'),
                   nullable=False)


class Unit(base):
    """Unit."""

    __tablename__ = 'Unit'
    __table_args__ = {'sqlite_autoincrement': True}
    unit_id = Column(Integer,
                     primary_key=True,
                     nullable=False)
    unit_name = Column(String(255),
                       nullable=False,
                       unique=True)


class DF_Parameter(base):
    """DF_Parameter."""

    __tablename__ = 'DF_Parameter'
    __table_args__ = (UniqueConstraint('df_id', 'mf_id', 'param_i', 'u_id',
                                       name='df_parameter'),
                      {'sqlite_autoincrement': True})
    dfp_id = Column(Integer,
                    primary_key=True,
                    nullable=False)
    df_id = Column(Integer,
                   ForeignKey('DeviceFeature.df_id'),
                   nullable=True)
    mf_id = Column(Integer,
                   ForeignKey('DM_DF.mf_id'),
                   nullable=True)
    # actually not use
    param_i = Column(Integer,
                     nullable=False)
    param_type = Column(Enum(*TYPE_LIST),
                        nullable=False)
    u_id = Column(Integer,
                  ForeignKey('User.u_id'),
                  nullable=True)
    idf_type = Column(Enum('variant', 'sample'),
                      nullable=False,
                      default='sample')
    fn_id = Column(Integer,
                   ForeignKey('Function.fn_id'),
                   nullable=True)
    min = Column(Float,
                 nullable=False,
                 default=0)
    max = Column(Float,
                 nullable=False,
                 default=0)
    # legacy
    normalization = Column(Boolean,
                           nullable=False,
                           default=0)

    # TODO:
    # unit_id = 1 for "None", if use Default Const.
    # otherwise, maybe have error.
    unit_id = Column(Integer,
                     ForeignKey('Unit.unit_id'),
                     nullable=False,
                     default=1)


class Tag(base):
    """Tag."""

    __tablename__ = 'Tag'
    __table_args__ = {'sqlite_autoincrement': True}
    tag_id = Column(Integer,
                    primary_key=True,
                    nullable=False)
    tag_name = Column(String(255),
                      nullable=False)
    param_no = Column(Integer,
                      nullable=False,
                      default=0)


class Tag_Parameter(base):
    """Tag_Parameter."""

    __tablename__ = 'Tag_Parameter'
    __table_args__ = {'sqlite_autoincrement': True}
    tagp_id = Column(Integer,
                     primary_key=True,
                     nullable=False)
    tag_id = Column(Integer,
                    ForeignKey('Tag.tag_id'))
    param_i = Column(Integer,
                     nullable=False)
    param_type = Column(Enum(*TYPE_LIST),
                        nullable=False)
    min = Column(Float,
                 default=0)
    max = Column(Float,
                 default=0)
    unit_id = Column(Integer,
                     ForeignKey('Unit.unit_id'),
                     nullable=False,
                     default=1)


class DM_DF_Tag(base):
    """DM_DF_Tag."""

    __tablename__ = 'DM_DF_Tag'
    __table_args__ = (UniqueConstraint('mf_id', 'tag_id', name='dm_df_tag'),
                      {'sqlite_autoincrement': True})
    mft_id = Column(Integer,
                    primary_key=True,
                    nullable=False)
    mf_id = Column(Integer,
                   ForeignKey('DM_DF.mf_id'),
                   nullable=False)
    tag_id = Column(Integer,
                    ForeignKey('Tag.tag_id'),
                    nullable=False)


class Device(base):
    """Device."""

    __tablename__ = 'Device'
    __table_args__ = {'sqlite_autoincrement': True}
    d_id = Column(Integer,
                  primary_key=True,
                  nullable=False)
    mac_addr = Column(String(255),
                      nullable=False,
                      unique=True)
    # legacy
    monitor = Column(String(255),
                     nullable=False,
                     default='')
    d_name = Column(String(255),
                    nullable=False)
    status = Column(Enum('online', 'offline'),
                    nullable=False,
                    default='online')
    u_id = Column(Integer,
                  ForeignKey('User.u_id'),
                  nullable=True)
    dm_id = Column(Integer,
                   ForeignKey('DeviceModel.dm_id'),
                   nullable=False)
    is_sim = Column(Boolean,
                    nullable=False)
    register_time = Column(DateTime,
                           nullable=False)
    extra_setup_webpage = Column(String(255),
                                 nullable=False,
                                 default='')
    device_webpage = Column(String(255),
                            nullable=False,
                            default='')


class Function(base):
    """Function."""

    __tablename__ = 'Function'
    __table_args__ = {'sqlite_autoincrement': True}
    fn_id = Column(Integer,
                   primary_key=True,
                   nullable=False)
    fn_name = Column(String(255),
                     nullable=False,
                     unique=True)

    # DF_Module is the 'many' side
    # Function is the 'one' side
    dfms = relationship('DF_Module', back_populates='fn')
    # MultipleJoin_Module is the 'many' side
    # Function is the 'one' side
    mjms = relationship('MultipleJoin_Module', back_populates='fn')
    is_protect = Column(Boolean,
                        nullable=False,
                        default=0)


class FunctionVersion(base):
    """FunctionVersion."""

    __tablename__ = 'FunctionVersion'
    __table_args__ = {'sqlite_autoincrement': True}
    fnvt_idx = Column(Integer,
                      primary_key=True,
                      nullable=False)
    fn_id = Column(Integer,
                   ForeignKey('Function.fn_id'),
                   nullable=False)
    u_id = Column(Integer,
                  ForeignKey('User.u_id'),
                  nullable=True)
    # legacy
    completeness = Column(Boolean,
                          default=1)

    # the field will used for modify date in iottalk v2.
    date = Column(Date,
                  nullable=False)
    code = Column(Text,
                  nullable=False)
    # legacy
    is_switch = Column(Boolean,
                       nullable=True,
                       default=0)
    # legacy
    non_df_args = Column(Text,
                         nullable=True,
                         default='')


class FunctionSDF(base):
    """FunctionSDF."""

    __tablename__ = 'FunctionSDF'
    __table_args__ = (UniqueConstraint('fn_id', 'u_id', 'df_id',
                                       name='mf_tag'),
                      {'sqlite_autoincrement': True})
    fnsdf_id = Column(Integer,
                      primary_key=True,
                      nullable=False)
    fn_id = Column(Integer,
                   ForeignKey('Function.fn_id'),
                   nullable=False)
    u_id = Column(Integer,
                  ForeignKey('User.u_id'),
                  nullable=True)
    df_id = Column(Integer,
                   ForeignKey('DeviceFeature.df_id'),
                   nullable=True)
    # legacy
    display = Column(Boolean,
                     nullable=False,
                     default=1)


class Project(base, ExportMixin):
    """Project."""

    __tablename__ = 'Project'
    __table_args__ = {'sqlite_autoincrement': True}
    p_id = Column(Integer,
                  primary_key=True,
                  nullable=False)
    p_name = Column(String(255),
                    nullable=False)
    u_id = Column(Integer,
                  ForeignKey('User.u_id'),
                  nullable=False)
    status = Column(Enum('on', 'off'),
                    nullable=False)
    # legacy
    restart = Column(Boolean,
                     nullable=False,
                     default=0)
    # legacy
    exception = Column(Text,
                       nullable=False,
                       default='')
    sim = Column(Enum('on', 'off'),
                 nullable=False,
                 default='off')

    nas = relationship('NetworkApplication', backref='project')
    # DeviceObject is the 'many' side
    # Project is the 'one' side
    dos = relationship('DeviceObject', back_populates='project')

    def export(self) -> dict:
        return {
            'NetworkApplication': [na.export() for na in self.nas],
            'DeviceObject': {do.do_id: do.export() for do in self.dos},
            **self.to_dict(('p_name',))
        }


class NetworkApplication(base, ExportMixin):
    """NetworkApplication."""

    __tablename__ = 'NetworkApplication'
    __table_args__ = (UniqueConstraint('na_idx', 'p_id', name='na'),
                      {'sqlite_autoincrement': True})
    na_id = Column(Integer,
                   primary_key=True,
                   nullable=False)
    na_name = Column(String(255),
                     nullable=False)
    na_idx = Column(Integer,
                    nullable=False)
    p_id = Column(Integer,
                  ForeignKey('Project.p_id'),
                  nullable=False)

    dfms = relationship('DF_Module', backref='na')
    mjms = relationship('MultipleJoin_Module', backref='na')

    def export(self) -> dict:
        return {
            'DF_Module': [dfm.export() for dfm in self.dfms],
            'MultipleJoin_Module': [mjm.export() for mjm in self.mjms],
            **self.to_dict(('na_name', 'na_idx'))
        }


class DeviceObject(base, ExportMixin):
    """DeviceObject."""

    __tablename__ = 'DeviceObject'
    __table_args__ = {'sqlite_autoincrement': True}
    do_id = Column(Integer,
                   primary_key=True,
                   nullable=False)
    dm_id = Column(Integer,
                   ForeignKey('DeviceModel.dm_id'),
                   nullable=False)
    p_id = Column(Integer,
                  ForeignKey('Project.p_id'),
                  nullable=False)
    # legacy
    do_idx = Column(Integer,
                    nullable=False,
                    default=0)
    d_id = Column(Integer,
                  ForeignKey('Device.d_id'),
                  nullable=True)

    # DeviceObject is the 'many' side
    # Project is the 'one' side
    project = relationship('Project', uselist=False, back_populates='dos')
    # DeviceObject is the 'many' side
    # DeviceModel is the 'one' side
    dm = relationship('DeviceModel', uselist=False, back_populates='dos')
    # DFObject is the 'many' side
    # DeviceObject is the 'one' side
    dfos = relationship('DFObject', back_populates='do')

    def export(self) -> dict:
        return {
            'dfo': {dfo.dfo_id: dfo.export() for dfo in self.dfos},
            **self.to_dict(('do_idx', 'dm.dm_name'))
        }


class DFObject(base, ExportMixin):
    """DFObject."""

    __tablename__ = 'DFObject'
    __table_args__ = (UniqueConstraint('do_id', 'df_id', name='dfo'),
                      {'sqlite_autoincrement': True})
    dfo_id = Column(Integer,
                    primary_key=True,
                    nullable=False)
    do_id = Column(Integer,
                   ForeignKey('DeviceObject.do_id'),
                   nullable=False)
    df_id = Column(Integer,
                   ForeignKey('DeviceFeature.df_id'),
                   nullable=False)
    alias_name = Column(String(255),
                        nullable=False)

    # 'DF_Module <-> DFObject' is many-to-one relationship
    # DF_Module is the 'many' side
    # DFObject is the 'one' side
    dfms = relationship('DF_Module', back_populates='dfo')
    # MultipleJoin_Module is the 'many' side
    # DFObject is the 'one' side
    mjms = relationship('MultipleJoin_Module', back_populates='dfo')
    # DFObject is the 'many' side
    # DeviceObject is the 'one' side
    do = relationship('DeviceObject', uselist=False, back_populates='dfos')
    # DFObject is the 'many' side
    # DeviceFeatre is the 'one' side
    df = relationship('DeviceFeature', uselist=False, back_populates='dfos')

    def export(self) -> dict:
        return self.to_dict(('df.df_name', 'alias_name'))


class DF_Module(base, ExportMixin):
    """DF_Module."""

    __tablename__ = 'DF_Module'
    __table_args__ = {'sqlite_autoincrement': True}
    na_id = Column(Integer,
                   ForeignKey('NetworkApplication.na_id'),
                   primary_key=True,
                   autoincrement=False,
                   nullable=False)
    dfo_id = Column(Integer,
                    ForeignKey('DFObject.dfo_id'),
                    primary_key=True,
                    autoincrement=False,
                    nullable=False)
    param_i = Column(Integer,
                     primary_key=True,
                     autoincrement=False,
                     nullable=False)
    idf_type = Column(Enum('variant', 'sample'),
                      nullable=False,
                      default='sample')
    fn_id = Column(Integer,
                   ForeignKey('Function.fn_id'),
                   nullable=True)
    min = Column(Float,
                 nullable=False,
                 default=0)
    max = Column(Float,
                 nullable=False,
                 default=0)

    normalization = Column(Boolean,
                           nullable=False,
                           default=0)
    color = Column(Enum('red', 'black'),
                   nullable=False,
                   default='black')

    # 'DF_Module <-> DFObject' is many-to-one relationship
    # DF_Module is the 'many' side
    # DFObject is the 'one' side
    dfo = relationship('DFObject', uselist=False, back_populates='dfms')
    # DF_Module is the 'many' side
    # Function is the 'one' side
    fn = relationship('Function', uselist=False, back_populates='dfms')

    def export(self) -> dict:
        ks = ('dfo_id', 'param_i', 'idf_type', 'min', 'max', 'normalization',
              'fn.fn_name')
        return self.to_dict(ks)


class MultipleJoin_Module(base, ExportMixin):
    """MultipleJoin_Module."""

    __tablename__ = 'MultipleJoin_Module'
    __table_args__ = (UniqueConstraint('na_id', 'dfo_id', name='mjm'),
                      {'sqlite_autoincrement': True})
    na_id = Column(Integer,
                   ForeignKey('NetworkApplication.na_id'),
                   primary_key=True,
                   autoincrement=False,
                   nullable=False)
    param_i = Column(Integer,
                     primary_key=True,
                     autoincrement=False,
                     nullable=False)
    fn_id = Column(Integer,
                   ForeignKey('Function.fn_id'))
    dfo_id = Column(Integer,
                    ForeignKey('DFObject.dfo_id'),
                    nullable=False)

    # MultipleJoin_Module is the 'many' side
    # DFObject is the 'one' side
    dfo = relationship('DFObject', uselist=False, back_populates='mjms')
    # MultipleJoin_Module is the 'many' side
    # Function is the 'one' side
    fn = relationship('Function', uselist=False, back_populates='mjms')

    def export(self) -> dict:
        return self.to_dict(('param_i', 'dfo_id', 'fn.fn_name'))
