#Importing relevant functions
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
plt.ioff()

from datetime import datetime, date, time, timedelta
import pandas as pd
import numpy as np
import ConfigParser
from scipy import stats
from scipy.interpolate import UnivariateSpline
from scipy.signal import gaussian
from scipy.ndimage import filters
import os
import sys
import platform
from sqlalchemy import create_engine

#Include the path of "Data Analysis" folder for the python scripts searching
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if not path in sys.path:
    sys.path.insert(1,path)
del path 
from querySenslopeDb import *

#Check the current OS of the machine
curOS = platform.system()

#import MySQLdb according to the OS
if curOS == "Windows":
    import MySQLdb as mysqlDriver
elif curOS == "Linux":
    import pymysql as mysqlDriver

#####################Defining important local functions
def up_one(p):
    #INPUT: Path or directory
    #OUTPUT: Parent directory
    out = os.path.abspath(os.path.join(p, '..'))
    return out  

#Include the path of "Analysis"folder for the python scrips searching
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
analysis_path = up_one(path)+'/Analysis/'

                      
if not analysis_path in sys.path:
    sys.path.insert(1,analysis_path)
del analysis_path

#Import file output path creator
from filepath import output_file_path                   

#Monitoring output directory
path2 = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
out_path = up_one(up_one(path2)) 

cfg = ConfigParser.ConfigParser()
cfg.read(path2 + '/server-config.txt')
    
def CreateMarkerAlerts(Hostdb,Userdb,Passdb,Namedb):
    db = mysqlDriver.connect(host = Hostdb, user = Userdb, passwd = Passdb)
    cur = db.cursor()
    
    cur.execute("USE {}".format(Namedb))
    cur.execute("CREATE TABLE IF NOT EXISTS {}(ma_id INT(11) AUTO_INCREMENT, ts TIMESTAMP, site_code VARCHAR(3),marker_name VARCHAR(10),displacement FLOAT, time_delta FLOAT, alert VARCHAR(3), PRIMARY KEY (ma_id))".format('marker_alerts'))
    db.commit()
    db.close()

def RoundTime(date_time):
    date_time = pd.to_datetime(date_time)
    time_hour = int(date_time.strftime('%H'))
    time_float = float(date_time.strftime('%H')) + float(date_time.strftime('%M'))/60

    quotient = time_hour / 4
    if quotient == 5:
        if time_float % 4 > 3.5:
            date_time = datetime.combine(date_time.date() + timedelta(1), time(4,0,0))
        else:
            date_time = datetime.combine(date_time.date() + timedelta(1), time(0,0,0))
    elif time_float % 4 > 3.5:
        date_time = datetime.combine(date_time.date(), time((quotient + 2)*4,0,0))
    else:
        date_time = datetime.combine(date_time.date(), time((quotient + 1)*4,0,0))
            
    return date_time

def get_rt_window(rt_window_length,roll_window_size,num_roll_window_ops):
    ##INPUT:
    ##rt_window_length; float; length of real-time monitoring window in days
    ##roll_window_size; integer; number of data points to cover in moving window operations
    
    ##OUTPUT: 
    ##end, start, offsetstart; datetimes; dates for the end, start and offset-start of the real-time monitoring window 

    ##set current time as endpoint of the interval
    end=datetime.now()

    ##round down current time to the nearest HH:00 or HH:30 time value
    end_Year=end.year
    end_month=end.month
    end_day=end.day
    end_hour=end.hour
    end_minute=end.minute
    if end_minute<30:end_minute=0
    else:end_minute=30
    end=datetime.combine(date(end_Year,end_month,end_day),time(end_hour,end_minute,0))

    #starting point of the interval
    start=end-timedelta(days=rt_window_length)
    
    #starting point of interval with offset to account for moving window operations 
    offsetstart=end-timedelta(days=rt_window_length+((num_roll_window_ops*roll_window_size-1)/48.))
    
    return end, start, offsetstart

def set_monitoring_window(roll_window_length,data_dt,rt_window_length,num_roll_window_ops):    
    ##INPUT:
    ##roll_window_length; float; length of rolling/moving window operations, in hours
    ##data_dt; float; time interval between data points, in hours    
    ##rt_window_length; float; length of real-time monitoring window, in days
    ##num_roll_window_ops; float; number of rolling window operations in the whole monitoring analysis
    
    ##OUTPUT:
    ##roll_window_numpts; number of data points per rolling window, end; endpoint of interval, 
    ##start; starting point of interval, offsetstart; starting point of interval with offset to account for moving window operations,
    ##monwin; empty dataframe with length of rt_window_length
    
    roll_window_numpts=int(1+roll_window_length/data_dt)
    end, start, offsetstart=get_rt_window(rt_window_length,roll_window_numpts,num_roll_window_ops)
    monwin_time=pd.date_range(start=start, end=end, freq='30Min',name='ts', closed=None)
    monwin=pd.DataFrame(data=np.nan*np.ones(len(monwin_time)), index=monwin_time)

    return roll_window_numpts, end, start, offsetstart, monwin

