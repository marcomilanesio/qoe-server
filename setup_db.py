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

#diagn_table = 'pisa_diagnosis_%s' % str_time
diagn_table = 'tma2015_wild_diagnosis'
create_diagnosis = '''CREATE TABLE %s (diagnosis_run TIMESTAMP, probeid INT8 NOT NULL, sid INT8 NOT NULL, session_start TIMESTAMP,
result TEXT, PRIMARY KEY (diagnosis_run, probeid, sid)) ; ''' % diagn_table

#session_table = "sessions_{0}".format(str_time)
session_table = 'tma2015_wild_sessions'
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


#summary_table = "pisa_summary_{0}".format(str_time)
summary_table = 'tma2015_wild_summary'
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


#services_table = "pisa_services_{0}".format(str_time)
services_table = 'tma2015_wild_services'
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


#ping_table = "pisa_ping_{0}".format(str_time)
ping_table = 'tma2015_wild_ping'
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


#trace_table = "pisa_trace_{0}".format(str_time)
trace_table = 'tma2015_wild_traces'
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
