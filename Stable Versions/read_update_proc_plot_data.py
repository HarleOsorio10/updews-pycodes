#"PLEASE READ:"

#   This program provides a spline-fit of data points representing individual node tilts.
#   A time-series plot of raw data points and spline-fit curve, and the velocity (derivative of spline-fit curve) is produced. 
#   The program also makes a cartesian plot of column segment positions along the xg-zg and xg-yg planes.
#   Two column segment positions plots are produced: one showing absolute column position, and another showing positions relative to initial date of data range provided by user
#   The end of the bottom segment is assumed to be fixed to stable ground, and thus, positions are measured from this point.



#libraries and modules
import os
from array import *
import csv
import math
import numpy as np
import scipy as sp
import scipy.optimize
from datetime import datetime, date, time, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator, AutoMinorLocator
from matplotlib import transforms as mtransforms
from matplotlib import font_manager as font
from matplotlib.figure import Figure #as mFig
from matplotlib.axis import Axis
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.backend_bases import NavigationToolbar2 as Nav

from scipy.interpolate import UnivariateSpline
import scipy.stats.stats as st
import ConfigParser

import sys
import threading
#import time
#import datetime
#import date
#import timedelta


#CONSTANTS

#B. plot parameters
#   legend parameters
legend_font_props = font.FontProperties()
legend_font_props.set_size('small')
ncol=1
#bbtoa=(1,0.5)
prop=legend_font_props
legloc='upper center'

#   grid parameters
g_which='both'
g_ax='both'
g_ls='-'
g_c='0.6'

#math/trigo functions
tan=math.tan
sin=math.sin
asin=math.asin
cos=math.cos
pow=math.pow
sqrt=math.sqrt
atan=math.atan
deg=math.degrees
rad=math.radians


#CLASSES

class Logger(object):
    def __init__(self, filename="Default.log"):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

class ColumnArray:
    def __init__(self, name, number_of_segments, segment_length):
        self.name = name
        self.nos = number_of_segments
        self.seglen = segment_length        

#FUNCTIONS

def Input_Loc_Col(loc_col_list,num_nodes_loc_col,col_seg_len_list,IWS):
    loc_col=loc_col_list[IWS]
    num_nodes=num_nodes_loc_col[IWS]
    fname=loc_col+"_proc.csv"
    seg_len=col_seg_len_list[IWS]
    return fname, num_nodes,loc_col,seg_len


def Create_Arrays_for_Input(num_nodes):
    all_nodes_data=range(num_nodes)
    return all_nodes_data


def Write_Input_File_to_Arrays(all_nodes_data,fname,node_len):
    num_nodes=len(all_nodes_data)
    cur_date=datetime.now()
    last_good_tilt_date_all_nodes=datetime.combine(date(1999,1,1),time(0,0,0))
    first_good_tilt_date_all_nodes=datetime.combine(date(2999,1,1),time(0,0,0))

    if os.path.exists(fname)==0:
        print "Error reading input file to arrays: Input file " + fname + " does not exist"
        return []        
    
    for cur_node_ID in range(num_nodes):
        
        dt=[]
        xz=array('f')
        xy=array('f')
        #moi=array('i')
        
        fo = csv.reader(open(fname, 'r'),delimiter=',')
        total_data_count=0
        for i in fo:
            if int(i[1])==cur_node_ID+1:
                tilt_data_filter=int(i[5])
                if tilt_data_filter==1:
                    
                    xz.append(float(i[6]))
                    xy.append(float(i[7]))
                    #moi.append(int(i[10]))

                    temp=i[0]
                    Y,m,d,H,M,S= int(temp[0:4]), int(temp[5:7]), int(temp[8:10]), int(temp[11:13]), int(temp[14:16]), int(temp[17:19])
                    cur_node_dt=datetime.combine(date(Y,m,d),time(H,M,S))
                    dt.append(cur_node_dt)
                    
                    total_data_count=total_data_count+1

        xlin,xzlin,xylin=xzxy_to_cart(node_len, xz, xy)

        if len(dt)==0:
            last_good_tilt_date=datetime.combine(date(1999,1,1),time(0,0,0))
            first_good_tilt_date=datetime.combine(date(1999,1,1),time(0,0,0))
        else:

            last_good_tilt_date=dt[len(dt)-1]
            if last_good_tilt_date>last_good_tilt_date_all_nodes:
                last_good_tilt_date_all_nodes=last_good_tilt_date  
        
            first_good_tilt_date=dt[0]
            if first_good_tilt_date<first_good_tilt_date_all_nodes:
                first_good_tilt_date_all_nodes=first_good_tilt_date 


        #if cur_date-last_good_tilt_date>timedelta(days=1):
        #    print " ",cur_node_ID+1,"   ", last_good_tilt_date.strftime("%Y-%m-%d %H:%M")

        cur_node_data=(dt,xzlin,xylin,xlin) 
        all_nodes_data[cur_node_ID]=cur_node_data

    return all_nodes_data



def compute_colpos_time(end_dt,days,numcolpos):
    colposdays=np.linspace(-days,0,numcolpos)
    colposdates=day_to_date(colposdays, end_dt)
    return colposdates


