import socket, select, datetime

class __Connect:

    IP = '127.0.0.1' # localhost
    Port = 1234 # random (?) port
    Encoding = 'UTF-8'
    ControlChar = '#'
    SeparatorChar = ''
    TimeOut = 20 # s
    Quiet = False

    __Status = 0 # 0 - closed; -1 - open for receiving; 1 - open for sending
    @property
    def isOpen(self):
        return bool(self.__Status)

    @property
    def Status(self):
        if self.__Status == -1:
            return 'ready for receiving'
        elif self.__Status == 1:
            return 'ready for sending'
        else: # 0
            return 'closed'
    
    @property
    def RemoteAddr(self):
        if self.__isIPConfirmed:
            return self.IP + " (confirmed)"
        else:
            return self.IP + " (unconfirmed)"

    _Socket = None
    __isIPConfirmed = False

    __iClock = None

    def __init__(self,IP='127.0.0.1',port=1234,encoding='UTF-8',controlChar='#',separatorChar='',timeOut=20):
        self.IP = IP
        self.Port = port
        self.Encoding = encoding
        self.ControlChar = controlChar
        self.SeparatorChar = separatorChar
        self.TimeOut = timeOut
    
    def __del__(self):
        if self.isOpen:
            self.Close()
    
    def Info(self):
        print(self.__class__.__name__.upper(), "connection")
        print("\tIP:\t\t", self.IP)
        print("\tPort:\t\t", self.Port)
        print("\tTime out:\t", self.TimeOut)
        print("\tStatus:\t\t", self.Status)
        print("Transfer")
        print("\tEncoding:\t\t", self.Encoding)
        print("\tSeparator character:\t", self.SeparatorChar)
        print("\tControl character:\t", self.ControlChar)
    
    def ConnectForReceiving(self):
        self._Socket.bind((self.IP, self.Port))

        if len(self.ControlChar):
            data = [0]
            while chr(data[0]) != self.ControlChar:
                while not(self.ReadytoReceive()): pass
                data, addr= self._Socket.recvfrom(16)
                self.__isIPConfirmed = addr[0] == self.IP
        self.__Status = -1
        self.Log('Connection with {:s} is {:s}'.format(self.RemoteAddr,self.Status))
    
    def ConnectForSending(self):
        err = self._Socket.connect_ex(((self.IP, self.Port)))
        if not(err):
            self.__Status = 1
            self.__isIPConfirmed = True
        else:
            self.Log('Establishing connection for sending with {:s} failed with error: {:s}'.format(self.RemoteAddr,err))
            return

        if len(self.ControlChar): self.SendData(self.ControlChar)
        self.Log('Connection with {:s} is {:s}'.format(self.RemoteAddr,self.Status))

    def Close(self):
        if self.Status == 'ready for sending' and len(self.ControlChar): self.SendData(self.ControlChar)

        self._Socket.close()
        self.__Status = 0
        self.Log('Connection closed with {:s}'.format(self.RemoteAddr))

    def ReOpen(self,operation='receiving'):
        if not(self.isOpen):
            if operation == 'receiving':
                self._Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.ConnectForReceiving()
            elif operation == 'sending':
                self._Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.ConnectForSending()
            else:
                self.Log('ERROR - Unknown operation:{:s}'.format(operation))

    def ReadytoReceive(self):
        return len(select.select([self._Socket],[],[],0.001)[0]) > 0
    
    def ReceiveData(self,n=0,dtype='str'):
        if self.Status != 'ready for receiving':
            self.Log('ERROR - Connection with {:s} is not ready for receiving!'.format(self.RemoteAddr))
            return

        dat = list(); info = ''; EOW = False
        while not(n) or len(dat) < n:
            if self.ReadytoReceive():
                d = self._Socket.recv(1024).decode(self.Encoding)
                EOW = not(len(self.SeparatorChar))
                if d[-1] == self.SeparatorChar: # strip off separator
                    d = d[0:-1]
                    EOW = True
                if d == self.ControlChar: # check for closure
                    self.Close()
                    break
                info += d
                if EOW:
                    dat.append(eval(dtype)(info))
                    info = ''
            else:
                t0 = datetime.datetime.now()
                while not(self.ReadytoReceive()) and ((datetime.datetime.now() - t0).total_seconds() < self.TimeOut): pass
                if not(self.ReadytoReceive()): break
        return dat

    def SendData(self,dat):
        if self.Status != 'ready for sending':
            self.Log('ERROR - Connection with {:s} is not ready for sending!'.format(self.RemoteAddr))
            return

        if type(dat) != list: dat = [dat]

        n = 0
        for d in dat:
            d = bytes(str(d)+self.SeparatorChar, self.Encoding)
            self._Socket.send(d) 
            n += 1
        
        return n

    def Clock(self):
        if not(self.__iClock is None):
            return datetime.datetime.now() - self.__iClock
        else:
            return None
    
    def ResetClock(self):
        self.__iClock = datetime.datetime.now()
    
    def Log(self,msg):
        if ~self.Quiet | any([msg.find(s) != -1 for s in ['ERROR','WARNING','USER']]):
            if not(self.__iClock is None):
                t = self.Clock()
            else:
                t = datetime.datetime.now()
            print('[{:s}] {:s}'.format(str(t), msg))


class Udp(__Connect):
    def __init__(self,IP='127.0.0.1',port=1234,encoding='UTF-8',controlChar='#',separatorChar='',timeOut=20):
        super().__init__()

        self._Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)