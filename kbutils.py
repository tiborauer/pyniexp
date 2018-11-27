import time

try:
    import keyboard
except ImportError:
    print('module "keyboard" is not installed')
    raise(ImportError)

kbLayout = [k[0] for k in keyboard._os_keyboard.official_virtual_keys.values()]

class Key:
    name = ''
    state = ''
    timeDown = 0
    timeUp = 0
    @property
    def time(self):
        return max(self.timeDown,self.timeUp)

    def __init__(self,name):
        self.name = name
        self.state = 'up'

    def eventTime(self,etype):
        if etype == 'down': return self.timeDown
        elif etype == 'up': return self.timeUp
        else: return -1
    
    def update(self,etype,val):
        self.state = etype
        if self.state == 'down': self.timeDown = val
        elif self.state == 'up': self.timeUp = val
        
class Kb:

    # Private property
    __keys = [Key(name) for name in kbLayout]

    def __init__(self):
        keyboard.hook(self.__store_keys)

    def stop(self):
        keyboard.unhook_all()

    def kbCheck(self):
        return [(k.name, k.state, k.time) for k in self.__keys]

    def __store_keys(self,e):
            K = [k for k in self.__keys if k.name == e.name]
            if len(K):
                K[0].update(e.event_type,e.time)