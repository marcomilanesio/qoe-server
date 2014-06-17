#!/usr/bin/python

import psycopg2
import ConfigParser
import datetime
import sys

conf_file = sys.argv[1]

config = ConfigParser.RawConfigParser()
config.read(conf_file)
dbname = config.get('server', 'dbname')
dbuser = config.get('server', 'dbuser')

try:
    conn = psycopg2.connect(database=dbname, user=dbuser) 
except psycopg2.DatabaseError, e:
    print 'Unable to connect to DB. Error %s' % e
    sys.exit(1)
    
now = datetime.datetime.now()
str_time = '%d%s%s' % (now.year, '{:02d}'.format(now.month), '{:02d}'.format(now.day))

ping_table = 'ping_%s' % str_time
trace_table = 'trace_%s' % str_time
stats_table = 'stats_%s' % str_time
diagn_table = 'diagnosis_%s' % str_time

create_ping = '''CREATE TABLE %s (id serial NOT NULL, clientID INT8 NOT NULL, sid INT8 NOT NULL, clientIP INET,
session_url TEXT, remoteaddress INET, ping_min FLOAT, ping_max FLOAT, ping_avg FLOAT, ping_std FLOAT,
PRIMARY KEY (id, clientID, sid, remoteaddress));''' % ping_table

create_trace = '''CREATE TABLE %s (id serial NOT NULL, clientID INT8 NOT NULL, sid INT8 NOT NULL,remoteaddress INET,
step_nr INT4, step_address INET, rtt_min FLOAT, rtt_max FLOAT, rtt_avg FLOAT, rtt_std FLOAT,
PRIMARY KEY (id, clientID, sid, remoteaddress, step_nr)) ;''' % trace_table

create_stats = '''CREATE TABLE %s (id serial NOT NULL, clientID INT8 NOT NULL, sid INT8 NOT NULL, session_start TIMESTAMP,
t_idle INT, t_tot INT, t_http INT, t_tcp INT, t_dns INT, cpu_perc INT, mem_perc INT,
page_dim INT, PRIMARY KEY (id, clientID, sid, session_start)) ;''' % stats_table

create_diagnosis = '''CREATE TABLE %s (diagnosis_run TIMESTAMP, clientID INT8 NOT NULL, sid INT8 NOT NULL, session_start TIMESTAMP,
result TEXT, PRIMARY KEY (diagnosis_run, clientID, sid)) ; ''' % diagn_table

tables = [create_ping, create_trace, create_stats, create_diagnosis]

if sys.argv[1] == 'd':
    print 'Dropping tables'
    for table_name in [ping_table, trace_table, stats_table, diagn_table]:
        q = 'Drop table if exists %s ' % table_name
        cur = conn.cursor()
        cur.execute(q)
        conn.commit()

for table in tables:
    cur = conn.cursor()
    cur.execute(table)
    conn.commit()

config.set('server', 'pingtable', ping_table)
config.set('server', 'tracetable', trace_table)
config.set('server', 'clienttable', stats_table)
config.set('server', 'diagnosistable', diagn_table)
with open(conf_file, 'wb') as configfile:
    config.write(configfile)
conn.close()
print 'Done'
