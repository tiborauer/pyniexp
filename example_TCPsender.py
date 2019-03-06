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
CONTROL_SIGNAL = [0, 0]

sender = Tcp(IP=TCP_IP,port=TCP_PORT,control_signal=CONTROL_SIGNAL)

sender.open_as_client()
sender.sending_time_stamp = True

sender.info()

for data in ['Bas',34,'Reg',78]:
    sender.send_data(data)

sender.close()