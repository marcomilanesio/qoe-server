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

#name = 'pisa'
#name = 'tma2015_wild'
name = 'local'
try:
    conn = psycopg2.connect(database=dbname, user=dbuser) 
except psycopg2.DatabaseError, e:
    print 'Unable to connect to DB. Error %s' % e
    sys.exit(1)
    
now = datetime.datetime.now()
str_time = '%d%s%s' % (now.year, '{:02d}'.format(now.month), '{:02d}'.format(now.day))

fullname = "{0}_{1}".format(name, str_time)

diagn_table = "diagnosis_{0}".format(fullname)
session_table = "sessions_{0}".format(fullname)
summary_table = "summary_{0}".format(fullname)
services_table = "services_{0}".format(fullname)
ping_table = "ping_{0}".format(fullname)
trace_table = "trace_{0}".format(fullname)

#print diagn_table, session_table, summary_table, services_table, ping_table, trace_table
#sys.exit(0)

create_diagnosis = '''CREATE TABLE %s (diagnosis_run TIMESTAMP, probeid INT8 NOT NULL, sid INT8 NOT NULL, session_start TIMESTAMP,
result TEXT, PRIMARY KEY (diagnosis_run, probeid, sid)) ; ''' % diagn_table

create_session_table = '''CREATE TABLE {0} (
    id serial NOT NULL,
    probeid INT8 NOT NULL,
    probeip INET,
    sid INT8,
    session_url TEXT,
    session_start TIMESTAMP,
    server_ip INET,
    full_load_time INT,
    page_dim INT,
    cpu_percent INT,
    mem_percent INT,
    services TEXT,
    active_measurements TEXT,
    PRIMARY KEY (id, probeid, session_start)
) '''.format(session_table)

create_summary_table = '''CREATE TABLE {0} (
    id serial NOT NULL,
    probeid INT8 NOT NULL,
    probeip INET,
    sid INT8,
    session_url TEXT,
    session_start TIMESTAMP,
    server_ip INET,
    full_load_time INT,
    page_dim INT,
    cpu_percent INT,
    mem_percent INT,
    PRIMARY KEY (id, probeid, session_start)
) '''.format(summary_table)

create_services_table = '''CREATE TABLE {0} (
    id serial NOT NULL,
    probeid INT8 NOT NULL,
    sid INT8,
    session_url TEXT,
    session_start TIMESTAMP,
    service_base_url TEXT,
    service_ip INET,
    netw_bytes INT,
    t_tcp INT,
    t_http INT,
    rcv_time INT,
    nr_obj INT,
    PRIMARY KEY (id, probeid, session_start)
) '''.format(services_table)

create_ping_table = '''CREATE TABLE {0} (
    id serial NOT NULL,
    probeid INT8 NOT NULL,
    sid INT8,
    session_start TIMESTAMP,
    server_ip INET,
    host INET,
    min FLOAT,
    max FLOAT,
    avg FLOAT,
    std FLOAT,
    loss INT,
    PRIMARY KEY (id, probeid, session_start)
) '''.format(ping_table)

create_trace_table = '''CREATE TABLE {0} (
    id serial NOT NULL,
    probeid INT8 NOT NULL,
    sid INT8,
    session_start TIMESTAMP,
    server_ip INET,
    hop_addr INET,
    hop_nr INT,
    min FLOAT,
    max FLOAT,
    avg FLOAT,
    std FLOAT,
    endpoints TEXT,
    PRIMARY KEY (id, probeid, session_start)
) '''.format(trace_table)


tables = [create_summary_table, create_ping_table, create_trace_table, create_services_table, create_diagnosis, create_session_table]

for table in tables:
    cur = conn.cursor()
    cur.execute(table)
    conn.commit()

config.set('server', 'pingtable', ping_table)
config.set('server', 'tracetable', trace_table)
config.set('server', 'servicestable', services_table)
config.set('server', 'summarytable', summary_table)
config.set('server', 'diagnosistable', diagn_table)
config.set('server', 'sessiontable', session_table)
with open(conf_file, 'wb') as configfile:
    config.write(configfile)
conn.close()
print 'Done'
