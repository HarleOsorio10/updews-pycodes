import re, sys
from datetime import datetime as dt
import cfgfileio as cfg

def getTimeFromSms(text):
  # timetxt = ""
  hm = "\d{1,2}"
  sep = " *:+ *"
  day = " *[AP]\.*M\.*"
  
  time_format_dict = {
      hm + sep + hm + day : "%I:%M%p",
      hm + day : "%I%p",
      hm + sep + hm + " *N\.*N\.*" : "%H:%M",
      hm + sep + hm + " +" : "%H:%M"
  }

  print text
  time_str = ''
  for fmt in time_format_dict:
    time_str_search = re.search(fmt,text)
    if time_str_search:
      time_str = time_str_search.group(0)
      time_str = re.sub(";",":",time_str)
      time_str = re.sub("[^APM0-9:]","",time_str)
      time_str = dt.strptime(time_str,time_format_dict[fmt]).strftime("%H:%M:%S")
      break
    else:
      print 'not', fmt
  
  return time_str

    
def getDateFromSms(text):
  # timetxt = ""
  mon_re1 = "[JFMASOND][AEPUCO][NBRYLGTVC]"
  mon_re2 = "[A-Z]{4,9}"
  day_re1 = "\d{1,2}"
  year_re1 = "(201[678]){0,1}"

  cur_year = str(dt.today().year)

  separator = "[\. ,]{0,3}"

  date_format_dict = {
      mon_re1 + separator + day_re1 + separator + year_re1 : "%b%d%Y",
      day_re1 + separator + mon_re1 + separator + year_re1 : "%d%b%Y",
      mon_re2 + separator + day_re1 + separator + year_re1 : "%B%d%Y",
      day_re1 + separator + mon_re2 + separator + year_re1 : "%d%B%Y"
  }

  date_str = ''
  for fmt in date_format_dict:
    date_str_search = re.search("^" + fmt,text)
    if date_str_search:
      date_str = date_str_search.group(0)
      date_str = re.sub("[^A-Z0-9]","",date_str)
      if len(date_str) < 6:
        date_str = date_str + cur_year 
      date_str = dt.strptime(date_str,date_format_dict[fmt]).strftime("%Y-%m-%d")
      break
      
  return date_str

def getGndMeas(text):

  c = cfg.config()
  print '\n\n*******************************************************'  
  print text
  
  # clean the message
  cleanText = re.sub(" +"," ",text.upper())
  cleanText = re.sub("\.+",".",cleanText)
  cleanText = re.sub(";",":",cleanText)
  cleanText = re.sub("\n"," ",cleanText)
  cleanText = cleanText.strip()
  sms_list = re.split(" ",re.sub("[\W]"," ",cleanText))
  
  sms_date = ""
  sms_time = ""
  records = []
  
  # check measurement type
  if sms_list[0][0] == 'R':
    meas_type = "ROUTINE"
  else:
    meas_type = "EVENT"
    
  data_field = re.split(" ",cleanText,maxsplit=2)[2]
  
  try:
    date_str = getDateFromSms(data_field)
    print "Date: " + date_str
  except:
    raise ValueError(c.reply.faildateen)
  
  try:
    time_str = getTimeFromSms(data_field)
    print "Time: " + time_str
  except:
    raise ValueError(c.reply.failtimeen)
  
  # get all the measurement pairs
  meas_pattern = "(?<= )[A-Z] *\d{1,3}\.*\d{0,2} *C*M"
  meas = re.findall(meas_pattern,data_field)
  # create records list
  if meas:
    pass
  else:
    raise ValueError(c.reply.failmeasen)
  
  # get all the weather information
  print repr(data_field)
  try:
    wrecord = re.search("(?<="+meas[-1]+" )[A-Z]+",data_field).group(0)
    recisvalid = False
    for keyword in ["ARAW","ULAN","BAGYO","LIMLIM","AMBON","ULAP"]:
        if keyword in wrecord:
            recisvalid = True
            print "valid"
            break
    if not recisvalid:
        raise AttributeError  
  except AttributeError:
    raise ValueError(c.reply.failweaen)
  
  # get all the name of reporter/s  
  try:
    observer_name = re.search("(?<="+wrecord+" ).+$",data_field).group(0)
    print observer_name
  except AttributeError:
    raise ValueError(c.reply.failobven)
    
  gnd_records = ""
  for m in meas:
    try:
        crid = m.split(" ",1)[0]
        cm = m.split(" ",1)[1]
        print cm
    except IndexError:
        crid = m[0]
        cm = m[1:]

    try:
      re.search("\d *CM",cm).group(0)
      cm = float(re.search("\d{1,3}\.*\d{0,2}",cm).group(0))
    except AttributeError:
      cm = float(re.search("\d{1,3}\.*\d{0,2}",cm).group(0))*100.0
      
    gnd_records = gnd_records + "('"+date_str+" "+time_str+"','"+sms_list[0]+"','"+sms_list[1]+"','"+observer_name+"','"+crid+"','"+str(cm)+"','"+wrecord+"'),"
    
  gnd_records = gnd_records[:-1]
  
  return gnd_records
  

  
  
