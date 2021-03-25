import sys, click, os, time
from .configManager import ConfigManager
from .dbManager import DBManager
from .migrationManager import MigrationManager
from .remappingSqls import find_objects_sql, get_ddl_sqls, drop_object_sqls
from tabulate import tabulate

db_object_master = ['tables', 'views', 'mat_views', 'database_types', 'enums', 'functions']
GEN_TBL_DDL_FUNC_NAME = 'generate_table_ddl'


def find_schemas_to_migrate(db: DBManager):
    headers, data = db.select_query(find_objects_sql.get("schema"))
    click.secho("I found {} schemas in the database... ".format(len(data)), fg='yellow')
    print(tabulate(data, headers=headers))

    db_schemas = [sch[0] for sch in data ]

    while True:
        choices = input_schema_names().lower()
        if choices == 'all' or choices == 'a' :
            return db_schemas

        choices = [ ch.strip() for ch in choices.split(",") ]

        if set(choices).issubset(db_schemas):
            return choices
        else:
            click.secho("ERROR!!: Invalid schema list applied.", fg='red')


def input_schema_names():
    print("--------------------------")
    return input("\nEnter a comma seperated list of schemas that you want to reverse engineer.\nFor all schemas enter(a/all): ")


def remap_schema(db: DBManager, schema: str):
    # find all tables in a schema
    # find all Views/mat views in the given schema
    # find all functions in the given schema
    # find all custom data types in the given schema
    # print a report and begin migration

    click.secho("\nBegining reverse engineering of schema: " + schema + '.......', fg='yellow')
    click.secho("Finding database objects of schema: " + schema + '.......', fg='yellow')

    db_objects_collection = {}
    length_collection = []

    for obj in db_object_master:
        result = find_db_object(db, schema, obj)
        db_objects_collection[obj] = result
        length_collection.append((obj, len(result)))

    click.secho("\nBelow is the summary of all database objects that will be remaped for schema: " + schema, fg='yellow')
    print(tabulate(length_collection, headers=('database_object_type', 'count')))
    print("\n")

    generate_migration_files(db, schema, db_objects_collection)


def find_db_object(db: DBManager, schema: str, db_object_type: str):
    click.secho("\nFinding all {}s in schema: {} .......".format(db_object_type, schema), fg='yellow' )
    _, data = db.select_query(find_objects_sql.get(db_object_type).format(schema) )
    click.secho('Finding {}s completed.'.format(db_object_type), fg='green')
    return data


def generate_migration_files(db: DBManager, schema: str, db_object_collection: dict):

    generate_migration_files_for_enums(db, schema, db_object_collection.get("enums"))

    generate_migration_files_for_types(db, schema, db_object_collection.get("database_types"))

    generate_migration_files_for_tables(db, schema, db_object_collection.get("tables"))

    generate_migration_files_for_views(db, schema, db_object_collection.get("views"))

    generate_migration_files_for_mat_views(db, schema, db_object_collection.get("mat_views"))

    generate_migration_files_for_functions(db, schema, db_object_collection.get("functions"))


def generate_migration_files_for_tables(db: DBManager, schema: str, table_list: list):
    # first create the stored proc which can generate DDL for tables.

    # then loop through table_list and get DDL of table.
    # then get all indexes of the given table. Remove all UNIQUE INDEXES from the SQL

    # combine CREATE TABLE DDL and CREATE INDEX DDL in one string.

    # create migration file for the given table

    # once migration file for all tables are generated then DROP the Stored function that generates table DDL.
    click.secho("\nGenerating migration files for tables ", fg='yellow')

    if len(table_list) < 1:
        click.secho("--- No tables found. Skipping table DDL generation.", fg='yellow')
        return

    print("\nCreating DDL generator......")
    sql = get_ddl_sqls.get('create_table_ddl_generator').format(schema)
    db.execute_query(sql)
    click.secho("\nDDL generator created.", fg='green')

    create_table_sql = get_ddl_sqls.get('get_table_ddl')
    create_index_sql = get_ddl_sqls.get('index_of_table')
    table_list.sort()

    for table_name in table_list:
        table_name = table_name[0]

        # exclude rokso version table while generating migration
        if table_name == db.revision_table:
            continue
        click.secho("\nGenerating DDL for table: {}.{}".format(schema, table_name), fg='yellow')
        # time.sleep(0.1)
        # get CREATE TABLE statement
        _, table_ddl = db.select_query(create_table_sql.format(schema,schema, table_name))
        table_ddl = table_ddl.pop()
        to_file_sql = table_ddl[0] + "\n\n "

        # get CREATE INDEX statements
        _, idx_ddl = db.select_query(create_index_sql.format(schema, table_name))

        for ddl in idx_ddl:
            ddl = ddl[0]
            # primary key and unique index are already part of CREATE TABLE statements so simply skip them.
            if 'CREATE UNIQUE INDEX' in ddl:
                continue
            else:
                to_file_sql += ddl + "; \n"

        # print('generated SQL for table: ', table_name)
        # print(to_file_sql)

        # now create migration file onto filesystem with generated SQL
        save_migration_file_with_db_entry(db, schema, 'tables', table_name, to_file_sql)


    print("\nRemoving DDL generator......")
    sql = get_ddl_sqls.get('drop_table_ddl_generator').format(schema)
    db.execute_query(sql)
    click.secho("\nDDL generator removed.", fg='green')
    click.secho("\nRemapping of tables complete", fg='green', bold=True)



