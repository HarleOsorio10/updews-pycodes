"""
Created on Mon Jun 13 11:08:15 2016

@author: PradoArturo
"""

#!/usr/bin/python

import socket
import os
import sys
import time
import json
import pandas as pd
#import datetime
from datetime import datetime
import queryPiDb as qpi

from twisted.python import log
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory
#import MySQLdb

#TODO: Add the accelerometer filter module you need to test
#import newAccelFilter as naf

#include the path of "Data Analysis" folder for the python scripts searching
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Data Analysis'))
if not path in sys.path:
    sys.path.insert(1,path)
del path   

import querySenslopeDb as qs

###############################################################################
# GSM Functionalities
###############################################################################

def writeToSMSoutbox(number, msg):
    try:
        qInsert = """INSERT INTO smsoutbox (recepients,sms_msg,send_status)
                    VALUES ('%s','%s','UNSENT');""" % (number,msg)
        print qInsert
        qpi.ExecuteQuery(qInsert)        
    
    except IndexError:
        print '>> Error in writing extracting database data to files..'

def sendMessageToGSM(recipients, msg):
    db, cur = qpi.SenslopeDBConnect('senslopedb')
    print '>> Connected to database'
    
    for number in recipients:
        print "%s: %s" % (number, msg)
        writeToSMSoutbox(number, msg)

def sendTimestampToGSM(host, port, recipients):
    db, cur = qpi.SenslopeDBConnect('senslopedb')
    print '>> Connected to database'
    
    i = datetime.now()
    txtmsg = "%s: Test text message from RPi" % (i)
    
    for number in recipients:
        sendDataFullCycle(host, port, txtmsg)
        print "%s: %s" % (number, txtmsg)
        writeToSMSoutbox(number, txtmsg)

###############################################################################
# Regular Sockets
###############################################################################

#Open a socket connection
def openSocketConn(host, port):
    s = socket.socket()
    s.connect((host, port))
    return s

#Close a socket connection
def closeSocketConn(sock_conn):
    sock_conn.close()

#One full cycle of opening connection
# sending data and closing connection
def sendDataFullCycle(host, port, msg):
    s = socket.socket()    
    s.connect((host, port))
    print msg
    s.send(msg)
    s.close()

def sendColumnNamesToSocket(host, port):
    try:
        db, cur = qs.SenslopeDBConnect('senslopedb')
        print '>> Connected to database'
    
        #Get all column names with installation status of "Installed"
        queryColumns = 'SELECT name, version FROM site_column WHERE installation_status = "Installed" ORDER BY s_id ASC'
        try:
            cur.execute(queryColumns)
        except:
            print '>> Error parsing database'
        
        columns = cur.fetchall()
    #    print columns
    
        for column in columns:
            columnName = column[0]
            sendDataFullCycle(host, port, columnName)
            print columnName
    
    except IndexError:
        print '>> Error in writing extracting database data to files..'

###############################################################################
# Web Sockets
###############################################################################

class DewsClientGSMProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")

        # def hello():
        #     self.sendMessage(u"Hello, world!".encode('utf8'))
        #     # self.sendMessage(b"\x00\x01\x03\x04", isBinary=True)
        #     self.factory.reactor.callLater(1, hello)

        # start sending messages every second ..
        # hello()

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            msg = format(payload.decode('utf8'))
            print("Text message received: %s" % msg)

            #The local ubuntu server is expected to receive a JSON message
            #parse the numbers from the message
            try:
                parsed_json = json.loads(msg)
                commType = parsed_json['type']

                if commType == 'smssend':
                    recipients = parsed_json['numbers']
                    print "Recipients of Message: %s" % (len(recipients))
                    
                    for recipient in recipients:
                        print recipient
                    
                    message = parsed_json['msg']
                    
                    sendMessageToGSM(recipients, message)
                    self.sendMessage(u"Sent an SMS!".encode('utf8'))
                else:
                    print "Error: No message type detected. Can't send an SMS."
                
            except:
                print "Error: Please check the JSON construction of your message"

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))

class DewsClientRegularProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")

        # def hello():
        #     self.sendMessage(u"Hello, world!".encode('utf8'))
        #     # self.sendMessage(b"\x00\x01\x03\x04", isBinary=True)
        #     self.factory.reactor.callLater(1, hello)

        # start sending messages every second ..
        # hello()

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            msg = format(payload.decode('utf8'))
            print("Text message received: %s" % msg)

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))