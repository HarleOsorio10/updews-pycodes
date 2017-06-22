import os,time,serial,re,sys,traceback
import MySQLdb, subprocess
from datetime import datetime as dt
from datetime import timedelta as td
import serverdbio as dbio
import somsparser as ssp
import mainserver as server
import cfgfileio as cfg
import argparse
import queryserverinfo as qsi
import lockscript as lock
import alertmessaging as amsg
import memcache
import lockscript
import gsmio
import surficialparser as surfp
mc = memcache.Client(['127.0.0.1:11211'],debug=0)

def update_last_msg_received_table(txtdatetime,name,sim_num,msg):
    query = """insert into senslopedb.last_msg_received
                (timestamp,name,sim_num,last_msg)
                values ('%s','%s','%s','%s')
                on DUPLICATE key update
                timestamp = '%s',
                sim_num = '%s',
                last_msg = '%s'""" %(txtdatetime,name,sim_num,msg,txtdatetime,sim_num,msg)
                
    dbio.commit_to_db(query, 'update_last_msg_received_table')
    
def update_sim_num_table(name,sim_num,date_activated):
    return
    db, cur = dbio.db_connect('local')
    
    query = """INSERT IGNORE INTO site_column_sim_nums (name,sim_num,date_activated)
                VALUES ('%s','%s','%s')""" %( name.upper(),sim_num,date_activated)

    dbio.commit_to_db(query, 'update_sim_num_table')

def check_name_of_number(number):
    db, cur = dbio.db_connect()
    
    while True:
        try:
            query = """select logger_name from loggers where 
                logger_id = (select logger_id from logger_mobile 
                where sim_num = '%s' order by date_activated desc limit 1) """ % (number)
                
            a = cur.execute(query)
            if a:
                out = cur.fetchall()
                return out[0][0]                    
            else:
                print '>> Number not in database', number
                return ''
        except MySQLdb.OperationalError:
        # except KeyboardInterrupt:
            print '4.',        
            time.sleep(2)
            
    db.close()

def twos_comp(hexstr):
    # print hexstr
    num = int(hexstr[2:4]+hexstr[0:2],16)
    if len(hexstr) == 4:
        sub = 65536
    else:
        sub = 4096
    if num > 2048:  
        return num - sub
    else:
        return num

def process_two_accle_col_data(sms):
    msg = sms.data
    sender = sms.simnum
    txtdatetime = sms.dt
    
    if len(msg.split(",")) == 3:
        print ">> Editing old data format"
        datafield = msg.split(",")[1]
        dtype = datafield[2:4].upper()
        if dtype == "20" or dtype == "0B":
            dtypestr = "x"
        elif dtype == "21" or dtype == "0C":
            dtypestr = "y"
        elif dtype == "6F" or dtype == "15":
            dtypestr = "b"
        elif dtype == "70" or dtype == "1A":
            dtypestr = "c"
        else:
            raise ValueError(">> Data type" + dtype + "not recognized")
            
        
        i = msg.find(",")
        msg = msg[:i] + "*" + dtypestr + "*" + msg[i+1:]
        msg = msg.replace(",","*").replace("/","")
        
    outl = []
    msgsplit = msg.split('*')
    tsm_name = msgsplit[0] # column id

    if len(msgsplit) != 4:
        print 'wrong data format'
        # print msg
        return

    if len(tsm_name) != 5:
        print 'wrong master name'
        return

    print msg

    dtype = msgsplit[1].upper()
   
    datastr = msgsplit[2]
    
    if len(datastr) == 136:
        datastr = datastr[0:72] + datastr[73:]
    
    ts = msgsplit[3].strip()
  
    if datastr == '':
        datastr = '000000000000000'
        print ">> Error: No parsed data in sms"
        return
   
    if len(ts) < 10:
       print '>> Error in time value format: '
       return
    
    ts_patterns = ['%y%m%d%H%M%S', '%Y-%m-%d %H:%M:%S']
    # timestamp = "20"+ts[0:2]+"-"+ts[2:4]+"-"+ts[4:6]+" "+ts[6:8]+":"+ts[8:10]+":00"
    #print '>>',
    #print timestamp
    #timestamp = dt.strptime(txtdatetime,'%y%m%d%H%M').strftime('%Y-%m-%d %H:%M:00')
    timestamp = ''
    ts = re.sub("[^0-9]","",ts)
    for pattern in ts_patterns:
        try:
            timestamp = dt.strptime(ts,pattern).strftime('%Y-%m-%d %H:%M:00')
            break
        except ValueError:
            print "Error: wrong timestamp format", ts, "for pattern", pattern
 
    if timestamp == '':
        raise ValueError(">> Error: Unrecognized timestamp pattern " + ts)

    update_sim_num_table(tsm_name,sender,timestamp[:8])

 # PARTITION the message into n characters
    if dtype == 'Y' or dtype == 'X':
       n = 15
       # PARTITION the message into n characters
       sd = [datastr[i:i+n] for i in range(0,len(datastr),n)]
    elif dtype == 'B':
        # do parsing for datatype 'B' (SOMS RAW)
        outl = ssp.soms_parser(msg,1,10,0)       
        for piece in outl:
            print piece
    elif dtype == 'C':
        # do parsing for datatype 'C' (SOMS CALIB/NORMALIZED)
        outl = ssp.soms_parser(msg,2,7,0)
        for piece in outl:
            print piece
    else:
        raise IndexError("Undefined data format " + dtype )
    
    # do parsing for datatype 'X' or 'Y' (accel data)
    if dtype.upper() == 'X' or dtype.upper() =='Y':
        outl = []
        for piece in sd:
            try:
                # print piece
                ID = int(piece[0:2],16)
                msgID = int(piece[2:4],16)
                xd = twos_comp(piece[4:7])
                yd = twos_comp(piece[7:10])
                zd = twos_comp(piece[10:13])
                bd = (int(piece[13:15],16)+200)/100.0
                line = [tsm_name,timestamp,ID,msgID,xd,yd,zd,bd]
                print line
                outl.append(line)
            except ValueError:
                print ">> Value Error detected.", piece,
                print "Piece of data to be ignored"
    
    spawn_alert_gen(tsm_name,timestamp)

    return outl

