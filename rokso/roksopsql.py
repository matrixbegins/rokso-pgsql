import click, sys, os, pathlib

try:
    from .lib import agent
except ImportError:
    from lib import agent


@click.group()
def cli():
    pass

@click.command('init', short_help='🚀 init your migration project. configures db connection parameters')
@click.option('--projectpath', prompt='Enter path to setup project',
    required=True, envvar='PG_MIG_DB_PROJECT_PATH', help="The path where the project will be setup. rokso can create this directory if not exists.")
@click.option('--dbhost', prompt='Enter database hostname ',
    required=True, envvar='PG_MIG_DB_HOST',
    help="Database host where rokso will connect to.")
@click.option('--dbport', prompt='Enter database port', default=5432,
    envvar='PG_MIG_DB_PORT_NUMBER', help="Port Number of database.")
@click.option('--dbname', prompt='Enter database name ',
    required=True, envvar='PG_MIG_DB_NAME',
    help="Database name where rokso will apply migrations.")
@click.option('--dbusername', prompt='Enter database username ',
    required=True, envvar='PG_MIG_DB_USER', help="Database username for connecting database.")
@click.option('--dbpassword', prompt='Enter database password',
    hide_input=True, envvar='PG_MIG_DB_PASSWORD',
    help="Database password for connecting database.")
@click.option('--dbschema', prompt='Enter a schema name', default="public",
    envvar='PG_MIG_DB_SCHEMA_NAME', help="Default Schema name for the given database.")
def init(dbhost, dbname, dbusername, dbpassword, projectpath, dbschema, dbport):
    """This commands configures basic environment variables that are needed to cary out database migrations.
    Make sure the given user has ALTER, ALTER ROUTINE, CREATE, CREATE ROUTINE, DELETE, DROP, EXECUTE,
    INDEX, INSERT, SELECT, SHOW DATABASES, UPDATE privileges.
    """
    agent.init_setup(dbhost, dbname, dbusername, dbpassword, projectpath, dbschema, dbport)


@click.command('status', short_help='✅ checks the current state of database and pending migrations')
def status():
    """ checks the current state of database and pending migrations. It's good to run this before running migrate command. """
    # click.echo('checking database status' + __file__)
    agent.db_status()


@click.command('remap', short_help='🔄 Reverse engineer your DB migrations from existing database.')
def remap():
    """ Reverse engineer your DB migrations from existing database.
     Make sure init command is complete and you have a valid config file and migrations directory setup. """
    click.echo('Starting remapping of existing database for versioning')
    agent.reverse_engineer_db()


@click.command('create', short_help='➕ create a database migration.')
@click.option('--dbschema', required=True, prompt='Enter the schema name', default="public",
            help="Schema name where this database object will reside.")
@click.option('--objecttype', prompt='Do you want to create a \n[T]able\n[V]iew\n[M]aterialized View\n[F]unctions\n[D]atabase Type:',
    default="T", help="The type of database object for which the migration will be created.",
    type=click.Choice(['T', 'V', 'M', 'F', 'D'], case_sensitive=False ) )
@click.option('--tablename', required=True, prompt='Enter table/procedure/function name that you want to create this migration for',
            help="The table/procedure/function name for which you want to create the migration.")
@click.option('--filename', required=True, prompt='Enter a file name for this migration',
            help="Name of the migration file.")
def create(tablename, filename, objecttype, dbschema):
    """ Creates a migration template file for specified table/database object name. """
    click.echo('creating a migration ...........')
    agent.create_db_migration(tablename, filename, objecttype, dbschema)


@click.command('migrate', short_help='⤴️  Apply all outstanding migrations to database.')
@click.option('--migration', help="Specific migration that needs to be carried out.\nThis option must be of format <tableName>/<fileName> and your file must be under the same path inside migration directory")
def migrate(migration):
    """ Apply all outstanding migrations to database.
    By specifing --migration option you can apply just one single migration. """
    # click.echo('Applying following migrations to database....' + migration)
    agent.apply_migration(migration)


@click.command('rollback', short_help='⤵️  Rollback last applied migration')
@click.option('--version',
                help="Rollbacks database state to specified version.\nThese version numbers can be obtained either from database or by running `rokso status`")
def rollback(version):
    """ Rollback last applied out migration
        By specifing --version option you can rollback to a previous DB state. """
    agent.rollback_db_migration(version)

@click.command('last-success', short_help='⤵️  last successful migration version number')

def last_success():
    agent.last_success()

cli.add_command(init)
cli.add_command(status)
cli.add_command(remap)
cli.add_command(create)
cli.add_command(migrate)
cli.add_command(rollback)
cli.add_command(last_success)


def main():
    return cli()


if __name__ == '__main__':
    main()
