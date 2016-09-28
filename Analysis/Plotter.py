##### IMPORTANT matplotlib declarations must always be FIRST to make sure that matplotlib works with cron-based automation
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as md
plt.ioff()

import os
import pandas as pd
import numpy as np
from datetime import timedelta

import errorAnalysis as err

def col_pos(colpos_dfts, col_pos_end, col_pos_interval, col_pos_number, num_nodes):
    
    cumsum_df = colpos_dfts.loc[colpos_dfts.ts == colpos_dfts.ts.values[0]][['xz','xy']].cumsum()
    colpos_dfts['cs_xz'] = cumsum_df.xz.values
    colpos_dfts['cs_xy'] = cumsum_df.xy.values
    
    return np.round(colpos_dfts, 4)
                
def nonrepeat_colors(ax,NUM_COLORS,color='gist_rainbow'):
    cm = plt.get_cmap(color)
    ax.set_color_cycle([cm(1.*(NUM_COLORS-i-1)/NUM_COLORS) for i in range(NUM_COLORS)])
    return ax
    
    
def subplot_colpos(dfts, ax_xz, ax_xy):
    #current column position x
    curcolpos_x = dfts.x.values

    #current column position xz
    curax = ax_xz
    curcolpos_xz = dfts.cs_xz.values
    curax.plot(curcolpos_xz,curcolpos_x,'.-')
    curax.set_xlabel('xz')
    curax.set_ylabel('x')
    
    #current column position xy
    curax=ax_xy
    curcolpos_xy = dfts.cs_xy.values
    curax.plot(curcolpos_xy,curcolpos_x,'.-', label=str(pd.to_datetime(dfts.ts.values[0])))
    curax.set_xlabel('xy')
    return
    
    
def plot_column_positions(df,colname,end):
#==============================================================================
# 
#     DESCRIPTION
#     returns plot of xz and xy absolute displacements of each node
# 
#     INPUT
#     colname; array; list of sites
#     x; dataframe; vertical displacements
#     xz; dataframe; horizontal linear displacements along the planes defined by xa-za
#     xy; dataframe; horizontal linear displacements along the planes defined by xa-ya
#==============================================================================

    try:
        fig=plt.figure()

        ax_xz=fig.add_subplot(121)
        ax_xy=fig.add_subplot(122,sharex=ax_xz,sharey=ax_xz)
        
        ax_xz=nonrepeat_colors(ax_xz,len(set(df.ts.values)))
        ax_xy=nonrepeat_colors(ax_xy,len(set(df.ts.values)))
                
        for i in sorted(set(df.ts), reverse = False):
            subplot_colpos(df.loc[df.ts == i], ax_xz=ax_xz, ax_xy=ax_xy)

        for tick in ax_xz.xaxis.get_minor_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(10)
            
        for tick in ax_xy.xaxis.get_minor_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(10)
       
        for tick in ax_xz.xaxis.get_major_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(10)
            
        for tick in ax_xy.xaxis.get_major_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(10)        
    
        plt.tight_layout(pad = 0.5)
        fig.subplots_adjust(top=0.945)        
        fig.suptitle(colname+" as of "+str(end),fontsize='medium')
    
    except:        
        print colname, "ERROR in plotting column position"
    return ax_xz,ax_xy

def vel_plot(df, velplot):
    velplot[df.id.values[0]] = df.id.values[0]
    return velplot

def vel_classify(df, config):
    vel=pd.DataFrame(index=sorted(set(df.ts)))
    nodal_df = df.groupby('id')
    velplot = nodal_df.apply(vel_plot, velplot=vel)
    velplot = velplot.reset_index().loc[velplot.reset_index().id == len(set(df.id))][['level_1'] + range(1, len(set(df.id))+1)].rename(columns = {'level_1': 'ts'}).set_index('ts')
    df = df.set_index(['ts', 'id'])
    try:
        L2mask = (df.abs()>config.io.t_vell2)&(df.abs()<=config.io.t_vell3)        
        L3mask = (df.abs()>config.io.t_vell3)
        L2mask = L2mask.reset_index().replace(False, np.nan)
        L3mask = L3mask.reset_index().replace(False, np.nan)
                    
        return velplot,L2mask,L3mask
    except:
        print "ERROR computing velocity classification"
        return 
    
def noise_envelope(df, tsdf):
    df['ts'] = tsdf
    return df

