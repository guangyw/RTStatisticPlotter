#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       server.py
#
#
#		Note: Client from the same ip address are regarded as one client. 
#       If a client tries to connect twice, only the second one will be displayed
#       
#       Copyright 2012 Guangyan <flear@flear-Aspire-4820TG>
#		
#       

  

from twisted.internet.protocol import Protocol, ServerFactory
#import Queue
import datetime
import threading
import matplotter

from twisted.internet import reactor

class serverProtocol(Protocol):
#	queue = Queue.Queue()		
	def connectionMade(self):
		self.addr = self.transport.getPeer().host
		print 'peer:'+self.addr+'connected'
		self.factory.startReceiving(self.addr)
				
	def dataReceived(self, data):
		data = data.split(';')[-2]
		#print data
		double_data = float(data)
		self.factory.outputData(double_data, self.addr)
	def connectionLost(self, reason):
		self.factory.receiving_finished()
		
class serverFactory(ServerFactory):
	addresses = []
	
	def __init__(self, dataToDisplay):
		self.dataToDisplay = dataToDisplay
	
	protocol = serverProtocol	
		
	def startReceiving(self, addr):
		self.start_time = datetime.datetime.now()
		print addr
		if ((addr in self.addresses) == False):
			self.addresses.append(addr)
			print 'add peer %s to local memory' % addr
		self.choose_to_display()
		#reactor.callInThread(matplotter.startPlotting, self.dataToDisplay, self.addresses.index(addr), addr) 
		#print "starting plotting thread # %s" % self.index
	
	def choose_to_display(self):
		print 'There are %d clients connected:' % len(self.addresses)
		for address in self.addresses:
			print '    '+str(self.addresses.index(address)) + ': ' + address
		choice = int(raw_input('choose the stream of data to display:  '))
		while (choice >= len(self.addresses)):			
			choice = int(raw_input('No stream with index %d, please choose again :  ' % choice))
		print 'starting print thread: %s' % self.addresses[choice]
		reactor.callInThread(matplotter.startPlotting, self.dataToDisplay, self.addresses.index(address), address)
		
	def outputData(self, data, addr):
		self.data_getTime = datetime.datetime.now()
		#print self.data_getTime
		self.time_diff = self.data_getTime - self.start_time
		#print self.time_diff
		self.index = self.addresses.index(addr)
		self.dataTuple = self.time_diff, self.addresses.index(addr), data
		#print self.dataTuple
		self.dataToDisplay[str(self.index)] = data
		#print self.dataToDisplay		
#		self.startPlotterThread(addr)
		
	def receiving_finished(self):
		pass
		
		
		
def main():
	dataToDisplay = {}	
	factory = serverFactory(dataToDisplay)
	port = reactor.listenTCP(35022, factory, interface = 'localhost')
	print 'server runing on %s' % (port.getHost())	
	reactor.run()			

if __name__ == '__main__':
	main()	

		
		
		
	
	