def compute_plot_intervals(last,first,plot_intervals):
    column_data_range=last-first
    column_data_range_td=(column_data_range.days)+(column_data_range.seconds/(3600*24.0))
    dt_int=range(plot_intervals+1)
    for x in range(plot_intervals+1):
        dt_int[x]=first+(x*timedelta(days=(column_data_range_td/(1.0*(plot_intervals)))))
        if x!=0:
            print dt_int[x]
    return dt_int


def accumulate_translate(X,XZ,XY,numnodes,numcolpos, dates_to_plot, loc_col):
    plt.figure(20)
    plt.clf()
    plt.figure(21)
    plt.clf()
    ac_x=np.ndarray(shape=(numcolpos,numnodes+1))
    ac_xz=np.ndarray(shape=(numcolpos,numnodes+1))
    ac_xy=np.ndarray(shape=(numcolpos,numnodes+1))
    for col in range(numcolpos):
        sum_x=0
        sum_xz=0
        sum_xy=0
        ac_x[col,0]=sum_x
        ac_xz[col,0]=sum_xz
        ac_xy[col,0]=sum_xy
        for row in range(numnodes):
            sum_x=sum_x+X[numnodes-row-1,col]
            sum_xz=sum_xz+XZ[numnodes-row-1,col]
            sum_xy=sum_xy+XY[numnodes-row-1,col]
            ac_x[col,row+1]=sum_x
            ac_xz[col,row+1]=sum_xz
            ac_xy[col,row+1]=sum_xy
    
        posdate=dates_to_plot[col].strftime("%Y-%m-%d")
        for g in [1,2]:
            colposfig=plt.figure(20+g-1)
            
            xz_ax=colposfig.add_subplot(121)
            xy_ax=colposfig.add_subplot(122, sharey=xz_ax, sharex=xz_ax)
            if g==1:
                ref_ac_xz=np.zeros(len(ac_xz[0]))
                ref_ac_xy=np.zeros(len(ac_xy[0]))
                if col==0:
                    colposfig.suptitle(loc_col+"absolute column positions")
            else:
                ref_ac_xz=ac_xz[0]
                ref_ac_xy=ac_xy[0]
                if col==0:
                    colposfig.suptitle(loc_col+" column positions relative to "+dates_to_plot[col].strftime("%Y-%m-%d"))

            plt.sca(xz_ax)
            xzline,=xz_ax.plot(ac_xz[col]-ref_ac_xz,ac_x[col],'o-', markersize=3, label=posdate)
            curcolor=plt.getp(xzline,'color')
            xz_ax.set_ylabel("vertical position, m")
            xz_ax.set_xlabel("zg, m;\n(+) towards downslope")
            xz_ax.set_ylabel("xg, m;\n(+) towards the surface",horizontalalignment='center')
            xz_ax.set_title("xg-zg-plane")
            if g==2:
                plt.xlim(-0.15,0.15)
                xz_ax.axvline(x=-.10,color='r', ls='-',lw=1,)
                xz_ax.axvline(x=.10,color='r', ls='-',lw=1,)
                xz_ax.axvline(x=.05,color='y', ls='-',lw=1,)
                xz_ax.axvline(x=-.05,color='y', ls='-',lw=1,)
            xz_ax.yaxis.set_major_locator(MaxNLocator(10))
            xz_ax.yaxis.set_minor_locator(AutoMinorLocator(2))
            xz_ax.xaxis.set_major_locator(MaxNLocator(7))
            xz_ax.grid(b=None, which=g_which,axis=g_ax,ls=g_ls,c=g_c)
            

            plt.sca(xy_ax)
            xyline,=xy_ax.plot(ac_xy[col]-ref_ac_xy,ac_x[col],'o-', color=curcolor, markersize=3, label=posdate)
            xy_ax.set_xlabel("yg, m;\n(+) to the right, facing downslope")
            #xy_ax.set_ylabel("xg, m;\n(+) towards the surface",horizontalalignment='center')
            xy_ax.set_title("xg-yg-plane")
            if g==2:
                plt.xlim(-0.15,0.15)
                xy_ax.axvline(x=-.10,color='r', ls='-',lw=1,)
                xy_ax.axvline(x=.10,color='r', ls='-',lw=1,)
                xy_ax.axvline(x=.05,color='y', ls='-',lw=1,)
                xy_ax.axvline(x=-.05,color='y', ls='-',lw=1,)
            xy_ax.yaxis.set_major_locator(MaxNLocator(10))
            xy_ax.yaxis.set_minor_locator(AutoMinorLocator(2))
            xy_ax.xaxis.set_major_locator(MaxNLocator(7))
            xy_ax.grid(b=None, which=g_which,axis=g_ax,ls=g_ls,c=g_c) 
            
            xy_ax.legend(loc='upper center',bbox_to_anchor=(0.7, 1.2),prop=legend_font_props)
        
        
            plt.tight_layout()
            plt.subplots_adjust(top=0.85)

    plt.figure(20)
    fig_name=OutputFigurePath+loc_col+"_colpos_abs.png"
    #fig_name=loc_col+"_colpos_abs.png" #os.path.abspath(os.getcwd() + "/../../../..")+"/FiguresForUpload/"+loc_col+"_colpos_abs.png"
    if PrintFigures:
        plt.savefig(fig_name, dpi=100, facecolor='w', edgecolor='w',orientation='landscape')

    plt.figure(21)
    fig_name=OutputFigurePath+loc_col+"_colpos_rel.png"
    #fig_name=loc_col+"_colpos_abs.png" #os.path.abspath(os.getcwd() + "/../../../..")+"/FiguresForUpload/"+loc_col+"_colpos_rel.png"
    if PrintFigures:
        plt.savefig(fig_name, dpi=100, facecolor='w', edgecolor='w',orientation='landscape')
    
    #plt.show()    
    
    
    return ac_x, ac_xz, ac_xy