def write_two_accel_data_to_db(dlist,msgtime):
    query = ("INSERT IGNORE INTO tilt_%s (ts,node_id,type_num,xval,yval,zval,"
        "batt) VALUES ") % (str(dlist[0][0].lower()))
    
    for item in dlist:
        timetowrite = str(item[1])
        query = query + """('%s',%s,%s,%s,%s,%s,%s),""" % (timetowrite,
            str(item[2]),str(item[3]),str(item[4]),str(item[5]),str(item[6]),
            str(item[7]))

    query = query[:-1]
    # print len(query)
    
    dbio.commit_to_db(query, 'write_two_accel_data_to_db')
   
def write_soms_data_to_db(dlist,msgtime):
    query = """INSERT IGNORE INTO soms_%s (ts,node_id,type_num,mval1,mval2) VALUES """ % (str(dlist[0][0].lower()))
    
    print "site_name", str(dlist[0][0])
    
    for item in dlist:            
        timetowrite = str(item[1])
        query = query + """('%s',%s,%s,%s,%s),""" % (timetowrite,str(item[2]),str(item[3]),str(item[4]),str(item[5]))

    query = query[:-1]
    query = query.replace("nan","NULL")
    
    dbio.commit_to_db(query, 'write_soms_data_to_db')
    
def pre_process_col_v1(sms):
    data = sms.data
    data = data.replace("DUE","")
    data = data.replace(",","*")
    data = data.replace("/","")
    data = data[:-2]
    return data
    
