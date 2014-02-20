##############################################################################
## This module reads and checks purged file and appends the processed file. ##
##############################################################################


import os
import csv
import math
import numpy as np
import scipy as sp
import scipy.optimize
import ConfigParser

from array import *
from datetime import datetime, date, time, timedelta

tan=math.tan
sin=math.sin
asin=math.asin
cos=math.cos
pow=math.pow
sqrt=math.sqrt
atan=math.atan
deg=math.degrees
rad=math.radians

loc_col_list=("eeet","sinb_purged","sint_purged","sinu_purged","lipb_purged","lipt_purged","bolb_purged","pugb_purged","pugt_purged","mamb_purged","mamt_purged","oslt_purged","oslb_purged","labt_purged", "labb_purged", "gamt_purged","gamb_purged", "humt_purged","humb_purged", "plat_purged","plab_purged","blct_purged","blcb_purged")
num_nodes_loc_col=(14,29,19,29,28,31,30,14,10,29,24,21,23,39,25,18,22,21,26,39,40,24,19)
col_seg_len_list=(0.5,1,1,1,0.5,0.5,0.5,1.2,1.2,1.0,1.0,1.,1.,1.,1.,1.,1.,1.,1,0.5,0.5,1,1)


############################################################
##                  INPUT FILE READER                     ##
############################################################

def Input_Loc_Col(loc_col_list,num_nodes_loc_col,col_seg_len_list,IWS):
    loc_col=loc_col_list[IWS]
    num_nodes=num_nodes_loc_col[IWS]
    fname=loc_col+"_proc.csv"
    seg_len=col_seg_len_list[IWS]
    return fname, num_nodes,loc_col,seg_len


############################################################
##                   UPDATE FUNCTION                      ##
############################################################

def update_proc_file(loc_col,num_nodes):
    print "Updating file",loc_col+"_proc.csv..."
    
    inputfname=loc_col+".csv"
    print inputfname

    ##checks if raw file exists##
    if os.path.exists(InputFilePath+inputfname)==0:
        print "Input file path does not exist for " + InputFilePath + inputfname
        print "Update failed!\n"
        return

    ##checks if processed file exists, determines the number of lines in the file##
    outputfname=loc_col+"_proc.csv"
    if os.path.exists(OutputFilePath+outputfname):
        fa1 = open(OutputFilePath+outputfname,'rb') 
        fa = csv.reader(fa1,delimiter=',')
        nL=len(list(fa))
        fa1.close()
        print "Update successful!\n"

    else:
        fa1 = open(OutputFilePath+outputfname,'wb')
        fa = csv.writer(fa1,delimiter=',')
        nL=0
        fa1.close()

    ##checks, records the last date recorded in the processed files##
    if nL==0:
        last_date_proc=datetime.combine(date(1999,1,1),time(0,0,0))

    else:
        fa1 = open(OutputFilePath+outputfname,'rb') 
        fa = csv.reader(fa1,delimiter=',')
        a=0

        for row in fa:
            if a==nL-1:strdate=row[0]
            a=a+1
        
        Y,m,d,H,M,S= int(strdate[0:4]), int(strdate[5:7]), int(strdate[8:10]), int(strdate[11:13]), int(strdate[14:16]), int(strdate[14:16])
        last_date_proc=datetime.combine(date(Y,m,d),time(H,M,S))
        fa1.close()

    ##reads latest raw data and appends to the processed data file##
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

            if moi=='':
                moi=str(-1)
            if int(moi)>=1000 and int(moi)<=10000:
                moifilter=str(1)

            else:moifilter=str(0)
            row=(dt,nodeID,x,y,z,tilt_data_filter,xz,xy,phi,rho,moi,moifilter)
            fa.writerow(row)
            lines_appended=lines_appended+1

    fa1.flush()
    fa1.close()
    fo1.close()


############################################################
##                     TILT FUNCTIONS                     ##
############################################################

def fxz(x,y,z):  ##tilt of column (from vertical) projected along the xz plane (parallel to downslope direction)##
    if y==0 and x==0:xz=90
    else:xz=round(deg(atan(z/(sqrt(y*y+x*x)))),1)

    return xz

def fxy(x,y,z): ##tilt of column (from vertical) projected along the xy plane (perpendicular to downslope direction)##
    if x==0 and z==0:xy=90
    else:xy=round(deg(atan(y/(sqrt(z*z+x*x)))),1)

    return xy 

def fphi(y,z): ##azimuth of column relative to the downslope direction##
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

def frho(x,y,z): ##tilt of column from vertical##
    if x==0:rho=90
    elif x>0:rho=round(deg(atan(sqrt(y*y+z*z)/(x))),1)
    else:rho=-round(deg(atan(sqrt(y*y+z*z)/(x))),1)

    return rho


############################################################
##                   FILTER FUNCTION                      ##
############################################################

