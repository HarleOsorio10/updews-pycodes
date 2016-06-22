import os,time,serial,re,sys
import datetime
from datetime import datetime as dt
from datetime import timedelta as td
import senslopedbio as dbio
import senslopeServer as server
import cfgfileio as cfg
import argparse
import StringIO

def getLatestQueryReport():
	c = cfg.config()
	querylatestreportoutput = c.fileio.queryoutput
	print querylatestreportoutput
	f = open(querylatestreportoutput,'r')
	filecontent = f.read()
	f.close()

	try:
		return re.search("(?<=Active loggers: )\d{1,2}(?=\W)",filecontent).group(0)
	except:
		return 'ERROR'

def getRuntimeLogs(db='local'):
	if db == 'local':
		script1 = 'procfro'
		script2 = 'alert'
		status1 = 'alive'
		status2 = 'checked'
	else:
		script1 = 'globe'
		script2 = 'smart'
		status1 = 'alive'
		status2 = 'alive'
	
	query = """(select * from runtimelog 
		where script_name = '%s' and status = '%s'
		order by timestamp desc limit 1)
		union
		(select * from runtimelog 
		where script_name = '%s' and status = '%s'
		order by timestamp desc limit 1)
		""" % (script1,status1,script2,status2)

	return dbio.querydatabase(query,'customquery',db)

def getNumberOfReporter(datedt):
	# today = dt.today()

	query = """select numbers from dewslcontacts 
		where nickname = (select nickname from servermonsched 
		where date = '%s')""" % (datedt.strftime("%Y-%m-%d"))

	num = dbio.querydatabase(query,'customquery')[0][0]

	return num

def sendStatusUpdates(reporter):
	c = cfg.config()
	active_loggers_count = getLatestQueryReport()

	loclogs = getRuntimeLogs('local')
	gsmlogs = getRuntimeLogs('gsm')

	status_message = "SERVER STATUS UPDATES\n"
	status_message += "Active loggers: %s\n" % (active_loggers_count)
	status_message += "Last logs for:\n"
	status_message += "Process messages: %s\n" % (loclogs[0][0].strftime("%B %d, %H:%M%p"))
	status_message += "Check alert: %s\n" % (loclogs[0][0].strftime("%B %d, %H:%M%p"))
	status_message += "Globe instance: %s\n" % (gsmlogs[0][0].strftime("%B %d, %H:%M%p"))
	status_message += "Smart instance: %s\n" % (gsmlogs[1][0].strftime("%B %d, %H:%M%p"))

	print dt.today()

	if reporter == 'scheduled':
		reportnumber = getNumberOfReporter(dt.today())
		server.WriteOutboxMessageToDb(status_message,reportnumber)
	elif int(active_loggers_count) < 60:
		print ">> Sending alert sms for server"
		server.WriteOutboxMessageToDb(status_message,c.smsalert.serveralert)

def getTimeOfDayDescription():
	today = dt.today()

	if today.hour < 12:
		return 'morning'
	elif today.hour>=12 and today.hour < 18:
		return 'afternoon'
	else:
		return 'evening'

def getNumberOfReporter(datedt):
	# today = dt.today()

	query = """select numbers from dewslcontacts 
		where nickname = (select nickname from servermonsched 
		where date = '%s')""" % (datedt.strftime("%Y-%m-%d"))

	num = dbio.querydatabase(query,'customquery')[0][0]

	return num

def sendServerMonReminder():
	tomorrow = dt.today()+td(hours=24)
	reportnumber = getNumberOfReporter(tomorrow)

	reminder_message = "Good %s. This is to remind you that you are assigned" % (getTimeOfDayDescription())
	reminder_message += " for server monitoring duties for tomorrow, %s." % (tomorrow.strftime("%A, %B %d"))
	reminder_message += " As such, you will be receiving regular sms regarding the sever status updates."
	reminder_message += " Thanks."
	server.WriteOutboxMessageToDb(reminder_message,reportnumber)

def getShifts(datedt):

	query = """select * from monshiftsched where `timestamp` = 
	(select `timestamp` from monshiftsched order by 
	abs(timediff(`timestamp`, "%s")) limit 1);
	""" % (datedt.strftime("%Y-%m-%d %H:%M:00"))

	return dbio.querydatabase(query,'customquery')

def getNumbersFromList(personnel_list):

	query = """select nickname,numbers from dewslcontacts where nickname in %s""" % (personnel_list)

	return dbio.querydatabase(query,'customquery')

def sendEventMonitoringReminder():
	next_shift = dt.today()+td(hours=12)
	shifts = getShifts(next_shift)
	report_dt = shifts[0][1]

	position = ['iompmt','iompct','oomps','oompmt','oompct']
	position_dict = {}
	for pos,per in zip(position,shifts[0][2:]):
		position_dict[per] = pos

	numbers = getNumbersFromList(str(shifts[0][2:]))
	numbers_dict = {}
	for nick,num in numbers:
		numbers_dict[nick] = num

	for key in position_dict:
		reminder_message = "Good %s Agent %s " % (getTimeOfDayDescription(),key)
		reminder_message += "your mission, should you choose to accept it, is to be the %s " % (position_dict[key])
		reminder_message += "for %s. " % (report_dt.strftime("%B %d, %H:%M%p"))
		reminder_message += "Good luck. This message will self destruct in 5, 4, 3, 2 ..."

		# print reminder_message

	 	server.WriteOutboxMessageToDb(reminder_message,numbers_dict[key])

