import os
import sys
import time
from datetime import datetime
import pandas as pd

path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../updews-pycodes/Analysis/'))
if not path in sys.path:
   sys.path.insert(1, path)
del path

import vcdgen as vcd
# import querySenslopeDb as qs
    
def getDF():

#        site = 'agbsb'
#        fdate = ''
#        tdate = ''
        
        site = sys.argv[1]
        fdate = sys.argv[2].replace("n",'')
        tdate = sys.argv[3].replace("n",'')
        df= vcd.vcdgen(site, tdate, fdate,1)

        print df

    
getDF();