def xzxy_to_cart(node_len, xz, xy):
    #xz and xy here are in angular units (degrees)
    cond=(xz==0)*(xy==0)

    H=np.round(np.where(cond,
                        node_len*np.ones(len(xz)),
                        node_len/np.sqrt(1+(np.tan(np.radians(xz)))**2+(np.tan(np.radians(xy)))**2)),2)

    a=np.where(cond,
               np.zeros(len(xz)),
               (np.round(H*np.tan(np.radians(xz)),4)))

    b=np.where(cond,
               np.zeros(len(xz)),
               (np.round(H*np.tan(np.radians(xy)),4)))
    ##########
    gt=0
    if gt==1:
        H=array('f')
        a=array('f')
        b=array('f')
        for q in range(len(xz)):
            if xz[q]==0 and xy[q]==0:
                h=node_len
                H.append(node_len)
                a.append(0)
                b.append(0)
            else:
                h=node_len/sqrt(1+(tan(rad(xz[q])))**2+(tan(rad(xy[q])))**2)
                H.append(round(h,2))
                a.append(round(h*tan(rad(xz[q])),4))
                b.append(round(h*tan(rad(xy[q])),4))
    #############3
    return H,a,b
def xzxy_to_cart2(node_len, xz, xy):
    #xz and xy here are already linear units
    cond=(xz==0)*(xy==0)
    diagbase=np.sqrt(np.power(xz,2)+np.power(xy,2))
    H=np.round(np.where(cond,
                        node_len*np.ones(len(xz)),
                        np.sqrt(node_len**2-np.power(diagbase,2))),2)
    a=xz
    b=xy

    ################
    gt=0
    if gt==1:
        H=array('f')
        a=array('f')
        b=array('f')
        for q in range(len(xz)):
            if xz[q]==0 and xy[q]==0:
                h=node_len
                H.append(node_len)
                a.append(0)
                b.append(0)
            else:
                h=node_len/sqrt(1+(tan(rad(xz[q])))**2+(tan(rad(xy[q])))**2)
                H.append(node_len)
                a.append(round(xz[q],4))
                b.append(round(xy[q],4))
    ###################       
    return H,a,b

def extract_tilt_for_colpos(splinef, colposdates, minspline, maxspline):
    tilt=array('f')
    #print colposdates
    end_date=max(colposdates)
    colposdays=[date_to_day(curdate, end_date) for curdate in colposdates]
    #print colposdays
    for c in range(len(colposdays)):
        if colposdays[c]<minspline:
            tilt.append(splinef(minspline))            
        elif colposdays[c]>maxspline:
            tilt.append(splinef(maxspline))
        else:
            tilt.append(splinef(colposdays[c]))
    return tilt

                      
def fitspline_tilt(date, tilt, days, date_end):
    if len(tilt)<10:
        #print "t0",
        return [],[],[],[],[],[]

    date_start=date_end-timedelta(days=days)
    subdays=array('f')
    subtilt=array('f')
    d=0
    while d<=len(date)-1:
        if date[d]>date_end:break
        days_before=date_end-date[d]
        days_before=0-(days_before.days+(days_before.seconds/(60*60*24.)))
        if days_before<-days:
            d=d+1     
            continue
        elif days_before>0:break
        else:
            subdays.append(days_before)
            subtilt.append(tilt[d])
            d=d+1

    if len(subtilt)<10:
        #print "s0",
        return [],[],[], [], [], [] 
    
    subtilt=np.asarray(subtilt)
   
    s0 = UnivariateSpline(subdays, subtilt, s=0)
    d2s0=abs(s0(subdays,2))
    weight=[100-st.percentileofscore(d2s0, score, kind='rank') for score in d2s0]
    sf=round(np.var(d2s0)/100.,1)
    
    s = UnivariateSpline(subdays, subtilt, w=weight, s=sf)
    #s = UnivariateSpline(subdays, subtilt, w=weight, s=round(sf+s.get_residual(),2))

    if np.sum([a for a in np.isnan(s(subdays))])>0:
        s = UnivariateSpline(subdays, subtilt, w=weight)

    if days<=30:
        subdays_fine = np.linspace(min(subdays), max(subdays), (max(subdays)-min(subdays))*50)
    elif days<=90:
        subdays_fine = np.linspace(min(subdays), max(subdays), (max(subdays)-min(subdays))*3)
    else:
        subdays_fine = np.linspace(min(subdays), max(subdays), 100)
    subtilt_fine = s(subdays_fine)
    subdtilt_fine= s(subdays_fine,1)

    return subtilt, subdays, subtilt_fine, subdtilt_fine, subdays_fine, s
    
def day_to_date(days, end_date):
    date=[end_date+timedelta(days=x) for x in days]
    return date

def date_to_day(curdate, end_date):
    daysbefore=end_date-curdate
    daysbefore=(daysbefore.days+(daysbefore.seconds/(60*60*24.)))
    return -1*daysbefore