def filter_good_data(a1,a2,a3):
    threshold_dot_prod=0.05
    print_output_text=0
    filter=1
    temp2=(a1,a2,a3)
    temp1=array('i')

    for ax in temp2:
        new=0

        if new==0:
            ##old individual axis filter##
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
            ##new individual axis filter##
            if abs(ax)>1023 and abs(ax)<2970:
                filter=0
                break

            else:
                temp1.append(ax)

    if filter==0:
        return filter

    ##arranges accel data into increasing values (due to precision issues)##
    temp_sort=np.sort(temp1)
    xa=temp_sort[0]
    ya=temp_sort[1]
    za=temp_sort[2]

    ##defines accel axis inclinations from horizontal plane (i^j^) and corresponding cones in unit sphere##
    ##given space defined by mutually perpendicular unit axes i^, j^, and k^##
    alpha=(asin(xa/1023.0))     ##inclination from horizontal plane##
    xa_conew=1*cos(alpha)       ##cone width, measured along i^j^ space##
    xa_coneh=sin(alpha)         ##cone height, measured along k^##
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

    ##arbitrarily sets x-accel axis (minimum value) along plane i^k^##
    xa_i=xa_conew
    xa_j=0
    xa_k=xa_coneh
    xa_ax=sp.array([xa_i, xa_j, xa_k])  ##defines position of xa_ax##

    ##determines position of y-accel axis (intermediate value) from xa_ax and ya_coneh##
    ya_k=ya_coneh

    ##defines system of two equations##
    fya = lambda y: [(pow(y[0],2)+pow(y[1],2)+pow(ya_k,2)-1),          ##equation of cone rim##
                     (xa_ax[0]*y[0] + xa_ax[1]*y[1] + xa_ax[2]*ya_k)]  ##equation of dot product of xa and ya = 0## 

    ##solves for y[0] and y[1]##
    y0 = scipy.optimize.fsolve(fya, [0.1, 0.1])         
    ya_i=y0[0]
    ya_j=y0[1]

    ##defines 2 possible positions of ya_ax##
    ya_ax_1=sp.array([ya_i, ya_j, ya_k])    
    ya_ax_2=sp.array([ya_i, -ya_j, ya_k])       

    ##determines the appropriate ya_ax that produces a theoretical z-accel axis consistent with the sign of za##
    za_k=za_coneh
    za_ax_t=sp.cross(xa_ax,ya_ax_1)     

    if (za_ax_t[2]+1)/(1+abs(za_ax_t[2]))==(1+za_k)/(1+abs(za_k)):
        ya_ax=ya_ax_1

    else:
        ya_ax=ya_ax_2
        za_ax_t=sp.cross(xa_ax,ya_ax_2)
    
    ##determines position of z-accel axis (minimum value) from xa_ax and ya_ax using dot product function##
    ##za_ax must be perpendicular to both xa_ax and ya_ax##
    za_k=za_coneh

    ##defines system of three equations##
    gza = lambda z: [ (xa_ax[0]*z[0] + xa_ax[1]*z[1] + xa_ax[2]*za_k), ##equation of dot product of xa and za = 0##
                      (ya_ax[0]*z[0] + ya_ax[1]*z[1] + ya_ax[2]*za_k), ##equation of dot product of ya and za = 0##
                      (z[0]**2 + z[1]**2 + za_k**2 - 1)]               ##equation of cone rim##

    ##solving for z[0] and z[1]##
    z0,d,e,f= scipy.optimize.fsolve(gza, [ 0.1, 0.1, 0.1],full_output=1)   
    za_i=z0[0]  
    za_j=z0[1]  
    za_ax=sp.array([za_i,za_j,za_k])

    ##checking the dot products of xa_ax, ya_ax, za_ax##
    if abs(sp.dot(xa_ax,ya_ax))>threshold_dot_prod or abs(sp.dot(ya_ax,za_ax))>threshold_dot_prod or abs(sp.dot(za_ax,xa_ax))>threshold_dot_prod: filter=0
    if print_output_text==1:
        np.set_printoptions(precision=2,suppress=True)
        print "xa:  ",xa_ax, round(sqrt(sum(i**2 for i in xa_ax)),4)
        print "ya:  ",ya_ax, round(sqrt(sum(i**2 for i in ya_ax)),4), round(sp.dot(xa_ax,ya_ax),4) 
        print "za_t:",za_ax_t, round(sqrt(sum(i**2 for i in za_ax_t)),4), round(sp.dot(xa_ax,za_ax_t),4), round(sp.dot(ya_ax,za_ax_t),4)
        print "za:  ",za_ax, round(sqrt(sum(i**2 for i in za_ax)),4), round(sp.dot(xa_ax,za_ax),4), round(sp.dot(ya_ax,za_ax),4), round(sp.dot(za_ax_t,za_ax),4)
        print abs(sp.dot(xa_ax,ya_ax)), abs(sp.dot(ya_ax,za_ax)), abs(sp.dot(za_ax,xa_ax)), filter        
    return filter


######################################################################
##                         MAIN PROGRAM                             ##
######################################################################

##gets configuration from file##
cfg = ConfigParser.ConfigParser()
cfg.read('IO-config.txt')

InputFilePath = cfg.get('I/O','InputFilePath')
OutputFilePath = cfg.get('I/O','OutputFilePath')
OutputFigurePath = cfg.get('I/O','OutputFigurePath')
PrintFigures = cfg.getboolean('I/O','PrintFigures')
CSVOutputFile = cfg.get('I/O','CSVOutputFilePath') + cfg.get('I/O','CSVOutputFile')

for INPUT_which_sensor in range(len(loc_col_list)):
    input_file_name,num_nodes,loc_col,seg_len=Input_Loc_Col(loc_col_list,num_nodes_loc_col,col_seg_len_list, INPUT_which_sensor)
    input_file_name=OutputFilePath+input_file_name

    update_proc_file(loc_col,num_nodes)
