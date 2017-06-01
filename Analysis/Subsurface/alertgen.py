from datetime import datetime
import os
import pandas as pd
import sys

import alertlib as lib
import proc
import rtwindow as rtw
import trendingalert as trend
#import ColumnPlotter as plotter

#include the path of outer folder for the python scripts searching
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if not path in sys.path:
    sys.path.insert(1,path)
del path   

import querydb as qdb

def writeOperationalTriggers(site_id, end):
    query = "SELECT op.alert_level, trigger_sym_id FROM (SELECT alert_level, ts, ts_updated FROM"
    query += " tsm_alerts as ta left join tsm_sensors as tsm on ta.tsm_id = tsm.tsm_id where site_id = %s) AS sub" %site_id
    query += " left join operational_trigger_symbols as op"
    query += " on op.alert_level = sub.alert_level"
    query += " where trigger_source = 'subsurface'"
    query += " and ts <= '%s'" %end
    query += " and ts_updated >= '%s'" %end
    df = qdb.GetDBDataFrame(query)
    
    trigger_sym_id = df.sort_values('alert_level', ascending=False)['trigger_sym_id'].values[0]
        
    operational_trigger = pd.DataFrame({'ts': [end], 'site_id': [site_id], 'trigger_sym_id': [trigger_sym_id], 'ts_updated': [end]})
    
    qdb.alert_toDB(operational_trigger, 'operational_triggers')

def main(tsm_name='', end='', end_mon=False):
    print tsm_name
    if tsm_name == '':
        tsm_name = sys.argv[1].lower()

    if end == '':
        try:
            end = pd.to_datetime(sys.argv[2])
        except:
            end = datetime.now()
    
    window,config = rtw.get_window(end)

    tsm_props = qdb.GetTSMList(tsm_name)[0]
    data = proc.proc_data(tsm_props, window, config, config.io.column_fix)
        
    tilt = data.tilt[window.start:window.end]
    lgd = data.lgd
    tilt = tilt.reset_index().sort_values('ts',ascending=True)
    nodal_tilt = tilt.groupby('node_id', as_index=False)     
        
    alert = nodal_tilt.apply(lib.node_alert, colname=tsm_props.tsm_name, num_nodes=tsm_props.nos, T_disp=config.io.t_disp, T_velL2=config.io.t_vell2, T_velL3=config.io.t_vell3, k_ac_ax=config.io.k_ac_ax, lastgooddata=lgd,window=window,config=config).reset_index(drop=True)
    alert = lib.column_alert(alert, config.io.num_nodes_to_check)

    valid_nodes_alert = alert.loc[~alert.node_id.isin(data.inv)]
    
    if max(valid_nodes_alert['col_alert'].values) > 0:
        pos_alert = valid_nodes_alert[valid_nodes_alert.col_alert > 0]
        site_alert = trend.main(pos_alert, tsm_props.tsm_id, window.end, data.inv)
    else:
        site_alert = max(lib.get_mode(list(valid_nodes_alert['col_alert'].values)))
        
    tsm_alert = pd.DataFrame({'ts': [window.end], 'tsm_id': [tsm_props.tsm_id], 'alert_level': [site_alert], 'ts_updated': [window.end]})

    qdb.alert_toDB(tsm_alert, 'tsm_alerts')
    
    writeOperationalTriggers(tsm_props.site_id, window.end)
########################
#
#    if tsm_props.tsm_name == 'mesta':
#        colname = 'msu'
#    elif tsm_props.tsm_name == 'messb':
#        colname = 'msl'
#    else:
#        colname = tsm_props.tsm_name[0:3]
#    query = "SELECT * FROM senslopedb.site_level_alert WHERE site = '%s' and source = 'public' and timestamp <= '%s' and updateTS >= '%s' ORDER BY updateTS DESC LIMIT 1" %(colname, window.end, window.end-timedelta(hours=0.5))
#    public_alert = q.GetDBDataFrame(query)
#    if public_alert.alert.values[0] != 'A0':
#        plot_time = ['07:30:00', '19:30:00']
#        if str(window.end.time()) in plot_time or end_mon:
#            plotter.main(proc, window, config, plotvel_start=window.end-timedelta(hours=3), plotvel_end=window.end, realtime=False)
#    elif RoundTime(pd.to_datetime(public_alert.timestamp.values[0])) == RoundTime(window.end):
#        plotter.main(proc, window, config, plotvel_start=window.end-timedelta(hours=3), plotvel_end=window.end, realtime=False)
#
########################
    
################################################################################

if __name__ == "__main__":
    run_start = datetime.now()
    print run_start
    main()
    print 'run time =', datetime.now()-run_start