def introduce():
	query = """select nickname,numbers from dewslcontacts
			where grouptags not like "%admin" 
			group by nickname
			"""
	print dbio.querydatabase(query,'customquery')
	return dbio.querydatabase(query,'customquery')

def getNonReportingSites():
	c = cfg.config()
	two_weeks_ago = (dt.today() - td(days=14)).strftime("%Y-%m-%d")
	query = """ SELECT name FROM `senslopedb`.`site_rain_props` s
		where name not in
		(
		SELECT site_id FROM `senslopedb`.`gndmeas` g
		where timestamp > '%s'
		#where site_id = 'agb'
		group by site_id
		)
		""" % (two_weeks_ago)
		
	non_rep_sites = dbio.querydatabase(query,'nonreporting')
	accu_sites = []
	for s in non_rep_sites:
		accu_sites.append(s[0])
	print accu_sites
	
	message = "Non reporting sites reminder.\n"
	message += "As of %s, the following sites have no ground data measurement: \n" % (two_weeks_ago)
	message += str(accu_sites)[1:-1]
	message = message.replace("'","")
	print repr(message)
	server.WriteOutboxMessageToDb(message,c.smsalert.communitynum)

def getLatestSmsFromColumn(colname):
	query = """ select timestamp,sms_msg from smsinbox where sms_msg like '%s%s%s' 
		order by timestamp desc limit 1 """ % ('%',colname,'%')
	
	last_col_msg = dbio.querydatabase(query,'getlatestcolmsg','gsm')

	tmp_msg = "Latest message from %s\n" % (colname.upper())
	if last_col_msg:
		tmp_msg += 'Timestamp: ' + last_col_msg[0][0].strftime("%Y-%m-%d %H:%M:%S") + '\n'
		tmp_msg += 'Message: ' + last_col_msg[0][1]
	else:
		tmp_msg += 'UNDEFINED'
	return tmp_msg

def GetSimNumofColumn(colname):
	query = """ select sim_num from site_column_sim_nums where name = '%s'; """ % (colname)

	num = dbio.querydatabase(query,'getsimumofcolumn')

	tmp_msg = "%s: " % (colname.upper())
	if num:
		return tmp_msg + num[0][0]
	else:
		return tmp_msg + 'UNDEFINED'

def GetLatestDataofNode(colname,nid):
	query = """ select * from %s where id = %d and 
	timestamp = (select max(timestamp) from %s where id = %d); """ % (colname,nid,colname,nid)

	print query
	data = dbio.querydatabase(query,'getlatestdataofnode')
	tmp_msg = "Latest data from %s %d\n" % (colname.upper(),nid)
	for line in data:
		tmp_msg += line[0].strftime("%Y-%m-%d %H:%M:%S") + ','
		tmp_msg += repr(line[1:]).replace('L','') + '\n'
	
	if len(data) == 0:
		tmp_msg += 'UNDEFINED'
	else:
		print ">> ", data
	
	return tmp_msg

def main():
	func = sys.argv[1] 
	if func == 'sendregularstatusupdates':
		sendStatusUpdates()
	elif func == 'sendservermonreminder':
		sendServerMonReminder()
	elif func == 'sendeventmonitoringreminder':
		sendEventMonitoringReminder()
	elif func == 'introduce':
		introduce()
	elif func == 'sendserveralert':
		sendStatusUpdates('server')
	elif func == 'getnonreportingsites':
		getNonReportingSites()
	elif func == 'test':
		test()
	else:
		print '>> Wrong argument'

# if __name__ == "__main__":
# 	main()

def ProcessServerInfoRequest(msg):
	parser = argparse.ArgumentParser(description="Request information from server\n PSRI [-options]")
	parser.add_argument("-s", "--sim_num", help="get sim number of column", action="store_true")
	parser.add_argument("-t", "--latest_ts", help="get timestamp of latest sms", action="store_true")
	parser.add_argument("-d", "--latest_node_data", help="get latest node data", action="store_true")
	
	parser.add_argument("-c", "--col_name", help="column name")
	parser.add_argument("-n", "--node_id", help="node id", type=int)
	# parser.add_argument("-m", "--msg_id", help="message id", type=int)
	
	# check if there is an error in parsing the arguments
	print msg.data
	try:
		args = parser.parse_args(msg.data.lower().split(' ')[1:])
	except:
		print '>> Error in parsing'
		# error_msg = StringIO.StringIO()
		error = parser.format_help().replace("processmessagesfromdb.py","PSRI")
		# error = error_msg.get
		print error
		server.WriteOutboxMessageToDb(error,msg.simnum)
		return

	if args.sim_num:
		num = GetSimNumofColumn(args.col_name.strip())
		print num
		server.WriteOutboxMessageToDb(num,msg.simnum)
	
	if args.latest_ts:
		ts_msg = getLatestSmsFromColumn(args.col_name.strip())
		print ts_msg
		server.WriteOutboxMessageToDb(ts_msg,msg.simnum)

	if args.latest_node_data:
		latest_data = GetLatestDataofNode(args.col_name.strip(),args.node_id)
		print latest_data
		server.WriteOutboxMessageToDb(latest_data,msg.simnum)

	return True

		
def test():
    msg = "-t -clabb -n10"
    ProcessServerInfoRequest(msg)

if __name__ == "__main__":
    main()
