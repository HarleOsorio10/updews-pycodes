import pandas as pd
import numpy as np
from datetime import timedelta as td
from datetime import datetime as dt
import sqlalchemy
from sqlalchemy import create_engine
import sys
import requests
import time
import csv

engine = create_engine('mysql+pymysql://updews:october50sites@127.0.0.1/senslopedb')
query = "select * from senslopedb.rain_props"
dfnew = pd.io.sql.read_sql(query,engine)
all_time = []
all_rainguage_noah = []
#fdate = "2017-10-22 00:00:00"
#tdate = "2017-10-29 00:00:00"

#fdata = raw_input('from: ')
#tdata = raw_input('to: ')
#tdate = dt.strptime(tdata, "%Y-%m-%d %H:%M:%S")
#fdate = dt.strptime(fdata, "%Y-%m-%d %H:%M:%S")

#rain_noah = []
#rain_arq  = []
#rain_senslope = []
#for site in dfnew.rain_senslope:
#        if site != None :
#            print site
#            start = time.time() 
#            rsite = str(site)
#            query = "select timestamp, rain from senslopedb.%s " %rsite
#            query += "where timestamp between '%s' and '%s'" %(pd.to_datetime(fdate)-td(3), tdate)
#            df = pd.io.sql.read_sql(query,engine)
#            df.columns = ['ts','rain']
#            df = df[df.rain >= 0]
#            df = df.set_index(['ts'])
#            if len(df) != 0:
#                df = df.resample('30Min').sum()
#                
#                df_inst = df.resample('30Min').sum()
#                
#                if max(df_inst.index) < pd.to_datetime(tdate):
#                    new_data = pd.DataFrame({'ts': [pd.to_datetime(tdate)], 'rain': [0]})
#                    new_data = new_data.set_index(['ts'])
#                    df = df.append(new_data)
#                    df = df.resample('30Min').sum()
#                      
#                df1 = pd.rolling_sum(df,48,min_periods=1)
#                df3 = pd.rolling_sum(df,144,min_periods=1)
#                
#                df['rval'] = df_inst
#                df['hrs24'] = df1
#                df['hrs72'] = df3
#                
#                df = df[(df.index >= fdate)&(df.index <= tdate)]
#                   
#                dfajson = df.reset_index().to_json(orient="records",date_format='iso')
#                dfajson = dfajson.replace("T"," ").replace("Z","").replace(".000","")
#                end = time.time()
#                rain_senslope.append({'from':fdate,'to':tdate,'site':site,'time':(end - start),'data_lenght':len(df)})  
#            else:
#                print 'no data'
#                end = time.time()
#                rain_senslope.append({'from':fdate,'to':tdate,'site':site,'time':'no data','data_lenght':'0'})  
#
#rain_senslope = pd.DataFrame(rain_senslope)
#rain_senslope.to_csv('//var//www//html//temp//data//rain_senslope_execution.csv')
#
#for site_arq in dfnew.rain_arq:
#        if site_arq != None :
#            print site_arq
#            start = time.time() 
#            rsite = str(site_arq)
#            query = "select timestamp, r15m from senslopedb.%s " %rsite
#            query += "where timestamp between '%s' and '%s'" %(pd.to_datetime(fdate)-td(3), tdate)
#            df = pd.io.sql.read_sql(query,engine)
#            df.columns = ['ts','rain']
#            df = df[df.rain >= 0]
#            df = df.set_index(['ts'])
#            if len(df) != 0:
#                df = df.resample('30Min').sum()
#                
#                df_inst = df.resample('30Min').sum()
#                
#                if max(df_inst.index) < pd.to_datetime(tdate):
#                    new_data = pd.DataFrame({'ts': [pd.to_datetime(tdate)], 'rain': [0]})
#                    new_data = new_data.set_index(['ts'])
#                    df = df.append(new_data)
#                    df = df.resample('30Min').sum()
#                      
#                df1 = pd.rolling_sum(df,48,min_periods=1)
#                df3 = pd.rolling_sum(df,144,min_periods=1)
#                
#                df['rval'] = df_inst
#                df['hrs24'] = df1
#                df['hrs72'] = df3
#                
#                df = df[(df.index >= fdate)&(df.index <= tdate)]
#                   
#                dfajson = df.reset_index().to_json(orient="records",date_format='iso')
#                dfajson = dfajson.replace("T"," ").replace("Z","").replace(".000","")
#                end = time.time()
#                rain_arq.append({'from':fdate,'to':tdate,'site':site_arq,'time':(end - start),'data_lenght':len(df)})    
#            else:
#                print 'no data'
#                end = time.time()
#                rain_arq.append({'from':fdate,'to':tdate,'site':site_arq,'time':(end - start),'data_lenght':'0'}) 
#                
#rain_arq = pd.DataFrame(rain_arq)
#rain_arq.to_csv('//var//www//html//temp//data//rain_arq_execution.csv')
# 
#for name in dfnew.RG1:
#    if(name != None and len(name) >= 10):
#         all_rainguage_noah.append(name)
#
#for name in dfnew.RG2:
#    if(name != None and len(name) >= 10):
#         all_rainguage_noah.append(name)
#
#for name in dfnew.RG3:
#    if(name != None and len(name) >= 10):
#         all_rainguage_noah.append(name)           
#
#for site_noah in all_rainguage_noah:
#        if site_noah != None :
#            print site_noah
#            start = time.time() 
#            rsite = str(site_noah)
#            query = "select timestamp, rval from senslopedb.%s " %rsite
#            query += "where timestamp between '%s' and '%s'" %(pd.to_datetime(fdate)-td(3), tdate)
#            df = pd.io.sql.read_sql(query,engine)
#            df.columns = ['ts','rain']
#            df = df[df.rain >= 0]
#            df = df.set_index(['ts'])
#            if len(df) != 0:
#                df = df.resample('30Min').sum()
#                
#                df_inst = df.resample('30Min').sum()
#                
#                if max(df_inst.index) < pd.to_datetime(tdate):
#                    new_data = pd.DataFrame({'ts': [pd.to_datetime(tdate)], 'rain': [0]})
#                    new_data = new_data.set_index(['ts'])
#                    df = df.append(new_data)
#                    df = df.resample('30Min').sum()
#                      
#                df1 = pd.rolling_sum(df,48,min_periods=1)
#                df3 = pd.rolling_sum(df,144,min_periods=1)
#                
#                df['rval'] = df_inst
#                df['hrs24'] = df1
#                df['hrs72'] = df3
#                
#                df = df[(df.index >= fdate)&(df.index <= tdate)]
#                   
#                dfajson = df.reset_index().to_json(orient="records",date_format='iso')
#                dfajson = dfajson.replace("T"," ").replace("Z","").replace(".000","")
#                end = time.time()
#                rain_noah.append({'site':site_noah,'time':(end - start),'data_lenght':len(df)})    
#            else:
#                print 'no data'
#                end = time.time()
#                rain_noah.append({'from':fdate,'to':tdate,'site':site_noah,'time':(end - start),'data_lenght':'0'}) 
#                
#rain_noah = pd.DataFrame(rain_noah)
#rain_noah.to_csv('//var//www//html//temp//data//rain_noah_execution.csv')
# 


