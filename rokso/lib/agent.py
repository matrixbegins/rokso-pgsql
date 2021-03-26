import sys, click, json, os, uuid
from tabulate import tabulate

from .configManager import ConfigManager
from .dbManager import DBManager
from .migrationManager import MigrationManager
from .remapHelper import find_schemas_to_migrate, remap_schema


json_dict = {}
initial_dirs = ["migration"]


allowed_db_object_types = {
    "t":        "tables",
    "tables":   "tables",
    "table":    "tables",

    "v":    "views",
    "view": "views",
    "views": "views",

    "m":    "mat_views",

    "f":            "functions",
    "function":     "functions",
    "functions":    "functions",

    "d":         "database_types",
    "type":     "database_types",

}


def custom_exit(CODE, message="", ex=""):

    click.secho("\n❌ Oooo... snap     \_(-_-)_/  \n" , fg='red' )
    if ex!="":
        print(ex)
    if message!="":
        print( message, "\n")

    exit(CODE)


def get_cwd():
    print("working directory:: ", os.getcwd())
    return os.getcwd()


def init_setup(dbhost:str, dbname:str, dbusername:str, dbpassword:str, projectpath:str, dbschema:str, dbport:str):
    """
        This function will check/create the config.json in project root.
        then it'll check/create the revision table in database
    """
    cwd = get_cwd()
    json_dict = { "host": dbhost, "database": dbname, "user": dbusername, "password": dbpassword, "dbschema": dbschema, "port": dbport }

    try:
        CMobj = ConfigManager()
        CMobj.init(json_dict, projectpath)
    except FileExistsError as e:
        custom_exit(0, "", e)
    except Exception as e:
        custom_exit(1, "Unable to initialize rokso.", e)

    config = CMobj.get_config(cwd)

    db = DBManager(config.get("database"))
    db.create_version_table()


def db_status():
    """
    Checks all the migrations processed so far from database
    then checks all pending migrations.
    """
    cwd = get_cwd()
    try:
        db = DBManager(ConfigManager().get_config(cwd).get("database"))
        cols , data = db.get_database_state()
    except FileNotFoundError as ex:
        custom_exit(1, "It seems the project setup is not complete.\nPlease run `rokso init` first.", ex)

    # get all successful migrations
    completed_migs = list(filter(lambda el: el[3] == "complete", data))

    # get any previous failed migrations
    failed_migs = list(filter(lambda el: el[3] == "error", data))

    click.secho("Last few successful migrations: ", fg='yellow')
    print(tabulate(completed_migs[-10:], headers=cols))

    if len(failed_migs) > 0:
        click.secho("\n[❗] However we have detected few failed migrations in the past. \n Please fix them first.\n", fg='yellow')
        print(tabulate(failed_migs, headers=cols))
        custom_exit(0)

    mg = MigrationManager(cwd + os.path.sep + 'migration')
    pending_migrations = mg.get_pending_migrations(data)

    if len(pending_migrations) > 0:
        toshow = []
        for pending in pending_migrations:
            toshow.append((pending, 'NA', 'pending'))

        click.secho("\nPending migrations for application: ", fg='yellow')
        print(tabulate(toshow, headers=('filename', 'version', 'status')))
        print("\n")
    else:
        print("\nNo new migration to process.\n")


def create_db_migration(tablename: str, filename: str, db_object_type: str, dbschema: str):
    mg = MigrationManager(get_cwd() + os.path.sep + 'migration')
    db_object_type = allowed_db_object_types.get(db_object_type.lower(), "tables")
    mg.create_migration_file(tablename, filename, db_object_type, dbschema)