def process_column_v1(sms):
    line = sms.data
    txtdatetime = sms.dt
    sender = sms.simnum

    tsm_name = line[0:4]
    print 'SITE: ' + tsm_name
    ##msgdata = line[5:len(line)-11] #data is 6th char, last 10 char are date
    msgdata = (line.split('*'))[1]
    print 'raw data: ' + msgdata
    #getting date and time
    #msgdatetime = line[-10:]
    try:
        timestamp = (line.split('*'))[2][:10]
        print 'date & time: ' + timestamp
    except:
        print '>> Date and time defaults to SMS not sensor data'
        timestamp = txtdatetime

    # col_list = cfg.get("Misc","AdjustColumnTimeOf").split(',')
    if tsm_name == 'PUGB':
        timestamp = txtdatetime
        print "date & time adjusted " + timestamp
    else:
        timestamp = dt.strptime(timestamp,'%y%m%d%H%M').strftime('%Y-%m-%d %H:%M:00')
        print 'date & time no change'
        
    dlen = len(msgdata) #checks if data length is divisible by 15
    #print 'data length: %d' %dlen
    nodenum = dlen/15
    #print 'number of nodes: %d' %nodenum
    if dlen == 0:
        print 'Error: There is NO data!'
        return 
    elif((dlen % 15) == 0):
        #print 'Data has correct length!'
        valid = dlen
    else:
        print 'Warning: Excess data will be ignored!'
        valid = nodenum*15
        
    update_sim_num_table(tsm_name,sender,timestamp[:10])
        
    query_tilt = """INSERT IGNORE INTO tilt_%s (ts,node_id,xval,yval,zval) VALUES """ % (str(tsm_name.lower()))
    query_soms = """INSERT IGNORE INTO soms_%s (ts,node_id,mval1) VALUES """ % (str(tsm_name.lower()))
    
    try:    
        i = 0
        while i < valid:
            #NODE ID
            #parsed msg.data - NODE ID:
            node_id = int('0x' + msgdata[i:i+2],16)
            i=i+2
            
            #X VALUE
            #parsed msg.data - TEMPX VALUE:
            tempx = int('0x' + msgdata[i:i+3],16)
            i=i+3
            
            #Y VALUE
            #parsed msg.data - TEMPY VALUE:
            tempy = int('0x' + msgdata[i:i+3],16)
            i=i+3
            
            #Z VALUE
            #parsed msg.data - ZVALUE:
            tempz = int('0x' + msgdata[i:i+3],16)
            i=i+3
            
            #M VALUE
            #parsed msg.data - TEMPF VALUE:
            tempf = int('0x' + msgdata[i:i+4],16)
            i=i+4
            
            valueX = tempx
            if valueX > 1024:
	            valueX = tempx - 4096

            valueY = tempy
            if valueY > 1024:
	            valueY = tempy - 4096

            valueZ = tempz
            if valueZ > 1024:
	            valueZ = tempz - 4096

            valueF = tempf #is this the M VALUE?

            query_tilt += """('%s',%d,%d,%d,%d),""" % (str(timestamp),node_id,valueX,valueY,valueZ)
            query_soms += """('%s',%d,%d),""" % (str(timestamp),node_id,valueF)

            print "%s\t%s\t%s\t%s\t%s" % (str(node_id),str(valueX),str(valueY),str(valueZ),str(valueF))
            
        query_tilt = query_tilt[:-1]
        query_soms = query_soms[:-1]

        # print query_tilt
        # print query_soms
        
        # print query

        if i!=0:
        #     # dbio.create_table(str(tsm_name), "sensor v1")
        #     dbio.commit_to_db(query_tilt, 'process_column_v1')
            dbio.commit_to_db(query_tilt, 'process_column_v1')
            dbio.commit_to_db(query_soms, 'process_column_v1')
        
        spawn_alert_gen(tsm_name,timestamp)
                
    except KeyboardInterrupt:
        print '\n>>Error: Unknown'
        raise KeyboardInterrupt
        return
    except ValueError:
        print '\n>>Error: Unknown'
        return

def process_piezometer(sms):    
    #msg = message
    line = sms.data
    sender = sms.simnum
    print 'Piezometer data: ' + line
    try:
    #PUGBPZ*13173214*1511091800 
        linesplit = line.split('*')
        msgname = linesplit[0].lower()
        msgname = re.sub("due","",msgname)
        msgname = re.sub("pz","",msgname)
        msgname = re.sub("ff","",msgname)
        
        print 'msg_name: ' + msgname
        data = linesplit[1]
        data = re.sub("F","",data)        
        
        print "data:", data

        # msgid = int(('0x'+data[:4]), 16)
        # p1 = int(('0x'+data[4:6]), 16)*100
        # p2 = int(('0x'+data[6:8]), 16)
        # p3 = int(('0x'+data[8:10]), 16)*.01
        p1 = int(('0x'+data[:2]), 16)*100
        p2 = int(('0x'+data[2:4]), 16)
        p3 = int(('0x'+data[4:6]), 16)*.01
        piezodata = p1+p2+p3
        
        t1 = int(('0x'+data[6:8]), 16)
        t2 = int(('0x'+data[8:10]), 16)*.01
        tempdata = t1+t2
        try:
            txtdatetime = dt.strptime(linesplit[2],'%y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:00')
        except ValueError:
            txtdatetime = dt.strptime(linesplit[2],'%y%m%d%H%M').strftime('%Y-%m-%d %H:%M:00')
            
    except IndexError and AttributeError:
        print '\n>> Error: Piezometer message format is not recognized'
        print line
        return
    except ValueError:    
        print '>> Error: Possible conversion mismatch ' + line
        return      

        # try:
    # dbio.create_table(str(msgname), "piezo")
    try:
      query = ("INSERT INTO piezo_%s (ts, frequency_shift, temperature ) VALUES"
      " ('%s', %s, %s)") % (msgname,txtdatetime,str(piezodata), str(tempdata))
      # print query
        # print query
    except ValueError:
        print '>> Error writing query string.', 
        return
    
    dbio.commit_to_db(query, 'process_piezometer')
        
    print 'End of Process Piezometer data'

