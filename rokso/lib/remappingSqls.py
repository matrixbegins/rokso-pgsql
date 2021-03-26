find_objects_sql = {

    "schema": """ select schema_name from information_schema.schemata
                where schema_name not like 'pg_%' and schema_name != 'information_schema';""" ,

    "tables": "SELECT table_name FROM information_schema.tables WHERE table_schema = '{}';",

    "views": "select table_name as view_name, view_definition from INFORMATION_SCHEMA.views where table_schema = '{}';",

    "mat_views": "select matviewname as view_name, definition as view_definition from pg_matviews where schemaname = '{}'",

    "database_types": """ WITH types AS (
                SELECT n.nspname,
                    pg_catalog.format_type ( t.oid, NULL ) AS obj_name,
                    CASE
                        WHEN t.typrelid != 0 THEN CAST ( 'tuple' AS pg_catalog.text )
                        WHEN t.typlen < 0 THEN CAST ( 'var' AS pg_catalog.text )
                        ELSE CAST ( t.typlen AS pg_catalog.text )
                        END AS obj_type,
                    coalesce ( pg_catalog.obj_description ( t.oid, 'pg_type' ), '' ) AS description
                    FROM pg_catalog.pg_type t
                    JOIN pg_catalog.pg_namespace n
                    ON n.oid = t.typnamespace
                    WHERE ( t.typrelid = 0
                        OR ( SELECT c.relkind = 'c'
                            FROM pg_catalog.pg_class c
                            WHERE c.oid = t.typrelid ) )
                    AND NOT EXISTS (
                        SELECT 1
                            FROM pg_catalog.pg_type el
                            WHERE el.oid = t.typelem
                            AND el.typarray = t.oid )
                    AND n.nspname = '{}'
                ),
                cols AS (
                SELECT n.nspname::text AS schema_name,
                    pg_catalog.format_type ( t.oid, NULL ) AS obj_name,
                    a.attname::text AS column_name,
                    pg_catalog.format_type ( a.atttypid, a.atttypmod ) AS data_type,
                    a.attnotnull AS is_required,
                    a.attnum AS ordinal_position,
                    pg_catalog.col_description ( a.attrelid, a.attnum ) AS description
                    FROM pg_catalog.pg_attribute a
                    JOIN pg_catalog.pg_type t
                    ON a.attrelid = t.typrelid
                    JOIN pg_catalog.pg_namespace n
                    ON ( n.oid = t.typnamespace )
                    JOIN types
                    ON ( types.nspname = n.nspname
                        AND types.obj_name = pg_catalog.format_type ( t.oid, NULL ) )
                    WHERE a.attnum > 0
                    AND NOT a.attisdropped
                )
                SELECT cols.schema_name, cols.obj_name,
                    'CREATE TYPE ' || cols.schema_name ||'.' || cols.obj_name ||
                        ' AS ( ' || string_agg('"' || cols.column_name || '" ' || cols.data_type,',' order by cols.ordinal_position) || ' );' as ddl
                FROM cols
                group by 1,2
                ORDER BY cols.schema_name, cols.obj_name;
            """,

    "enums": """ SELECT n.nspname AS "schema", t.typname
            , string_agg(e.enumlabel, '|' ORDER BY e.enumsortorder) AS enum_labels,
            'CREATE TYPE ' || n.nspname || '.' || t.typname || ' AS ENUM (''' || string_agg(e.enumlabel, ''', ''' ORDER BY e.enumsortorder) || ''');' as enum_ddl
            FROM   pg_catalog.pg_type t
            JOIN   pg_catalog.pg_namespace n ON n.oid = t.typnamespace
            JOIN   pg_catalog.pg_enum e ON t.oid = e.enumtypid
            WHERE   n.nspname = '{}'
            GROUP  BY 1,2;  """,

    "functions": """ select p.proname AS function_name
                    ,pg_get_functiondef(p.oid) AS func_def
                    ,pg_get_function_arguments(p.oid) AS args
                    ,pg_get_function_result(p.oid) AS result
                FROM   pg_proc p INNER JOIN   pg_namespace n ON n.oid = p.pronamespace
                WHERE  n.nspname = '{}'; """

}


