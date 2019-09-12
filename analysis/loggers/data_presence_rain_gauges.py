# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 14:27:21 2019

@author: DELL
"""

import time,serial,re,sys,traceback
import MySQLdb, subprocess
from datetime import datetime
from datetime import timedelta as td
import pandas as psql
import numpy as np
import MySQLdb, time 
from time import localtime, strftime
import pandas as pd
#import __init__
import itertools
import os
from sqlalchemy import create_engine
from dateutil.parser import parse


columns = ['rain_id', 'presence', 'last_data', 'ts_updated', 'diff_days']
df = pd.DataFrame(columns=columns)


def get_rain_gauges():
    localdf=0
    db = MySQLdb.connect(host = '192.168.150.253', user = 'root', passwd = 'senslope', db = 'senslopedb')
    query = "select gauge_name, rain_id from senslopedb.rainfall_gauges where data_source = 'senslope' and date_deactivated is null"
    localdf = psql.read_sql(query,db)
    return localdf

def get_data(lgrname):
    db = MySQLdb.connect(host = '192.168.150.253', user = 'root', passwd = 'senslope', db = 'senslopedb')
    query= "SELECT max(ts) FROM "+ 'rain_' + lgrname + "  where ts > '2010-01-01' and '2019-01-01' order by ts desc limit 1 "
    localdf = psql.read_sql(query,db)
    print (localdf)
    return localdf




def dftosql(df):
    gdf = get_rain_gauges()
    logger_active = pd.DataFrame()
    for i in range (0,len(gdf)):
        logger_active= logger_active.append(get_data(gdf.gauge_name[i]))
        print (logger_active)

    logger_active = logger_active.reset_index()
    timeNow= datetime.today()
    df['last_data'] = logger_active['max(ts)']
    df['last_data'] = pd.to_datetime(df['last_data'])   
    df['ts_updated'] = timeNow
    df['rain_id'] = gdf.rain_id
    diff = df['ts_updated'] - df['last_data']
    tdta = diff
    fdta = tdta.astype('timedelta64[D]')
    days = fdta.astype(int)
    df['diff_days'] = days

    df.loc[(df['diff_days'] > -1) & (df['diff_days'] < 3), 'presence'] = 'active' 
    df['presence'] = df['diff_days'].apply(lambda x: '1' if x <= 3 else '0') 
    print (df) 
    engine=create_engine('mysql+mysqlconnector://root:senslope@192.168.150.253:3306/analysis_db', echo = False)
#    df.to_csv('loggers2.csv')
#    engine=create_engine('mysql+mysqlconnector://root:senslope@127.0.0.1:3306/senslopedb', echo = False)

    df.to_sql(name = 'data_presence_rain_gauges', con = engine, if_exists = 'replace', index = False)
    return df


dftosql(df)