def uptoDB_gndmeas_alerts(df,df2):
    #INPUT: Dataframe containing all alerts df, previous alert data frame df2
    #OUTPUT: Writes to sql all ground measurement related alerts database
        
    #Merges the two data frame according to site and alerts
    df3 = pd.merge(df.reset_index(),df2.reset_index(),how = 'left',on = ['site','alert'])
    df3 = df3[df3.timestamp_y.isnull()]
    df3 = df3[['timestamp_x','site','alert','cracks_x']]
    df3.columns = ['timestamp','site','alert','cracks']
    
    #Delete possible duplicates or nd alert    
    df3_group = df3.groupby(['site','timestamp'])
    df3_group.apply(del_data)
    
    df3 = df3.set_index('timestamp')
    
    engine=create_engine('mysql://'+Userdb+':'+Passdb+'@'+Hostdb+':3306/'+Namedb)
    df3.to_sql(name = 'gndmeas_new_alerts', con = engine, if_exists = 'append', schema = Namedb, index = True)

def uptoDB_marker_alerts(df,df2):
    #INPUT: Dataframe containing all alerts df, previous alert data frame df2
    #OUTPUT: Writes to sql all ground measurement related alerts database
        
    #Merges the two data frame according to site and alerts
    df3 = pd.merge(df.reset_index(),df2.reset_index(),how = 'left',on = ['site_code','marker_name','alert'])
    df3 = df3[df3.ts_y.isnull()]
    df3 = df3[['ts_x','site_code','marker_name','displacement_x','time_delta_x','alert']]
    df3.columns = ['ts','site_code','marker_name','displacement','time_delta','alert']
    
    #Delete possible duplicates or nd alert    
    df3_group = df3.groupby(['site_code','marker_name','ts'])
    df3_group.apply(del_new_db_data)
    
    df3 = df3.set_index('ts')
    
    engine=create_engine('mysql://'+Userdb+':'+Passdb+'@'+Hostdb+':3306/'+Namedb)
    df3.to_sql(name = 'marker_alerts', con = engine, if_exists = 'append', schema = Namedb, index = True)

def get_ground_data_with_recent_cracks(site,end,num_pts):
    query = "SELECT g1.timestamp, g1.crack_id, g1.site_id,g1.meas, COUNT(*) num FROM gndmeas g1 INNER JOIN gndmeas g2 ON g1.timestamp <= g2.timestamp AND g1.crack_id = g2.crack_id AND g1.site_id = g2.site_id AND g1.site_id = '{}' AND g1.timestamp <= '{}' AND g2.timestamp <= '{}' AND g1.crack_id in (SELECT crack_id FROM gndmeas WHERE site_id = '{}' AND timestamp = (SELECT max(timestamp) FROM gndmeas WHERE timestamp <= '{}' AND site_id = '{}')) GROUP BY g1.crack_id, g1.timestamp,g1.site_id HAVING COUNT(*) <= 10 ORDER by num desc".format(site,end,end,site,end,site)
    
    df = GetDBDataFrame(query)
    return df

def get_latest_ground_df(site=None,end = None):
    #INPUT: String containing site name    
    #OUTPUT: Dataframe of the last 10 recent ground measurement in the database
    if site == None and end == None:
        query = 'SELECT g1.timestamp,g1.site_id,g1.crack_id,g1.meas, COUNT(*) num FROM senslopedb.gndmeas g1 JOIN senslopedb.gndmeas g2 ON g1.site_id = g2.site_id AND g1.crack_id = g2.crack_id AND g1.timestamp <= g2.timestamp group by g1.timestamp,g1.site_id, g1.crack_id HAVING COUNT(*) <= 10 ORDER BY site_id, crack_id, num desc'
    elif end != None and site != None:
        query = 'SELECT g1.timestamp,g1.site_id,g1.crack_id,g1.meas, COUNT(*) num FROM senslopedb.gndmeas g1 JOIN senslopedb.gndmeas g2 ON g1.site_id = g2.site_id AND g1.crack_id = g2.crack_id AND g1.timestamp <= g2.timestamp  AND g1.site_id = "{}" AND g1.timestamp <= "{}" AND g2.timestamp <= "{}" group by g1.timestamp,g1.site_id, g1.crack_id HAVING COUNT(*) <= 10 ORDER BY site_id, crack_id, num desc'.format(site,end,end)
    elif site == None and end != None:
        query = 'SELECT g1.timestamp,g1.site_id,g1.crack_id,g1.meas, COUNT(*) num FROM senslopedb.gndmeas g1 JOIN senslopedb.gndmeas g2 ON g1.site_id = g2.site_id AND g1.crack_id = g2.crack_id AND g1.timestamp <= g2.timestamp  AND g1.timestamp <= "{}" AND g2.timestamp <= "{}" group by g1.timestamp,g1.site_id, g1.crack_id HAVING COUNT(*) <= 10 ORDER BY site_id, crack_id, num desc'.format(end,end)
    else:
        query = 'SELECT g1.timestamp,g1.site_id,g1.crack_id,g1.meas, COUNT(*) num FROM senslopedb.gndmeas g1 JOIN senslopedb.gndmeas g2 ON g1.site_id = g2.site_id AND g1.crack_id = g2.crack_id AND g1.timestamp <= g2.timestamp AND g1.site_id = "{}" group by g1.timestamp,g1.site_id, g1.crack_id HAVING COUNT(*) <= 10 ORDER BY site_id, crack_id, num desc'.format(site)

    df = GetDBDataFrame(query)
    return df[['timestamp','site_id','crack_id','meas']]