def plot_disp_vel(df, colname, max_min_df, window, config, disp_offset = 'mean'):
#==============================================================================
# 
#     DESCRIPTION:
#     returns plot of xz and xy displacements per node, xz and xy velocities per node
# 
#     INPUT:
#     xz; array of floats; horizontal linear displacements along the planes defined by xa-za
#     xy; array of floats; horizontal linear displacements along the planes defined by xa-ya
#     xz_vel; array of floats; velocity along the planes defined by xa-za
#     xy_vel; array of floats; velocity along the planes defined by xa-ya
#==============================================================================

    num_nodes = len(set(df.id))
  
    #setting up zeroing and offseting parameters
    nodal_df = df.groupby('id')
    if disp_offset == 'max':
        xzd_plotoffset = nodal_df['xz'].apply(lambda x: x.max() - x.min()).max()
    elif disp_offset == 'mean':
        xzd_plotoffset = nodal_df['xz'].apply(lambda x: x.max() - x.min()).mean()
    elif disp_offset == 'min':
        xzd_plotoffset = nodal_df['xz'].apply(lambda x: x.max() - x.min()).min()
    else:
        xzd_plotoffset = 0


    # defining cumulative (surface) displacement
    dfts = df.groupby('ts')
    cs_df = dfts[['xz', 'xy']].sum()    
    cs_df = cs_df - cs_df.values[0] + xzd_plotoffset * num_nodes
    cs_df = cs_df.sort_index()
    
    #creating noise envelope
    first_row = df.loc[df.ts == window.start].sort_values('id').set_index('id')[['xz', 'xy']]
        
    max_min_df['xz_maxlist'] = max_min_df['xz_maxlist'].values - first_row['xz'].values
    max_min_df['xz_minlist'] = max_min_df['xz_minlist'].values - first_row['xz'].values
    max_min_df['xy_maxlist'] = max_min_df['xy_maxlist'].values - first_row['xy'].values
    max_min_df['xy_minlist'] = max_min_df['xy_minlist'].values - first_row['xy'].values
        
    max_min_df = max_min_df.reset_index()
    max_min_df = max_min_df.append([max_min_df] * (len(set(df.ts))-1), ignore_index = True)
    nodal_max_min_df = max_min_df.groupby('id')

    noise_df = nodal_max_min_df.apply(noise_envelope, tsdf = sorted(set(df.ts)))
    nodal_noise_df = noise_df.groupby('id')
    noise_df = nodal_noise_df.apply(df_add_offset_col, offset = xzd_plotoffset, num_nodes = num_nodes)
    noise_df = noise_df.set_index('ts')

    # conpensates double offset of node 1 due to df.apply
    a = noise_df.loc[noise_df.id == 1] - (num_nodes - 1) * xzd_plotoffset
    a['id'] = 1
    noise_df = noise_df.loc[noise_df.id != 1]
    noise_df = noise_df.append(a)
    noise_df = noise_df.sort_index()
    
    nodal_noise_df = noise_df.groupby('id')
    
    #zeroing and offseting xz,xy
    df0 = nodal_df.apply(df_zero_initial_row, window = window)
    nodal_df0 = df0.groupby('id')
    df0off = nodal_df0.apply(df_add_offset_col, offset = xzd_plotoffset, num_nodes = num_nodes)
    df0off = df0off.set_index('ts')
    
    # conpensates double offset of node 1 due to df.apply
    a = df0off.loc[df0off.id == 1] - (num_nodes - 1) * xzd_plotoffset
    a['id'] = 1
    df0off = df0off.loc[df0off.id != 1]
    df0off = df0off.append(a)
    df0off = df0off.sort_index()
    
    nodal_df0off = df0off.groupby('id')
    
    try:
        fig=plt.figure()
           
        #creating subplots        
        ax_xzd=fig.add_subplot(141)
        ax_xyd=fig.add_subplot(142,sharex=ax_xzd,sharey=ax_xzd)
        
        ax_xzv=fig.add_subplot(143)
        ax_xzv.invert_yaxis()
        ax_xyv=fig.add_subplot(144,sharex=ax_xzv,sharey=ax_xzv)
        
        #plotting cumulative (surface) displacments
        ax_xzd.plot(cs_df.index, cs_df['xz'].values,color='0.4',linewidth=0.5)
        ax_xyd.plot(cs_df.index, cs_df['xy'].values,color='0.4',linewidth=0.5)
        ax_xzd.fill_between(cs_df.index,cs_df['xz'].values,xzd_plotoffset*(num_nodes),color='0.8')
        ax_xyd.fill_between(cs_df.index,cs_df['xy'].values,xzd_plotoffset*(num_nodes),color='0.8')       
       
        #assigning non-repeating colors to subplots axis
        ax_xzd=nonrepeat_colors(ax_xzd,num_nodes)
        ax_xyd=nonrepeat_colors(ax_xyd,num_nodes)
        ax_xzv=nonrepeat_colors(ax_xzv,num_nodes)
        ax_xyv=nonrepeat_colors(ax_xyv,num_nodes)
    
        #plotting displacement for xz
        curax=ax_xzd
        plt.sca(curax)
        nodal_df0off['xz'].apply(plt.plot)
        nodal_noise_df['xz_maxlist'].apply(plt.plot, ls=':')
        nodal_noise_df['xz_minlist'].apply(plt.plot, ls=':')
        curax.set_title('3-day displacement\n XZ axis',fontsize='small')
        curax.set_ylabel('displacement scale, m', fontsize='small')
        y = df0off.loc[df0off.index == window.start].sort_values('id')['xz'].values
        x = window.start
        z = sorted(set(df.id))
        for i,j in zip(y,z):
           curax.annotate(str(j),xy=(x,i),xytext = (5,-2.5), textcoords='offset points',size = 'x-small')
        
        #plotting displacement for xy
        curax=ax_xyd
        plt.sca(curax)
        nodal_df0off['xy'].apply(plt.plot)
        nodal_noise_df['xy_maxlist'].apply(plt.plot, ls=':')
        nodal_noise_df['xy_minlist'].apply(plt.plot, ls=':')
        curax.set_title('3-day displacement\n XY axis',fontsize='small')
        y = df0off.loc[df0off.index == window.start].sort_values('id')['xy'].values
        x = window.start
        z = sorted(set(df.id))
        for i,j in zip(y,z):
           curax.annotate(str(j),xy=(x,i),xytext = (5,-2.5), textcoords='offset points',size = 'x-small')
    
        #plotting velocity for xz
        curax=ax_xzv
        plt.sca(curax)
        vel_xz = df[['ts', 'vel_xz', 'id']]
        vel_xz = vel_xz.loc[(vel_xz.ts >= window.end - timedelta(hours=3)) & (vel_xz.ts <= window.end)]
        velplot,L2,L3 = vel_classify(vel_xz, config)  
        velplot.plot(ax=curax,marker='.',legend=False)
    
        L2 = L2.sort_values('ts', ascending = True).set_index('ts')
        nodal_L2 = L2.groupby('id')
        nodal_L2['vel_xz'].apply(plt.plot,marker='^',ms=8,mfc='y',lw=0,)
    
        L3 = L3.sort_values('ts', ascending = True).set_index('ts')
        nodal_L3 = L3.groupby('id')
        nodal_L3['vel_xz'].apply(plt.plot,marker='^',ms=10,mfc='r',lw=0,)
        
        y = sorted(set(df.id))
        x = window.end - timedelta(hours=2.5)
        z = sorted(set(df.id))
        for i,j in zip(y,z):
            curax.annotate(str(j),xy=(x,i),xytext = (5,-2.5), textcoords='offset points',size = 'x-small')            
        curax.set_ylabel('node ID', fontsize='small')
        curax.set_title('3-hr velocity alerts\n XZ axis',fontsize='small')  
        
        #plotting velocity for xy        
        curax=ax_xyv
        plt.sca(curax)   
        vel_xy = df[['ts', 'vel_xy', 'id']]
        vel_xy = vel_xy.loc[(vel_xy.ts >= window.end - timedelta(hours=3)) & (vel_xy.ts <= window.end)]
        velplot,L2,L3 = vel_classify(vel_xy, config)
        velplot.plot(ax=curax,marker='.',legend=False)
        
        L2 = L2.sort_values('ts', ascending = True).set_index('ts')
        nodal_L2 = L2.groupby('id')
        nodal_L2['vel_xy'].apply(plt.plot,marker='^',ms=8,mfc='y',lw=0,)
    
        L3 = L3.sort_values('ts', ascending = True).set_index('ts')
        nodal_L3 = L3.groupby('id')
        nodal_L3['vel_xy'].apply(plt.plot,marker='^',ms=10,mfc='r',lw=0,)
               
        y = sorted(set(df.id))
        x = window.end - timedelta(hours=2.5)
        z = sorted(set(df.id))
        for i,j in zip(y,z):
            curax.annotate(str(j),xy=(x,i),xytext = (5,-2.5), textcoords='offset points',size = 'x-small')            
        curax.set_title('3-hr velocity alerts\n XY axis',fontsize='small')                        
            
        # rotating xlabel
        
        for tick in ax_xzd.xaxis.get_minor_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(6)
            
        for tick in ax_xyd.xaxis.get_minor_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(6)
    
        for tick in ax_xzv.xaxis.get_minor_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(6)
    
        for tick in ax_xyv.xaxis.get_minor_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(6)
    
        for tick in ax_xzd.xaxis.get_major_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(6)
            
        for tick in ax_xyd.xaxis.get_major_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(6)
    
        for tick in ax_xzv.xaxis.get_major_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(6)
    
        for tick in ax_xyv.xaxis.get_major_ticks():
            tick.label.set_rotation('vertical')
            tick.label.set_fontsize(6)
                
        for item in ([ax_xzd.xaxis.label, ax_xzv.yaxis.label, ax_xyd.xaxis.label, ax_xyv.yaxis.label]):
            item.set_fontsize(8)
            
        dfmt = md.DateFormatter('%m-%d\n%H:%M')
        ax_xzd.xaxis.set_major_formatter(dfmt)
        ax_xyd.xaxis.set_major_formatter(dfmt)
            
        fig.tight_layout()
        
        fig.subplots_adjust(top=0.85)        
        fig.suptitle(colname+" as of "+str(velplot.index[-1]),fontsize='medium')
        line=mpl.lines.Line2D((0.5,0.5),(0.1,0.8))
        fig.lines=line,
        
    except:      
        print colname, "ERROR in plotting displacements and velocities"
    return