def update_proc_file(loc_col,num_nodes):
    print "\n"#Updating file ",loc_col+"_proc.csv...", 
    
    #     READING INPUT SENSOR DATA
    inputfname=loc_col+".csv"
    #check if raw file exists
    if os.path.exists(InputFilePath+inputfname)==0:
        print "Input file path does not exist for " + InputFilePath + inputfname
        return

    #check if processed file exists, and determines the number of lines in the file
    outputfname=loc_col+"_proc.csv"
    if os.path.exists(OutputFilePath+outputfname):
        fa1 = open(OutputFilePath+outputfname,'rb') 
        fa = csv.reader(fa1,delimiter=',')
        nL=len(list(fa))
        fa1.close()
    else:
        fa1 = open(OutputFilePath+outputfname,'wb')
        fa = csv.writer(fa1,delimiter=',')
        nL=0
        fa1.close()
    #checks and records the last date recorded in the processed files
    if nL==0:
        last_date_proc=datetime.combine(date(1999,1,1),time(0,0,0))
    else:
        fa1 = open(OutputFilePath+outputfname,'rb') 
        fa = csv.reader(fa1,delimiter=',')
        a=0
        for row in fa:
            if a==nL-1:strdate=row[0]
            a=a+1
        #print row[0]
        Y,m,d,H,M,S= int(strdate[0:4]), int(strdate[5:7]), int(strdate[8:10]), int(strdate[11:13]), int(strdate[14:16]), int(strdate[14:16])
        last_date_proc=datetime.combine(date(Y,m,d),time(H,M,S))
        fa1.close()
    #reads latest raw data and appends to the processed data file
    fa1 = open(OutputFilePath+outputfname,'ab')    
    fa = csv.writer(fa1,delimiter=',')
    fo1 = open(InputFilePath+inputfname, 'rb')
    fo = csv.reader(fo1,delimiter=',')
    lines_appended=0
    for i in fo:
        if i[2]=="id":continue
        strdate=i[0]
        Y,m,d,H,M,S= int(strdate[0:4]), int(strdate[5:7]), int(strdate[8:10]), int(strdate[11:13]), int(strdate[14:16]), int(strdate[17:19])
        if Y<2009:continue
        date_raw=datetime.combine(date(Y,m,d),time(H,M,S))
        if date_raw<=last_date_proc:
            continue
        else:
            dt=i[0]
            nodeID=i[2]
            x=i[3]
            y=i[4]
            z=i[5]
            tilt_data_filter=str(filter_good_data(int(x),int(y),int(z)))
            xz=str(fxz(int(x),int(y),int(z)))
            xy=str(fxy(int(x),int(y),int(z)))
            phi=str(fphi(int(y),int(z)))
            rho=str(frho(int(x),int(y),int(z)))
            moi=i[6]
            if int(moi)>=1000 and int(moi)<=10000:
                moifilter=str(1)
            else:moifilter=str(0)
            row=(dt,nodeID,x,y,z,tilt_data_filter,xz,xy,phi,rho,moi,moifilter)
            fa.writerow(row)
            lines_appended=lines_appended+1
    fa1.flush()
    #fa1.fsync()
    fa1.close()
    fo1.close()

    
#tilt functions
def fxz(x,y,z):  #tilt of column (from vertical) projected along the xz plane (parallel to downslope direction)
    if y==0 and x==0:xz=90
    else:xz=round(deg(atan(z/(sqrt(y*y+x*x)))),1)
    return xz
def fxy(x,y,z): #tilt of column (from vertical) projected along the xy plane (perpendicular to downslope direction)
    if x==0 and z==0:xy=90
    else:xy=round(deg(atan(y/(sqrt(z*z+x*x)))),1)
    return xy 
def fphi(y,z): #azimuth of column relative to the downslope direction 
    if z==0:
        if y>0:phi=90.0
        elif y<0:phi=270.0
        else:phi=0.0
    if z>0:
        if y>=0:phi=round(deg(atan(y/(z/1.0))),1)
        else:phi=round(360+deg(atan(y/(z/1.0))),1)
    if z<0:
        phi=round(180+deg(atan(y/(z/1.0))),1)
    return phi
def frho(x,y,z): #tilt of column (from vertical)
    if x==0:rho=90
    elif x>0:rho=round(deg(atan(sqrt(y*y+z*z)/(x))),1)
    else:rho=-round(deg(atan(sqrt(y*y+z*z)/(x))),1)
    return rho

