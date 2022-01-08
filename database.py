import sqlite3

sql_create_hash_table = """ CREATE TABLE IF NOT EXISTS hash (
                                id integer PRIMARY KEY,
                                name text NOT NULL,
                                url text NOT NULL,
                                hash text NOT NULL
                            ); """

sql_create_cache_table = """ CREATE TABLE IF NOT EXISTS cache (
                                id integer PRIMARY KEY,
                                hash_id integer NOT NULL,
                                status integer DEFAULT 0 NOT NULL
                            ); """

sql_create_local_table = """ CREATE TABLE IF NOT EXISTS local (
                                id integer PRIMARY KEY,
                                path text NOT NULL,
                                hash text NOT NULL
                            ); """
class Database:
    def __init__(self, db):
        self.conn = self.create_connection(db)

    def create_connection(self, db_file):
        conn = sqlite3.connect(db_file)
        return conn

    def create_table(self, create_table_sql):
        if self.conn is not None:
            c = self.conn.cursor()
            c.execute(create_table_sql)

    def query(self, q, *args):
        c = self.conn.cursor()
        rows = c.execute(q, (*args,))
        return rows
    
    def commit(self):
        self.conn.commit()
