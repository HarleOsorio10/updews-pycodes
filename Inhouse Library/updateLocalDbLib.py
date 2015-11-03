# -*- coding: utf-8 -*-
"""
Created on Tue Jun 02 10:20:04 2015

@author: chocolate server
"""

import urllib
import urllib2
import datetime
import time
import json
import pandas as pd
import MySQLdb, ConfigParser
from StringIO import StringIO
from MySQLdb import OperationalError
from pandas.io import sql
from pandas.io.json import json_normalize

dbname = "senslopedb"
dbhost = "127.0.0.1"
#dbuser = "root"
#dbpwd = "dyn4m1ght"
dbuser = "updews"
dbpwd = "october50sites"
entryLimit = 600

###############################################################################
# Read from Database
###############################################################################

def getLatestTimestamp(col):
    dbc = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpwd,db=dbname)
    cur = dbc.cursor()
    query = "select max(timestamp) from %s.%s" % (dbname, col)
    ret = 0
    try:
        a = cur.execute(query)
        ret = cur.fetchall()[0][0]
    except TypeError:
        print "Error"
        ret = 0
    finally:
        dbc.close()
        print ret
        return ret
        
def checkEntryExistence(table,col,value):
    dbc = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpwd,db=dbname)
    cur = dbc.cursor()
    query = "select %s from %s.%s where %s = '%s'" % (col,dbname,table,col,value)
    #print query
    ret = 0
    try:
        a = cur.execute(query)
        ret = cur.fetchall()[0][0]
    except TypeError:
        print "Error"
        ret = 0
    finally:
        dbc.close()
        return ret
    
###############################################################################
# Create Tables on Database    
###############################################################################
        
def createSensorTable(table,version):
    dbc = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpwd,db=dbname)
    cur = dbc.cursor()
    
    if version == 1:
        query = "CREATE TABLE `%s`.`%s` (`timestamp` DATETIME NOT NULL DEFAULT '0000-00-00 00:00:00',`id` INT(11) NOT NULL DEFAULT '0',`xvalue` INT(11) NULL DEFAULT NULL,`yvalue` INT(11) NULL DEFAULT NULL,`zvalue` INT(11) NULL DEFAULT NULL,`mvalue` INT(11) NULL DEFAULT NULL,PRIMARY KEY (`id`, `timestamp`)) ENGINE = InnoDB DEFAULT CHARACTER SET = latin1;" % (dbname,table)
    elif version == 2:
        query = "CREATE TABLE `%s`.`%s` (`timestamp` DATETIME NOT NULL DEFAULT '0000-00-00 00:00:00',`id` INT(11) NOT NULL DEFAULT '0',`msgid` SMALLINT(6) NOT NULL DEFAULT '0',`xvalue` INT(11) NULL DEFAULT NULL,`yvalue` INT(11) NULL DEFAULT NULL,`zvalue` INT(11) NULL DEFAULT NULL,`batt` DOUBLE NULL DEFAULT NULL, PRIMARY KEY (`id`, `msgid`,`timestamp`)) ENGINE = InnoDB DEFAULT CHARACTER SET = latin1;" % (dbname,table)
    #print query
    print "Created sensor table version %s: '%s'" % (version,table)
    ret = 0
    
    try:
        a = cur.execute(query)
        ret = cur.fetchall()[0][0]
    except TypeError:
        print "Error"
        ret = 0
    finally:
        dbc.close()
        return ret      
        
###############################################################################
# Truncate Tables on Database    
###############################################################################        
        
def truncateTable(col):
    dbc = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpwd,db=dbname)
    cur = dbc.cursor()
    query = "SET foreign_key_checks = 0; TRUNCATE TABLE %s.%s;" % (dbname, col)
    ret = 0
    try:
        a = cur.execute(query)
        ret = cur.fetchall()[0][0]
    except TypeError:
        print "Error"
        ret = 0
    finally:
        dbc.close()
        print ret
        return ret            
        
###############################################################################
# Download data from the dewslandslide web API        
###############################################################################        
        
