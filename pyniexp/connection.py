import socket, select, datetime, sys

class __Connect:

    @property
    def Status(self):
        raise NotImplementedError("NYI")

    @property
    def StatusForSending(self):
        raise NotImplementedError("NYI")

    @property
    def StatusForReceiving(self):
        raise NotImplementedError("NYI")

    @property
    def isOpen(self):
        return bool(self._Status)
 
    @property
    def RemoteAddr(self):
        if self._isIPConfirmed:
            return self.IP + " (confirmed)"
        else:
            return self.IP + " (unconfirmed)"

    def __init__(self,IP='127.0.0.1',port=1234,encoding='UTF-8',controlChar='#',separatorChar='',timeOut=20):
        self.IP = IP
        self.Port = port
        self.Encoding = encoding
        self.ControlChar = controlChar
        self.SeparatorChar = separatorChar
        self.TimeOut = timeOut

        self.sendTimeStamp = False
        self.Quiet = False

        self._Socket = None
        self._Status = 0 # 0 - closed; -1 - open for receiving; 1 - open for sending
        self._isIPConfirmed = False

        self._iClock = None
    
    def __del__(self):
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
    
    def Close(self):
        if self.isOpen:
            self._Socket.close()
            self._Status = 0
            self.Log('Connection closed with {:s}'.format(self.RemoteAddr))
    
    def ReadytoReceive(self):
        return len(select.select([self._Socket],[],[],0.001)[0]) > 0

    def ReceiveData(self,n=0,dtype='str'):
        raise NotImplementedError("NYI")

    def SendData(self,dat):
        raise NotImplementedError("NYI")

    def Clock(self):
        if not(self._iClock is None):
            return datetime.datetime.now() - self._iClock
        else:
            return None
    
    def ResetClock(self):
        self._iClock = datetime.datetime.now()
    
    def Log(self,msg):
        if ~self.Quiet | any([msg.find(s) != -1 for s in ['ERROR','WARNING','USER']]):
            if not(self._iClock is None):
                t = self.Clock()
            else:
                t = datetime.datetime.now()
            print('[{:s}] {:s}'.format(str(t), msg))


class Udp(__Connect):
    
    @property
    def Status(self):
        if self._Status == -1:
            return 'ready for receiving'
        elif self._Status == 1:
            return 'ready for sending'
        else: # 0
            return 'closed'

    @property
    def StatusForSending(self):
        return self.Status == 'ready for sending'

    @property
    def StatusForReceiving(self):
        return self.Status == 'ready for receiving'

    def __init__(self,IP='127.0.0.1',port=1234,encoding='UTF-8',controlChar='#',separatorChar='',timeOut=20):
        super().__init__(IP,port,encoding,controlChar,separatorChar,timeOut)

        self._Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def ConnectForReceiving(self):
        self._Socket.bind((self.IP, self.Port))

        if len(self.ControlChar):
            data = [0]
            while chr(data[0]) != self.ControlChar:
                while not(self.ReadytoReceive()): pass
                data, addr= self._Socket.recvfrom(16)
                self._isIPConfirmed = addr[0] == self.IP
        self.IP = addr[0]
        self._Status = -1
        self.Log('Connection with {:s} is {:s}'.format(self.RemoteAddr,self.Status))
    
    def ConnectForSending(self):
        err = self._Socket.connect_ex(((self.IP, self.Port)))
        if not(err):
            self._Status = 1
            self._isIPConfirmed = True
        else:
            self.Log('Establishing connection for sending with {:s} failed with error: {:s}'.format(self.RemoteAddr,err))
            return

        if len(self.ControlChar): 
            self.sendTimeStamp = False
            self.SendData(self.ControlChar)
        self.Log('Connection with {:s} is {:s}'.format(self.RemoteAddr,self.Status))

    def Close(self):
        if self.isOpen:
            if self.Status == 'ready for sending' and len(self.ControlChar): self.SendData(self.ControlChar)

            super().Close()

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

    def SendData(self,dat):
        if not(self.StatusForSending):
            self.Log('ERROR - Connection with {:s} is not ready for sending!'.format(self.RemoteAddr))
            return

        if type(dat) != list: dat = [dat]
        
        t = datetime.datetime.now()
        if self.sendTimeStamp: dat.insert(0,t.timestamp())

        n = 0
        for d in dat:
            if type(d) != bytes:
                d = bytes(str(d)+self.SeparatorChar, self.Encoding)
            self._Socket.send(d) 
            n += 1
        
        return t, n-self.sendTimeStamp
    
    def ReceiveData(self,n=0,dtype='str'):
        if not(self.StatusForReceiving):
            self.Log('ERROR - Connection with {:s} is not ready for receiving!'.format(self.RemoteAddr))
            return

        if self.sendTimeStamp: n += 1

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
                    if self.sendTimeStamp and not(len(dat)): dat.append(datetime.datetime.fromtimestamp(float(info)))
                    else: 
                        try:
                            info = eval(dtype)(info)
                        except ValueError: pass
                        dat.append(info)
                    info = ''
            else:
                t0 = datetime.datetime.now()
                while not(self.ReadytoReceive()) and ((datetime.datetime.now() - t0).total_seconds() < self.TimeOut): pass
                if not(self.ReadytoReceive()): break
        
        return dat


class Tcp(__Connect):

    @property
    def Status(self):
        if self._Status == -1:
            return 'open as server'
        elif self._Status == 1:
            return 'open as client'
        else: # 0
            return 'closed'

    @property
    def StatusForSending(self):
        return self.Status.find('open') != -1

    @property
    def StatusForReceiving(self):
        return self.Status.find('open') != -1

    def __init__(self,IP=None,port=1234,controlChar='',separatorChar='',timeOut=20):
        super().__init__(IP,port,'',controlChar,separatorChar,timeOut)

        self._Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        if sys.byteorder == 'little': self.encoding = '<'
        elif sys.byteorder == 'big': self.encoding = '>'

    def OpenAsServer(self):
        self._Socket.bind(('', self.Port))
        self._Socket.listen(1)
        self._Socket, addr = self._Socket.accept()
        self._Status = -1
        if not(self.IP is None):
            self._isIPConfirmed = addr[0] == self.IP
        self.IP = addr[0]
        self.Log('{:s}; connected with client at {:s}:{:d}'.format(self.Status,self.IP,addr[1]))

    def OpenAsClient(self):
        self._Socket.connect((self.IP, self.Port))
        self._Status = 1
        self._isIPConfirmed = True
        self.Log('{:s}; connected to server at {:s}:{:d}'.format(self.Status,self.IP,self.Port))

    def SendData(self,dat):
        pass

    def ReceiveData(self,n=0,dtype='str'):
        pass

    def Flush(self):
        try:
            self._Socket.recv(1024000000000)
        except:
            pass