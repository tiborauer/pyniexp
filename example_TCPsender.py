# -*- coding: utf-8 -*-

# testing UDP
"""

__________________________________________________________________________
Copyright (C) 2016-2017 OpenNFT.org

Written by Tibor Auer
"""

from pyniexp.connection import Tcp

TCP_IP = "127.0.0.1"
TCP_PORT = 1234
TCP_SEPARATOR = '#'

sender = Tcp(IP=TCP_IP,port=TCP_PORT,separatorChar=TCP_SEPARATOR)

sender.OpenAsClient()
sender.sendTimeStamp = True

sender.Info()

for data in ['a1',34,'b2',78]:
    sender.SendData(data)

sender.Close()