############################ groound #################################
#gnd_data = []
#for site in dfnew.name:
#    start = time.time() 
#    if site == 'mng':
#        site ='man'
#    elif site == 'png':
#        site = 'pan'
#    elif site == 'bto':
#        site = 'bat'
#    elif site == 'jor':
#        site = "pob"
#        
#    
#    query = "SELECT id,timestamp, UPPER(crack_id) AS crack_id,meas FROM senslopedb.gndmeas where timestamp between '%s' and '%s' and site_id ='%s' and meas <= '500' order by site_id asc"%(fdate,tdate,site) 
#    df = pd.io.sql.read_sql(query,engine)
#    df.columns = ['id','ts','crack_id','meas']
#    df = df.set_index(['ts'])
#    dfajson = df.reset_index().to_json(orient='records',date_format='iso')
#    dfajson = dfajson.replace("T"," ").replace("Z","").replace(".000","")
#    dfajson_data = dfajson
#    end = time.time()
#    gnd_data.append({'from':fdate,'to':tdate,'site':site,'time':(end - start),'data_lenght':len(df)}) 
#    
#gnd_data = pd.DataFrame(gnd_data)
#gnd_data.to_csv('//var//www//html//temp//data//gnd_py_ex.csv')    


import os
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../updews-pycodes/Analysis/'))
if not path in sys.path:
   sys.path.insert(1, path)
del path

import vcdgen as vcd

sub_data = []
fdate =['','2017-09-25 00:00:00']
tdate = '2017-10-01 00:00:00'
for time_f  in fdate:
    for site in dfnew.name: 
        start = time.time()           

        if time_f  == '':
            if tdate == '':
                df= vcd.vcdgen(site)
            else:
                df= vcd.vcdgen(site, tdate, time_f )
        else:
            df= vcd.vcdgen(site, tdate, time_f )
        print site 
        end = time.time()
        sub_data.append({'from':time_f,'to':tdate,'site':site,'time':(end - start),'data_lenght':len(df)})
        print [{'from':time_f,'to':tdate,'site':site,'time':(end - start),'data_lenght':len(df)}]
sub_data = pd.DataFrame(sub_data)
sub_data.to_csv('//var//www//html//temp//data//sub_py_ex.csv') 