from alembic import op
import sqlalchemy as sa

import six
import uuid


def sqlite_alter_columns(table_name, column_defs):
    """
    ref: https://programtalk.com/vs2/python/9674/gertty/gertty/dbsupport.py/

    Implement alter columns for SQLite.

    The ALTER COLUMN command isn't supported by SQLite specification.
    Instead of calling ALTER COLUMN it uses the following workaround:

    * create temp table '{table_name}_{rand_uuid}', with some column
      defs replaced;
    * copy all data to the temp table;
    * drop old table;
    * rename temp table to the old table name.
    """
    connection = op.get_bind()
    meta = sa.MetaData(bind=connection)
    meta.reflect()

    changed_columns = {}
    indexes = []
    for col in column_defs:
        # If we are to have an index on the column, don't create it
        # immediately, instead, add it to a list of indexes to create
        # after the table rename.
        if col.index:
            indexes.append(('ix_%s_%s' % (table_name, col.name),
                            table_name,
                            [col.name],
                            col.unique))
            col.unique = False
            col.index = False
        changed_columns[col.name] = col

    # construct lists of all columns and their names
    old_columns = []
    new_columns = []
    column_names = []
    for column in meta.tables[table_name].columns:
        column_names.append(column.name)
        old_columns.append(column)
        if column.name in changed_columns.keys():
            new_columns.append(changed_columns[column.name])
        else:
            col_copy = column.copy()
            new_columns.append(col_copy)

    for key in meta.tables[table_name].foreign_keys:
        constraint = key.constraint
        con_copy = constraint.copy()
        new_columns.append(con_copy)

    for index in meta.tables[table_name].indexes:
        # If this is a single column index for a changed column, don't
        # copy it because we may already be creating a new version of
        # it (or removing it).
        idx_columns = [col.name for col in index.columns]
        if len(idx_columns) == 1 and idx_columns[0] in changed_columns.keys():
            continue
        # Otherwise, recreate the index.
        indexes.append((index.name,
                        table_name,
                        [col.name for col in index.columns],
                        index.unique))

    # create temp table
    tmp_table_name = "%s_%s" % (table_name, six.text_type(uuid.uuid4()))
    op.create_table(tmp_table_name, *new_columns)
    meta.reflect()

    try:
        # copy data from the old table to the temp one
        sql_select = sa.sql.select(old_columns)
        connection.execute(sa.sql.insert(meta.tables[tmp_table_name])
                           .from_select(column_names, sql_select))
    except Exception:
        op.drop_table(tmp_table_name)
        raise

    # drop the old table and rename temp table to the old table name
    op.drop_table(table_name)
    op.rename_table(tmp_table_name, table_name)

    # (re-)create indexes
    for index in indexes:
        op.create_index(op.f(index[0]), index[1], index[2], unique=index[3])