def generate_migration_files_for_enums(db: DBManager, schema: str, enum_list: list):
    click.secho("\nGenerating migration files for ENUMS ", fg='yellow')
    if len(enum_list) < 1:
        click.secho("  --- No ENUMS found. Skipping ENUM DDL generation.", fg='yellow')
        return

    for en in enum_list:
        create_enum_ddl = en[3]
        enum_name = en[1]
        # print(enum_name, ' : ', create_enum_ddl)
        # generate migration file on filesystem.
        save_migration_file_with_db_entry(db, schema, 'enums', enum_name, create_enum_ddl)

    click.secho("\nRemapping of ENUMS complete", fg='green', bold=True)


def generate_migration_files_for_types(db: DBManager, schema: str, type_list: list):
    click.secho("\nGenerating migration files for Composite data types. ", fg='yellow')
    if len(type_list) < 1:
        click.secho("  --- No Composite data types found. Skipping Composite data types DDL generation.", fg='yellow')
        return

    for comp_type in type_list:
        type_name = comp_type[1]    # we are having a side effect of having schema name appended to the type_name and DDL let's remove that.
        type_name = type_name.replace('{}.'.format(schema), '')
        type_ddl = comp_type[2]
        type_ddl = type_ddl.replace('CREATE TYPE {}.{}.'.format(schema, schema), 'CREATE TYPE {}.'.format(schema) )
        # print("DDL of ", type_name, " : ", type_ddl)

        # generate migration file on filesystem.
        save_migration_file_with_db_entry(db, schema, 'database_types', type_name, type_ddl)

    click.secho("\nRemapping of Composite data types complete", fg='green', bold=True)


def generate_migration_files_for_views(db: DBManager, schema: str, view_list: list):
    click.secho("\nGenerating migration files for Views. ", fg='yellow')
    if len(view_list) < 1:
        click.secho("  --- No Views found. Skipping Views DDL generation.", fg='yellow')
        return

    for vw in view_list:
        view_ddl = vw[1]
        view_name = vw[0]
        # print(view_name, ' : ', view_ddl)

        # generate migration file on filesystem.
        save_migration_file_with_db_entry(db, schema, 'views', view_name, view_ddl)

    click.secho("\nRemapping of VIEWS complete", fg='green', bold=True)


def generate_migration_files_for_mat_views(db: DBManager, schema: str, view_list: list):
    click.secho("\nGenerating migration files for MATERIALIZED Views. ", fg='yellow')
    if len(view_list) < 1:
        click.secho("  --- No MATERIALIZED Views found. Skipping MATERIALIZED Views DDL generation.", fg='yellow')
        return

    for vw in view_list:
        view_ddl = vw[1]
        view_name = vw[0]
        # print(view_name, ' : ', view_ddl)

        # generate migration file on filesystem.
        save_migration_file_with_db_entry(db, schema, 'mat_views', view_name, view_ddl)

    click.secho("\nRemapping of MATERIALIZED VIEWS complete", fg='green', bold=True)


def generate_migration_files_for_functions(db: DBManager, schema: str, function_list: list):
    click.secho("\nGenerating migration files for stored functions. ", fg='yellow')
    if len(function_list) < 1:
        click.secho("  --- No stored functions found. Skipping stored functions DDL generation.", fg='yellow')
        return

    for func in function_list:
        if func[0] == GEN_TBL_DDL_FUNC_NAME:
            continue
        func_ddl = func[1]
        func_name = func[0]

        # generate migration file on filesystem.
        save_migration_file_with_db_entry(db, schema, 'functions', func_name, func_ddl)

    click.secho("\nRemapping of FUNCTIONS complete", fg='green', bold=True)


def save_migration_file_with_db_entry(db: DBManager, schema: str, object_type: str, object_name: str, ddl: str):
    mg = MigrationManager(os.getcwd() + os.path.sep + 'migration')

    drop_sql = drop_object_sqls.get(object_type).format(schema, object_name)

    # save new migration file
    migration_file_name = mg.create_migration_file_with_sql(schema, object_type, object_name, ddl, drop_sql)

    # print('migration_file_name:: ', migration_file_name)

    # now insert into the migration_version table
    version_no = click.get_current_context().params["db_version"]
    # print('checking context:: ', version_no)
    db.insert_new_migration(migration_file_name, version_no, "complete" )