def apply_migration(migration_file_name):
    """
        Checks if any previous migration is in
        @TODO:: check lockings for ALTER statements
    """
    version_no = str(uuid.uuid4())[:8]
    cwd = get_cwd()
    try:
        db = DBManager(ConfigManager().get_config(cwd).get("database"))
        col, data = db.get_database_state()
    except FileNotFoundError as ex:
        custom_exit(1, "It seems the project setup is not complete.\nPlease run `rokso init` first.", ex)

    # get any previous failed migrations
    failed_migs = list(filter(lambda el: el[3] == "error", data))

    failed_files = [f[1] for f in failed_migs]

    mg = MigrationManager(cwd + os.path.sep + 'migration')
    if migration_file_name:
        # if migration file is not in among the previously failed migrations then do not proceed.
        if len(failed_migs) > 0 and migration_file_name != failed_files[0]:
            click.secho("""\n[❗] We have detected some failed migrations which still need to be fixed.
The given migration file name is not same or belongs to the list of below failed migration.
Please fix below files and follow the following order to apply migration. """, fg='yellow')
            print(tabulate(failed_migs, headers=col))
            custom_exit(1)

        # process single migration
        sql = mg.import_single_migration(migration_file_name)

        try:
            print("🌀Applying migration file: ", migration_file_name)
            db.apply_migration(sql.get('apply'), migration_file_name, version_no)
            click.secho("✅ Your database is at revision# {}".format(version_no), fg='green' )
            print("\n")
        except Exception as ex:
            print("Exception in applying migration", ex)


    else:
        # checking for failed migration. If present then attempt to migrate them first and do not proceed with new migrations.
        if len(failed_migs) > 0:
            click.secho("""\n[❗] We have detected some failed migrations. Attempting to run following first.\n Once these are successful run `rokso migrate` again to apply new migrations.""", fg='yellow')
            print(tabulate(failed_migs, headers=col))
            pending_migrations = failed_files
        else:
            pending_migrations = mg.get_pending_migrations(data)

        if len(pending_migrations) > 0:
            for p_mig in pending_migrations:

                sql = mg.import_single_migration(p_mig)
                try:
                    print("🌀Applying migration file: ", p_mig)
                    db.apply_migration(sql.get('apply'), p_mig, version_no)
                except Exception as ex:
                    print("✅ Your database is at revision# {}".format(version_no) )
                    custom_exit(1, "Your migration '{}' has failed. Please fix it and retry.".format(p_mig), ex)

            click.secho("✅ Your database is at revision# {} \n".format(version_no), fg='green' )

        else:
            print("Nothing to migrate ....\n")


def rollback_db_migration(version):
    # check the revision number in database if nothing is found then report error
    # get all the files for the given revision number and all new revision after that.
    # render details on screen about all the eligible files for rollback
    # on confirmation process rollback one by one.
    cwd = get_cwd()
    try:
        db = DBManager(ConfigManager().get_config(cwd).get("database"))
        mg = MigrationManager(cwd + os.path.sep + 'migration')
    except FileNotFoundError as ex:
        custom_exit(1, "It seems the project setup is not complete.\nPlease run `rokso init` first.", ex)

    if version:
        cols, result = db.get_migrations_more_than_revision(version)
    else:
        cols, result = db.get_latest_db_revision()
        # getting all the files on the latest revision number
        cols, result = db.get_migrations_at_revision(result[0][2] )

    if len(result) < 1:
        custom_exit(1, "No Files to rollback. Probably {} is the latest version.".format(version))

    print("Following files will be rolledback: ")
    print(tabulate(result, headers=cols))
    confirm = input("\nPlease confirm to proceed(y/yes):")
    if confirm.lower() in ['y', 'yes']:
        try:
            for roll in result:
                sql = mg.import_single_migration(roll[1])
                print("\n🔄 Rolling back file:: ", roll[1])
                db.rollback_migration(sql.get('rollback'), roll[0])
        except Exception as ex:
            custom_exit(1, "An error occurred while performing rollback.", ex)

        print("✅ Rollback complete.\n")

    else:
        print("No operation performed.\n")


def reverse_engineer_db():
    """
        1. finds all the tables in database
        2. extract the table definition for each table from DB
        3. create the migration files under "migrations" dir located in project root.
        4. make an entry in version table for that migration
        5. @TODO:: get an optional argument of list of table for which the data should also be dumped.
    """
    cwd = get_cwd()

    try:
        db = DBManager(ConfigManager().get_config(cwd).get("database"))
        _, data = db.get_database_state()
    except FileNotFoundError as ex:
        custom_exit(1, "It seems the project setup is not complete.\nPlease run `rokso init` first.", ex)

    if len(data) > 0:
        custom_exit(1, "It seems you already have some rokso migrations in your database. Reverse engineering is possible just after the project setup.")
    else:
        print("Starting reverse engineering")
        version_no = str(uuid.uuid4())[:8]
        click.get_current_context().params["db_version"] = version_no
        # Find all schemas in the given database that may need migration.

        schemas = find_schemas_to_migrate(db)
        # print("schema names:: ", schemas)

        if len(schemas) > 0:
            for schema in schemas:
                remap_schema(db, schema)

            click.secho("✅ Reverse engineering of database complete.", bold=True, fg='green')
            click.secho("your database is at revision# {}\n".format(version_no), bold=True, blink=True)
        else:
            print("\nNo Schema found or selected to reverse engineer")
            return


def last_success():

    db = DBManager(ConfigManager().get_config(get_cwd()).get("database"))
    try:
        cols , data = db.get_latest_db_revision()
        if len(data) > 0:
            click.secho('Last successful version: ' + data[0][2], fg='green', bold=True)

        else:
            click.secho("No last revision detected", fg='yellow')
            exit(0)
    except Exception as e:
        #print(e.__class__.__name__)
        if int(str(e).split('(')[0]) == 1146:
            custom_exit(0, "Table does not exist, kindly initate rokso", e)
        else:
            custom_exit(1, "something went wrong", e)

