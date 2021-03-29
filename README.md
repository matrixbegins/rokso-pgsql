# rokso-migrations

A NOT so simple database migrations utility for Postgresql based database migration in python.
Rokso for Postgresql supports multi-schema migrations of a single database.

## Features

* Create your migrations simply with CLI.
* Suitable for large projects because we maintain migration files under a dedicated directory of a database object
* Reverse engineer your migrations from existing database.
* Check database state like `git status`.

## Installation

**This is work in progress and the package is still not properly published.**
```
pip install roksopsql
```
or
```
pip3 install roksopsql
```


## Usage

To see what rokso can do:
```
➜  roksopsql --help
Usage: roksopsql [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  create        ➕ create a database migration.
  init          🚀 init your migration project. configures db connection
                parameters

  last-success  ⤵️  last successful migration version number
  migrate       ⤴️  Apply all outstanding migrations to database.
  remap         🔄 Reverse engineer your DB migrations from existing database.
  rollback      ⤵️  Rollback last applied migration
  status        ✅ checks the current state of database and pending migrations

```

### Setup


#### DB setup
Let's say for a database `tutorial` we have two schemas. `online` and `offline`, offline being primary schema. We'll create one table and one database function in `offline` schema and another table in `online` schema.
```
> psql
postgres=# create database tutorial;
postgres=# \c tutorial
tutorial=# create schema offline;
tutorial=# create schema online;
```

There are many ways to initiate your project.
To start create a directory where you want to create project

```
➜  mkdir tutorial
➜  cd tutorial
➜  tutorial ✗ roksopsql init
Enter path to setup project: .
Enter database hostname : /var/www/projects/python/rokso/tutorial
Enter database port [Default:5432] [5432]:
Enter database name : tutorial
Enter database username : pguser
Enter database password:
Enter a schema name [Default:public] [public]: offline
working directory::  /var/www/projects/python/rokso/tutorial
[*] Checking state of config file in CWD
[*] Config file has been created
[#] Generating required dir(s) if not exist
PostgreSQL server information
{'user': 'pguser', 'dbname': 'tutorial', 'host': 'localhost', 'port': '5432', 'tty': '', 'options': '', 'sslmode': 'prefer', 'sslcompression': '0', 'krbsrvname': 'postgres', 'target_session_attrs': 'any'}

You are connected to -  PostgreSQL 13.2 on x86_64-apple-darwin19.6.0, compiled by Apple clang version 12.0.0 (clang-1200.0.32.29), 64-bit

Executing>>
            CREATE TABLE IF NOT EXISTS offline.rokso_db_version (
                id serial PRIMARY KEY,
                filename text NOT NULL,
                version varchar(100) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                scheduledAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                executedAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT filename_UNQ UNIQUE (filename)
            );

query completed successfully..
>> Time taken: 0.0203 secs
```
The above command does following things:
- Creates a directory `migration` under the project directory. This directory holds the migration sqls for database.
- Creates a file `config.json` which holds the connection string to Database.
- Creates a version control table `rokso_db_version` in the database with given schema.

Check all contents now
```
➜ tutorial ✗ ll
-rw-r--r--  1 user  staff   192B 29 Mar 19:11 config.json
drwxr-xr-x  2 user  staff    64B 29 Mar 19:11 migration

```

Check the table in database

```
psql>\d+ offline.rokso_db_version;
+-------------+--------------+------+-----+-------------------+-------------------+
| Field       | Type         | Null | Key | Default           | Extra             |
+-------------+--------------+------+-----+-------------------+-------------------+
| id          | int          | NO   | PRI | NULL              | auto_increment    |
| filename    | varchar(255) | NO   | UNI | NULL              |                   |
| version     | varchar(100) | NO   |     | NULL              |                   |
| status      | varchar(20)  | NO   |     | pending           |                   |
| scheduledAt | timestamp    | NO   |     | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
| executedAt  | timestamp    | NO   |     | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
+-------------+--------------+------+-----+-------------------+-------------------+

```

Now we are ready for creating our new migrations

### Create migrations
Rokso can generate migrations for your tables, materialized views, views, functions and custom data types. They all are organized under their respective directories.
#### NOTE: For a multi-schema migrations Rokso assumes that database exits with all schemas that you want to manage.
To create a new migration run following command:

