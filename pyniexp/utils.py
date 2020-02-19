from time import time
from multiprocessing import Value
from enum import Enum

class Status(Enum):
    DISCONNECTED = 0
    CONNECTED = 1
    UNCONFIGURED = 1
    CONFIGURED = 2
    STOPPED = 2
    RUNNING = 3

def binvec2dec(binvec):
    return sum([binvec[i]*(2**i) for i in range(0,len(binvec))])

def ismember(list1, list2):
    return [any([kb == kp for kp in list2]) for kb in list1]

def list_find(str_list, pattern):
    return [i for i in range(0,len(str_list)) if str_list[i].find(pattern) != -1]

class clock:
    
    def __init__(self):
        self._t0 = Value('d',time()) 
        
     # Clock
    @property
    def clock(self):
        return time() - self._t0.value

    def reset_clock(self):
        self._t0.value = time()