def process_earthquake(msg):
    line = msg.data.upper()
    print "Processing earthquake data"
    print line

    # dbio.create_table('earthquake', 'earthquake')

    #find date
    if re.search("\d{1,2}\w+201[6789]",line):
        datestr_init = re.search("\d{1,2}\w+201[6789]",msg.data).group(0)
        pattern = ["%d%B%Y","%d%b%Y"]
        datestr = None
        for p in pattern:
            try:
                datestr = dt.strptime(datestr_init,p).strftime("%Y-%m-%d")
                break
            except:
                print ">> Error in datetime conversion", datestr, "for pattern", p
        if datestr == None:
            return False
    else:
        print ">> No date string recognized"
        return False

    #find time
    if re.search("\d{1,2}[:\.]\d{1,2} *[AP]M",line):
        timestr = re.search("\d{1,2}[:\.]\d{1,2} *[AP]M",line).group(0)
        timestr = timestr.replace(" ","").replace(".",":")
        try:
            timestr = dt.strptime(timestr,"%I:%M%p").strftime("%H:%M:00")
        except:
            print ">> Error in datetime conversion", timestr
            return False
    else:
        print ">> No time string recognized"
        return False

    datetimestr = datestr + ' ' + timestr
    
    #find magnitude
    if re.search("((?<=M[SBLVOW]\=)|(?<=M\=)|(?<=MLV\=))\d+\.\d+(?= )",line):
        magstr = re.search("((?<=M[SBLVOW]\=)|(?<=M\=)|(?<=MLV\=))\d+\.\d+(?= )"
            ,line).group(0)
    else:
        print ">> No magnitude string recognized"
        magstr = 'NULL'

    #find depth
    if re.search("(?<=D\=)\d+(?=K*M)",line):
        depthstr = re.search("(?<=D\=)\d+(?=K*M)",line).group(0)
    else:
        print ">> No depth string recognized"
        depthstr = 'NULL'

    #find latitude
    if re.search("\d+\.\d+(?=N)",line):
        latstr = re.search("\d+\.\d+(?=N)",line).group(0)
    else:
        print ">> No latitude string recognized"
        latstr = 'NULL'

    #find longitude
    if re.search("\d+\.\d+(?=E)",line):
        longstr = re.search("\d+\.\d+(?=E)",line).group(0)
    else:
        print ">> No longitude string recognized"
        longstr = 'NULL'

    #find epicenter distance
    if re.search("(?<=OR )\d+(?=KM)",line):
        diststr = re.search("(?<=OR )\d+(?=KM)",line).group(0)
    else:
        print ">> No distance string recognized"
        diststr = 'NULL'

    # find heading
    if re.search("[NS]\d+[EW]",line):
        headstr = re.search("[NS]\d+[EW]",line).group(0)
    else:
        print ">> No heading string recognized"
        headstr = 'NULL'

    # find Municipality
    if re.search("(?<=OF )[A-Z ]+(?= \()",line):
        munistr = re.search("(?<=OF )[A-Z ]+(?= \()",line).group(0)
    else:
        print ">> No municipality string recognized"
        munistr = 'NULL'

    # find province
    if re.search("(?<=\()[A-Z ]+(?=\))",line):
        provistr = re.search("(?<=\()[A-Z ]+(?=\))",line).group(0)
    else:
        print ">> No province string recognized"
        provistr = 'NULL'

    # find issuer
    if re.search("(?<=\<)[A-Z]+(?=\>)",line):
        issuerstr = re.search("(?<=\<)[A-Z]+(?=\>)",line).group(0)
    else:
        print ">> No issuer string recognized"
        issuerstr = 'NULL'

    query = ("INSERT INTO earthquake_events (ts, magnitude, depth, latitude, "
        "longitude, issuer) VALUES ('%s',%s,%s,%s,%s,'%s') ON DUPLICATE KEY "
        "UPDATE magnitude=magnitude, depth=depth, latitude=latitude, longitude="
        "longitude, issuer=issuer;") % (datetimestr,magstr,depthstr,
        latstr,longstr,issuerstr)

    print query

    query.replace("'NULL'","NULL")

    dbio.commit_to_db(query, 'earthquake')

    # subprocess.Popen(["python",cfg.config().fileio.eqprocfile])
    # p = subprocess.Popen("python "+cfg.config().fileio.eqprocfile, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)

    return True


