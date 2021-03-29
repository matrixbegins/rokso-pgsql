import json, sys, os
import importlib
import importlib.util
from datetime import datetime

migration_file_template = """apply_sql = \"""
%s
\"""

rollback_sql = "%s"

migrations = {
    "apply": apply_sql,
    "rollback": rollback_sql
}
"""

db_object_type_directory = {
    "enums":            "100.database_types",
    "database_types":   "100.database_types",
    "tables":           "200.tables",
    "views":            "300.views",
    "mat_views":        "400.mat_views",
    "functions":        "500.functions"
}

empty_migration_template = migration_file_template % ('WRITE your DDL/DML query here', 'WRITE your ROLLBACK query here.')


class MigrationManager:
    def __init__(self, path):
        self.migration_path = path
        sys.path.append(self.migration_path)
        pass


    def module_from_file(self, module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


    def import_migration_files(self):
        for main_dir, subdirs, files in os.walk(self.migration_path):
            print('\n\nprocessing directory: ', main_dir)
            print('subdirectory: ', subdirs)
            if "__pycache__" in main_dir:
                continue
            for f in files:
                print("processing file:: ", f)
                modulename = f.strip('.py')
                module = self.module_from_file(os.path.basename(main_dir) + '_' + modulename , main_dir + os.path.sep + f)

                print(module.migrations)


    def import_single_migration(self, file_name:str):
        """ Imports your migration python file as module for processing.
            The file_name path must be in tableName/fileName.py format
        """
        full_path = self.migration_path + os.path.sep + os.path.sep + file_name
        if os.path.exists(full_path):
            modulename = file_name.strip('.py')
            module = self.module_from_file( modulename.replace(os.path.sep, '_') , full_path)
            # print(module.migrations)
            return module.migrations
        else:
            raise Exception("✅ {} does not exists.\n Please make sure the name of the migration file is correct and it must be in <tableName>/<fileName>.py format."
                    .format(self.migration_path + os.path.sep + os.path.sep + file_name))


    def create_migration_file(self, table_name: str, file_name: str, db_object_type: str, dbschema: str):
        new_file_name = self.get_new_file_name(file_name)
        self.create_dir_write_file(table_name, new_file_name, empty_migration_template, db_object_type, dbschema)

        print("[*] migration file {} has been generated".format(new_file_name) )


    def create_dir_write_file(self, object_name: str, file_name: str, content: str, db_object_type: str, dbschema: str):
        dir_path = self.migration_path + os.path.sep + dbschema + os.path.sep \
            + db_object_type_directory.get(db_object_type) + os.path.sep + object_name

        print("migration filepath::", dir_path)
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            raise e

        mg_file = open(dir_path + os.path.sep + file_name, "w+")
        mg_file.write(content)
        mg_file.close()


    def get_new_file_name(self, file_name: str) -> str:
        now = datetime.now()
        time_part = now.strftime("%Y_%m_%d__%H_%M_%S")
        name_temp = "{}_{}.py"
        return name_temp.format(time_part, file_name)


    def get_all_migration_files(self) -> list:
        list1 = []
        for main_dir, subdirs, files in os.walk(self.migration_path):
            # print('\n\nprocessing directory: ', main_dir)
            if "__pycache__" in main_dir:
                continue
            for f in files:
                list1.append(main_dir + os.path.sep + f)

        return list1


    def create_migration_file_with_sql(self, dbschema:str, object_type: str, object_name:str, create_sql:str, drop_sql: str ) -> str:
        file_name = self.get_new_file_name('create_{}_{}'.format(object_type, object_name) )

        content = migration_file_template % (create_sql, drop_sql)

        self.create_dir_write_file(object_name, file_name, content, object_type, dbschema)

        print("file {}{}{} has been created.".format(object_name, os.path.sep, file_name))
        return dbschema + os.path.sep + db_object_type_directory.get(object_type) \
            + os.path.sep + object_name + os.path.sep + file_name


    def get_pending_migrations(self, db_results):
        """
            Accepts a resultset of migration table to compare with all migration files on file system and resultset.
            @TODO:: ensure order of execution of SQLs in accordance with var: db_object_type_directory
        """
        processed_files = []
        for file in db_results:
            if file[3] == "complete":
                processed_files.append(file[1])

        #print(processed_files)
        all_files = self.get_all_migration_files()
        base_path_removed = [f.replace(self.migration_path + os.path.sep, '') for f in all_files]

        return sorted(list(set(base_path_removed) - set(processed_files)) )