#filter function
def filter_good_data(a1,a2,a3):
    threshold_dot_prod=0.05
    print_output_text=0
    filter=1
    temp2=(a1,a2,a3)
    temp1=array('i')
    for ax in temp2:
        new=0
        if new==0:
            #old individual axis filter:
            if ax<-1023:
                ax=ax+4096
                if ax>1223:
                    filter=0
                    break
                elif ax>1023:
                    ax=1023
                    temp1.append(ax)
                else:temp1.append(ax)
            elif ax<1024:
                temp1.append(ax)
                continue
            else:
                filter=0
                break
        else:
        #new individual axis filter as of July 9 2013
            if abs(ax)>1023 and abs(ax)<2970:
                filter=0
                break
            else:
                temp1.append(ax)
    if filter==0:
        return filter
    #arrange accel data into increasing values  (due to precision issues)
    temp_sort=np.sort(temp1)
    xa=temp_sort[0]
    ya=temp_sort[1]
    za=temp_sort[2]
    #given space defined by mutually perpendicular unit axes i^, j^, and k^
    #define accel axis inclinations from horizontal plane (i^j^) and corresponding cones in unit sphere
    alpha=(asin(xa/1023.0))     #inclination from horizontal plane
    xa_conew=1*cos(alpha)       #cone width, measured along i^j^ space
    xa_coneh=sin(alpha)         #cone height, measured along k^
    xa_k=xa_coneh
    xa_cone=sp.array([deg(alpha), xa_coneh, xa_conew])

    beta=(asin(ya/1023.0))
    ya_conew=1*cos(beta)
    ya_coneh=sin(beta)
    ya_k=ya_coneh
    ya_cone=sp.array([deg(beta), ya_coneh, ya_conew])

    gamma=(asin(za/1023.0))
    za_conew=1*cos(gamma)
    za_coneh=sin(gamma)
    za_k=za_coneh
    za_cone=sp.array([deg(gamma), za_coneh, za_conew])

    #arbitrarily set x-accel axis (minimum value) along plane i^k^
    xa_i=xa_conew
    xa_j=0
    xa_k=xa_coneh
    xa_ax=sp.array([xa_i, xa_j, xa_k])  #defining position of xa_ax

    #determine position of y-accel axis (intermediate value) from xa_ax and ya_coneh
    ya_k=ya_coneh
                #defining system of two equations
    fya = lambda y: [(pow(y[0],2)+pow(y[1],2)+pow(ya_k,2)-1),          #equation of cone rim
                     (xa_ax[0]*y[0] + xa_ax[1]*y[1] + xa_ax[2]*ya_k)]  #equation of dot product of xa and ya = 0    
                #solving for y[0] and y[1]
    y0 = scipy.optimize.fsolve(fya, [0.1, 0.1])         
    ya_i=y0[0]
    ya_j=y0[1]
                #defining 2 possible positions of ya_ax
    ya_ax_1=sp.array([ya_i, ya_j, ya_k])    
    ya_ax_2=sp.array([ya_i, -ya_j, ya_k])       
                #determining the appropriate ya_ax that produces a theoretical z-accel axis consistent with the sign of za
    za_k=za_coneh
    za_ax_t=sp.cross(xa_ax,ya_ax_1)     
    if (za_ax_t[2]+1)/(1+abs(za_ax_t[2]))==(1+za_k)/(1+abs(za_k)):
        ya_ax=ya_ax_1
    else:
        ya_ax=ya_ax_2
        za_ax_t=sp.cross(xa_ax,ya_ax_2)
    
    #determine position of z-accel axis (minimum value) from xa_ax and ya_ax using dot product function --> za_ax must be perpendicular to both xa_ax and ya_ax
    za_k=za_coneh
                #defining system of three equations
    gza = lambda z: [ (xa_ax[0]*z[0] + xa_ax[1]*z[1] + xa_ax[2]*za_k), #equation of dot product of xa and za = 0
                      (ya_ax[0]*z[0] + ya_ax[1]*z[1] + ya_ax[2]*za_k), #equation of dot product of ya and za = 0
                      (z[0]**2 + z[1]**2 + za_k**2 - 1)]               #equation of cone rim
                #solving for z[0] and z[1]
    z0,d,e,f= scipy.optimize.fsolve(gza, [ 0.1, 0.1, 0.1],full_output=1)   
    za_i=z0[0]  
    za_j=z0[1]  
    za_ax=sp.array([za_i,za_j,za_k])
    #checking the dot products of xa_ax, ya_ax, za_ax    
    if abs(sp.dot(xa_ax,ya_ax))>threshold_dot_prod or abs(sp.dot(ya_ax,za_ax))>threshold_dot_prod or abs(sp.dot(za_ax,xa_ax))>threshold_dot_prod: filter=0
    if print_output_text==1:
        np.set_printoptions(precision=2,suppress=True)
        print "xa:  ",xa_ax, round(sqrt(sum(i**2 for i in xa_ax)),4)
        print "ya:  ",ya_ax, round(sqrt(sum(i**2 for i in ya_ax)),4), round(sp.dot(xa_ax,ya_ax),4) 
        print "za_t:",za_ax_t, round(sqrt(sum(i**2 for i in za_ax_t)),4), round(sp.dot(xa_ax,za_ax_t),4), round(sp.dot(ya_ax,za_ax_t),4)
        print "za:  ",za_ax, round(sqrt(sum(i**2 for i in za_ax)),4), round(sp.dot(xa_ax,za_ax),4), round(sp.dot(ya_ax,za_ax),4), round(sp.dot(za_ax_t,za_ax),4)
        print abs(sp.dot(xa_ax,ya_ax)), abs(sp.dot(ya_ax,za_ax)), abs(sp.dot(za_ax,xa_ax)), filter        
    return filter


########################################################################

