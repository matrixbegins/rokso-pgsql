import psycopg2
from psycopg2 import Error


class ConnectionManager:
    def __init__(self, config):
        try:
            self.connection = psycopg2.connect(**config)
            # Create a cursor to perform database operations
            cursor = self.connection.cursor()
            # Print PostgreSQL details
            print("PostgreSQL server information")
            print(self.connection.get_dsn_parameters(), "\n")
            # Executing a SQL query
            cursor.execute("SELECT version();")
            # Fetch result
            record = cursor.fetchone()
            print("You are connected to - ", record[0], "\n")

        except Error as e:
            print("Error while connecting to PgSQL Database \n", e)
            raise e


    def get_connection(self):
        return self.connection

    def close_connection(self):
        if (self.connection):
            self.connection.close()
