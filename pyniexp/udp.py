import socket, select, time

class Connection:

    IP = '127.0.0.1' # localhost
    Port = 5077 # random (?) port
    Encoding = 'UTF-8'
    ControlChar = '#'
    TimeOut = 20 # s

    __isOpen = False
    @property
    def isOpen(self):
        return self.__isOpen

    __Socket = None
    __RemoteAddr = ''
    __Buffer = []

    def __init__(self,*args): # IP, port, control character
        parList = ['IP', 'Port','Encoding','ControlChar','TimeOut']
        for i in range(0,len(args)):
            setattr(self,parList[i],args[i])
        
        self.__Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def __del__(self):
        if self.isOpen:
            self.Close()
    
    def WaitForConnection(self):
        self.__Socket.bind((self.IP, self.Port))

        data = [0]
        while chr(data[0]) != self.ControlChar:
            while not(self.ReadytoRead()): pass
            data, addr= self.__Socket.recvfrom(16)
            self.__RemoteAddr = addr[0]
        print("Connection started from: ", self.__RemoteAddr)
        self.__isOpen = True

    def Close(self):
        self.__Socket.close()
        self.__isOpen = False
        print("Connection closed with: ", self.__RemoteAddr)

    def ReOpen(self):
        if not(self.isOpen):
            self.__Socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.WaitForConnection()

    def ReadytoRead(self):
        return len(select.select([self.__Socket],[],[],0.001)[0]) > 0
    
    def ReadData(self,n=1,dtype='str'):
        dat = list()
        for i in range(0,n):
            if self.ReadytoRead():
                d = self.__Socket.recv(1024)
                if chr(d) == self.ControlChar: 
                    self.Close()
                    break
                dat.append(eval(dtype)(d))
            else:
                t0 = time.time()
                while not(self.ReadytoRead()) or (time.time() - t0 < self.TimeOut): pass
                if not(self.ReadytoRead()): break
        return dat