```
➜ tutorial git:(master) ✗ roksopsql create
Enter the schema name [public]: offline
Do you want to create a
[T]able
[V]iew
[M]aterialized View
[F]unctions
[D]atabase Type: (T, V, M, F, D) [T]: T
Enter table/procedure/function name that you want to create this migration for.: user_master
Enter a file name for this migration.: create_table_user_master
creating a migration ...........
working directory::  /var/www/projects/python/rokso/tutorial
migration filepath:: /var/www/projects/python/rokso/tutorial/migration/offline/200.tables/user_master
[*] migration file 2021_03_29__19_14_28_create_table_user_master.py has been generated
```
Now you can see a new file under migration directory has been generated:
```
➜  tutorial git:(master) ✗ ll migration
total 0
drwxr-xr-x  3 user  staff    29 Mar 19:14 offline

➜  tutorial git:(master) ✗ ll migration/offline
total 0
drwxr-xr-x  3 user  staff    96B 29 Mar 19:14 200.tables
➜  tutorial git:(master) ✗ ll migration/offline/200.tables
total 0
drwxr-xr-x  3 user  staff    96B 29 Mar 19:14 user_master
➜  tutorial git:(master) ✗ ll migration/offline/200.tables/user_master
total 8
-rw-r--r--  1 user  staff   171B 29 Mar 19:14 2021_03_29__19_14_28_create_table_user_master.py

➜  tutorial git:(master) ✗ cat migration/offline/200.tables/user_master/2021_03_29__19_14_28_create_table_user_master.py
apply_sql = """
WRITE your DDL/DML query here
"""

rollback_sql = "WRITE your ROLLBACK query here."

migrations = {
    "apply": apply_sql,
    "rollback": rollback_sql
}

```

Now you can edit this file and add the DDL/INSERTS/UPDATES in `apply_sql` and its extremely important to write `rollback_sql`. However if you do not want a rollback statement then leave the `rollback_sql` empty and Rokso will not report an error while executing or rolling back migrations.


### Apply/Run migrations
After you have written your DDLs/DMLs in migration files, we are ready to carry out the migration, i.e. make a database change.
Let's create more migrations.
```
# create a migration for a database function.

➜  tutorial git:(master) ✗ roksopsql create
Enter the schema name [public]: offline
Do you want to create a
[T]able
[V]iew
[M]aterialized View
[F]unctions
[D]atabase Type: (T, V, M, F, D) [T]: F
Enter table/procedure/function name that you want to create this migration for.: generate_booking_number
Enter a file name for this migration: create_function_generate_booking_number
creating a migration ...........
working directory::  /var/www/projects/python/rokso/tutorial
migration filepath:: /var/www/projects/python/rokso/tutorial/migration/offline/500.functions/generate_booking_number
[*] migration file 2021_03_29__19_34_09_create_function_generate_booking_number.py has been generated
```
One more migration for another schema `online`

```
➜  tutorial git:(master) ✗ roksopsql create
Enter the schema name [public]: online
Do you want to create a
[T]able
[V]iew
[M]aterialized View
[F]unctions
[D]atabase Type: (T, V, M, F, D) [T]: T
Enter table/procedure/function name that you want to create this migration for: website_user
Enter a file name for this migration.: create_table_website_user
creating a migration ...........
working directory::  /var/www/projects/python/rokso/tutorial
migration filepath:: /var/www/projects/python/rokso/tutorial/migration/online/200.tables/website_user
[*] migration file 2021_03_29__19_37_31_create_table_website_user.py has been generated
```
After the files are generated, write your DDLs/DMLs into those files.

#### Now check database status
Rokso shows you last few successful migrations and also pending migrations if any.
```
➜  tutorial git:(master) ✗ roksopsql status
Executing>>  SELECT * FROM offline.rokso_db_version
>> Time taken: 0.0012secs
Last few successful migrations:
id    filename    version    status    scheduledat    executedat
----  ----------  ---------  --------  -------------  ------------

Pending migrations for application:
filename                                                                                                       version    status
-------------------------------------------------------------------------------------------------------------  ---------  --------
offline/200.tables/user_master/2021_03_29__19_14_28_create_table_user_master.py                                NA         pending
offline/500.functions/generate_booking_number/2021_03_29__19_34_09_create_function_generate_booking_number.py  NA         pending
online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py                               NA         pending

```

In this case we don't have any prior migrations recorded in DB because we started with fresh database.

#### Applying single migration

```
➜  tutorial git:(master) ✗ roksopsql migrate --migration offline/200.tables/user_master/2021_03_29__19_14_28_create_table_user_master.py

Executing>>  SELECT * FROM offline.rokso_db_version
>> Time taken: 0.0017secs
🌀Applying migration file:  offline/200.tables/user_master/2021_03_29__19_14_28_create_table_user_master.py

Executing>>

CREATE TABLE IF NOT EXISTS offline.user_master (
        id serial PRIMARY KEY,
        user_name varchar(255) NOT NULL,
        email varchar(100) NOT NULL,
        user_password VARCHAR(50) NOT NULL,
        createdAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updatedAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT email_UNQ UNIQUE (email)
    );


query completed successfully..
>> Time taken: 0.0321 secs

Executing>>
                INSERT INTO offline.rokso_db_version
                (filename, version, status, scheduledAt, executedAt)
                VALUES('offline/200.tables/user_master/2021_03_29__19_14_28_create_table_user_master.py', 'b23b4a2d', 'complete', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (filename) DO UPDATE SET status = 'complete', version = 'b23b4a2d', executedAt=CURRENT_TIMESTAMP;

query completed successfully..
>> Time taken: 0.0077 secs
✅ Your database is at revision# b23b4a2d

```

