DROP TABLE collected_ping;
DROP TABLE collected_trace;
DROP TABLE collected_stats;
DROP TABLE diagnosis;
CREATE TABLE collected_ping (id serial NOT NULL, clientID INT8 NOT NULL, sid INT8 NOT NULL, clientIP INET, session_url TEXT, remoteaddress INET, ping_min TEXT, ping_max TEXT, ping_avg TEXT, ping_std TEXT, PRIMARY KEY (id, clientID, sid, remoteaddress));
CREATE TABLE collected_trace (id serial NOT NULL, clientID INT8 NOT NULL, sid INT8 NOT NULL,remoteaddress INET, step_nr INT4, step_address INET, rtt_min TEXT, rtt_max TEXT, rtt_avg TEXT, rtt_std TEXT,PRIMARY KEY (id, clientID, sid, remoteaddress, step_nr)) ;
CREATE TABLE collected_stats (id serial NOT NULL, clientID INT8 NOT NULL, sid INT8 NOT NULL, session_start TIMESTAMP, t_idle TEXT, t_tot TEXT, t_http TEXT, t_tcp TEXT,t_dns TEXT, cpu_perc TEXT, mem_perc TEXT, page_dim TEXT, PRIMARY KEY (id, clientID, sid, session_start)) ;
CREATE TABLE diagnosis (diagnosis_run TIMESTAMP, clientID INT8 NOT NULL, sid INT8 NOT NULL, session_start TIMESTAMP, result TEXT, PRIMARY KEY (diagnosis_run, clientID, sid)) ;