def get_latest_ground_df2(site = None,end = None):
    '''
    Get the latest 10 recent ground measurement per marker of specified site and timestamp.
    
    Paramters
    ----------------
    site - string
        site code of site of interest
    end - string (YYYY-MM-DD HH:MM)
        end timestamp
    
    Returns
    ---------------
    ground_data - pd.DataFrame()
        Latest 10 ground data
    '''
    #### Get query of ground data of specified site and timestamp
    query = 'SELECT timestamp,site_id,crack_id,meas FROM gndmeas WHERE timestamp <= "{}" AND site_id = "{}"'.format(end,site) 
    
    #### Get all ground data
    all_surficial = GetDBDataFrame(query)
    
    #### Uppercase site and marker_id
    all_surficial.loc[:,['crack_id']] = all_surficial['crack_id'].apply(lambda x:x.upper())
    all_surficial.loc[:,['site_id']] = all_surficial['site_id'].apply(lambda x:x.upper())
    
    #### Group data according to site and crack_id
    all_surficial_group = all_surficial.groupby(['site_id','crack_id'],as_index = False)
    
    ####  Get latest 10 data per crack
    ground_data = all_surficial_group.apply(lambda x:x.tail(10)).reset_index()[['timestamp','site_id','crack_id','meas']]
    
    return ground_data

def get_latest_marker_data(site,marker,end):
    '''
    Get the latest 10 recent ground measurement per marker of specified site, marker and end timestamp.
    
    Paramters
    ----------------
    site - string
        site code of site of interest
    marker - string
        marker name of interest
    end - string (YYYY-MM-DD HH:MM)
        end timestamp
    
    Returns
    ---------------
    marker_data - pd.DataFrame()
        Latest 10 marker data for specified marker
    '''
    #### Get query of ground data of specified site and timestamp
    query = 'SELECT timestamp,site_id,crack_id,meas FROM gndmeas WHERE timestamp <= "{}" AND site_id = "{}" AND crack_id = "{}"'.format(end,site,marker) 
    
    #### Get all ground data
    all_surficial = GetDBDataFrame(query)
    
    #### Uppercase site and marker_id
    all_surficial.loc[:,['crack_id']] = all_surficial['crack_id'].apply(lambda x:x.upper())
    all_surficial.loc[:,['site_id']] = all_surficial['site_id'].apply(lambda x:x.upper())
    
    #### Group data according to site and crack_id
    all_surficial_group = all_surficial.groupby(['site_id','crack_id'],as_index = False)
    
    ####  Get latest 10 data per crack
    marker_data = all_surficial_group.apply(lambda x:x.tail(10)).reset_index()[['timestamp','site_id','crack_id','meas']]
    
    return marker_data
    


def get_ground_df(start = '',end = '',site=None):
    #INPUT: Optional start time, end time, and site name
    #OUTPUT: Ground measurement data frame

    query = 'SELECT timestamp, site_id, crack_id, meas FROM senslopedb.gndmeas '
    if not start:
        start = '2010-01-01'
    query = query + 'WHERE timestamp > "{}"'.format(start)
    
    if end:
        query = query + ' AND timestamp <= "{}"'.format(end)
    if site != None:
        query = query + ' AND site_id = "{}"'.format(site)
    
    return GetDBDataFrame(query)
    
def crack_eval(df,out_folder,end):
    #INPUT: df containing crack parameters
    #OUTPUT: crack alert according to protocol table

    #Impose the validity of the groundmeasurement
    out_df = pd.Series()
    df = df[df.timestamp <= end]
    df.sort_values('timestamp',inplace = True)
    try:
        if RoundTime(end) != RoundTime(df.timestamp.iloc[-1]):
            crack_alert = 'nd'
        else:
            #Obtain the time difference and displacement between the latest values (Return l0 if only one value is present)
            if len(df) >= 2:
                time_delta = (df.timestamp.iloc[-1]  - df.timestamp.iloc[-2]) / np.timedelta64(1,'D')
                abs_disp = np.abs(df.meas.iloc[-1]-df.meas.iloc[-2])
                cur_vel = abs_disp / time_delta
                crack_alert = 'nd'    
                
                #1cm Reliability Cap
                if abs_disp < 1:
                    crack_alert = 'l0'
                else:
                    #Based on alert table (convert velocity to cm/hour)
                    cur_vel = cur_vel/24.
                    if cur_vel >= 1.8:
                        crack_alert = 'l3'
                    elif cur_vel >= 0.25:
                        crack_alert = 'l2'
                    else:
                        crack_alert = 'l0'
                    #Perform p value computation for specific crack
#                    if abs_disp == 1:
#                        if len(df) >= 4:
#                            #get the last 4 data values for the current feature
#                            last_cur_feature_measure = df.tail(4).meas.values
#                            last_cur_feature_time = (df.timestamp.tail(4).values - df.timestamp.values[0])/np.timedelta64(1,'D')
#                
#                            #perform linear regression to get p value
#                            m, b, r, p, std = stats.linregress(last_cur_feature_time,last_cur_feature_measure)
#                            #^&*()
#                            print p
#                            
#                            #Evaluate p value
#                            if p > 0.05:
#                                crack_alert = 'l0p'
                                
                    #Perform Trending Test if alert is not L0
                    if (crack_alert != 'l0' and crack_alert != 'l0p'):
                        trend_alert = check_trending(df,out_folder,plot = False)
                        if (trend_alert != 'Legit' and crack_alert != 'l3'):
                            crack_alert = 'l0t'
                
                
            else:
                crack_alert = 'l0'
        

    except:
        print 'Timestamp error for '+' '.join(list(np.concatenate((df.site_id.values,df.crack_id.values))))
        crack_alert = 'nd'
    
    try:
        abs_disp = np.abs(df.meas.iloc[-1]-df.meas.iloc[-2])
        time_delta = (df.timestamp.iloc[-1]  - df.timestamp.iloc[-2]) / np.timedelta64(1,'h')
    except:
        abs_disp = None
        time_delta = None
            
    out_df['crack_alerts'] = crack_alert
    out_df['displacement'] = abs_disp
    out_df['time_delta'] = time_delta
    return out_df