def GeneratePlots():
    #default legend parameters
    legend_font_props = font.FontProperties()
    legend_font_props.set_size('x-small')
    ncol=1
    bbtoa=(1,0.5)
    loc="center left"
    prop=legend_font_props

    print ColumnPropertiesFile

    fo = csv.reader(open(ColumnPropertiesFile, 'r'),delimiter=',')
    column_list = []
    for line in fo:
        col = ColumnArray(line[0], int(line[1]), float(line[2]))
        column_list.append(col)

    thresholdtilt=0.05 #degrees
    offsettilt=3

    thresholdvel=0.005 #degrees/day
    offsetvel=3
        
    cur_date=datetime.now()
    
    csvout=[]
    for column in column_list:

        #1    SELECTING COLUMN TO PLOT
            
        #************************************************************ defining input file name, number of nodes, name and segment lengths of columns
        # input_file_name -> "column_name"_proc.csv
        # num_nodes -> number of nodes per column
        # loc_col -> name of column
        # seg_len -> segment length of column
        input_file_name = OutputFilePath + column.name + "_proc.csv"        

        #************************************************************ updates database
        update_proc_file(column.name,column.nos)

        #************************************************************ creates array for whole data set
        all_nodes_data1=Create_Arrays_for_Input(column.nos)

        #************************************************************* reads text file into file objects and assigns data from file object into arrays
        all_nodes_data=Write_Input_File_to_Arrays(all_nodes_data1,input_file_name,column.seglen)
        if all_nodes_data==[]:
            print "Error reading data for column " + column.name
            continue

        #DEFINING DATE RANGE TO PLOT

        latest_record_time=datetime.combine(date(1999,1,1),time(0,0,0))   #initializes latest_record_time

        now_time=datetime.now()

        print "DATA for ",column.name," as of ", now_time.strftime("%Y-%m-%d %H:%M")    

        INPUT_fit_interval=3#(float(raw_input("Input # days before end date: ")))
        INPUT_days_to_plot=INPUT_fit_interval
        start_dt=now_time-timedelta(days=INPUT_fit_interval)
        INPUT_number_colpos=INPUT_fit_interval+1#int(raw_input("Input number of column positions to plot, including start and end dates: "))
        dates_to_plot=compute_colpos_time(now_time,INPUT_fit_interval,INPUT_number_colpos)
        #compute_plot_intervals(now_time,start_dt,INPUT_number_colpos)

        #EXTRACTING DATA WITHIN DATE RANGE

        allnodes_splinefit=range(column.nos)    
        
        allnodes_colpos_splinefit_X=np.ndarray(shape=(column.nos,INPUT_number_colpos))
        allnodes_colpos_splinefit_XZ=np.ndarray(shape=(column.nos,INPUT_number_colpos))
        allnodes_colpos_splinefit_XY=np.ndarray(shape=(column.nos,INPUT_number_colpos))

        colstatus=np.ndarray(shape=(column.nos,6),dtype=int)

        for INPUT_which_node in range(column.nos):
            colstatus[INPUT_which_node,0]=INPUT_which_node+1
            cur_node_data=all_nodes_data[INPUT_which_node]
            cur_node_date=cur_node_data[0]
            cur_node_tilt_xz=cur_node_data[1]
            cur_node_tilt_xy=cur_node_data[2]

            colstatus[INPUT_which_node,1]=1 #main dbase not updated

            xzsplinefit=[[],[],[],[],[],[]]
            xysplinefit=[[],[],[],[],[],[]]
            curnode_splinefit=[xzsplinefit, xysplinefit]
            allnodes_splinefit[INPUT_which_node]=curnode_splinefit

            #if len(cur_node_date)==0:continue

            if len(cur_node_date)==0:
                colpos_xztilt=np.zeros(INPUT_number_colpos)
                colpos_xytilt=np.zeros(INPUT_number_colpos)
            else:
                colpos_xztilt=np.asarray([cur_node_tilt_xz[-1] *(g/g) for g in range(1,INPUT_number_colpos+1)])
                colpos_xytilt=np.asarray([cur_node_tilt_xy[-1] *(h/h) for h in range(1,INPUT_number_colpos+1)])

                if cur_node_date[-1]>=now_time-timedelta(days=1.):
                    #computing spline fit of xz tilt of current node within defined date range
                    subtilt, subdays, subtilt_fine, subdtilt_fine, subdays_fine,spline = fitspline_tilt(cur_node_date,cur_node_tilt_xz,INPUT_days_to_plot,now_time)     
                    xzsplinefit=[subtilt, subdays, subtilt_fine, subdtilt_fine, subdays_fine,spline]

                    if subdays<-1 or len(subdays)==0:
                        #sub dbase not updated
                        py=0
                    else:
                        if np.sum([a for a in np.isnan(subtilt)])>0 or np.sum([b for b in np.isnan(subtilt_fine)])>0:
                            # dbase updated, spline fit failed
                            py=0
                        else:
                            colpos_xztilt=extract_tilt_for_colpos(spline, dates_to_plot, min(subdays), max(subdays))
                            
                            
                            #computing spline fit of xy tilt of current node within defined date range
                            subtilt, subdays, subtilt_fine, subdtilt_fine, subdays_fine,spline = fitspline_tilt(cur_node_date,cur_node_tilt_xy,INPUT_days_to_plot,now_time)     
                            xysplinefit=[subtilt, subdays, subtilt_fine, subdtilt_fine, subdays_fine,spline]
                        
                            if subdays<-1 or len(subdays)==0:
                                #sub dbase not updated
                                py=0
                            else:
                                if np.sum([a for a in np.isnan(subtilt)])>0 or np.sum([b for b in np.isnan(subtilt_fine)])>0:
                                    # dbase updated, spline fit failed
                                    py=0
                                else:
                                    #dbase updated, spline fit successful
                                    colpos_xytilt=extract_tilt_for_colpos(spline, dates_to_plot, min(subdays), max(subdays))
                                    colstatus[INPUT_which_node,1]=0  
                                    curnode_splinefit=[xzsplinefit, xysplinefit]
                                    allnodes_splinefit[INPUT_which_node]=curnode_splinefit
            
           
            X,XZ,XY=xzxy_to_cart2(column.seglen, colpos_xztilt, colpos_xytilt)
            for q in range(INPUT_number_colpos):
                allnodes_colpos_splinefit_X[INPUT_which_node,q]=round(X[q],2)
                allnodes_colpos_splinefit_XZ[INPUT_which_node,q]=round(XZ[q],4)
                allnodes_colpos_splinefit_XY[INPUT_which_node,q]=round(XY[q],4)
            
       
        got=1

        if got==1:
            printfigures=0
            Tvela1=0.005 #m/day
            Tvela2=0.5 #m/day
            Ttilt=0.05 #m
            op_axis_k=0.1
            adj_node_k=0.5

            print column.name, now_time.strftime("%Y-%m-%d %H:%M")

            #def evaluate_alert(allnodes_splinefit,column.nos,Tvela1,Tvela2,Ttilt,op_axis_k, adj_node_k):
            
            for cur_node in range(column.nos):
                nodealert=-1
                curnode_splinefit=allnodes_splinefit[cur_node]
                xzsplinefit=curnode_splinefit[0]
                xysplinefit=curnode_splinefit[1]
                xzdays=xzsplinefit[4]
                xztilt=xzsplinefit[2]
                if len(xztilt)==0:
                    out=[cur_node+1,-1]
                    