Checking status again:
```
➜  tutorial git:(master) ✗ roksopsql status
Executing>>  SELECT * FROM offline.rokso_db_version
>> Time taken: 0.004secs
Last few successful migrations:
  id  filename                                                                         version    status    scheduledat                 executedat
----  -------------------------------------------------------------------------------  ---------  --------  --------------------------  --------------------------
   1  offline/200.tables/user_master/2021_03_29__19_14_28_create_table_user_master.py  b23b4a2d   complete  2021-03-29 20:04:01.691033  2021-03-29 20:04:01.691033

Pending migrations for application:
filename                                                                                                       version    status
-------------------------------------------------------------------------------------------------------------  ---------  --------
offline/500.functions/generate_booking_number/2021_03_29__19_34_09_create_function_generate_booking_number.py  NA         pending
online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py                               NA         pending
```

Now we have prior migration with revision number and rest of the pending migrations.


#### Applying all outstanding migrations

```
➜  tutorial git:(master) ✗ roksopsql migrate

Executing>>  SELECT * FROM offline.rokso_db_version
>> Time taken: 0.0054secs
🌀Applying migration file:  offline/500.functions/generate_booking_number/2021_03_29__19_34_09_create_function_generate_booking_number.py

Executing>>

CREATE OR REPLACE FUNCTION offline.generate_booking_number()
 RETURNS character varying
 LANGUAGE plpgsql
AS $function$
declare
        str_str varchar;
        output_str varchar;
        year_var integer;
        day_var integer;
begin
        SELECT array_to_string(ARRAY(SELECT chr((65 + round(random() * 25)) :: integer) into str_str
                FROM generate_series(1,15)), '');
        select substring(str_str, 2, 4) into str_str;
        SELECT date_part('year', CURRENT_TIMESTAMP) into year_var;
        SELECT 700 + date_part('doy', CURRENT_TIMESTAMP) into day_var;
        select concat(year_var, '-', day_var, '-', str_str) into output_str;
        return output_str;
END;
$function$
;


query completed successfully..
>> Time taken: 0.0823 secs

Executing>>
                INSERT INTO offline.rokso_db_version
                (filename, version, status, scheduledAt, executedAt)
                VALUES('offline/500.functions/generate_booking_number/2021_03_29__19_34_09_create_function_generate_booking_number.py', '22d0747c', 'complete', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (filename) DO UPDATE SET status = 'complete', version = '22d0747c', executedAt=CURRENT_TIMESTAMP;

query completed successfully..
>> Time taken: 0.0023 secs
🌀Applying migration file:  online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py

Executing>>

CREATE TABLE IF NOT EXISTS online.website_user (
        id serial PRIMARY KEY,
        user_name varchar(255) NOT NULL,
        email varchar(100) NOT NULL,
        user_password VARCHAR(50) NOT NULL,
        phone_number varchar(20) NOT NULL,
        img_url varchar(250) NOT NULL,
        createdAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updatedAt timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT email_UNQ UNIQUE (email)
    );


query completed successfully..
>> Time taken: 0.0202 secs

Executing>>
                INSERT INTO offline.rokso_db_version
                (filename, version, status, scheduledAt, executedAt)
                VALUES('online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py', '22d0747c', 'complete', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (filename) DO UPDATE SET status = 'complete', version = '22d0747c', executedAt=CURRENT_TIMESTAMP;

query completed successfully..
>> Time taken: 0.0011 secs
✅ Your database is at revision# 22d0747c

```

Check the status again

```
➜  tutorial git:(master) ✗ roksopsql status
Executing>>  SELECT * FROM offline.rokso_db_version
>> Time taken: 0.0049secs
Last few successful migrations:
  id  filename                                                                                                       version    status    scheduledat                 executedat
----  -------------------------------------------------------------------------------------------------------------  ---------  --------  --------------------------  --------------------------
   1  offline/200.tables/user_master/2021_03_29__19_14_28_create_table_user_master.py                                b23b4a2d   complete  2021-03-29 20:04:01.691033  2021-03-29 20:04:01.691033
   2  offline/500.functions/generate_booking_number/2021_03_29__19_34_09_create_function_generate_booking_number.py  22d0747c   complete  2021-03-29 20:09:50.909159  2021-03-29 20:09:50.909159
   3  online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py                               22d0747c   complete  2021-03-29 20:09:50.932331  2021-03-29 20:09:50.932331

No new migration to process.
```

