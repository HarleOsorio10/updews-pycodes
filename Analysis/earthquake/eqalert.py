##### IMPORTANT matplotlib declarations must always be FIRST to make sure that matplotlib works with cron-based automation
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
plt.ioff()


import numpy as np
import pandas as pd
import sys
from datetime import datetime
from sqlalchemy import create_engine
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
import os


path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if not path in sys.path:
    sys.path.insert(1,path)
del path   

import querydb as qdb
import configfileio as cfg

config = cfg.config()


def plot_basemap(ax,mag,eq_lat,eq_lon,plotsites,critdist):
    latmin = plotsites.latitude.min()-0.2
    latmax = plotsites.latitude.max()+0.2
    lonmin = plotsites.longitude.min()-0.2
    lonmax = plotsites.longitude.max()+0.2
    
    m = Basemap(llcrnrlon=lonmin,llcrnrlat=latmin,urcrnrlon=lonmax,urcrnrlat=latmax,
            resolution='f',projection='merc',lon_0=(lonmin+lonmax)/2,lat_0=
            (latmin+latmax)/2            
            )
            
    m.drawcoastlines()
    m.fillcontinents(color='coral',lake_color='aqua')
    
    # draw parallels and meridians.
    del_lat = latmax - latmin
    del_lon = lonmax - lonmin
    m.drawparallels(np.arange(latmin,latmax,del_lat/4),labels=[True,True,False,False])
    merids=m.drawmeridians(np.arange(lonmin,lonmax,del_lon/4),labels=[False,False,False,True])
    
    for x in merids:
        try:
            merids[x][1][0].set_rotation(10)
        except:
            pass
        
    m.drawmapboundary(fill_color='aqua')
    plt.title("Earthquake Map for Event\n Mag %s, %sN, %sE" % (str(mag),str(eq_lat),str(eq_lon)))
    
    return m,ax
    
def plot_eq(m,mag,eq_lat,eq_lon,ax):
    critdist = get_crit_dist(mag)    
    x,y = m(eq_lon, eq_lat)
    m.scatter(x,y,c='red',marker='o',zorder=10,label='earthquake')
    m.tissot(eq_lon,eq_lat,get_radius(critdist),256,zorder=5,color='red',alpha=0.4)

def get_radius(km):
    return float(np.rad2deg(km/6371.))    

def get_crit_dist(mag):
    return (29.027 * (mag**2)) - (251.89*mag) + 547.97

def get_distance_to_eq(df,eq_lat,eq_lon):#,eq_lat,eq_lon):   
    dlon=eq_lon-df.longitude
    dlat=eq_lat-df.latitude
    dlon=np.radians(dlon)
    dlat=np.radians(dlat)
    a=(np.sin(dlat/2))**2 + ( np.cos(np.radians(eq_lat)) * np.cos(np.radians(df.latitude)) * (np.sin(dlon/2))**2 )
    c= 2 * np.arctan2(np.sqrt(a),np.sqrt(1-a))
    d= 6371 * c
    
    df['dist'] = d    
    
    return df

def get_unprocessed():
    query = """ select * from %s.earthquake_events where processed=0 """ % (qdb.Namedb)
    dfeq =  qdb.get_db_dataframe(query)
    dfeq = dfeq.set_index('eq_id')
#    dfeq = dfeq[dfeq.issuer != 'CRB']
    return dfeq

def get_sites():
    query = """SELECT s.site_id, site_code, latitude, longitude FROM """
    query += """%s.loggers as l """ % (qdb.Namedb)
    query += """left join """
    query += """%s.sites as s """ % (qdb.Namedb)
    query += """on s.site_id = l.site_id """
      
    df = qdb.get_db_dataframe(query)
    df = df.drop_duplicates('site_id',keep='last').dropna()
    return df
    
def up_to_eq_alerts(alerts,name):
    engine=create_engine('mysql://root:senslope@192.168.150.128:3306/senslopedb')
    alerts.to_sql(name = name, con = engine, if_exists = 'append', schema = qdb.Namedb, index = False)

def up_to_op_trig(op_trig,name):
    engine=create_engine('mysql://root:senslope@192.168.150.128:3306/senslopedb')
    op_trig.to_sql(name = name, con = engine, if_exists = 'append', schema = qdb.Namedb, index = False)

       
def get_alert_symbol():
    query = 'SELECT trigger_sym_id FROM %s.operational_trigger_symbols' % (qdb.Namedb)
    query += ''' WHERE trigger_source = 'earthquake' '''
    sym = qdb.get_db_dataframe(query)
    return sym.trigger_sym_id[0]

def create_table():
    query = ''
    query += 'CREATE TABLE `senslopedb`.`earthquake_alerts` ('
    query += '`ea_id` SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,'
    query += '`eq_id` INT(10) UNSIGNED NOT NULL,'
    query += '`site_id` TINYINT(3) UNSIGNED NOT NULL,'
    query += '`distance` DECIMAL(5,3) NULL,'
    query += 'PRIMARY KEY (`ea_id`),'
    query += 'UNIQUE INDEX `uq_earthquake_alerts` (`eq_id` ASC,`site_id` ASC),'
    query += 'INDEX `fk_earthquake_alerts_sites_idx` (`site_id` ASC),'
    query += 'INDEX `fk_earthquake_alerts_earthquake_events_idx` (`eq_id` ASC),'
    query += 'CONSTRAINT `fk_earthquake_alerts_sites`'
    query += '  FOREIGN KEY (`site_id`)'
    query += '  REFERENCES `senslopedb`.`sites` (`site_id`)'
    query += '  ON DELETE NO ACTION'
    query += '  ON UPDATE CASCADE,'
    query += 'CONSTRAINT `fk_earthquake_alerts_earthquake_events`'
    query += '  FOREIGN KEY (`eq_id`)'
    query += '  REFERENCES `senslopedb`.`earthquake_events` (`eq_id`)'
    query += ' ON DELETE NO ACTION'
    query += ' ON UPDATE CASCADE);'
    return query