get_ddl_sqls = {
    "create_table_ddl_generator": """
        CREATE OR REPLACE FUNCTION {}.generate_table_ddl(p_schema_name character varying, p_table_name character varying)
    RETURNS SETOF text AS
    $BODY$
    DECLARE
        v_table_ddl   text;
        column_record record;
        table_rec record;
        constraint_rec record;
        firstrec boolean;
    BEGIN
        FOR table_rec IN
            SELECT c.relname, c.oid FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                    WHERE relkind = 'r'
                    AND n.nspname = p_schema_name
                    AND relname~ ('^('||p_table_name||')$')
            ORDER BY c.relname
        LOOP
            FOR column_record IN
                SELECT
                    b.nspname as schema_name,
                    b.relname as table_name,
                    a.attname as column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) as column_type,
                    CASE WHEN
                        (SELECT substring(pg_catalog.pg_get_expr(d.adbin, d.adrelid) for 128)
                        FROM pg_catalog.pg_attrdef d
                        WHERE d.adrelid = a.attrelid AND d.adnum = a.attnum AND a.atthasdef) IS NOT NULL THEN
                        CASE when strpos( (SELECT substring(pg_catalog.pg_get_expr(d.adbin, d.adrelid) for 128)
                FROM pg_catalog.pg_attrdef d
                        WHERE d.adrelid = a.attrelid AND d.adnum = a.attnum AND a.atthasdef),  'nextval') = 0 then
                'DEFAULT '|| (SELECT substring(pg_catalog.pg_get_expr(d.adbin, d.adrelid) for 128)
                        FROM pg_catalog.pg_attrdef d
                            WHERE d.adrelid = a.attrelid AND d.adnum = a.attnum AND a.atthasdef)
                else
                    'serial'
                end
                    ELSE
                        ''
                    END as column_default_value,
                    CASE WHEN a.attnotnull = true THEN
                        'NOT NULL'
                    ELSE
                        'NULL'
                    END as column_not_null,
                    a.attnum as attnum,
                    e.max_attnum as max_attnum
                FROM
                    pg_catalog.pg_attribute a
                    INNER JOIN
                    (SELECT c.oid,
                        n.nspname,
                        c.relname
                    FROM pg_catalog.pg_class c
                        LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.oid = table_rec.oid
                    ORDER BY 2, 3) b
                    ON a.attrelid = b.oid
                    INNER JOIN
                    (SELECT
                        a.attrelid,
                        max(a.attnum) as max_attnum
                    FROM pg_catalog.pg_attribute a
                    WHERE a.attnum > 0
                        AND NOT a.attisdropped
                    GROUP BY a.attrelid) e
                    ON a.attrelid=e.attrelid
                WHERE a.attnum > 0
                AND NOT a.attisdropped
                ORDER BY a.attnum
            LOOP
                IF column_record.attnum = 1 THEN
                    v_table_ddl:='CREATE TABLE '||column_record.schema_name||'.'||column_record.table_name||' (';
                ELSE
                    v_table_ddl:=v_table_ddl||',';
                END IF;

                IF column_record.attnum <= column_record.max_attnum then

                IF column_record.column_default_value = 'serial' then
                    v_table_ddl:=v_table_ddl||chr(10)||
                            '    '||column_record.column_name||' '||column_record.column_default_value||' '||column_record.column_not_null;
                else
                    v_table_ddl:=v_table_ddl||chr(10)||
                            '    '||column_record.column_name||' '||column_record.column_type||' '||column_record.column_default_value||' '||column_record.column_not_null;
                end if;
                END IF;
            END LOOP;

            firstrec := TRUE;
            FOR constraint_rec IN
                SELECT conname, pg_get_constraintdef(c.oid) as constrainddef
                    FROM pg_constraint c
                        WHERE conrelid=(
                            SELECT attrelid FROM pg_attribute
                            WHERE attrelid = (
                                SELECT oid FROM pg_class WHERE relname = table_rec.relname
                                    AND relnamespace = (SELECT ns.oid FROM pg_namespace ns WHERE ns.nspname = p_schema_name)
                            ) AND attname='tableoid'
                        )
            LOOP
                v_table_ddl:=v_table_ddl||','||chr(10);
                v_table_ddl:=v_table_ddl||'CONSTRAINT '||constraint_rec.conname;
                v_table_ddl:=v_table_ddl||chr(10)||'    '||constraint_rec.constrainddef;
                firstrec := FALSE;
            END LOOP;
            v_table_ddl:=v_table_ddl||');';
            RETURN NEXT v_table_ddl;
        END LOOP;
    END;
    $BODY$
    LANGUAGE plpgsql volatile COST 100;
        """,

    "drop_table_ddl_generator":   """ DROP FUNCTION IF EXISTS {}.generate_table_ddl; """,

    "index_of_table": """ select pg_get_indexdef(format('%I.%I', schemaname, indexname)::regclass) as ddl
                from pg_indexes where schemaname = '{}' and tablename = '{}'; """,

    "get_table_ddl": "select {}.generate_table_ddl( '{}', '{}');"

}


drop_object_sqls = {

    "schema":      "DROP SCHEMA IF EXISTS {} CASCADE;",
    "tables":       "DROP TABLE IF EXISTS {}.{} ;",
    "views":        "DROP VIEW IF EXISTS {}.{} ;",
    "mat_views":    "DROP MATERIALIZED VIEW IF EXISTS {}.{} ;",
    "database_types":   "DROP TYPE IF EXISTS {}.{} ;",
    "enums":        "DROP TYPE IF EXISTS {}.{} ;",
    "functions":    "DROP FUNCTION IF EXISTS  {}.{} ;",
}

