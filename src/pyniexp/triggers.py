import serial
from .utils import getLogger, listSerial

logger = getLogger()

class BrainVision:
    _port = []
    _isConnected = False

    def isConnected(self):
        return self._isConnected

    def __init__(self,port='COM6'):
        if not any([p == port for p in listSerial()]):
            logger.error('port {} is not available'.format(port))
        else:
            self._port = serial.Serial(port)
            self._port.write([0x00])
            self._isConnected = True
    
    def __del__(self):
        if self.isConnected: 
            self.close()

    def close(self):
        self._port.write([0xFF])
        self._port.close()
    
    def send(self,val):
        if val > 255:
            logger.error('trigger value {:d} is larger than 255'.format(val))
        else:
            self._port.write([val])
            self._port.write([0x00])