def site_eval(df):
    #INPUT: Dataframe containing crack alerts
    #OUTPUT: Site alert based on the higher perceived risk from the crack alerts, list of cracks that exhibited l2 or l3 alerts, and timestamp

    crack_alerts = df.crack_alerts.values
    if 'l3' in crack_alerts:
        site_alert = 'l3'
    elif 'l2' in crack_alerts:
        site_alert = 'l2'
    elif 'l0t' in crack_alerts:
        site_alert = 'l0t'
    elif 'l0p' in crack_alerts:
        site_alert = 'l0p'
    elif 'l0' in crack_alerts:
        site_alert = 'l0'
    else:
        site_alert = 'nd'
    
    #Determine which crack has an l2 or l3 alert
    mask = np.logical_or(np.logical_or(crack_alerts == 'l3', crack_alerts == 'l2'),crack_alerts == 'l0t')
    cracks_to_check = df.crack_id.values[mask]

    return pd.Series([site_alert,', '.join(list(cracks_to_check))], index = ['site_alert','cracks_to_check'])

def PlotSite(df,tsn,print_out_path):
    cracks = df.groupby('crack_id')
    site_name = ''.join(list(np.unique(df.site_id.values)))
    plt.figure(figsize = (12,9))
    cracks.agg(PlotCrack)
    plt.xlabel('Timestamp', fontsize = 15)
    plt.ylabel('Displacement (cm)', fontsize = 15)
    plt.suptitle('{} Ground Measurements for {}'.format(site_name.upper(),pd.to_datetime(df.timestamp.values[-1]).strftime('%b %d, %Y %H:%M')),fontsize = 18)
    plt.legend(loc='upper left',fancybox = True, framealpha = 0.5)
    plt.grid(True)
    plt.xticks(rotation = 45)
    plt.savefig(print_out_path+'surficial_'+tsn+'_'+site_name,dpi=160, facecolor='w', edgecolor='w',orientation='landscape',mode='w',bbox_inches = 'tight')
    plt.close()

    
def PlotCrack(df):
    df.sort_values('timestamp',inplace = True)
    disp = df.meas.values
    time = df.timestamp.values
    crack_name = ''.join(list(np.unique(df.crack_id.values)))
    markers = ['x','d','+','s','*']
    plt.plot(time,disp,label = crack_name,marker = markers[df.index[0]%len(markers)])

def alert_toDB(df,end):
    
    query = "SELECT timestamp, site, source, alert FROM senslopedb.%s WHERE site = '%s' and source = 'ground' AND updateTS <= '%s' ORDER BY timestamp DESC LIMIT 1" %('site_level_alert', df.site.values[0], end)
    
    df2 = GetDBDataFrame(query)
    try:
        if len(df2) == 0 or ((df2.alert.values[0] != df.alert.values[0]) and (df2.timestamp.values[0] != df.timestamp.values[0])):
            engine = create_engine('mysql://'+Userdb+':'+Passdb+'@'+Hostdb+':3306/'+Namedb)
            df['updateTS'] = end
            df.to_sql(name = 'site_level_alert', con = engine, if_exists = 'append', schema = Namedb, index = False)
        elif (df2.timestamp.values[0] == df.timestamp.values[0]) and (df2.alert.values[0] != df.alert.values[0]):
            db, cur = SenslopeDBConnect(Namedb)
            query = "UPDATE senslopedb.%s SET updateTS='%s', alert='%s' WHERE site = '%s' and source = 'ground' and alert = '%s' and timestamp = '%s'" %('site_level_alert', pd.to_datetime(str(end)), df.alert.values[0], df2.site.values[0], df2.alert.values[0], pd.to_datetime(str(df2.timestamp.values[0])))
            cur.execute(query)
            db.commit()
            db.close()
        elif df2.alert.values[0] == df.alert.values[0]:
            engine = create_engine('mysql://'+Userdb+':'+Passdb+'@'+Hostdb+':3306/'+Namedb)
            df['updateTS'] = end
            df.to_sql(name = 'site_level_alert', con = engine, if_exists = 'append', schema = Namedb, index = False)
    except:
        print "Cannot write to db {}".format(df.site.values[0])

def moving_average(series,sigma = 3):
    b = gaussian(39,sigma)
    average = filters.convolve1d(series,b/b.sum())
    var = filters.convolve1d(np.power(series-average,2),b/b.sum())
    return average,var

