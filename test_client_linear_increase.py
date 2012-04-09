#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       test_linear_increase.py
#       
#       Copyright 2012 Guangyan <flear@flear-Aspire-4820TG>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#       
#       


#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       untitled.py
#       
#       Copyright 2012 Guangyan <flear@flear-Aspire-4820TG>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#       
#       
import socket
import time

class DataGen(object):
    """ A silly class that generates pseudo-random data for
        display in the plot.
    """
    def __init__(self, init=0):
        self.data = self.init = init
        
    def next(self):
        self._recalc_data()
        return str(self.data)+';'
    
    def _recalc_data(self):
		self.data+=1
        
def main():
	destIP = '127.0.0.1'
	hostPort = 35022
	datagen = DataGen()
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((destIP, hostPort))
	print "connected to server on %s port %s" % (destIP, hostPort)
	time.sleep(1)
	while 1:
		s.send(datagen.next())
		time.sleep(0.02)
		print 'sending data %s' % (datagen.next())
	s.close()

if __name__ == '__main__':
	main()



