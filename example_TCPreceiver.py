# -*- coding: utf-8 -*-

# testing UDP
"""

__________________________________________________________________________
Copyright (C) 2016-2017 OpenNFT.org

Written by Tibor Auer
"""

from pyniexp.connection import Tcp

TCP_PORT = 1234

receiver = Tcp(port=TCP_PORT)

receiver.OpenAsServer()
receiver.sendTimeStamp = True

receiver.Info()

n = 0
while n < 3:
    data = receiver.ReceiveData(n=1,dtype='float')
    
    #header_size = struct.unpack('<I', s.wait(4)[0])[0]

    n += 1

receiver.Close()