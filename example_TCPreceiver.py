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

print(receiver.ReceiveData(n=2,dtype='str'))
print(receiver.ReceiveData(n=1,dtype='int'))
print(receiver.ReceiveData(n=2,dtype='str'))
print(receiver.ReceiveData(n=1,dtype='int'))

receiver.Close()