def process_arq_weather(sms):
    
    #msg = message
    line = sms.data
    sender = sms.simnum

    print 'ARQ Weather data: ' + line

    line = re.sub("(?<=\+) (?=\+)","NULL",line)

    try:
    # ARQ+1+3+4.143+4.128+0.0632+5.072+0.060+0000+13+28.1+75.0+55+150727/160058
        #table name
        linesplit = line.split('+')
       
        msgname = check_name_of_number(sender).lower()
        if msgname:
            print ">> Number registered as", msgname
            msgname_contact = msgname
            
        # else:
            # print ">> New number", sender
            # msgname = ''
            
        rain = int(linesplit[1])*0.5
        batv1 = linesplit[3]
        batv2 = linesplit[4]
        csq = linesplit[9]
        
        if csq=='':
            csq = 'NULL'
        temp = linesplit[10]
        hum = linesplit[11]
        flashp = linesplit[12]
        txtdatetime = dt.strptime(linesplit[13],'%y%m%d/%H%M%S').strftime('%Y-%m-%d %H:%M:00')

        # update_sim_num_table(msgname_contact,sender,txtdatetime[:8])
            
        
        # print str(r15m),str(r24h),batv1, batv2, current, boostv1, boostv2, charge, csq, temp, hum, flashp,txtdatetime 

        
    except IndexError and AttributeError:
        print '\n>> Error: Rain message format is not recognized'
        print line
        return
    except ValueError:    
        print '>> Error: Possible conversion mismatch ' + line
        return
        
    # if msgname:
    #     dbio.create_table(str(msgname), "arqweather")
    # else:
    #     print ">> Error: Number does not have station name yet"
    #     return

    try:
        query = ("INSERT INTO rain_%s (ts,rain,temperature,humidity,battery1,"
            "battery2,csq VALUES ('%s',%s,%s,%s,%s,%s,%s)") % (msgname,
            txtdatetime,rain,temp,hum,batv1,batv2,csq)
        # print query
    except ValueError:
        print '>> Error writing query string.', 
        return

    dbio.commit_to_db(query, 'process_arq_weather')
           
    print 'End of Process ARQ weather data'

def check_logger_model(logger_name):
    query = ("SELECT model_id FROM senslopedb.loggers where "
        "logger_name = '%s'") % logger_name

    return dbio.querydatabase(query,'check_logger_model')[0][0]
    
def process_rain(sms):

    line = sms.data
    sender = sms.simnum
    
    #msg = message
    line = re.sub("[^A-Z0-9,\/:\.\-]","",line)

    print 'Weather data: ' + line
    
    if len(line.split(',')) > 9:
        line = re.sub(",(?=$)","",line)
    line = re.sub("(?<=,)(?=(,|$))","NULL",line)
    line = re.sub("(?<=,)NULL(?=,)","0.0",line)
    print line

    try:
    
        logger_name = check_name_of_number(sender)
        logger_model = check_logger_model(logger_name)
        print logger_name,logger_model
        if logger_model in [23,24,25,26]:
            msgtable = logger_name
        else:
            msgtable = line.split(",")[0][:-1]+'G'
        # msgtable = check_name_of_number(sender)
        msgdatetime = re.search("\d{02}\/\d{02}\/\d{02},\d{02}:\d{02}:\d{02}",
            line).group(0)

        txtdatetime = dt.strptime(msgdatetime,'%m/%d/%y,%H:%M:%S')
        
        txtdatetime = txtdatetime.strftime('%Y-%m-%d %H:%M:00')
        
        # data = items.group(3)
        rain = line.split(",")[6]
        csq = line.split(",")[8]

    except IndexError and AttributeError:
        print '\n>> Error: Rain message format is not recognized'
        print line
        return
    except KeyboardInterrupt:
        print '\n>>Error: Weather message format unknown ' + line
        return
        
    # update_sim_num_table(msgtable,sender,txtdatetime[:10])

    # dbio.create_table(str(msgtable),"weather")

    try:
        query = ("INSERT INTO rain_%s (ts,rain,csq) "
            "VALUES ('%s',%s,%s)") % (msgtable.lower(),txtdatetime,rain,csq)
        # print query            
    except:
        print '>> Error writing weather data to database. ' +  line
        return

    try:
        dbio.commit_to_db(query, 'ProcesRain')
    except MySQLdb.ProgrammingError:
        # print query[:-2]
        dbio.commit_to_db(query[:-2]+')', 'process_rain')
        
    print 'End of Process weather data'