def downloadLatestData(col,fromDate='',toDate=''):
    url = 'http://www.dewslandslide.com/ajax/getSenslopeData.php?db=%s&accelsite&site=%s&limit=%s&start=%s&end=%s' % (dbname,col,entryLimit,fromDate,toDate)
    print url
    print "Downloading", col, "data from", fromDate, "...",
    
    # comment out this part for direct (no proxy) connection
    # urllib2.install_opener(
        # urllib2.build_opener(
            # urllib2.ProxyHandler({'http': 'proxy.engg.upd.edu.ph:8080'})
        # )
    # )    
    
    try:
        f = urllib2.urlopen(url);
        s = f.read().strip()
        #print s
        conv = StringIO(s)
        df = pd.DataFrame.from_csv(conv, sep=',', parse_dates=False)
        print "downloadLatestData done"
        return df
    except urllib2.URLError:
        print "<urlopen error [Errno 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>"

def downloadFullSiteColumnTable():
    #url = 'http://localhost/temp/getSenslopeData.php?db=%s&sitecolumnjson' % (dbname)
    url = 'http://www.dewslandslide.com/ajax/getSenslopeData.php?db=%s&sitecolumnjson' % (dbname)  
    #url = 'http://www.dewslandslide.com'    
    print url
    
    try:
        jsonData = pd.read_json(url, orient='columns')
        df = pd.DataFrame(jsonData)
        df = df.set_index(['s_id'])
        print "downloadFullSiteColumnTable done" 
        #print df
    except urllib2.URLError:
        print "<urlopen error [Errno 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>"
        #return empty data frame
        return pd.DataFrame()
    
    except ValueError:
        print "No Data from web server. Table does not exist on web server"
        #return empty data frame
        return pd.DataFrame()
        
    return df
    
def downloadFullColumnPropsTable():
    #url = 'http://localhost/temp/getSenslopeData.php?db=%s&columninfojson' % (dbname)
    url = 'http://www.dewslandslide.com/ajax/getSenslopeData.php?db=%s&columninfojson' % (dbname)
    #url = 'http://www.dewslandslide.com'    
    print url
    
    try:
        jsonData = pd.read_json(url, orient='columns')
        df = pd.DataFrame(jsonData)
        df = df.set_index(['s_id'])
        print "downloadFullColumnPropsTable done" 
        print df
    except urllib2.URLError:
        print "<urlopen error [Errno 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>"
        #return empty data frame
        return pd.DataFrame()
    
    except ValueError:
        print "No Data from web server. Table does not exist on web server"
        #return empty data frame
        return pd.DataFrame()
        
    return df

def downloadSiteColumnData(col):
    url = 'http://localhost/temp/getSenslopeData.php?db=%s&singlesitecolumn&name=%s' % (dbname,col)
    #print url
    
    try:
        jsonData = pd.read_json(url, orient='columns')
        df = pd.DataFrame(jsonData)
        #df.columns = ['s_id','name','date_install','date_activation','lat','long','sitio','barangay','municipality','province','region','loc_desc','affected_households','installation_status','version']
        #df = df.set_index(['s_id'])
        #print df.iloc[0]['name']
        newSite = df.iloc[0]['name']
        version = df.iloc[0]['version']
        print "downloadSiteColumnData done" 
        
        exists = checkEntryExistence("site_column","name",newSite)
        if exists == 0:
            #create the new table
            print "%s site not found in site_column... adding it to table" % (newSite)
            createSensorTable(newSite,version)
        else:
            #create the new table
            print "%s site already exists in site_column" % (newSite)
            createSensorTable(newSite,version)

        #return df
    except urllib2.URLError:
        print "<urlopen error [Errno 10060] A connection attempt failed because the connected party did not properly respond after a period of time, or established connection failed because connected host has failed to respond>"
        return None
    
    except ValueError:
        print "No Data from web server. Table does not exist on web server"
        return None
        
    return True
   
###############################################################################
# Writes to Database
###############################################################################   
   
# Append Write
def writeDFtoLocalDB(col,df,fromDate='',numDays=30):
    dbc = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpwd,db=dbname)
    print "writing df to", col, "db",
    df.to_sql(con=dbc, name=col, if_exists='append', flavor='mysql')
    dbc.close()

    print "writeDFtoLocalDB done"   

# Overwrite (Used mostly on static info updating)
def overwriteDFtoLocalDB(col,df):   
    dbc = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpwd,db=dbname)
    print "writing df to", col, "db",

    try:
        df.to_sql(con=dbc, name=col, if_exists='replace', flavor='mysql')
        dbc.close()
    except OperationalError as e:
        if 'MySQL server has gone away' in str(e):
            print 'write failed...'
            time.sleep(3)
        else:
            raise e()

    print "overwriteDFtoLocalDB done"    

