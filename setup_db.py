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

ping_table = '_%s_ping' % str_time
trace_table = '_%s_trace' % str_time
stats_table = '_%s_stats' % str_time
diagn_table = '_%s_diagnosis' % str_time

create_ping = '''CREATE TABLE %s (id serial NOT NULL, clientID INT8 NOT NULL, sid INT8 NOT NULL, clientIP INET, session_url TEXT, remoteaddress INET, ping_min TEXT, ping_max TEXT, ping_avg TEXT, ping_std TEXT, PRIMARY KEY (id, clientID, sid, remoteaddress));''' % ping_table
create_trace = '''CREATE TABLE %s (id serial NOT NULL, clientID INT8 NOT NULL, sid INT8 NOT NULL,remoteaddress INET, step_nr INT4, step_address INET, rtt_min TEXT, rtt_max TEXT, rtt_avg TEXT, rtt_std TEXT,PRIMARY KEY (id, clientID, sid, remoteaddress, step_nr)) ;''' % trace_table
create_stats = '''CREATE TABLE %s (id serial NOT NULL, clientID INT8 NOT NULL, sid INT8 NOT NULL, session_start TIMESTAMP, t_idle TEXT, t_tot TEXT, t_http TEXT, t_tcp TEXT,t_dns TEXT, cpu_perc TEXT, mem_perc TEXT, page_dim TEXT, PRIMARY KEY (id, clientID, sid, session_start)) ;''' % stats_table
create_diagnosis = '''CREATE TABLE %s (diagnosis_run TIMESTAMP, clientID INT8 NOT NULL, sid INT8 NOT NULL, session_start TIMESTAMP, result TEXT, PRIMARY KEY (diagnosis_run, clientID, sid)) ; ''' % diagn_table

tables = [create_ping, create_trace, create_stats, create_diagnosis]

for table in tables:
    cur = conn.cursor()
    cur.execute(table)
    conn.commit()

config.set('server','pingtable', ping_table)
config.set('server','tracetable', trace_table)
config.set('server','clienttable', stats_table)
config.set('server','diagnosistable', diagn_table)
with open(conf_file, 'wb') as configfile:
    config.write(configfile)
conn.close()
print 'Done'
