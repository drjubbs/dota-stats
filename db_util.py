# -*- coding: utf-8 -*-
"""Utility functions to manage the MySQL database"""

def create_version_001(conn):
    """Create the initial database version"""

    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS dota_matches")

    stmt = "CREATE TABLE `dota_matches` ("
    stmt +=  "`match_id` bigint(20) NOT NULL,"
    stmt += "`start_time` bigint(20) DEFAULT NULL,"
    stmt += "`radiant_heroes` char(32) DEFAULT NULL,"
    stmt += "`dire_heroes` char(32) DEFAULT NULL,"
    stmt += "`radiant_win` tinyint(1) DEFAULT NULL,"
    stmt += "`api_skill` int(11) DEFAULT NULL,"
    stmt += "`items` varchar(1024) DEFAULT NULL,"
    stmt += "`gold_spent` varchar(1024) DEFAULT NULL,"
    stmt += "PRIMARY KEY (`match_id`)"
    stmt += ") ENGINE=MyISAM DEFAULT CHARSET=utf8mb4;"
    cursor.execute(stmt)
    conn.commit()