def check_trending(df,out_folder,plot = False):
    ##### Get the data from the crack dataframe    
    cur_t = (df.timestamp.values - df.timestamp.values[0])/np.timedelta64(1,'D')
    cur_x = df.meas.values
    
    ##### Interpolate the last 10 data points
    _,var = moving_average(cur_x)
    sp = UnivariateSpline(cur_t,cur_x,w=1/np.sqrt(var))
    
    t_n = np.linspace(cur_t[0],cur_t[-1],1000)
    x_n = sp(t_n)
    v_n = sp.derivative(n=1)(t_n)
    a_n = sp.derivative(n=2)(t_n)
    
    v_s = abs(sp.derivative(n=1)(cur_t))
    a_s = abs(sp.derivative(n=2)(cur_t))
    
    
    ##### Federico et al. constants    
    slope = 1.49905955613175
    intercept = -3.00263765777028
    t_crit = 4.53047399738543
    var_v_log = 215.515369339559
    v_log_mean = 2.232839766
    sum_res_square = 49.8880017417971
    n = 30.
    
    ##### Trending Alert Evaluation
    cur_v = v_s[-1]
    cur_a = a_s[-1]
    delta = t_crit*np.sqrt(1/(n-2)*sum_res_square*(1/n + (np.log(cur_v) - v_log_mean)**2/var_v_log))
    
    log_a_t = slope * np.log(cur_v) + intercept
    log_a_t_up = log_a_t + delta
    log_a_t_down = log_a_t - delta
    
    a_t_up = np.e**log_a_t_up
    a_t_down = np.e**log_a_t_down
    
    ##### Plot points in the confidence interval envelope
    if plot == True:
        ##### Plotting Colors
        tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),    
                     (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),    
                     (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),    
                     (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),    
                     (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]
        
        for i in range(len(tableau20)):    
            r, g, b = tableau20[i]    
            tableau20[i] = (r / 255., g / 255., b / 255.)
        #################
        
        v_theo = np.linspace(min(v_s),max(v_s),10000)
        uncertainty = t_crit*np.sqrt(1/(n-2)*sum_res_square*(1/n + (np.log(v_theo) - v_log_mean)**2/var_v_log))
        
        log_a_theo = slope * np.log(v_theo) + intercept
        log_a_theo_up = log_a_theo + uncertainty
        log_a_theo_down = log_a_theo - uncertainty
        
        a_theo = np.e**log_a_theo
        a_theo_up = np.e**log_a_theo_up
        a_theo_down = np.e**log_a_theo_down
        
        fig = plt.figure()
        fig.set_size_inches(15,8)
        fig.suptitle('{} Crack {} {}'.format(str(df.site_id.values[0]).upper(),str(df.crack_id.values[0]).title(),pd.to_datetime(df.timestamp.values[-1]).strftime("%b %d, %Y %H:%M")))
        ax1 = fig.add_subplot(121)
        ax1.get_xaxis().tick_bottom()    
        ax1.get_yaxis().tick_left()
        ax1.grid()
        l1 = ax1.plot(v_theo,a_theo,c = tableau20[0],label = 'Fukuzono (1985)')
        ax1.plot(v_theo,a_theo_up,'--',c = tableau20[0])
        ax1.plot(v_theo,a_theo_down,'--', c = tableau20[0])
        ax1.plot(v_s,a_s,c = tableau20[10])
        l2 = ax1.plot(v_s[:-1],a_s[:-1],'o',c = tableau20[19],label = 'Previous')
        l3 = ax1.plot(v_s[-1],a_s[-1],'*',c = tableau20[6],label = 'Current')

        
        lns = l1 + l2 + l3
        labs = [l.get_label() for l in lns]
        ax1.legend(lns,labs,loc = 'upper left',fancybox = True, framealpha = 0.5)        
        
        ax1.set_xlabel('velocity (cm/day)')
        ax1.set_ylabel('acceleration (cm/day$^2$)')
        ax1.set_xscale('log')
        ax1.set_yscale('log')
        
        ax2 = fig.add_subplot(222)
        ax2.grid()
        ax2.plot(cur_t,cur_x,'.',c = tableau20[0],label = 'Data')
        ax2.plot(t_n,x_n,c = tableau20[12],label = 'Interpolation')
        ax2.legend(loc = 'upper left',fancybox = True, framealpha = 0.5)
        ax2.set_ylabel('disp (meters)')
        
        ax3 = fig.add_subplot(224, sharex = ax2)
        ax3.grid()
        ax3.plot(t_n,v_n, color = tableau20[4],label = 'Velocity')
        ax3.set_ylabel('velocity (cm/day)')
        ax3.set_xlabel('time (days)')
        ax3.legend(loc = 'upper left',fancybox = True, framealpha = 0.5)
        
        ax4 = ax3.twinx()
        ax4.plot(t_n,a_n,'-r',label = 'Acceleration')
        ax4.set_ylabel('acceleration (m/day$^2$)')
        ax4.legend(loc = 'upper right',fancybox = True, framealpha = 0.5)

        tsn = pd.to_datetime(df.timestamp.values[-1]).strftime("%Y-%m-%d_%H-%M-%S")
        out_filename = out_folder + '{} {} {}'.format(tsn,str(df.site_id.values[0]),str(df.crack_id.values[0]))
        plt.savefig(out_filename,facecolor='w', edgecolor='w',orientation='landscape',mode='w',bbox_inches = 'tight')
        
    if (cur_a <= a_t_up and cur_a >= a_t_down):
        #Reject alert if v and a have opposite signs
        if v_n[-1]*a_n[-1] >= 0:
            return 'Legit'
        else:
            return 'Reject'
    else:
        return 'Reject'
    
def GetPreviousAlert(end):
    try:
        query = 'SELECT * FROM senslopedb.gndmeas_new_alerts WHERE timestamp = "{}"'.format(end)
        df = GetDBDataFrame(query)
    except:
        df = pd.DataFrame(columns = ['timestamp','site','alert','cracks'])
    return df

def GetPreviousAlertNewDB(end):
    try:
        query = 'SELECT * FROM senslopedb.marker_alerts WHERE ts = "{}"'.format(end)
        df = GetDBDataFrame(query)
    except:
        df = pd.DataFrame(columns = ['ts','site_code','marker_name','displacement','time_delta','alert'])
    return df


def FixMesData(df):
    if df.site_id.values[0] == 'mes':
        if df.crack_id.values[0] in ['A','B','C','D','E','F']:
            df.replace(to_replace = {'site_id':{'mes':'msl'}},inplace = True)
        else:
            df.replace(to_replace = {'site_id':{'mes':'msu'}},inplace = True)
    
    return df

