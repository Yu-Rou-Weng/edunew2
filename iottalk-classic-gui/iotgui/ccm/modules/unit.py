"""
Unit Module.

contains:

    op_create_unit
    op_get_unit_list
"""
from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import record_parser
from iotgui.db import model


class Unit(Interface):
    """Device Feature Unit class."""

    def op_create_unit(self, ctx, unit_name):
        """
        Create new Unit.

        :param unit_name: <Unit.unit_name>
        :type unit_name: str

        :return: <Unit>
        """
        db_session = ctx.db_session
        unit_record = (db_session.query(model.Unit)
                                 .filter(model.Unit.unit_name == unit_name)
                                 .first())
        if unit_record:
            return record_parser(unit_record)

        new_unit = model.Unit(unit_name=unit_name)
        db_session.add(new_unit)
        db_session.commit()

        return record_parser(new_unit)

    def op_get_unit_list(self, ctx):
        """
        Get Unit list.

        :return: List[<Unit>]
        """
        db_session = ctx.db_session
        unit_records = (db_session
                        .query(model.Unit)
                        .all())

        unit_list = []
        for unit_record in unit_records:
            unit_list.append(record_parser(unit_record))

        return unit_list
