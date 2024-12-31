"""
Function module.

contains:

    op_create_function
    op_update_function
    op_delete_function
    op_get_function_list
    op_get_device_feature_function_list
    op_get_na_function_list
    op_get_function_version_list
    op_get_function_info
    op_get_dfo_function_info
    op_create_functionSDF
    op_delete_functionSDF
"""
import itertools

from datetime import date
from sqlalchemy import func, or_

from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import CCMError, record_parser
from iotgui.db import model


class Function(Interface):
    """Function class."""

    def _compile_validation(self, code):
        try:
            # check compile error
            run_code = compile(code, 'run', mode='exec')
            context = {}
            exec(run_code, context)
        except Exception as e:
            raise CCMError('Compile Error: ' + str(e))

        # check run function is defined
        if 'run' not in context:
            raise CCMError('Compile Error: function name `run` is undefined')

    def op_create_function(self, ctx, fn_name, code, df_id=None, is_protect=False):
        """
        Create new Function.

        If function name is exist, update the function code for login user.
        Note: Function name should start with alphabet.

        :param fn_name: <Function.fn_name>
        :param code: <FunctionVersion.code>
        :param df_id: <DeviceFeature.df_id>, optional
                      if df_id give,
                      this function code is for the Device Feature,
                      o.w. for the join
        :param is_protect: <Function.is_protect>, optional
                           If True, this function can't be modify.
                           Allow settings only during initdb.
                           see https://jira.iottalk.tw/browse/GUI-4
        :type fn_name: str
        :type code: str
        :type df_id: int
        :type is_protect: boolean

        :return:
            {
                'fn_id': <Function.fn_id>,
                'fnvt_idx': <FunctionVersion.fnvt_idx>
            }
        """
        db_session = ctx.db_session

        # check function name is start with alphabet
        if not fn_name[0].isalpha():
            raise CCMError('Function name should start with alphabet.')

        # Check function name exist.
        query_fn = (db_session
                    .query(model.Function)
                    .filter(model.Function.fn_name == fn_name)
                    .first())
        if query_fn:
            # function is exist
            return self.op_update_function(ctx, query_fn.fn_id, code, df_id)

        # check function code first, only check compile
        self._compile_validation(code)

        # Save new function name.
        new_fn = model.Function(fn_name=fn_name,
                                is_protect=ctx.u_id is None and is_protect)
        db_session.add(new_fn)
        db_session.commit()

        # Save new function code.
        return self.op_update_function(ctx, new_fn.fn_id, code, df_id)

    def op_update_function(self, ctx, fn_id, code, df_id=None, fnvt_idx=None):
        """
        Update the Function code.

        If 'fnvt_idx' given, check owner is correct, then update code and date.
        Otherwise, create new function version.

        :param fn_id': <Function.fn_id>
        :param code': <FunctionVersion.code>
        :param df_id': <DeviceFeature.df_id>, optional
                       if given, add this function to SDF list,
                       else add to join function list
        :param fnvt_idx': <FunctionVersion.fnvt_idx>, optional
                          if given, update the function code by version,
                          else create new version
        :type fn_id: int
        :type code: str
        :type df_id: int
        :type fnvt_idx: int

        :return:
            {
                'fn_id': <Function.fn_id>,
                'fnvt_idx': <FunctionVersion.fnvt_idx>
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # check function exist
        query_fn = (db_session.query(model.Function)
                              .filter(model.Function.fn_id == fn_id)
                              .first())
        if not query_fn:
            raise CCMError('Function id not find.')
        elif u_id is not None and query_fn.is_protect == 1:
            msg = 'This function is a const function of the system and cannot be modified.'
            raise CCMError(msg)

        # check function code first
        self._compile_validation(code)

        # Add to Function list
        if df_id:
            self.op_create_functionSDF(ctx, fn_id, df_id)

        # get df_module usage info, for update esm link function
        query_dfm = (db_session.query(model.DF_Module)
                               .select_from(model.DF_Module)
                               .join(model.NetworkApplication)
                               .join(model.Project)
                               .filter(model.DF_Module.fn_id == fn_id,
                                       model.Project.u_id == u_id,
                                       model.DF_Module.param_i == 0)
                               .all())

        # check version id (fnvt_idx) is given,
        # if given, update the version,
        # otherwise create new version.
        if fnvt_idx:  # update version
            # check user is function version owner
            query_fnvt = (db_session.query(model.FunctionVersion)
                                    .filter(model.FunctionVersion.fnvt_idx == fnvt_idx,
                                            model.FunctionVersion.u_id == u_id)
                                    .first())
            if query_fnvt:
                # update graph function (na_id, dfo_id, new_fn_list, normalization)
                # this setting should be called before update database,
                # cause this function will check the data change between
                # database and user update.
                for dfm in query_dfm:
                    self._set_link_func(ctx, dfm.na_id, dfm.dfo_id, [fn_id],
                                        dfm.normalization)

                # update version
                query_fnvt.code = code
                query_fnvt.date = date.today()
                db_session.commit()
            else:
                # given version not find or user is not owner, raise CCMError
                raise CCMError('Function Version not find, or you are not owner.')
        else:  # create new version
            # update graph function (na_id, dfo_id, new_fn_list, normalization)
            # this setting should be called before update database,
            # cause this function will check the data change between
            # database and user update.
            for dfm in query_dfm:
                self._set_link_func(ctx, dfm.na_id, dfm.dfo_id, [fn_id], dfm.normalization)

            # Save new code
            new_fnv = model.FunctionVersion(fn_id=fn_id,
                                            code=code,
                                            date=date.today(),
                                            u_id=u_id)
            db_session.add(new_fnv)
            db_session.commit()

            fnvt_idx = new_fnv.fnvt_idx

        return {'fn_id': fn_id, 'fnvt_idx': fnvt_idx}

    def op_delete_function(self, ctx, fn_id):
        """
        Delete the Function by given fn_id.

        Server will check the Function is used or not.
        If delete successful, server will return fn_id, else return NULL

        :param fn_id: <Function.fn_id>
        :type fn_id: int

        :return:
            {
                'fn_id': '<Function.fn_id>'
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # check in used.
        # DF_Parameter, check feature default function.
        dfp_count, = (db_session.query(func.count(model.DF_Parameter.fn_id))
                                .select_from(model.DF_Parameter)
                                .filter(model.DF_Parameter.fn_id == fn_id)
                                .first())
        # DF_Module, check exist join link used.
        dfm_count, = (db_session.query(func.count(model.DF_Module.fn_id))
                                .filter(model.DF_Module.fn_id == fn_id)
                                .first())
        # MultipleJoin_Module, check multiple join function used.
        mjm_count, = (db_session.query(func.count(model.MultipleJoin_Module.fn_id))
                                .filter(model.MultipleJoin_Module.fn_id == fn_id)
                                .first())
        # FunctionSDF, check other user use for SDF
        sdf_count, = (db_session.query(func.count(model.FunctionSDF.fn_id))
                                .filter(model.FunctionSDF.u_id != u_id,
                                        model.FunctionSDF.u_id.isnot(None),
                                        model.FunctionSDF.fn_id == fn_id)
                                .first())

        if dfp_count or dfm_count or mjm_count or sdf_count:
            raise CCMError('This function is used, can not delete.')

        # check function exist
        query_fn = (db_session.query(model.Function)
                              .filter(model.Function.fn_id == fn_id)
                              .first())
        if not query_fn:
            raise CCMError('Function id not find.')
        elif u_id is not None and query_fn.is_protect == 1:
            raise CCMError('This function is a const function of the system\
                            and cannot be modified.')

        # Delete FunctionSDF
        (db_session.query(model.FunctionSDF)
                   .filter(model.FunctionSDF.fn_id == fn_id)
                   .delete())

        # Delete FunctionVersion
        (db_session.query(model.FunctionVersion)
                   .filter(model.FunctionVersion.fn_id == fn_id)
                   .delete())

        # Delete Function
        (db_session.query(model.Function)
                   .filter(model.Function.fn_id == fn_id)
                   .delete())

        db_session.commit()

        return {'fn_id': fn_id}

    def op_get_function_list(self, ctx):
        """
        Get all Functions.

        List all function name in Function which user can use.

        :return:
            {
                'fn_list': [ <Function>, ...]
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # query general function and user owned function
        query_fn = (db_session.query(model.Function)
                              .select_from(model.Function)
                              .join(model.FunctionVersion)
                              .filter(or_(model.FunctionVersion.u_id.is_(None),
                                          model.FunctionVersion.u_id == u_id))
                              .order_by(model.Function.fn_name)
                              .all())

        fn_list = []
        for function in query_fn:
            fn_list.append(record_parser(function))

        return {'fn_list': fn_list}

    def op_get_device_feature_function_list(self, ctx, df_id):
        """
        Get all Functions for Device Feature could use.

        The list of function only contain which store in FunctionSDF with
        login user and device feature.

        :param df_id: <DeviceFeature.df_id>
        :type df_id: int

        :return:
            {
                'fn_list': [ <Function>, ...]
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # query general function and user owned function
        query_fn = (db_session.query(model.Function)
                              .select_from(model.FunctionSDF)
                              .join(model.Function)
                              .filter(model.FunctionSDF.df_id == df_id,
                                      or_(model.FunctionSDF.u_id == u_id,
                                          model.FunctionSDF.u_id.is_(None)))
                              .order_by(model.Function.fn_name)
                              .all())

        fn_list = []
        for function in query_fn:
            fn_list.append(record_parser(function))

        return {'fn_list': fn_list}

    def op_get_na_function_list(self, ctx):
        """
        Get all Functions for Network Application could use.

        The list of function only contain which store in FunctionSDF with
        login user and NetworkApplication (df_id == None).

        :return:
            {
                'fn_list': [ <Function>, ...]
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # query general function and user owned function
        query_fn = (db_session.query(model.Function)
                              .select_from(model.FunctionSDF)
                              .join(model.Function)
                              .filter(model.FunctionSDF.df_id.is_(None),
                                      or_(model.FunctionSDF.u_id == u_id,
                                          model.FunctionSDF.u_id.is_(None)))
                              .order_by(model.Function.fn_name)
                              .all())

        fn_list = []
        for function in query_fn:
            fn_list.append(record_parser(function))

        return {'fn_list': fn_list}

    def op_get_function_version_list(self, ctx, fn_id):
        """
        Get the Function's version list by given fn_id.

        Return general function version and user's function version.

        :param fn_id: <Function.fn_id>
        :type fn_id: int

        :return:
            {
                'fnvt_list': [
                    <FunctionVersion>,
                    ...
                ]
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        query_fnvt = (db_session.query(model.FunctionVersion)
                                .filter(model.FunctionVersion.fn_id == fn_id,
                                        or_(model.FunctionVersion.u_id.is_(None),
                                            model.FunctionVersion.u_id == u_id))
                                .all())

        fnvt_list = []
        for fnvt in query_fnvt:
            fnvt_list.append(record_parser(fnvt))

        return {'fnvt_list': fnvt_list}

    def op_get_function_info(self, ctx, fn_id=None, fnvt_idx=None):
        """
        Get the latest Function's infomation by given fn_id.

        If 'fnvt_idx' given, return the version function,
        or return the lastest function version by login user with 'fn_id'.

        One of fnvt_id or fn_id should be supplied.

        :param fn_id: <Function.fn_id>, optional
        :param fnvt_idx: <FunctionVersion.fnvt_idx>, optional
                         specified the version
        :type fn_id: int
        :type fnvt_idx: int

        :return:
            {
                'fnvt_idx': '<FunctionVersion.fnvt_idx>',
                'name': '<Function.fn_name>',
                'code': '<FunctionVersion.code>',
                'date': '<FunctionVersion.date>'
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # query_fn = [<fn_name>, <fnvt_idx>, <code>, <date>]
        if not fnvt_idx and (not fn_id or int(fn_id) <= 0):
            # query no function
            query_fn = [None, None, None, None]
        elif fnvt_idx:
            # query by function version id (fnvt_idx)
            query_fn = (db_session.query(model.Function.fn_name,
                                         model.FunctionVersion.fnvt_idx,
                                         model.FunctionVersion.code,
                                         model.FunctionVersion.date)
                                  .select_from(model.FunctionVersion)
                                  .join(model.Function)
                                  .filter(model.FunctionVersion.fnvt_idx == fnvt_idx,
                                          or_(model.FunctionVersion.u_id == u_id,
                                              model.FunctionVersion.u_id.is_(None)))
                                  .order_by(model.FunctionVersion.fnvt_idx.desc())
                                  .first())

            if not query_fn:
                raise CCMError('Function version not find by fnvt_idx.')
        elif fn_id:
            # query by function id (fn_id)
            query_fn = (db_session.query(model.Function.fn_name,
                                         model.FunctionVersion.fnvt_idx,
                                         model.FunctionVersion.code,
                                         model.FunctionVersion.date)
                                  .select_from(model.FunctionVersion)
                                  .join(model.Function)
                                  .filter(model.FunctionVersion.fn_id == fn_id,
                                          or_(model.FunctionVersion.u_id == u_id,
                                              model.FunctionVersion.u_id.is_(None)))
                                  .order_by(model.FunctionVersion.fnvt_idx.desc())
                                  .first())

            if not query_fn:
                raise CCMError('Function version not find by fn_id.')
        else:
            raise CCMError('Can\'t query by given info.')

        result = {
            'name': query_fn[0],
            'fnvt_idx': query_fn[1],
            'code': query_fn[2],
            'date': str(query_fn[3])
        }

        return result

    def op_get_dfo_function_info(self, ctx, dfo_id=None, na_id=None):
        """
        Get Functions detail info by DFObject.

        For the GUI Function modify page.
        Return the list of specified function for df,
        the list of not specified function for df

        :param dfo_id: <DFObject.dfo_id>, optional
                       if given, return the function list for correspond
                       Device Feature by the given Device Feature Object,
                       else, return the function list for join
            }

        :return:
            {
                'df_id': '<DeviceFeature.df_id>',
                'dfo_id': '<DFObject.dfo_id>',
                'df_name': '<DeviceFeature.df_name>',
                'fn_list': [ <Function>, ...],  # DeviceFeature Function list
                'other_fn_list': [ <Function>, ...],
                'dfm_fn_list': [<DF_Module.fn_id>, ...],  # only for GUI usage
            }
        """
        db_session = ctx.db_session

        # default info for join
        result = {
            'df_id': None,
            'dfo_id': dfo_id,
            'df_name': 'Join'
        }

        # check is not join
        if dfo_id:
            # get given dfo info
            query_df = (db_session.query(model.DeviceFeature)
                                  .select_from(model.DFObject)
                                  .join(model.DeviceFeature)
                                  .filter(model.DFObject.dfo_id == dfo_id)
                                  .first())

            if not query_df:
                raise CCMError('Given Device Feture Object not find.')

            result['df_id'] = query_df.df_id
            result['df_name'] = query_df.df_name

        # get Function list
        if result['df_id']:
            # get df function list
            df_fn_list = self.op_get_device_feature_function_list(
                ctx, result['df_id']).get('fn_list', [])

            # query dfm useage function, only for GUI
            dfo_fn_list = (db_session.query(model.DF_Module.fn_id)
                                     .select_from(model.DF_Module)
                                     .filter(model.DF_Module.dfo_id == dfo_id)
                                     .all())
            result['dfm_fn_list'] = [fn_id for fn_id, in dfo_fn_list]
        else:
            # get join function list
            df_fn_list = self.op_get_na_function_list(ctx).get('fn_list', [])

            # query join function, only for GUI
            join_fn_id = (db_session.query(model.MultipleJoin_Module.fn_id)
                                    .select_from(model.MultipleJoin_Module)
                                    .filter(model.MultipleJoin_Module.na_id == na_id)
                                    .first())
            if join_fn_id:
                result['multiplejoin_fn_id'] = join_fn_id[0]

        result['fn_list'] = df_fn_list

        # other Function list which not in used list
        all_fn_list = self.op_get_function_list(ctx).get('fn_list', [])
        other_fn_list = list(itertools.filterfalse(lambda x: x in df_fn_list,
                                                   all_fn_list))
        result['other_fn_list'] = other_fn_list

        return result

    def op_create_functionSDF(self, ctx, fn_id, df_id=None):
        """
        Add the Function to the usage list for
        Device Feature or Network Application.

        This addition will store in the FunctionSDF,
        and specified the login user.
        This API NOT support add the function to the usage list for general.

        :param fn_id: <Function.fn_id>
        :param df_id: <DeviceFeature.df_id>, optional
                      if given, add the function to the function list
                      by given Device Feature,
                      else, add the function to the join function list
        :type fn_id: int
        :type df_id: int

        :return:
            {
                'df_id': '<DeviceFeature.df_id>',
                'fn_id': '<Function.fn_id>'
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # check df is exist
        if df_id:
            query_df = (db_session.query(model.DeviceFeature)
                                  .filter(model.DeviceFeature.df_id == df_id)
                                  .first())

            if not query_df:
                raise CCMError('Device Feature not find.')

        # check record exist
        query_sdf = (db_session.query(model.FunctionSDF)
                               .filter(model.FunctionSDF.fn_id == fn_id,
                                       model.FunctionSDF.df_id == df_id,
                                       model.FunctionSDF.u_id == u_id)
                               .all())

        if not query_sdf:
            # create new record
            new_fnsdf = model.FunctionSDF(fn_id=fn_id,
                                          df_id=df_id,
                                          u_id=u_id,)
            db_session.add(new_fnsdf)
            db_session.commit()

        return {'fn_id': fn_id, 'df_id': df_id}

    def op_delete_functionSDF(self, ctx, fn_id, df_id=None):
        """
        Remove the Function to the usage list for Device Feature or Network Application.

        This will remove the specified setting which store in the FunctionSDF,
        and specified the login user.
        This API NOT support remove the function to the usage list for general.

        :param fn_id: <Function.fn_id>
        :param df_id: <DeviceFeature.df_id>, optional
                      if given, remove the function to the function list
                      by given Device Feature,
                      else, remove the function to the join function list
        :type fn_id: int
        :type df_id: int

        :return:
            {
                'df_id': '<DeviceFeature.df_id>',
                'fn_id': '<Function.fn_id>'
            }
        """
        u_id = ctx.u_id
        db_session = ctx.db_session

        # TODO: this check should only check for login user
        # check in used
        # DF_Parameter, check feature default function.
        dfp_count, = (db_session.query(func.count(model.DF_Parameter.fn_id))
                                .select_from(model.DF_Parameter)
                                .join(model.DM_DF,
                                      model.DM_DF.mf_id == model.DF_Parameter.mf_id)
                                .filter(model.DF_Parameter.fn_id == fn_id,
                                        or_(model.DM_DF.df_id == df_id,
                                            model.DF_Parameter.df_id == df_id))
                                .first())
        # DF_Module, check exist join link used.
        dfm_count, = (db_session.query(func.count(model.DF_Module.fn_id))
                                .select_from(model.DF_Module)
                                .join(model.DFObject)
                                .filter(model.DF_Module.fn_id == fn_id,
                                        model.DFObject.df_id == df_id)
                                .first())
        # MultipleJoin_Module, check multiple join function used.
        mjm_count, = (db_session.query(func.count(model.MultipleJoin_Module.fn_id))
                                .select_from(model.MultipleJoin_Module)
                                .join(model.DFObject)
                                .filter(model.MultipleJoin_Module.fn_id == fn_id,
                                        model.DFObject.df_id == df_id)
                                .first())

        if dfp_count or dfm_count or mjm_count:
            raise CCMError('This function is used, can not delete.')

        # move out function (delete FunctionSDF)
        (db_session
            .query(model.FunctionSDF)
            .filter(model.FunctionSDF.df_id == df_id,
                    model.FunctionSDF.fn_id == fn_id,
                    model.FunctionSDF.u_id == u_id)
            .delete())
        db_session.commit()

        return {'fn_id': fn_id, 'df_id': df_id}
