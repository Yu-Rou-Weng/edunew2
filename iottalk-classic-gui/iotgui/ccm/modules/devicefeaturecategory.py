"""
DeviceFeatureCategory Module.

contains:

    op_create_device_feature_category
    op_get_device_feature_category_list
"""
from iotgui.ccm.modules.interface import Interface
from iotgui.ccm.modules.utils import record_parser
from iotgui.db import model


class DeviceFeatureCategory(Interface):
    """Device Feature Category class."""

    def op_create_device_feature_category(self, ctx, dfc_name):
        """
        Create new Device Feature Category.

        :param dfc_name: <DeviceFeatureCategory.dfc_name>
        :type dfc_name: str

        :return:
            {
                'dfc_name': <DeviceFeatureCategory.dfc_name>
            }
        """
        db_session = ctx.db_session
        dfc_record = (db_session.query(model.DeviceFeatureCategory)
                                .filter(model.DeviceFeatureCategory.dfc_name == dfc_name)
                                .first())
        if dfc_record:
            return {'dfc_name': dfc_name}

        new_dfc = model.DeviceFeatureCategory(
            dfc_name=dfc_name,
        )
        db_session.add(new_dfc)
        db_session.commit()

        return {'dfc_name': dfc_name}

    def op_get_device_feature_category_list(self, ctx):
        """
        Get all Device Feature Categories.

        :return: List[<DeviceFeatureCategory>]
        """
        db_session = ctx.db_session
        dfc_records = (db_session.query(model.DeviceFeatureCategory)
                                 .all())

        category_list = []
        for dfc_record in dfc_records:
            category_list.append(record_parser(dfc_record))

        return category_list
