#!/usr/bin/env python3
# coding: utf-8
"""Script for creating and updating database tables"""
import sys
import os
import mariadb
import serialize
import logging

# Logging
log=logging.getLogger("dota")
if int(os.environ['DOTA_LOGGING'])==0:
    log.setLevel(logging.INFO)
else:
    log.setLevel(logging.DEBUG)
ch=logging.StreamHandler(sys.stdout)
fmt=logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt="%Y-%m-%dT%H:%M:%S %Z")
ch.setFormatter(fmt)
log.addHandler(ch)

def usage():
    """Basic usage information"""
    print()
    print("update_db.py ['DROP'|'NEW'|'UPGRADE']")
    print()
    sys.exit(-1)

def drop_all_tables(conn):
    cursor=conn.cursor()
    cursor.execute("SHOW TABLES;")
    tables=cursor.fetchall()
    for table in [t[0] for t in tables]:
        log.info("Dropping table %s", table)
        cursor.execute("DROP TABLE {}".format(table))
    conn.commit()

def create_version_1_0(conn):

    cursor=conn.cursor()
    log.info("Creating table dota_matches") 
    stmt="CREATE TABLE dota_matches (match_id BIGINT PRIMARY KEY, "
    stmt+="start_time BIGINT, radiant_heroes CHAR(32), dire_heroes CHAR(32), "
    stmt+="radiant_win BOOLEAN, api_skill INTEGER, items VARCHAR(1024), "
    stmt+="gold_spent VARCHAR(1024)) ENGINE = 'MyISAM';"
    cursor.execute(stmt)

    log.info("Creating fetch_summary")
    stmt="CREATE TABLE fetch_summary (date_hour_skill CHAR(32) PRIMARY "
    stmt+="KEY, skill INT, rec_count INT) ENGINE='MyISAM';"
    cursor.execute(stmt)

    log.info("Creating table fetch_history")
    stmt="CREATE TABLE fetch_history (match_id BIGINT PRIMARY KEY, "
    stmt+="start_time BIGINT) ENGINE='MyISAM';"
    cursor.execute(stmt)

    log.info("Creating table fetch_win_rate")
    stmt="CREATE TABLE fetch_win_rate (hero_skill CHAR(128) PRIMARY KEY, "
    stmt+="skill TINYINT, hero CHAR(128), time_range CHAR(128), radiant_win INT, "
    stmt+="radiant_total INT, radiant_win_pct FLOAT, dire_win INT, dire_total INT, "
    stmt+="dire_win_pct FLOAT, win INT, total INT, win_pct FLOAT) ENGINE='MyISAM';"
    cursor.execute(stmt)
    conn.commit()

def main():
    if len(sys.argv)!=2:
        usage()

    # Setup database
    conn = mariadb.connect(
        user=os.environ['DOTA_USERNAME'],
        password=os.environ['DOTA_PASSWORD'],
        host=os.environ['DOTA_HOSTNAME'],
        database=os.environ['DOTA_DATABASE'])

    if sys.argv[1]=="DROP":
        drop_all_tables(conn)
    elif sys.argv[1]=="NEW":
        drop_all_tables(conn)
        create_version_1_0(conn)
    else:
        usage()

if __name__=="__main__":
    main()


"""
if not "config" in [t[0] for t in cursor.fetchall()]:
    print("Creating version 1.0 database....)


    cursor.execute("CREATE TABLE config (name VARCHAR(128) PRIMARY KEY, value VARCHAR(128));")
    cursor.execute("INSERT INTO config (name, value) VALUES ('version', '1.0');")a

    

    conn.commit()

cursor.execute("SELECT value from config where name='version'")
db_version=cursor.fetchone()[0]
print("Database version: {}".format(db_version))
    
if db_version=="1.0":
    print("Upgrading from version 1.0...")
    print("Adding match details column....")
    cursor.execute("ALTER TABLE dota_matches ADD COLUMN IF NOT EXISTS (match_details VARBINARY(384)) AFTER api_skill;")
    print("Renaming table")
    cursor.execute("RENAME TABLE IF EXISTS dota_matches TO match_info;")
    conn.commit()

    print("Creating protobuf records")

    stmt="SELECT match_id, radiant_heroes, dire_heroes, items, gold_spent "
    stmt+="FROM dota_matches LIMIT 2000 OFFSET 0;"

    cursor.execute(stmt)
    rows=cursor.fetchall()

    match_ids=[]
    pb_values=[]
    for row in rows:
        match_ids.append(row[0])
        match_pb=serialize.protobuf_match_details(row[1],row[2],row[3],row[4])
        pb_values.append(match_pb.SerializeToString())

    stmt_update="UPDATE dota_matches SET match_details=%s WHERE match_id=%d"
    cursor.executemany(stmt_update, list(zip(pb_values, match_ids)))

    stmt_test="SELECT match_details FROM dota_matches LIMIT 2000";
    cursor.execute(stmt_test)
    rows=cursor.fetchall()



conn.close()

"""