def plot_map(output_path,sites,crits,mag, eq_lat, eq_lon,ts,critdist):
    plotsites = sites[sites.dist <= critdist*3]
    plotsites = plotsites.append([{'latitude':eq_lat,'longitude':eq_lon,'site_code':''}])
    
    lats = pd.Series.tolist(plotsites.latitude)
    lons = pd.Series.tolist(plotsites.longitude)
    labels = pd.Series.tolist(plotsites.site_code)
    
    
    plotcrits = pd.merge(crits, plotsites, on=['site_id','site_code','latitude','longitude','dist'])
    critlats = pd.Series.tolist(plotcrits.latitude)
    critlons = pd.Series.tolist(plotcrits.longitude)
    
    #add duplicate kasi topak yung basemap for cases na 1 or 2 sites lang
    critlons.append(critlons[-1])
    critlats.append(critlats[-1])
    
    critlabels = pd.Series.tolist(plotcrits.site_code)
    
    
    fig,ax = plt.subplots(1)
    m,ax=plot_basemap(ax,mag,eq_lat,eq_lon,plotsites,critdist)
    plot_eq(m,mag,eq_lat,eq_lon,ax)
    
    try:
        m.plot(lons,lats,label='sites',marker='o',latlon=True,linewidth=0,color='yellow')
    
    except IndexError: #basemap has error when plotting exactly one or two items, duplicate an item to avoid
        lons.append(lons[-1])
        lats.append(lats[-1])
        m.plot(lons,lats,label='sites',marker='o',latlon=True,linewidth=0,color='yellow')
    
    try:
        m.plot(critlons,critlats,latlon=True,label='critical sites',markersize=12,linewidth=1, marker='^', color='red')
    
    except IndexError: #basemap has error when plotting exactly two items. duplicate last entry
        critlons.append(critlons[-1])
        critlats.append(critlats[-1])
        m.plot(critlons,critlats,latlon=True,label='critical sites',markersize=12,linewidth=1, marker='^', color='red')
    
    
    x,y = m(lons,lats)
    
    for n in range(len(plotsites)):
        try:
            ax.annotate(labels[n],xy=(x[n],y[n]),fontweight='bold',fontsize=12)
        except IndexError:
            pass
        
    plt.savefig(output_path+'eq_%s' % ts.strftime("%Y-%m-%d %H-%M-%S"))
    return 0

    
output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))

if not os.path.exists(output_path+config.io.eq_plots_path):
    os.makedirs(output_path+config.io.eq_plots_path)

output_path += config.io.eq_plots_path
events_table = 'earthquake_events'

eq_a = pd.DataFrame(columns=['site_id','eq_id','distance'])

############################ MAIN ############################

def main():
    dfeq = get_unprocessed()
    sym = get_alert_symbol()
    to_plot = 1
    
    for i in dfeq.index:
        cur = dfeq.loc[i]
        
        mag, eq_lat, eq_lon,ts = cur.magnitude, cur.latitude, cur.longitude,cur.ts
           
        
        critdist = get_crit_dist(mag)
    
        if False in np.isfinite([mag,eq_lat,eq_lon]): #has NaN value in mag, lat, or lon 
            query = """ update %s set processed = -1 where eq_id = %s """ % (events_table, i)
            qdb.execute_query(query)
            continue
         
        
        print mag
        if mag >=4:    
            sites = get_sites()
            dfg = sites.groupby('site_id')
            sites = dfg.apply(get_distance_to_eq,eq_lat=eq_lat,eq_lon=eq_lon)
            
            query = """update %s set processed = 1, critical_distance = %s where eq_id = %s""" % (events_table,critdist,i)
            qdb.execute_query(query) 
            
            #tanggal weird values
            sites = sites[sites.latitude>1]
            
            
            crits = sites[sites.dist<=critdist]
            
            if len(crits.site_id.values) > 0: #merong may trigger
                
                crits['ts']  = ts
                crits['source'] = 'earthquake'
                crits['trigger_sym_id'] = sym
                crits['ts_updated'] = ts       
                crits['eq_id'] = i
                crits['distance'] = critdist
            
            
            
                eq_a = crits[['eq_id','site_id','distance']]
                op_trig = crits[['ts','site_id','trigger_sym_id','ts_updated']]
         
                
            
                try:
                    up_to_op_trig(op_trig,'operational_triggers')
                    up_to_eq_alerts(eq_a,'earthquake_alerts')
                except:
                    pass
                
                query = """ update %s set processed = 1, critical_distance = %s where eq_id = %s """ % (events_table,critdist,i)
                qdb.execute_query(query)            
                
                if to_plot:
                    plot_map(output_path,sites,crits,mag, eq_lat, eq_lon,ts,critdist)
                    
            else:
                print "> No affected sites. "
                query = """ update %s set processed = 1 where eq_id = %s """ % (events_table,i)
                qdb.execute_query(query)       
        
        else:
            print '> Magnitude too small. '
            query = """ update %s set processed = 1 where eq_id = %s """ % (events_table,i)
            qdb.execute_query(query)  
            pass
    
    return 0

if __name__ == "__main__":
    main()
    print datetime.now()