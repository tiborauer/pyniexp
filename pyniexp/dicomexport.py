from connection import Tcp
from utils import list_find

import pickle

TCP_PORT = 5677
CONTROL_SIGNAL = [0, 0]

receiver = Tcp(port=TCP_PORT,control_signal=CONTROL_SIGNAL,encoding='latin-1')

receiver.open_as_server()

# receive_initial()
data = receiver.receive_data(n=2,dtype='uint')
print(data)
hdr = receiver.receive_data(n=data[0],dtype='str').split('\n')
with open('hdr_initial.pkl','wb') as f:
    pickle.dump(hdr, f)

for i in range(0,5):
    data = receiver.receive_data(n=2,dtype='uint')
    print(data)
    hdr = receiver.receive_data(n=data[0],dtype='str').split('\n')
    img = receiver.receive_data(n=int(data[1]/2),dtype='ushort')
    print(len(img))

    with open('hdr_img{:d}.pkl'.format(i),'wb') as f:
        pickle.dump([hdr, img], f)

def get_header_data(hdr,field,multiple=False):
    ind = list_find(hdr,field)
    if not(len(ind)): return [None]
    if not(multiple): ind = [ind[0]]

    field0 = field
    for i in range(0,len(ind)):
        if len(ind) > 1: field = '{}.{:d}'.format(field0,i)