def FixSiteCode(df):
    df.replace(to_replace = {'site_id':{'bto':'bat','png':'pan','mng':'man','jor':'pob'}},inplace = True)
    return df
    
def del_data(df):
    #INPUT: Data frame of site and timestamp by groupby
    #Deletes the row at gndmeas_alerts table of [site] at time [end]            
    db, cur = SenslopeDBConnect(Namedb)
    query = "DELETE FROM senslopedb.gndmeas_new_alerts WHERE timestamp = '{}' AND site = '{}'".format(pd.to_datetime(str(df.timestamp.values[0])),str(df.site.values[0]))
    cur.execute(query)
    db.commit()

    try:
        query = "SELECT MAX(ma_id) FROM marker_alerts"
        max_id = GetDBDataFrame(query)['MAX(ma_id)'].values[0]
        query = "ALTER TABLE marker_alerts AUTO_INCREMENT = {}".format(max_id)
        cur.execute(query)
        db.commit()
    except:
        db.close()

def del_new_db_data(df):
    #INPUT: Data frame of site and timestamp by groupby
    #Deletes the row at gndmeas_alerts table of [site] at time [end]            
    db, cur = SenslopeDBConnect(Namedb)
    query = "DELETE FROM senslopedb.marker_alerts WHERE ts = '{}' AND site_code = '{}' AND marker_name = '{}'".format(pd.to_datetime(str(df.ts.values[0])),str(df.site_code.values[0]),str(df.marker_name.values[0]))
    cur.execute(query)
    db.commit()
    db.close()


def GenerateGroundDataAlert(site=None,end=None):
    if site == None and end == None:
        site, end = sys.argv[1].lower()[:3],sys.argv[2].lower()    
    
    monitoring_out_path = output_file_path(site,'surficial',end = pd.to_datetime(end))['monitoring_output']
    print_out_path = monitoring_out_path
    print_out_path2 = monitoring_out_path + 'TrendingPlots/'
    for path in [print_out_path,print_out_path2]:
        if not os.path.exists(path):
            os.makedirs(path)

    #Set the monitoring window
#    if end == None:
#        roll_window_numpts, end, start, offsetstart, monwin = set_monitoring_window(roll_window_length,data_dt,rt_window_length,num_roll_window_ops)
    
#    Use this so set the end time    
#    end = datetime(2016,8,12,11,30)

############################################ MAIN ############################################

    #Step 1: Get the ground data from local database 
    df = get_latest_ground_df2(site,end)
    end = pd.to_datetime(end)
    #lower caps all site_id names while cracks should be in title form
    df['site_id'] = map(lambda x: x.lower(),df['site_id'])
    df['crack_id'] = map(lambda x: x.title(),df['crack_id'])

    #Apply mes data fix
    df = df.groupby(['site_id','crack_id']).apply(FixMesData)    
    #Fix site code
    df = FixSiteCode(df)
    #Step 2: Evaluate the alerts per crack
    crack_alerts = df.groupby(['site_id','crack_id']).apply(crack_eval,print_out_path2,end).reset_index()
    
    #Step 3: Evaluate alerts per site
    site_alerts = crack_alerts.groupby(['site_id']).apply(site_eval).reset_index()    
    
    #Step 4: Include the timestamp of the run, create release ready data frame
    ground_alert_release = site_alerts
    ground_alert_release['timestamp'] = end
    ground_alert_release.columns = ['site','alert','cracks','timestamp']
    ground_alert_release = ground_alert_release.set_index(['timestamp'])
    
    print ground_alert_release
    
    #### Set df for new db release
    new_db_release = crack_alerts[crack_alerts.crack_alerts != 'nd']
    new_db_release['ts'] = end    
    new_db_release.columns = ['site_code','marker_name','alert','displacement','time_delta','ts']
    new_db_release.set_index(['ts'],inplace = True)
    #Step 5: Upload the results to the gndmeas_alerts database
    
    ##Get the previous alert database
    ground_alert_previous = GetPreviousAlert(end)
    uptoDB_gndmeas_alerts(ground_alert_release,ground_alert_previous)
    
    marker_alerts_previous = GetPreviousAlertNewDB(end)
    uptoDB_marker_alerts(new_db_release,marker_alerts_previous)
    
    
    
    #Step 6: Upload to site_level_alert        
    ground_site_level = ground_alert_release.reset_index()
    ground_site_level['source'] = 'ground'
    
    df_for_db = ground_site_level[['timestamp','site','source','alert']]    
    df_for_db.dropna()
    
    site_DBdf = df_for_db.groupby('site')
    site_DBdf.apply(alert_toDB,end)    
    
    
#    #Step 7: Displacement plot for each crack and site for the last 30 days
#    start = pd.to_datetime(end) - timedelta(days = 30)
#    ground_data_to_plot = get_ground_df(start,end,site)
#    ground_data_to_plot['site_id'] = map(lambda x: x.lower(),ground_data_to_plot['site_id'])
#    ground_data_to_plot['crack_id'] = map(lambda x: x.title(),ground_data_to_plot['crack_id'])
#    
#    tsn=pd.to_datetime(end).strftime("%Y-%m-%d_%H-%M-%S")
#    site_data_to_plot = ground_data_to_plot.groupby('site_id')
#    site_data_to_plot.apply(PlotSite,tsn,print_out_path)

    #Step 7: Displacement plot for each crack and site for last 10 data points of recent cracks with measurement.