If all migrations are already carried out and you run `migrate` command again then rokso will do nothing, very much like `git commit`. **Also note that the revision number will be same to all files which are applied together.**

```
➜  tutorial git:(master) ✗ roksopsql migrate
Executing>>  SELECT * FROM offline.rokso_db_version
>> Time taken: 0.0021secs
Nothing to migrate ....

```

It may happen while executing a series of migrations an error can occur in-between. e.g. Let's say 5 migrations(files) were in pipeline and then while execution third migration failed, in this case Rokso will still mark first two files as successful and further migration will stop.

### Rollback migrations

For rolling back migrations, rokso support two modes: last successful migration and rolling back to a particular version, just like `git reset`. To ensure rolling back actually works, make sure all the rollback SQLs are properly written in migration files.

#### Rolling back last migration

This step is simple enough.
```
➜  tutorial git:(master) ✗ roksopsql rollback


Executing>>  SELECT * from offline.rokso_db_version ORDER BY id DESC LIMIT 1;
>> Time taken: 0.0055secs

Executing>>   SELECT * FROM offline.rokso_db_version WHERE version = '22d0747c' ORDER  BY id desc
>> Time taken: 0.0157secs
Following files will be rolledback:
  id  filename                                                                          version    status    scheduledat                 executedat
----  --------------------------------------------------------------------------------  ---------  --------  --------------------------  --------------------------
   3  online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py  22d0747c   complete  2021-03-29 20:09:50.932331  2021-03-29 20:09:50.932331

Please confirm to proceed(y/yes):y

🔄 Rolling back file::  online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py

Executing>>  DROP TABLE IF EXISTS online.website_user;
query completed successfully..
>> Time taken: 0.0318 secs

Executing>>  DELETE FROM offline.rokso_db_version WHERE id = 3 ;
query completed successfully..
>> Time taken: 0.0023 secs
✅ Rollback complete.

```

#### Rolling back to a specific version

Get status to identify which version to rollback

```
➜  tutorial git:(master) ✗ roksopsql status

Executing>>  SELECT * FROM offline.rokso_db_version
>> Time taken: 0.001secs
Last few successful migrations:
  id  filename                                                                                                       version    status    scheduledat                 executedat
----  -------------------------------------------------------------------------------------------------------------  ---------  --------  --------------------------  --------------------------
   7  offline/200.tables/user_master/2021_03_29__19_14_28_create_table_user_master.py                                bc5c6eb7   complete  2021-03-29 20:34:42.248132  2021-03-29 20:34:42.248132
   8  offline/500.functions/generate_booking_number/2021_03_29__19_34_09_create_function_generate_booking_number.py  5fc1fec2   complete  2021-03-29 20:36:32.758463  2021-03-29 20:36:32.758463
   9  online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py                               5fc1fec2   complete  2021-03-29 20:36:32.765727  2021-03-29 20:36:32.765727

No new migration to process.


```

Choose a version number from output and supply it as argument.
```
➜  tutorial git:(master) ✗ roksopsql rollback --version bc5c6eb7



Executing>>   SELECT * FROM offline.rokso_db_version WHERE scheduledAt > (SELECT scheduledAt FROM offline.rokso_db_version WHERE version = 'bc5c6eb7' ORDER  BY id desc LIMIT 1) ORDER BY id DESC;
>> Time taken: 0.0058secs
Following files will be rolledback:
  id  filename                                                                                                       version    status    scheduledat                 executedat
----  -------------------------------------------------------------------------------------------------------------  ---------  --------  --------------------------  --------------------------
   9  online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py                               5fc1fec2   complete  2021-03-29 20:36:32.765727  2021-03-29 20:36:32.765727
   8  offline/500.functions/generate_booking_number/2021_03_29__19_34_09_create_function_generate_booking_number.py  5fc1fec2   complete  2021-03-29 20:36:32.758463  2021-03-29 20:36:32.758463

Please confirm to proceed(y/yes):y

🔄 Rolling back file::  online/200.tables/website_user/2021_03_29__19_37_31_create_table_website_user.py

Executing>>  DROP TABLE IF EXISTS online.website_user;
query completed successfully..
>> Time taken: 0.0167 secs

Executing>>  DELETE FROM offline.rokso_db_version WHERE id = 9 ;
query completed successfully..
>> Time taken: 0.0007 secs

🔄 Rolling back file::  offline/500.functions/generate_booking_number/2021_03_29__19_34_09_create_function_generate_booking_number.py

Executing>>  DROP FUNCTION IF EXISTS offline.generate_booking_number;
query completed successfully..
>> Time taken: 0.0088 secs

Executing>>  DELETE FROM offline.rokso_db_version WHERE id = 8 ;
query completed successfully..
>> Time taken: 0.0051 secs
✅ Rollback complete.

```


### Reverse engineer your migrations

