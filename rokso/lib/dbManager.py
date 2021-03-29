import psycopg2
from psycopg2 import Error
from .connectionManager import ConnectionManager
from time import time

default_version_table_name = "rokso_db_version"

class DBManager:
    def __init__(self, config):
        self.revision_table = config.get("version_table_name", default_version_table_name)
        self.default_schema = config.get('dbschema', 'public')
        self.config = {k: config[k] for k in ('host', 'database', 'user', 'password', 'port')}
        self.connection = ConnectionManager(self.config).get_connection()

    def execute_query(self, sql):
        try:
            cursor = self.connection.cursor()
            print("\nExecuting>> ", sql )
            tic = time()
            cursor.execute(sql)
            self.connection.commit()
            toc = time()
            print("query completed successfully..")
            print(">> Time taken: {} secs ".format(round(toc - tic, 4)) )

        except Error as e:
            print("There was an error executing sql:: " + sql, "\n ❌", e)
            raise e


    def select_query(self, sql):
        try:
            cursor = self.connection.cursor()
            print("\nExecuting>> ", sql )
            tic = time()
            cursor.execute(sql)
            toc = time()
            print(">> Time taken: {}secs ".format(round(toc - tic, 4)) )
            # print("cursor desc::", cursor.description)
            # print("cursor list::", self.extract_column_names(cursor))
            return self.extract_column_names(cursor), cursor.fetchall()

        except Error as e:
            print("There was an error executing sql:: " + sql, "\n ❌", e)


    def extract_column_names(self, cursor):
        return [col.name for col in cursor.description]


    def create_version_table(self):
        """ Creates database version table in the given database """

        sql = """
            CREATE TABLE IF NOT EXISTS {} (
                id serial PRIMARY KEY,
                filename text NOT NULL,
                version varchar(100) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                scheduledAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                executedAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT filename_UNQ UNIQUE (filename)
            );
        """
        self.execute_query(sql.format(self.get_table_name_with_schema()))


    def get_database_state(self):
        return self.select_query("SELECT * FROM {}".format(self.get_table_name_with_schema()))


    def apply_migration(self, sql, filename, version ):

        try:
            self.execute_query(sql)
            self.insert_new_migration(filename, version, 'complete')
        except Error as e:
            self.insert_new_migration(filename, version, 'error')
            raise e


    def insert_new_migration(self, filename, version, status='pending' ):
        sql = """
                INSERT INTO {}
                (filename, version, status, scheduledAt, executedAt)
                VALUES('{}', '{}', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (filename) DO UPDATE SET status = '{}', version = '{}', executedAt=CURRENT_TIMESTAMP;
            """
        self.execute_query(sql.format(self.get_table_name_with_schema(), filename, version, status, status, version))


    def rollback_migration(self, sql, id):
        try:
            self.execute_query(sql)
            self.remove_migration(id)
        except Error as e:
            raise e


    def remove_migration(self, id):
        sql = "DELETE FROM {} WHERE id = {} ;"
        return self.execute_query(sql.format(self.get_table_name_with_schema(), id))


    def get_latest_db_revision(self):
        """ returns last successful revision od migration. """
        sql = "SELECT * from {} ORDER BY id DESC LIMIT 1;"
        return self.select_query(sql.format(self.get_table_name_with_schema()))


    def get_migrations_at_revision(self, version):
        sql = """ SELECT * FROM {} WHERE version = '{}' ORDER  BY id desc"""
        return self.select_query(sql.format(self.get_table_name_with_schema(), version))


    def get_migrations_more_than_revision(self, version):
        sql = """ SELECT * FROM {} WHERE scheduledAt > (SELECT scheduledAt FROM {} WHERE version = '{}' ORDER  BY id desc LIMIT 1) ORDER BY id DESC; """
        return self.select_query(sql.format(self.get_table_name_with_schema(),self.get_table_name_with_schema(), version))


    def get_table_name_with_schema(self):
        return f"{self.default_schema}.{self.revision_table}"