#    ground_data_to_plot = get_ground_data_with_recent_cracks(site,end,10)
#    ground_data_to_plot['site_id'] = map(lambda x: x.lower(),ground_data_to_plot['site_id'])
#    ground_data_to_plot['crack_id'] = map(lambda x: x.title(),ground_data_to_plot['crack_id'])
#    
#    tsn=pd.to_datetime(end).strftime("%Y-%m-%d_%H-%M-%S")
#    site_data_to_plot = ground_data_to_plot.groupby('site_id')
#    site_data_to_plot.apply(PlotSite,tsn,print_out_path)
#
#    ### Event folder plotting
#    if max(map(lambda x:x in ('l2','l0t','l3'),new_db_release.alert.values)*1):
#        positive_trigger = True
#    else:
#        positive_trigger = False
#        
#    event_out_path = output_file_path(site,'surficial',end = pd.to_datetime(end),positive_trigger = positive_trigger)['event']
#
#    #### Plot to event folder file if site is currently at event monitoring or positive trigger
#    if event_out_path:
#        site_data_to_plot.apply(PlotSite,tsn,event_out_path)
#        crack_alerts = df.groupby(['site_id','crack_id']).apply(crack_eval,event_out_path,end).reset_index()
#    
#    
#    end_time = datetime.now()
#    print "time = ",end_time-start_time

def PlotForEvent(site,end,window = 30):
    event_out_path = output_file_path(site,'surficial',monitoring_end = True,end = pd.to_datetime(end))['event']
    print event_out_path
    if event_out_path:
        start = pd.to_datetime(end) - timedelta(days = 30)
    
        ground_data_to_plot = get_ground_df(start,end,site)
        ground_data_to_plot['site_id'] = map(lambda x: x.lower(),ground_data_to_plot['site_id'])
        ground_data_to_plot['crack_id'] = map(lambda x: x.title(),ground_data_to_plot['crack_id'])
        
        tsn=pd.to_datetime(end).strftime("%Y-%m-%d_%H-%M-%S")
        site_data_to_plot = ground_data_to_plot.groupby('site_id')
        site_data_to_plot.apply(PlotSite,tsn,event_out_path)

def PlotMarkerData(site,end,window = 30):
    '''
    Plot the marker data of specified site, end timestamp with the given window
    
    Parameters
    -----------------
    site - str
        site code of the site of interest
    end - string (YYYY-MM-DD HH:MM)
        end timestamp
    
    Optional Parameters
    -----------------
    window - int (default - 30)
        time window of the plot
    
    Returns
    ---------------
    None
    
    '''
    monitoring_out_path = output_file_path(site,'surficial',end = pd.to_datetime(end))['monitoring_output']
    print_out_path = monitoring_out_path
    print_out_path2 = monitoring_out_path + 'TrendingPlots/'
    for path in [print_out_path,print_out_path2]:
        if not os.path.exists(path):
            os.makedirs(path)

    
    start = pd.to_datetime(end) - timedelta(days = 30)
    ground_data_to_plot = get_ground_df(start,end,site)
    ground_data_to_plot['site_id'] = map(lambda x: x.lower(),ground_data_to_plot['site_id'])
    ground_data_to_plot['crack_id'] = map(lambda x: x.title(),ground_data_to_plot['crack_id'])
    
    tsn=pd.to_datetime(end).strftime("%Y-%m-%d_%H-%M-%S")
    site_data_to_plot = ground_data_to_plot.groupby('site_id')
    site_data_to_plot.apply(PlotSite,tsn,print_out_path)