def writeAccelToLocalDB(col,df,fromDate='',numDays=30):
    dbc = MySQLdb.connect(host=dbhost,user=dbuser,passwd=dbpwd,db=dbname)
    print "writing df to", col, "db",

    try:
        df.to_sql(con=dbc, name=col, if_exists='append', flavor='mysql')
        dbc.close()
    except OperationalError as e:
        if 'MySQL server has gone away' in str(e):
            #limit the number of days to reduce size of update data
            print 'reconnecting and trying again...'
            
            date_1 = datetime.datetime.strptime(fromDate, "%Y-%m-%d %H:%M:%S")
            end_date = date_1 + datetime.timedelta(days=numDays)
            toDate = end_date.strftime("%Y-%m-%d %H:%M:%S")

            df = downloadLatestData(col,fromDate,toDate)
            writeAccelToLocalDB(col,df,fromDate,numDays/2)
            print e
            
            time.sleep(3)
        else:
            raise e()

    print "writeAccelToLocalDB done"

###############################################################################

#local file paths
cfg = ConfigParser.ConfigParser()
cfg.read('IO-config.txt')    

columnproperties_path = cfg.get('I/O','ColumnPropertiesPath')
purged_path = cfg.get('I/O','InputFilePath')
monitoring_path = cfg.get('I/O','MonitoringPath')
LastGoodData_path = cfg.get('I/O','LastGoodData')
proc_monitoring_path = cfg.get('I/O','OutputFilePathMonitoring2')

#file names
columnproperties_file = cfg.get('I/O','ColumnProperties')
purged_file = cfg.get('I/O','CSVFormat')
monitoring_file = cfg.get('I/O','CSVFormat')
LastGoodData_file = cfg.get('I/O','CSVFormat')
proc_monitoring_file = cfg.get('I/O','CSVFormat')

#file headers
columnproperties_headers = cfg.get('I/O','columnproperties_headers').split(',')
purged_file_headers = cfg.get('I/O','purged_file_headers').split(',')
monitoring_file_headers = cfg.get('I/O','monitoring_file_headers').split(',')
LastGoodData_file_headers = cfg.get('I/O','LastGoodData_file_headers').split(',')
proc_monitoring_file_headers = cfg.get('I/O','proc_monitoring_file_headers').split(',')
alert_headers = cfg.get('I/O','alert_headers').split(',')

sensors=pd.read_csv(columnproperties_path+columnproperties_file,names=columnproperties_headers,index_col=None)

#update the site tables for accelerometer data
def updateAccelData():
    for col in sensors['colname']:
    	downloadMore = True
    	while downloadMore:
        
    		print col
    		ts = getLatestTimestamp(col)
    		if ts == 0:
            		# auto generate tables that don't exist in the database of the local 
             		# machine running the script
    			print 'There is no table named: ' + col
    			existingOnWebServer = downloadSiteColumnData(col)
    			ts2 = "2000-01-01+00:00:00"
       
    			if existingOnWebServer == None:
        				downloadMore = False
    				
    			continue
    		elif ts == None:
    			ts2 = "2000-01-01+00:00:00"
    		else:
    			ts2 = ts.strftime("%Y-%m-%d+%H:%M:%S")
            
    		df = downloadLatestData(col,ts2)
    		numElements = len(df.index)
    		print "Number of dataframe elements: %s" % (numElements)
    		#print df
    		writeAccelToLocalDB(col,df,ts2)
    
    		if numElements < entryLimit:
    			downloadMore = False

#update the site_column data
def updateSiteColumnTable():
    df = downloadFullSiteColumnTable()
    isDFempty = df.empty
    targetTable = "site_column"      

    if isDFempty == True:
        print 'Update failed...'
    else:
        print 'Updating %s table...' % (targetTable)
        numElements = len(df.index)
        print "Number of %s elements: %s" % (targetTable, numElements)
          
        truncateTable(targetTable)
        writeDFtoLocalDB(targetTable,df)

#update the site_column_props data
def updateColumnPropsTable():
    df = downloadFullColumnPropsTable()
    isDFempty = df.empty
    targetTable = "site_column_props"
    
    if isDFempty == True:
        print 'Update failed...'
    else:
        print 'Updating %s table...' % (targetTable)
        numElements = len(df.index)
        print "Number of %s elements: %s" % (targetTable, numElements)
          
        truncateTable(targetTable)
        writeDFtoLocalDB(targetTable,df)