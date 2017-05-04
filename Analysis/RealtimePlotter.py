##### IMPORTANT matplotlib declarations must always be FIRST to make sure that matplotlib works with cron-based automation
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
plt.ion()

import pandas as pd
from datetime import date, time, datetime, timedelta

import rtwindow as rtw
import querySenslopeDb as q
import genproc as g
import ColumnPlotter as plotter

def mon_main():
    while True:
        plot_all_data = raw_input('plot from start to end of data? (Y/N): ').lower()
        if plot_all_data == 'y' or plot_all_data == 'n':
            break
    
    # plots segment of data
    if plot_all_data == 'n':
    
        while True:
            monitoring_window = raw_input('plot with 3 day monitoring window? (Y/N): ').lower()
            if monitoring_window == 'y' or monitoring_window == 'n':
                break
    
        # plots with 3 day monitoring window
        if monitoring_window == 'y':
            while True:
                try:
                    col = q.GetSensorList(raw_input('sensor name: '))
                    break
                except:
                    print 'sensor name is not in the list'
                    continue
            
            while True:
                test_specific_time = raw_input('test specific time? (Y/N): ').lower()
                if test_specific_time == 'y' or test_specific_time == 'n':
                    break
            
            while True:
                try:
                    if test_specific_time == 'y':
                        end = pd.to_datetime(raw_input('plot end timestamp (format: 2016-12-31 23:30): '))
                        window, config = rtw.getwindow(end)
                    elif test_specific_time == 'n':
                        window, config = rtw.getwindow()
                    break
                except:
                    print 'invalid datetime format'
                    continue

            column_fix = raw_input('column fix for colpos (top/bottom); default for monitoring is fix bottom: ').lower()
            if column_fix != 'top':
                column_fix = 'bottom'
                
            config.io.column_fix = column_fix
            
            monitoring = g.genproc(col[0], window, config, config.io.column_fix, realtime=True)
            plotter.main(monitoring, window, config, plotvel_start=window.end-timedelta(hours=3), plotvel_end=window.end)#, plot_inc=False)
            
        # plots with customizable monitoring window
        elif monitoring_window == 'n':
            while True:
                try:
                    col = q.GetSensorList(raw_input('sensor name: '))
                    break
                except:
                    print 'sensor name is not in the list'
                    continue
                
            while True:
                try:
                    end = pd.to_datetime(raw_input('plot end timestamp (format: 2016-12-31 23:30): '))
                    window, config = rtw.getwindow(end)
                    break
                except:
                    print 'invalid datetime format'
                    continue
    
            while True:
                start = raw_input('monitoring window (in days) or datetime (format: 2016-12-31 23:30): ')
                try:
                    window.start = window.end - timedelta(int(start))
                    break
                except:
                    try:
                        window.start = pd.to_datetime(start)
                        break
                    except:
                        print 'datetime format or integer only'
                        continue
    
            window.offsetstart = window.start - timedelta(days=(config.io.num_roll_window_ops*window.numpts-1)/48.)
    
            while True:
                try:
                    col_pos_interval = int(raw_input('interval between column position dates, in days: '))
                    break
                except:
                    print 'enter an integer'
                    continue
                
            config.io.col_pos_interval = str(col_pos_interval) + 'D'
            config.io.num_col_pos = int((window.end - window.start).days/col_pos_interval + 1)

            column_fix = raw_input('column fix for colpos (top/bottom); default for monitoring is fix bottom: ').lower()
            if column_fix != 'top':
                column_fix = 'bottom'
                
            config.io.column_fix = column_fix
    
            while True:
                show_all_legend = raw_input('show all legend in column position plot? (Y/N): ').lower()
                if show_all_legend == 'y' or show_all_legend == 'n':        
                    break
    
            if show_all_legend == 'y':
                show_part_legend = False
            elif show_all_legend == 'n':
                while True:
                    try:
                        show_part_legend = int(raw_input('every nth legend to show: '))
                        if show_part_legend <= config.io.num_col_pos:
                            break
                        else:
                            print 'integer should be less than number of column position dates to plot:', config.io.num_col_pos
                            continue
                    except:
                        print 'enter an integer'
                        continue

            while True:
                plotvel = raw_input('plot velocity? (Y/N): ').lower()
                if plotvel == 'y' or plotvel == 'n':        
                    break
                
            if plotvel == 'y':
                plotvel = True
            else:
                plotvel = False
    
            monitoring = g.genproc(col[0], window, config, config.io.column_fix, comp_vel = plotvel)
            plotter.main(monitoring, window, config, plotvel=plotvel, show_part_legend = show_part_legend, plotvel_end=window.end, plotvel_start=window.start, plot_inc=False, comp_vel=plotvel)
        
    # plots from start to end of data
    elif plot_all_data == 'y':
        while True:
            try:
                col = q.GetSensorList(raw_input('sensor name: '))
                break
            except:
                print 'sensor name is not in the list'
                continue
            
        while True:
            try:
                col_pos_interval = int(raw_input('interval between column position dates, in days: '))
                break
            except:
                print 'enter an integer'
                continue

        query = "(SELECT * FROM senslopedb.%s where timestamp > '2010-01-01 00:00' ORDER BY timestamp LIMIT 1)" %col[0].name
        query += " UNION ALL"
        query += " (SELECT * FROM senslopedb.%s ORDER BY timestamp DESC LIMIT 1)" %col[0].name
        start_end = q.GetDBDataFrame(query)
        
        end = pd.to_datetime(start_end['timestamp'].values[1])
        window, config = rtw.getwindow(end)
        
        start_dataTS = pd.to_datetime(start_end['timestamp'].values[0])
        start_dataTS_Year=start_dataTS.year
        start_dataTS_month=start_dataTS.month
        start_dataTS_day=start_dataTS.day
        start_dataTS_hour=start_dataTS.hour
        start_dataTS_minute=start_dataTS.minute
        if start_dataTS_minute<30:start_dataTS_minute=0
        else:start_dataTS_minute=30
        window.offsetstart=datetime.combine(date(start_dataTS_Year,start_dataTS_month,start_dataTS_day),time(start_dataTS_hour,start_dataTS_minute,0))
        
        window.numpts = int(1+config.io.roll_window_length/config.io.data_dt)
        window.start = window.offsetstart + timedelta(days=(config.io.num_roll_window_ops*window.numpts-1)/48.)
        config.io.col_pos_interval = str(col_pos_interval) + 'D'
        config.io.num_col_pos = int((window.end - window.start).days/col_pos_interval + 1)
    
        column_fix = raw_input('column fix for colpos (top/bottom); default for monitoring is fix bottom: ').lower()
        if column_fix != 'top':
            column_fix = 'bottom'
            
        config.io.column_fix = column_fix
    
        while True:
            show_all_legend = raw_input('show all legend in column position plot? (Y/N): ').lower()
            if show_all_legend == 'y' or show_all_legend == 'n':        
                break
    
        if show_all_legend == 'y':
            show_part_legend = False
        elif show_all_legend == 'n':
            while True:
                try:
                    show_part_legend = int(raw_input('every nth legend to show: '))
                    if show_part_legend <= config.io.num_col_pos:
                        break
                    else:
                        print 'integer should be less than number of column position dates to plot:', config.io.num_col_pos
                        continue
                except:
                    print 'enter an integer'
                    continue

        while True:
            plotvel = raw_input('plot velocity? (Y/N): ').lower()
            if plotvel == 'y' or plotvel == 'n':        
                break
            
        if plotvel == 'y':
            plotvel = True
        else:
            plotvel = False

        monitoring = g.genproc(col[0], window, config, config.io.column_fix, comp_vel = plotvel)
        plotter.main(monitoring, window, config, plotvel=plotvel, show_part_legend = show_part_legend, plot_inc=False, comp_vel=plotvel)

##########################################################
if __name__ == "__main__":
    start = datetime.now()
    mon_main()
    print 'runtime =', str(datetime.now() - start)