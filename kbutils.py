import time

try:
    import keyboard
except ImportError:
    print('module "keyboard" is not installed')
    raise(ImportError)

kbLayout = [k[0] for k in keyboard._os_keyboard.official_virtual_keys.values()]

class Kb:

    # Public property
    __readInterval = 0.1 # seconds
    @property
    def readInterval(self):
        return self.__readInterval
    
    @readInterval.setter
    def readInterval(self,val):
        MINVAL = 0.1
        self.__readInterval = max(val,MINVAL)

    # Private property
    __Buffer = []

    def __init__(self):
        keyboard.hook(self.__store_keys)

    def Stop(self):
        keyboard.unhook_all()

    def kbCheck(self,doClearBuffer=True):
        val = [(k.name, k.event_type, k.time) for k in self.__Buffer if time.time() - k.time <= self.readInterval]
        if doClearBuffer:
            self.__Buffer = []
        return val

    def __store_keys(self,e):
            self.__Buffer.append(e)