def PlotTrendingAnalysis(site,marker,end):
    
    monitoring_out_path = output_file_path(site,'surficial',end = pd.to_datetime(end))['monitoring_output']
    print_out_path = monitoring_out_path
    print_out_path2 = monitoring_out_path + 'TrendingPlots/'
    for path in [print_out_path,print_out_path2]:
        if not os.path.exists(path):
            os.makedirs(path)
    
    #### Get marker data
    df = get_latest_marker_data(site,marker,end)
    
    ##### Get the data from the crack dataframe    
    cur_t = (df.timestamp.values - df.timestamp.values[0])/np.timedelta64(1,'D')
    cur_x = df.meas.values
    
    ##### Interpolate the last 10 data points
    _,var = moving_average(cur_x)
    sp = UnivariateSpline(cur_t,cur_x,w=1/np.sqrt(var))
    
    t_n = np.linspace(cur_t[0],cur_t[-1],1000)
    x_n = sp(t_n)
    v_n = sp.derivative(n=1)(t_n)
    a_n = sp.derivative(n=2)(t_n)
    
    v_s = abs(sp.derivative(n=1)(cur_t))
    a_s = abs(sp.derivative(n=2)(cur_t))
    
    
    ##### Federico et al. constants    
    slope = 1.49905955613175
    intercept = -3.00263765777028
    t_crit = 4.53047399738543
    var_v_log = 215.515369339559
    v_log_mean = 2.232839766
    sum_res_square = 49.8880017417971
    n = 30.
            
    ##### Plotting Colors
    tableau20 = [(31, 119, 180), (174, 199, 232), (255, 127, 14), (255, 187, 120),    
                 (44, 160, 44), (152, 223, 138), (214, 39, 40), (255, 152, 150),    
                 (148, 103, 189), (197, 176, 213), (140, 86, 75), (196, 156, 148),    
                 (227, 119, 194), (247, 182, 210), (127, 127, 127), (199, 199, 199),    
                 (188, 189, 34), (219, 219, 141), (23, 190, 207), (158, 218, 229)]
    
    for i in range(len(tableau20)):    
        r, g, b = tableau20[i]    
        tableau20[i] = (r / 255., g / 255., b / 255.)
    #################
    
    v_theo = np.linspace(min(v_s),max(v_s),10000)
    uncertainty = t_crit*np.sqrt(1/(n-2)*sum_res_square*(1/n + (np.log(v_theo) - v_log_mean)**2/var_v_log))
    
    log_a_theo = slope * np.log(v_theo) + intercept
    log_a_theo_up = log_a_theo + uncertainty
    log_a_theo_down = log_a_theo - uncertainty
    
    a_theo = np.e**log_a_theo
    a_theo_up = np.e**log_a_theo_up
    a_theo_down = np.e**log_a_theo_down
    
    fig = plt.figure()
    fig.set_size_inches(15,8)
    fig.suptitle('{} Crack {} {}'.format(str(df.site_id.values[0]).upper(),str(df.crack_id.values[0]).title(),pd.to_datetime(df.timestamp.values[-1]).strftime("%b %d, %Y %H:%M")))
    ax1 = fig.add_subplot(121)
    ax1.get_xaxis().tick_bottom()    
    ax1.get_yaxis().tick_left()
    ax1.grid()
    l1 = ax1.plot(v_theo,a_theo,c = tableau20[0],label = 'Fukuzono (1985)')
    ax1.plot(v_theo,a_theo_up,'--',c = tableau20[0])
    ax1.plot(v_theo,a_theo_down,'--', c = tableau20[0])
    ax1.plot(v_s,a_s,c = tableau20[10])
    l2 = ax1.plot(v_s[:-1],a_s[:-1],'o',c = tableau20[19],label = 'Previous')
    l3 = ax1.plot(v_s[-1],a_s[-1],'*',c = tableau20[6],label = 'Current')

    
    lns = l1 + l2 + l3
    labs = [l.get_label() for l in lns]
    ax1.legend(lns,labs,loc = 'upper left',fancybox = True, framealpha = 0.5)        
    
    ax1.set_xlabel('velocity (cm/day)')
    ax1.set_ylabel('acceleration (cm/day$^2$)')
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    
    ax2 = fig.add_subplot(222)
    ax2.grid()
    ax2.plot(cur_t,cur_x,'.',c = tableau20[0],label = 'Data')
    ax2.plot(t_n,x_n,c = tableau20[12],label = 'Interpolation')
    ax2.legend(loc = 'upper left',fancybox = True, framealpha = 0.5)
    ax2.set_ylabel('disp (meters)')
    
    ax3 = fig.add_subplot(224, sharex = ax2)
    ax3.grid()
    ax3.plot(t_n,v_n, color = tableau20[4],label = 'Velocity')
    ax3.set_ylabel('velocity (cm/day)')
    ax3.set_xlabel('time (days)')
    ax3.legend(loc = 'upper left',fancybox = True, framealpha = 0.5)
    
    ax4 = ax3.twinx()
    ax4.plot(t_n,a_n,'-r',label = 'Acceleration')
    ax4.set_ylabel('acceleration (m/day$^2$)')
    ax4.legend(loc = 'upper right',fancybox = True, framealpha = 0.5)

    tsn = pd.to_datetime(df.timestamp.values[-1]).strftime("%Y-%m-%d_%H-%M-%S")
    out_filename = print_out_path2 + '{} {} {}'.format(tsn,str(df.site_id.values[0]),str(df.crack_id.values[0]))
    plt.savefig(out_filename,facecolor='w', edgecolor='w',orientation='landscape',mode='w',bbox_inches = 'tight')
    


################## #Stand by Functionalities

#    if PrintGAlert:
#        #Creating Monitoring Output directory if it doesn't exist
#        print_out_path = out_path + output_file_path
#        print print_out_path        
#        if not os.path.exists(print_out_path):
#            os.makedirs(print_out_path)
#        
#        print "Ground measurement report as of {}".format(end)
#        print "{:5}: {:5}; Last Date of Measurement; Features to Check".format('Site','Alert')
#        i = 0
#        for site, galert in ground_alert_release:
#            print "{:5}: {:5}; {:24}; {}".format(site,galert[0],str(galert[1]),galert[2])
#            i += 1
#        
#
#        with open (print_out_path+'groundalert.txt', 'w') as t:
#            i = 0
#            t.write("Ground measurement report as of {}".format(end)+'\n')
#            t.write("{:5}: {:5}; Last Date of Measurement; Features to Check".format('Site','Alert')+'\n')
#            for site, galert in ground_alert_release:
#                t.write ("{:5}: {:5}; {:25}; {}".format(site,galert[0],str(galert[1]),galert[2])+'\n')
#                i += 1

#    if PrintJSON:        
#        #converting the data frame to JSON format
#        dfajson = ground_alert_release.to_json(orient="records",date_format='iso')
#        
#        #ensuring proper datetime format
#        i = 0
#        while i <= len(dfajson):
#            if dfajson[i:i+9] == 'timestamp':
#                dfajson = dfajson[:i] + dfajson[i:i+36].replace("T"," ").replace("Z","").replace(".000","") + dfajson[i+36:]
#                i += 1
#            else:
#                i += 1
#        print dfajson
#    print dfa[['alert_timestamp','site_id','g alert','features to check']].set_index(['alert_timestamp'])
#    uptoDB(dfa[['alert_timestamp','site_id','g alert','features to check']].set_index(['alert_timestamp']))