##                    print out
                    csvout.append([now_time.strftime("%Y-%m-%d %H:%M"),column.name,
                               str(cur_node+1),
                               str(nodealert)])
                    continue
                xzvel=xzsplinefit[3]

                xytilt=xysplinefit[2]
                xyvel=xysplinefit[3]

                if abs(xzvel[-1])>=abs(xyvel[-1]):
                    if abs(xzvel[-1])>Tvela1:
                        if abs(xztilt[-1]-xztilt[0])<=Ttilt:
                            nodealert=0
                        else:
                            if abs(xzvel[-1])<=Tvela2:
                                if abs(xyvel[-1])>op_axis_k*abs(xzvel[-1]):
                                    nodealert=1
                                else:
                                    nodealert=0
                            else:
                                if abs(xyvel[-1])>op_axis_k*abs(xzvel[-1]):
                                    nodealert=2
                                else:
                                    nodealert=0
                    else:
                        nodealert=0
                else:
                    if abs(xyvel[-1])>Tvela1:
                        if abs(xytilt[-1]-xytilt[0])<=Ttilt:
                            nodealert=0
                        else:
                            if abs(xyvel[-1])<=Tvela2:
                                if abs(xzvel[-1])>op_axis_k*abs(xyvel[-1]):
                                    nodealert=1
                                else:
                                    nodealert=0
                            else:
                                if abs(xzvel[-1])>op_axis_k*abs(xyvel[-1]):
                                    nodealert=2
                                else:
                                    nodealert=0
                    else:
                        nodealert=0
                        
                out=[cur_node+1,nodealert,round(xztilt[-1]-xztilt[0],2),round(xzvel[-1],3),round(xytilt[-1]-xytilt[0],2),round(xyvel[-1],3)]

                if nodealert > 0:
                    print out

                csvout.append([now_time.strftime("%Y-%m-%d %H:%M"),column.name,
                               str(cur_node+1),
                               str(nodealert),
                               str(round(xztilt[-1]-xztilt[0],2)),
                               str(round(xzvel[-1],3)),
                               str(round(xytilt[-1]-xytilt[0],2)),
                               str(round(xyvel[-1],3))])
                
                if nodealert>=0:
                    printfigures=printfigures+1
                      
                    
               
        if PrintFigures:
        
            #PLOTTING COLUMN POSITION
            ac_X,ac_XZ, ac_XY=accumulate_translate(allnodes_colpos_splinefit_X,allnodes_colpos_splinefit_XZ,
                                                   allnodes_colpos_splinefit_XY, column.nos, INPUT_number_colpos,dates_to_plot,
                                                   column.name)
                    

            #PLOTTING SPLINE-FITTED TIME SERIES (TILT, VELOCITY) WITHIN DATE RANGE
            for INPUT_which_axis in [0,1]:
                tiltvelfig=plt.figure(10+INPUT_which_axis)
                plt.clf()
                axtilt=tiltvelfig.add_subplot(121)
                axvel=tiltvelfig.add_subplot(122, sharex=axtilt)
                
                if INPUT_which_axis==0:
                    tiltvelfig.suptitle(column.name+" XZ as of "+str(now_time.strftime("%Y-%m-%d %H:%M")))
                else:
                    tiltvelfig.suptitle(column.name+" XY as of "+str(now_time.strftime("%Y-%m-%d %H:%M")))

                for INPUT_which_node in range(column.nos):
                    #extracting data from array
                    curnode_splinefit=allnodes_splinefit[INPUT_which_node]
                    
                    curaxsplinefit=curnode_splinefit[INPUT_which_axis]
                    subtilt=curaxsplinefit[0]
                    subdays=curaxsplinefit[1]
                    subtilt_fine=curaxsplinefit[2]
                    subdtilt_fine=curaxsplinefit[3]
                    subdays_fine=curaxsplinefit[4]
                    spline =curaxsplinefit[5]

                    subdates=day_to_date(subdays, now_time)
                    subdates_fine=day_to_date(subdays_fine, now_time)
                                    
                    axtilt.axhspan(offsettilt*thresholdtilt*(column.nos-(INPUT_which_node))-thresholdtilt,offsettilt*thresholdtilt*(column.nos-(INPUT_which_node))+thresholdtilt,color='0.9')
                    axtilt.axhline(y=(offsettilt*thresholdtilt*(column.nos-(INPUT_which_node))),color='0.6')
                    axtilt.plot(subdates, [offsettilt*thresholdtilt*(column.nos-(INPUT_which_node))+ (q-subtilt_fine[0]) for q in subtilt], '+-', color='0.4')
                    axtilt.plot(subdates_fine, [offsettilt*thresholdtilt*(column.nos-(INPUT_which_node))+ (q-subtilt_fine[0]) for q in subtilt_fine], '-',linewidth=1,label="n"+str(INPUT_which_node+1))
                    

                    axvel=tiltvelfig.add_subplot(122, sharex=axtilt)
                    
                    offsetvel=0
                    #axvel.axhspan(offsetvel*thresholdvel*(column.nos-(INPUT_which_node))-thresholdvel,offsetvel*thresholdvel*(column.nos-(INPUT_which_node))+thresholdvel,color='0.9')
                    #axvel.axhline(y=(offsetvel*thresholdvel*(column.nos-(INPUT_which_node))),color='0.6')
                    axvel.plot(subdates_fine, [offsetvel*thresholdvel*(column.nos-(INPUT_which_node))+ q for q in subdtilt_fine], '-',linewidth=1,label="n"+str(INPUT_which_node+1))
                    

            
                days_vlines=[now_time+timedelta(days=-q) for q in range(0,int(INPUT_fit_interval)+1)]
                for dvl in range(len(days_vlines)):
                    if dvl!=0:lw=(0.2)
                    else:lw=(1)
                    plt.sca(axtilt)
                    axtilt.axvline(x=days_vlines[dvl], color='r',lw=lw)
                    plt.sca(axvel)
                    axvel.axvline(x=days_vlines[dvl], color='r',lw=lw)

                for cpvl in range(len(dates_to_plot)):
                    plt.sca(axtilt)
                    axtilt.axvline(x=dates_to_plot[cpvl], color='b',lw=0.5)
                    
                #plt.figure(tiltvelfig.number)
                plt.sca(axtilt)
                cax=plt.gca()
                cax.yaxis.set_major_locator(MaxNLocator(4))
                cax.yaxis.set_minor_locator(AutoMinorLocator(4))
                cax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d %H:%M')
                plt.xlim(now_time+timedelta(days=-INPUT_fit_interval),now_time+timedelta(days=0))    
                plt.ylabel("displacement (m)")
                plt.xlabel("date,time")
                

                plt.figure(tiltvelfig.number)
                plt.sca(axvel)
                cax=plt.gca()
                axvel.axhline(y=0.005,color='y', ls=':',lw=3,label="A1: Slow")
                axvel.axhline(y=.50,color='r', ls=':',lw=3,label="A2: Mod")
                axvel.axhline(y=-0.005,color='y', ls=':',lw=3,)
                axvel.axhline(y=-.50,color='r', ls=':',lw=3,)
                
                cax.yaxis.set_major_locator(MaxNLocator(4))
                cax.yaxis.set_minor_locator(AutoMinorLocator(4))
                cax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d %H:%M')
                plt.yscale('symlog', linthreshy=.01,linscaley=1)
                plt.ylim(-1,1)
                plt.xlabel("date,time")
                plt.ylabel("velocity (m/day)")
                #plt.legend()
                cax.legend(ncol=1,loc="upper left", bbox_to_anchor=(1,1),prop=legend_font_props)

                tiltvelfig.autofmt_xdate()

                if INPUT_which_axis==0:
                    fig_name=OutputFigurePath+column.name+"_xz.png"
                else:
                    fig_name=OutputFigurePath+column.name+"_xy.png"

                plt.savefig(fig_name, dpi=100, facecolor='w', edgecolor='w',orientation='landscape')
            
            
        #plt.show()
    csvout=np.asarray(csvout)
    with open(CSVOutputFile, "wb") as f:
        writer = csv.writer(f)
        writer.writerows(csvout)
        print "\nAlert file written"
##        check_another_sensor=2#int(raw_input("Choose another sensor? (1) Yes     (2) No : "))

# get configuration settings from configuration file
cfg = ConfigParser.ConfigParser()
cfg.read('node-alerts-config.txt')

InputFilePath = cfg.get('I/O','InputFilePath')
OutputFilePath = cfg.get('I/O','OutputFilePath')
OutputFigurePath = cfg.get('I/O','OutputFigurePath')
PrintFigures = cfg.getboolean('I/O','PrintFigures')
CSVOutputFile = cfg.get('I/O','CSVOutputFilePath') + cfg.get('I/O','CSVOutputFile')
ColumnPropertiesFile = cfg.get('I/O','ColumnPropertiesFile')


#MAIN

#AutoGeneratePlots()
##GeneratePlots()







 
