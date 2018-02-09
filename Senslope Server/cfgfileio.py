import ConfigParser, os, serial

# USAGE
# 
# 
# import cfgfileio as cfg
# 
# s = cfg.config()
# print s.dbio.hostdb
# print s.io.rt_to_fill
# print s.io.printtimer
# print s.misc.debug


cfgfiletxt = 'senslope-server-config.txt'
cfile = os.path.dirname(os.path.realpath(__file__)) + '/' + cfgfiletxt
    
def readCfgFile():
    cfg = ConfigParser.ConfigParser()
    cfg.read(cfile)
    return cfg

def saveConfigChanges(cfg):
    with open(cfile, 'wb') as c:
        cfg.write(c)

class Container(object):
	pass
        
class config:
	def __init__(self):

		cfg = readCfgFile()            
		self.cfg = cfg

		self.localdb = Container()
		self.localdb.user = cfg.get("LocalDB","username")
		self.localdb.host = cfg.get("LocalDB","host")
		self.localdb.pwd = cfg.get("LocalDB","password")
		self.localdb.name = cfg.get("LocalDB","dbname")
		self.localdb.inbox = cfg.get("LocalDB","inboxname")
		
		self.gsmdb = Container()
		self.gsmdb.user = cfg.get("GSMDB","username")
		self.gsmdb.host = cfg.get("GSMDB","host")
		self.gsmdb.pwd = cfg.get("GSMDB","password")
		self.gsmdb.name = cfg.get("GSMDB","dbname")
		self.gsmdb.inbox = cfg.get("GSMDB","inboxname")

		self.sandboxdb = Container()
		self.sandboxdb.user = cfg.get("SandboxDB","username")
		self.sandboxdb.host = cfg.get("SandboxDB","host")
		self.sandboxdb.pwd =  cfg.get("SandboxDB","password")
		self.sandboxdb.name = cfg.get("SandboxDB","dbname")
		self.sandboxdb.inbox = cfg.get("SandboxDB","inboxname")

		self.serialio = Container()
		self.serialio.baudrate = cfg.getint("Serial","baudrate")
		self.serialio.globeport = cfg.get("Serial","globeport")
		self.serialio.smartport = cfg.get("Serial","smartport")
		self.serialio.callport = cfg.get("Serial","callport")
		self.serialio.timeout = cfg.getint("Serial","timeout")

		self.gsmio = Container()
		self.gsmio.resetpin = cfg.getint("gsmio","resetpin")
		
		self.smsalert = Container()
		self.smsalert.communitynum = cfg.get("SMSAlert","communityphonenumber")
		self.smsalert.sunnum = cfg.get("SMSAlert","sunnumbers")
		self.smsalert.globenum = cfg.get("SMSAlert","globenumbers")
		self.smsalert.smartnum = cfg.get("SMSAlert","smartnumbers")
		self.smsalert.serveralert = cfg.get("SMSAlert","serveralert")

		self.reply = Container()
		self.reply.successen = cfg.get("ReplyMessages","successen")
		self.reply.successtag = cfg.get("ReplyMessages","successtag")
		self.reply.faildateen = cfg.get("ReplyMessages","faildateen")
		self.reply.failtimeen = cfg.get("ReplyMessages","failtimeen")
		self.reply.failmeasen = cfg.get("ReplyMessages","failmeasen")
		self.reply.failweaen = cfg.get("ReplyMessages","failweaen")
		self.reply.failobven = cfg.get("ReplyMessages","failobven")
		self.reply.failooben = cfg.get("ReplyMessages","failooben")

		self.fileio = Container()
		self.fileio.allalertsfile = cfg.get("FileIO","allalertsfile")
		self.fileio.eqprocfile = cfg.get("FileIO","eqprocfile")
		self.fileio.queryoutput = cfg.get("FileIO","querylatestreportoutput")
		self.fileio.alertgenscript = cfg.get("FileIO","alertgenscript")
		self.fileio.alertanalysisscript = cfg.get("FileIO","alertanalysisscript")
		self.fileio.masyncscript = cfg.get("FileIO","masyncscript")
		self.fileio.masynclogs = cfg.get("FileIO","masynclogs")
		self.fileio.websocketdir = cfg.get("FileIO","websocketdir")
		self.fileio.gndalert1 = cfg.get("FileIO","gndalert1")
		self.fileio.gndalert2 = cfg.get("FileIO","gndalert2")
		self.fileio.gndalert3 = cfg.get("FileIO","gndalert3")
		self.fileio.monitoringoutputdir = cfg.get("FileIO","monitoringoutputdir")
		
		
		self.simprefix = Container()
		self.simprefix.smart = cfg.get("simprefix","smart")
		self.simprefix.globe = cfg.get("simprefix","globe")

		self.mode = Container()
		self.mode.script_mode = cfg.get("mode","script_mode")
		if self.mode.script_mode == 'gsmserver':
			self.mode.sendmsg = True
			self.mode.procmsg = False
			self.mode.logtoinstance = 'GSM'
		elif self.mode.script_mode == 'procmsg':
			self.mode.sendmsg = False
			self.mode.procmsg = True
			self.mode.logtoinstance = 'LOCAL'

		self.io = Container()
		self.io.proc_limit = cfg.getint("io","proc_limit")
		self.io.active_lgr_limit = cfg.getint("io","active_lgr_limit")
		

