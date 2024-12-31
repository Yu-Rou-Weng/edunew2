"""
Project module.

contains:

    op_create_project
    op_update_project
    op_delete_project
    op_get_project_list
    op_get_project_status
    op_get_project_info
    op_search_project
    op_rename_project

    is_project_owner
"""
from sqlalchemy import and_

from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError, record_parser
from iotgui.db import model


class Project(Interface):
    """Project class."""

    def op_create_project(self, ctx, p_name):
        """
        Create a new Project, and return new p_id.

        The project name should be unique for a user.

        :param p_name: <Project.p_name>
        :type p_name: str

        :return:
            {
                'p_id': '<Project.p_id>'
            }
        """
        u_id = ctx.u_id

        # check project name is in use
        if self.op_search_project(ctx, p_name):
            raise CCMError('project name already exists')

        # create new project
        new_project = model.Project(
            p_name=p_name,
            status='off',
            restart=0,
            u_id=u_id,
            exception='',
            sim='off',
        )
        ctx.db_session.add(new_project)
        ctx.db_session.commit()

        return {'p_id': new_project.p_id}

    def op_update_project(self, ctx, p_id, status):
        """
        Update Project's status.

        :param p_id: <Project.p_id>
        :param status: 'on' / 'off'
        :type p_id: int
        :type status: str

        :return:
            {
                'p_id': '<Project.p_id>',
                'status': 'on' / 'off'
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # check project exist
        project_record = self._query_project(db_session, u_id, p_id)
        if not project_record:
            raise CCMError('project id {} not found'.format(p_id))

        pre_status = project_record.status
        if str(pre_status) == str(status):
            return {'status': status, 'p_id': p_id}

        # update Project status
        (db_session.query(model.Project)
                   .filter(and_(model.Project.p_id == p_id,
                                model.Project.u_id == u_id))
                   .update({'status': status}))
        db_session.commit()

        # update esm graph status
        na_list = self.op_get_na_list(ctx, p_id).get('na', [])
        if str(status) == 'on':  # 'off' > 'on'
            for na in na_list:
                # attach graph
                self.attach_graph(ctx, na['na_id'])
                # add all link
                na_info = self.op_get_na_info(ctx, na['na_id'], p_id)
                for dfm in na_info.get('input', []):
                    self.add_link(ctx, na['na_id'], dfm['dfo_id'])
                for dfm in na_info.get('output', []):
                    self.add_link(ctx, na['na_id'], dfm['dfo_id'])
        elif str(status) == 'off':  # 'on' > 'off'
            for na in na_list:
                # remove all link
                na_info = self.op_get_na_info(ctx, na['na_id'], p_id)
                for dfm in na_info.get('input', []):
                    if dfm['mac_addr']:
                        self.remove_link(na['na_id'], dfm['mac_addr'], 'input',
                                         dfm['df_name'])
                for dfm in na_info.get('output', []):
                    if dfm['mac_addr']:
                        self.remove_link(na['na_id'], dfm['mac_addr'], 'output',
                                         dfm['df_name'])
                # detach graph
                self.detach_graph(na['na_id'])

        return {'status': status, 'p_id': p_id}

    def op_delete_project(self, ctx, p_id):
        """
        Delete a Project by given p_id.

        Only allow delete owner project.

        :param p_id: <Project.p_id>
        :type p_id: int

        :return:
            {
                'p_id': '<Project.p_id>'
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # check project exist
        project_records = (db_session.query(model.Project)
                                     .filter(model.Project.p_id == p_id,
                                             model.Project.u_id == u_id)
                                     .all())
        if not project_records:
            raise CCMError('project {} not found'.format(p_id))

        # delete all NetworkApplication
        na_records = (db_session.query(model.NetworkApplication)
                                .filter(model.NetworkApplication.p_id == p_id)
                                .all())
        for na_record in na_records:
            self.op_delete_na(ctx, na_record.na_id)

        # delete all DeviceObject (and Simulated device)
        do_records = (db_session
                      .query(model.DeviceObject)
                      .filter(model.DeviceObject.p_id == p_id)
                      .all())
        for do_record in do_records:
            self.op_delete_device_object(ctx, do_record.do_id)

        # delete Project
        (db_session
            .query(model.Project)
            .filter(model.Project.p_id == p_id)
            .delete())
        db_session.commit()

        return {'p_id': p_id}

    def op_get_project_list(self, ctx):
        """
        Query all Projects of logging user owned.

        :return: List[<Project>]
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        project_records = (db_session.query(model.Project)
                                     .filter(model.Project.u_id == u_id)
                                     .all())

        project_list = []
        for project_record in project_records:
            project_list.append(record_parser(project_record))

        return project_list

    def op_get_project_status(self, ctx, p_id):
        """
        Get the Project's status.

        :param p_id: <Project.p_id>
        :type p_id: int

        :return:
            'on' / 'off'
        """
        project_record = (ctx.db_session
                             .query(model.Project)
                             .filter(and_(model.Project.p_id == p_id))
                             .first())
        if not project_record:
            raise CCMError('project id {} not found'.format(p_id))

        return project_record.status

    def op_get_project_info(self, ctx, p_id):
        """
        Get the Project's connective situation.

        Includes input Device Object list,
        output Device Object list,
        and NetworkApplicatioin list.

        :param p_id: <Project.p_id>
        :type p_id: int

        :return:
            {
                'p_id': '<Project.p_id>',
                'sim': '<Project.sim>',
                'na': [ <na_info>, ...],
                'ido': [ '<do_info>', ...],
                'odo': [ '<do_info>, ...']
            }

            <na_info>: check op_get_na_list

            <do_info>:
                {
                    'do_id': '<DeviceObject.do_id>',
                    'dm_name': '<DeviceModel.dm_name>',
                    'd_id': '<Device.d_id>',
                    'd_name': '<Device.d_name>',
                    'status': '<Device.status>',
                    'dfo': [ <dfo_info>, ...]
                }

            <dfo_info>:
                {
                    'dfo_id': '<DFObject.dfo_id>',
                    'alias_name': '<DFObject.alias_name>',
                    'df_type': '<DeviceFeature.df_type>',
                    'src': '<image path>'  # image path... may upload
                }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # check project exist
        project_record = (db_session.query(model.Project)
                                    .filter(and_(model.Project.p_id == p_id,
                                                 model.Project.u_id == u_id))
                                    .first())
        if not project_record:
            raise CCMError('project not found. u_id:{}, p_id:{}.'.format(u_id, p_id))

        result = record_parser(project_record)
        result['na'] = self.op_get_na_list(ctx, p_id)['na']
        result['ido'] = []
        result['odo'] = []

        do_records = (
            db_session.query(model.DeviceObject.do_id,
                             model.DeviceObject.d_id,
                             model.DeviceModel.dm_id,
                             model.DeviceModel.dm_name,
                             model.Device.d_name,
                             model.Device.status)
                      .select_from(model.DeviceObject)
                      .join(model.DeviceModel)
                      .outerjoin(model.Device,
                                 and_(model.Device.d_id == model.DeviceObject.d_id,
                                      model.Device.is_sim == 0))
                      .filter(model.DeviceObject.p_id == p_id)
                      .order_by(model.DeviceObject.do_id)
                      .all()
        )
        for do_record in do_records:
            ido = record_parser(do_record)
            ido['dfo'] = []

            odo = record_parser(do_record)
            odo['dfo'] = []

            dfo_records = (db_session.query(model.DeviceFeature.df_id,
                                            model.DFObject.dfo_id,
                                            model.DFObject.alias_name,
                                            model.DeviceFeature.df_type)
                                     .select_from(model.DFObject)
                                     .join(model.DeviceFeature)
                                     .filter(model.DFObject.do_id == do_record.do_id)
                                     .order_by(model.DeviceFeature.df_name)
                                     .all())

            for dfo_record in dfo_records:
                dfo = record_parser(dfo_record)

                # use Tag to icon
                tags = self.op_get_dm_df_tag(ctx,
                                             df_id=dfo_record.df_id,
                                             dm_id=do_record.dm_id).get('tags', [])
                if tags:
                    dfo['src'] = ('/static/images/ec_icon/{}.png'
                                  .format(tags[0].get('tag_name', ' ')[0].upper()))
                else:
                    dfo['src'] = None

                if dfo_record.df_type == 'input':
                    ido['dfo'].append(dfo)
                elif dfo_record.df_type == 'output':
                    odo['dfo'].append(dfo)

            if ido['dfo']:
                result['ido'].append(ido)

            if odo['dfo']:
                result['odo'].append(odo)

        return result

    def op_search_project(self, ctx, p_name):
        """
        Check project name is in use.

        If used, return p_id, else None.

        :param p_name: <Project.p_name>
        :type p_name: str

        :return:
            <Project.p_id> / None
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        project_record = (db_session.query(model.Project)
                                    .filter(model.Project.p_name == p_name)
                                    .filter(model.Project.u_id == u_id)
                                    .first())

        return project_record.p_id if project_record else None

    def op_rename_project(self, ctx, p_id: int, newname: str):
        """
        Rename a project

        :param p_id: the project id

        :return:
            {
                'p_id': <Project.p_id>,
                'p_name': <Project.p_name>,
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        p = self._query_project(db_session, u_id, p_id)
        if not p:
            raise CCMError('project not found')

        # check name duplication
        if self.op_search_project(ctx, newname):
            raise CCMError('project name already exists')

        # rename
        p.p_name = str(newname)
        db_session.commit()
        return {'p_id': p.p_id, 'p_name': p.p_name}

    @staticmethod
    def _query_project(db_session, u_id, p_id):
        return (db_session
                .query(model.Project)
                .filter(and_(model.Project.p_id == p_id,
                             model.Project.u_id == u_id))
                .first())

    @classmethod
    def is_project_owner(cls, db_session, u_id, p_id, throw_err=False):
        '''
        Given a u_id and p_id, test the ownership.

        :param throw_err: if ``True``, this function will raise CCMError for
            the case of project not found.
        '''
        x = cls._query_project(db_session, u_id, p_id)
        if x is None and throw_err:
            raise CCMError('Project id {} not found'.format(p_id))
        return x is not None
