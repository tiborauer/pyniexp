# -*- coding: utf-8 -*-

# testing UDP
"""

__________________________________________________________________________
Copyright (C) 2016-2017 OpenNFT.org

Written by Tibor Auer
"""

from pyniexp.network import Tcp

TCP_IP = '127.0.0.1'
TCP_PORT = 1234
CONTROL_SIGNAL = [0, 0]

receiver = Tcp(IP=TCP_IP,port=TCP_PORT,control_signal=CONTROL_SIGNAL)

receiver.open_as_server()
receiver.sending_time_stamp = True

receiver.info()

n = 0
while receiver.is_open:
    n += 1
    data_cond = receiver.receive_data(n=3,dtype='str')
    data_fb = receiver.receive_data(n=1,dtype='int')
    if len(data_cond) > 1:
        receiver.log('volume #{:3d}, condition: {}, feedback: {} - {}'.format(n,data_cond[1],data_fb[0],data_fb[1]))
    elif receiver.is_open: receiver.log('volume #{:3d} no data!'.format(n))

receiver.close()