def df_zero_initial_row(df, window):
    #zeroing time series to initial value;
    #essentially, this subtracts the value of the first row
    #from all the rows of the dataframe
    columns = list(df.columns)
    columns.remove('ts')
    columns.remove('id')
    for m in columns:
        df[m] = df[m] - df.loc[df.ts == window.start][m].values[0]
    return np.round(df,4)

def df_add_offset_col(df, offset, num_nodes):
    #adding offset value based on column value (node ID);
    #topmost node (node 1) has largest offset
    columns = list(df.columns)
    columns.remove('ts')
    columns.remove('id')
    for m in columns:
        df[m] = df[m] + (num_nodes - df.id.values[0]) * offset
    return np.round(df,4)
    
    
def main(monitoring, window, config):

    colname = monitoring.colprops.name
    num_nodes = monitoring.colprops.nos
    seg_len = monitoring.colprops.seglen
    monitoring_vel = monitoring.vel.reset_index()[['ts', 'id', 'xz', 'xy', 'vel_xz', 'vel_xy']]
    
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
    
    if not os.path.exists(output_path+config.io.outputfilepath):
        os.makedirs(output_path+config.io.outputfilepath)
        
    # compute column position
    colposdates = pd.date_range(end=window.end, freq=config.io.col_pos_interval, periods=config.io.num_col_pos, name='ts', closed=None)
    colpos_df = pd.DataFrame({'ts': colposdates, 'id': [num_nodes+1]*len(colposdates), 'xz': [0]*len(colposdates), 'xy': [0]*len(colposdates)})
    for colpos_ts in colposdates:
        colpos_df = colpos_df.append(monitoring_vel.loc[monitoring_vel.ts == colpos_ts, ['ts', 'id', 'xz', 'xy']])
    colpos_df['x'] = colpos_df['id'].apply(lambda x: (num_nodes + 1 - x) * seg_len)
    colpos_df = colpos_df.sort('id', ascending = False)
    colpos_dfts = colpos_df.groupby('ts')
    colposdf = colpos_dfts.apply(col_pos, col_pos_end = window.end, col_pos_interval = config.io.col_pos_interval, col_pos_number = config.io.num_col_pos, num_nodes = num_nodes)

    # noise envelope
    max_min_df, max_min_cml = err.cml_noise_profiling(monitoring_vel)

    # plot column position
    plot_column_positions(colposdf,colname,window.end)

    lgd = plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize='x-small')

    plt.savefig(output_path+config.io.outputfilepath+colname+'ColPos_'+str(window.end.strftime('%Y-%m-%d_%H-%M'))+'.png',
                dpi=160, facecolor='w', edgecolor='w',orientation='landscape',mode='w', bbox_extra_artists=(lgd,), bbox_inches='tight')
    
    # plot displacement and velocity
    plot_disp_vel(monitoring_vel, colname, max_min_df, window, config)
    plt.savefig(output_path+config.io.outputfilepath+colname+'_DispVel_'+str(window.end.strftime('%Y-%m-%d_%H-%M'))+'.png',
                dpi=160, facecolor='w', edgecolor='w',orientation='landscape',mode='w')
    