def process_stats(msg):

    print 'Site status: ' + msg.data
    
    try:
        msgtable = "stats"
        items = re.match(r("(\w{4})[-](\d{1,2}[.]\d{02}),(\d{01}),(\d{1,2})/"
            "(\d{1,2}),#(\d),(\d),(\d{1,2}),(\d)[*](\d{10})"),line)
        
        site = items.group(1)
        voltage = items.group(2)
        chan = items.group(3)
        att = items.group(4)
        retVal = items.group(5)
        msgs = items.group(6)
        sim = items.group(7)
        csq = items.group(8)
        sd = items.group(9)

        #getting date and time
        msgdatetime = line[-10:]
        print 'date & time: ' + msgdatetime

        col_list = cfg.get("Misc","AdjustColumnTimeOf").split(',')
        if site in col_list:
            msgdatetime = txtdatetime
            print "date & time adjusted " + msgdatetime
        else:
            print 'date & time no change'


    except IndexError and AttributeError:
        print '\n>> Error: Status message format is not recognized'
        print line
        return
    except:
        print '\n>>Error: Status message format unknown ' + line
        return

    dbio.create_table(str(msgtable),"stats")
        
    try:
        query = ("INSERT INTO %s (timestamp,site,voltage,chan,att,retVal,msgs,"
            "sim,csq,sd) VALUES ('%s','%s','%s','%s','%s','%s','%s','%s','%s',"
            "'%s')") %(str(msgtable),str(msgdatetime),str(site),str(voltage),
            str(chan),str(att),str(retVal),str(msgs),str(sim),str(csq),str(sd))
            
    except:
        print '>> Error writing status data to database. ' +  line
        return

    
    dbio.commit_to_db(query, 'process_stats')
        
    print 'End of Process status data'

def check_message_source(msg):
    c = cfg.config()
    identity = dbio.check_number_if_exists(msg.simnum,'community')
    if identity:
        smsmsg = "From: %s %s of %s\n" % (identity[0][1],identity[0][0],
            identity[0][2])
        smsmsg += msg.data
        # server.write_outbox_message_to_db(smsmsg,c.smsalert.communitynum)
        return
    elif dbio.check_number_if_exists(msg.simnum,'dewsl'):
        print ">> From senslope staff"
        return

    name = dbio.check_number_if_exists(msg.simnum,'sensor')    
    if name:
        print ">> From sensor", name[0][0]
    else:
        print "From unknown number ", msg.simnum

