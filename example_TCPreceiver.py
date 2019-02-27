# -*- coding: utf-8 -*-

# testing UDP
"""

__________________________________________________________________________
Copyright (C) 2016-2017 OpenNFT.org

Written by Tibor Auer
"""

from pyniexp.connection import Tcp

TCP_PORT = 1234
TCP_SEPARATOR = '#'

receiver = Tcp(port=TCP_PORT,separatorChar=TCP_SEPARATOR)

receiver.OpenAsServer()
receiver.sendTimeStamp = True

receiver.Info()

n = 0
cond = 'test'
while n < 2:
    data = receiver.ReceiveData(n=1,dtype='float')

    n += 1
    # if n == 1: receiver.ResetClock()
    if len(data) > 1: receiver.Log('volume #{:3d}, condittion: {}, feedback: {} - {}'.format(n,cond,data[0],data[1]))
    elif receiver.isOpen: receiver.Log('volume #{:3d} no data!'.format(n))

receiver.Close()