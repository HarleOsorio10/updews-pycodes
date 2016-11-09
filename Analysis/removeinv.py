import pandas as pd
from datetime import datetime, timedelta

import querySenslopeDb as q

def invalert(df):
    inv_alert = df['alertmsg'].values[0].split('\n')
    ts = pd.to_datetime(inv_alert[0].replace('As of ',''))
    site = inv_alert[1][0:3]
    alert = inv_alert[1][4:6]
    source = inv_alert[1][7:len(inv_alert[1])]
    alertdf = pd.DataFrame({'ts': [ts], 'site': [site], 'alert': [alert], 'source': [source]})
    return alertdf

def removeinvpub(df):
    ts = pd.to_datetime(df.ts[0])
    db, cur = q.SenslopeDBConnect(q.Namedb)
    query = "DELETE FROM site_level_alert where site = '%s' and source = 'public' and alert = '%s' and timestamp <= '%s' \
            and updateTS >= '%s'" %(df.site[0], df.alert[0], ts+timedelta(hours=0.5), ts-timedelta(hours=0.5))
    cur.execute(query)
    db.commit()
    db.close()

def main(ts=datetime.now()):
    query = "SELECT * FROM smsalerts where ts_set >= '%s' and alertstat = 'invalid'" %(pd.to_datetime(ts) - timedelta(3))
    df = q.GetDBDataFrame(query)
    
    dfid = df.groupby('alert_id')
    alertdf = dfid.apply(invalert)
    alertdf = alertdf.reset_index(drop=True)
    
    invalertdf = alertdf.loc[alertdf.ts >= ts - timedelta(hours=0.5)]
    invalertdf = invalertdf[~(invalertdf.source.str.contains('sensor'))]
    invalertdf = invalertdf.loc[invalertdf.alert == 'A1']

    try:    
        sitealertdf = invalertdf.groupby('site')
        sitealertdf.apply(removeinvpub)
    except:
        print 'No invalid alert'

    allpub = pd.read_csv('PublicAlert.txt', sep = '\t')
    withalert = allpub.loc[allpub.alert != 'A0'].site
    alertdf = alertdf[alertdf.site.isin(withalert)][['alert', 'site']]
    
    alertdf.to_csv('InvalidAlert.txt', sep=':', header=False, index=False, mode='w')

if __name__ == '__main__':
    start = datetime.now()
    main()
    print 'runtime =', str(datetime.now() - start)