def spawn_alert_gen(tsm_name, timestamp):
    # spawn alert alert_gens

    print "For alertgen.py", tsm_name, timestamp
    print timestamp
    timestamp = (dt.strptime(timestamp,'%Y-%m-%d %H:%M:%S')+\
        td(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
    print timestamp
    # return

    alertgenlist = mc.get('alertgenlist')

    if alertgenlist == None:
        mc.set('alertgenlist',[])
        print "Setting alertgenlist for the first time"
        alertgenlist = []

    alert_info = dict()

    # check if tsm_name is already in the list for processing
    for_processing = False
    for ai in alertgenlist:
        if ai['tsm_name'] == tsm_name.lower():
            for_processing = True
            break

    if for_processing:
        print tsm_name, "already in alert gen list"
    else:
        # insert tsm_name to list
        print "Adding", tsm_name, "to alert gen list"
        alert_info['tsm_name'] = tsm_name.lower()
        alert_info['ts'] = timestamp
        alertgenlist.insert(0, alert_info)
        mc.set('alertgenlist',[])
        mc.set('alertgenlist',alertgenlist)

def process_surficial_observation(msg):
    c = cfg.config()
    proceed_with_analysis = False
    obv = []
    try:
        obv = surfp.parse_surficial_text(msg.data)
        print 'Updating observations'
        mo_id = surfp.update_surficial_observations(obv)
        surfp.update_surficial_data(obv,mo_id)
        server.write_outbox_message_to_db("READ-SUCCESS: \n" + msg.data,
            c.smsalert.communitynum,'users')
        server.write_outbox_message_to_db(c.reply.successen, msg.simnum,'users')
        proceed_with_analysis = True
    except ValueError as e:
        print str(e)
        errortype = re.search("(WEATHER|DATE|TIME|GROUND MEASUREMENTS|NAME)", 
            str(e).upper()).group(0)
        print ">> Error in manual ground measurement SMS", errortype

        server.write_outbox_message_to_db("READ-FAIL: (%s)\n%s" % 
            (errortype,msg.data),c.smsalert.communitynum,'users')
        server.write_outbox_message_to_db(str(e), msg.simnum,'users')
    except KeyError:
        print '>> Error: Possible site code error'
        server.write_outbox_message_to_db("READ-FAIL: (site code)\n%s" % 
            (msg.data),c.smsalert.communitynum,'users')
    # except:
    #     # pass
    #     server.write_outbox_message_to_db("READ-FAIL: (Unhandled) \n" + 
    #         msg.data,c.smsalert.communitynum,'users')

    # spawn surficial measurement analysis
    if proceed_with_analysis:
        sc = mc.get('server_config')
        surf_cmd_line = "python %s %s '%s' > %s 2>&1" % (sc['fileio']['gndalert1'],obv['site_id'], obv['ts'], sc['fileio']['surfscriptlogs'])
        p = subprocess.Popen(surf_cmd_line, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)


def parse_all_messages(args,allmsgs=[]):
    c = cfg.config()
    read_success_list = []
    read_fail_list = []

    print "table:", args.table

    cur_num = 0

    if allmsgs==[]:
        print 'Error: No message to Parse'
        sys.exit()
    
    while allmsgs:
        try:
            isMsgProcSuccess = True
            print '\n\n*******************************************************'
            #gets per text message
            msg = allmsgs.pop(0)
            # msg.data = msg.data.upper()
            cur_num = msg.num
                         
            msgname = check_name_of_number(msg.simnum)
            
            ##### Added for V1 sensors removes unnecessary characters pls see function pre_process_col_v1(data)
            if re.search("\*FF",msg.data) or re.search("PZ\*",msg.data):
                process_piezometer(msg)
            # elif re.search("[A-Z]{4}DUE\*[A-F0-9]+\*\d+T?$",msg.data):
            elif re.search("[A-Z]{4}DUE\*[A-F0-9]+\*.*",msg.data):
               msg.data = pre_process_col_v1(msg)
               process_column_v1(msg)
            elif re.search("EQINFO",msg.data.upper()):
                isMsgProcSuccess = process_earthquake(msg)
            elif re.search("^PSIR ",msg.data.upper()):
                isMsgProcSuccess = qsi.process_server_info_request(msg)
            elif re.search("^SENDGM ",msg.data.upper()):
                isMsgProcSuccess = qsi.server_messaging(msg)
            elif re.search("^ACK \d+ .+",msg.data.upper()):
                isMsgProcSuccess = amsg.process_ack_to_alert(msg)   
            elif re.search("^ *(R(O|0)*U*TI*N*E )|(EVE*NT )", msg.data.upper()):
                process_surficial_observation(msg)                  
            elif re.search("^[A-Z]{4,5}\*[xyabcXYABC]\*[A-F0-9]+\*[0-9]+T?$",
                msg.data):
                try:
                    dlist = process_two_accle_col_data(msg)
                    if dlist:
                        if len(dlist[0]) < 7:
                            write_soms_data_to_db(dlist,msg)
                        else:
                            write_two_accel_data_to_db(dlist,msg)
                except IndexError:
                    print "\n\n>> Error: Possible data type error"
                    print msg.data
                except ValueError:
                    print ">> Value error detected"
            elif re.search("[A-Z]{4}\*[A-F0-9]+\*[0-9]+$",msg.data):
                #process_column_v1(msg.data)
                process_column_v1(msg)
            #check if message is from rain gauge
            # elif re.search("^\w{4},[\d\/:,]+,[\d,\.]+$",msg.data):
            elif re.search("^\w{4},[\d\/:,]+",msg.data):
                process_rain(msg)
            elif re.search(r("(\w{4})[-](\d{1,2}[.]\d{02}),(\d{01}),(\d{1,2})/"
                "(\d{1,2}),#(\d),(\d),(\d{1,2}),(\d)[*](\d{10})"),msg.data):
                process_stats(msg)
            elif re.search("ARQ\+[0-9\.\+/\- ]+$",msg.data):
                process_arq_weather(msg)
            elif (msg.data.split('*')[0] == 'COORDINATOR' or 
                msg.data.split('*')[0] == 'GATEWAY'):
                isMsgProcSuccess = process_gateway_msg(msg)
            elif re.search("^MANUAL RESET",msg.data):
                server.write_outbox_message_to_db("SENSORPOLL SENSLOPE", 
                    msg.simnum,'loggers')
                isMsgProcSuccess = True
            else:
                print '>> Unrecognized message format: '
                print 'NUM: ' , msg.simnum
                print 'MSG: ' , msg.data
                check_message_source(msg)            
                isMsgProcSuccess = False
                
            if isMsgProcSuccess:
                read_success_list.append(msg.num)
            else:
                read_fail_list.append(msg.num)
    # method for updating the read_status all messages that have been processed
    # so that they will not be processed again in another run
        except:
            # print all the traceback routine so that the error can be traced
            print (traceback.format_exc())
            print ">> Setting message read_status to fatal error"
            dbio.set_read_status(cur_num, read_status=-1, table = args.table)
            continue
        
    return read_success_list, read_fail_list
    
def record_surficial_measurements(gnd_meas):
    # print gnd_meas
    
    # dbio.create_table("gndmeas","gndmeas")
    
    # query = "INSERT INTO gndmeas (timestamp, meas_type, site_id, observer_name, crack_id, meas, weather) VALUES " + gnd_meas
    # query += "ON DUPLICATE KEY UPDATE meas = values(meas), observer_name = values(observer_name), weather = values(weather);"
    
    query = ("INSERT INTO gndmeas (timestamp, meas_type, site_id, "
        "observer_name, crack_id, meas, weather) VALUES %s"
        "ON DUPLICATE KEY UPDATE meas = values(meas), "
        "observer_name = values(observer_name), weather = values(weather);"
        % (gnd_meas))
    
    # print query
    
    dbio.commit_to_db(query, 'record_surficial_measurements')

def record_manual_weather(mw_text):
    # print gnd_meas
    
    dbio.create_table("manualweather","manualweather")
    
    query = ("INSERT IGNORE INTO manualweather (timestamp, meas_type, site_id,"
            " observer_name, weatherdesc) VALUES ") + mw_text
    
    dbio.commit_to_db(query, 'record_manual_weather')


def get_router_ids():
    db, cur = dbio.db_connect()

    query = "SELECT `logger_id`,`logger_name` from `loggers` where `model_id` in (SELECT `model_id` FROM `logger_models` where `logger_type`='router') and `logger_name` is not null"

    nums = dbio.querydatabase(query,'get_router_ids')
    nums = {key: value for (value, key) in nums}

    return nums
        
def process_gateway_msg(msg):
    print ">> Coordinator message received"
    print msg.data
    
    # dbio.create_table("coordrssi","coordrssi")

    routers = get_router_ids()
    
    msg.data = re.sub("(?<=,)(?=(,|$))","NULL",msg.data)
    
    try:
        datafield = msg.data.split('*')[1]
        timefield = msg.data.split('*')[2]
        timestamp = dt.strptime(timefield,"%y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        
        smstype = datafield.split(',')[0]
        # process rssi parameters
        if smstype == "RSSI":
            site_name = datafield.split(',')[1]
            rssi_string = datafield.split(',',2)[2]
            print rssi_string
            # format is
            # <router name>,<rssi value>,...
            query = "INSERT IGNORE INTO router_rssi (ts, logger_id, rssi_val) VALUES "
            tuples = re.findall("[A-Z]+,\d+",rssi_string)
            for item in tuples:
                query += "('%s',%d,%s)," % (timestamp,routers[item.split(',')[0].lower()],item.split(',')[1] )
                
            query = query[:-1]

            print query
            
            dbio.commit_to_db(query, 'process_gateway_msg')

            return True
        else:
            print ">> Processing coordinator weather"
    except IndexError:
        print "IndexError: list index out of range"
        return False
    # except:
    #     print ">> Unknown Error", msg.data
    #     return False

def get_arguments():
    parser = argparse.ArgumentParser(description="Run SMS parser\n smsparser [-options]")
    parser.add_argument("-db", "--dbhost", help="host name (check senslope-server-config.txt")
    parser.add_argument("-t", "--table", help="smsinbox table")
    parser.add_argument("-m", "--mode", help="mode to run")
    parser.add_argument("-g", "--gsm", help="gsm name")
    parser.add_argument("-s", "--status", help="inbox/outbox status",type=int)
    parser.add_argument("-l", "--messagelimit", help="maximum number of messages to process at a time",type=int)
    parser.add_argument("-r", "--runtest", help="run test function",action="store_true")
    parser.add_argument("-b", "--bypasslock", help="bypass lock script function",action="store_true")
    
    try:
        args = parser.parse_args()

        if args.status == None:
            args.status = 0
        if args.messagelimit == None:
            args.messagelimit = 200
        if args.dbhost == None:
            args.dbhost = 'local'
        return args        
    except IndexError:
        print '>> Error in parsing arguments'
        error = parser.format_help()
        print error
        sys.exit()


def test():
    sms = ""
    msg = gsmio.sms('', '', sms, '')
    
def main():
    args = get_arguments()

    if not args.bypasslock:
        lockscript.get_lock('smsparser %s' % args.table)

    # dbio.create_table("runtimelog","runtime")
    # logRuntimeStatus("procfromdb","startup")

    if args.runtest:
        test()
        sys.exit()

    print 'SMS Parser'

    # force backup
    while True:
        allmsgs = dbio.get_all_sms_from_db(host=args.dbhost,table=args.table,read_status=args.status,limit=args.messagelimit)
        
        if len(allmsgs) > 0:
            msglist = []
            for item in allmsgs:
                smsItem = gsmio.sms(item[0], str(item[2]), str(item[3]), str(item[1]))
                msglist.append(smsItem)
            allmsgs = msglist

            read_success_list, read_fail_list = parse_all_messages(args,allmsgs)

            dbio.set_read_status(read_success_list, read_status=1,table=args.table)
            dbio.set_read_status(read_fail_list, read_status=-1,table=args.table)
            # sleeptime = 5
        else:
            # server.logRuntimeStatus("procfromdb","alive")
            print dt.today().strftime("\nServer active as of %A, %B %d, %Y, %X")
            return
            # time.sleep(sleeptime)
        sys.exit()

if __name__ == "__main__":
    main()
    
