import pandas as pd
import numpy as np
from datetime import timedelta as td
from datetime import datetime as dt
import sqlalchemy
from sqlalchemy import create_engine
import sys
import requests
import json

#
gsite = sys.argv[1]
fdate = sys.argv[2]
tdate = sys.argv[3]

#gsite = 'bar'
#fdate = '2013-01-01'
#tdate = '2017-01-01'
engine = create_engine('mysql+pymysql://root:senslope@127.0.0.1/senslopedb')
query = "SELECT timestamp, UPPER(crack_id) AS crack_id,meas FROM senslopedb.gndmeas where timestamp between '%s' and '%s 23:59:59' and site_id ='%s' and meas <= '500' order by site_id asc"%(fdate,tdate,gsite) 
df = pd.io.sql.read_sql(query,engine)
df.columns = ['ts','crack_id','meas']
df = df.set_index(['ts'])
dfajson = df.reset_index().to_json(orient='records',date_format='iso')
dfajson = dfajson.replace("T"," ").replace("Z","").replace(".000","")
print dfajson
