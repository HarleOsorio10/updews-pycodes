# -*- coding: utf-8 -*-
"""
Created on Wed Jan 20 18:10:45 2016

@author: SENSLOPEY
"""

import pandas as pd
import querySenslopeDb as qDb



column = raw_input('Enter column name: ')
gid = int(raw_input('Enter id: '))

def getsomsrawdata(column="", gid=0):
    ''' 
        only for landslide sensors v2 and v3
        output:  df = unfiltered SOMS data (calibrated and raw) of a specific node of the defined column 
        param:
            column = column name (ex. laysa)
            gid = geographic id of node [1-40]
    '''
    
    v2=['NAGSA', 'BAYSB', 'AGBSB', 'MCASB', 'CARSB', 'PEPSB','BLCSA']
    df = pd.DataFrame(columns=['sraw', 'scal'])
    
    try:
        soms = qDb.GetSomsData(siteid=column)
    except:
        print 'No data available for ' + column.upper()
        return df
        
    soms.index = soms.ts

    if column.upper() in v2:
        if column.upper()=='NAGSA':
            df.sraw =(((8000000/(soms.mval1[(soms.msgid==21) & (soms.id==gid)]))-(8000000/(soms.mval2[(soms.msgid==21) & (soms.id==gid)])))*4)/10
            df.scal=soms.mval1[(soms.msgid==26) & (soms.id==gid)]
        else:
            df.sraw =(((20000000/(soms.mval1[(soms.msgid==21) & (soms.id==gid)]))-(20000000/(soms.mval2[(soms.msgid==21) & (soms.id==gid)])))*4)/10
            df.scal=soms.mval1[(soms.msgid==112) & (soms.id==gid)]
        
    else: # if version 3
        df.sraw=soms.mval1[(soms.msgid==110) & (soms.id==gid)]
        df.scal=soms.mval1[(soms.msgid==113) & (soms.id==gid)]
        
    return df

