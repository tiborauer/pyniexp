import socket, sys, struct
from datetime import datetime
from select import select
from pyniexp.utils import clock

class __Connect(clock):

    @property
    def status(self):
        raise NotImplementedError("NYI")

    @property
    def status_for_sending(self):
        raise NotImplementedError("NYI")

    @property
    def status_for_receiving(self):
        raise NotImplementedError("NYI")

    @property
    def is_open(self):
        return bool(self._status)
 
    @property
    def remote_address(self):
        if self._is_IP_confirmed:
            return self.IP + " (confirmed)"
        else:
            return self.IP + " (unconfirmed)"
    
    _control_signal = {'value': '', 'decode': '', 'n_bytes': 0}
    @property
    def control_signal(self):
        val = self._control_signal['value']
        if type(val) != list: val = [val]
        return val
    @control_signal.setter
    def control_signal(self,val):
        self._control_signal['value'] = val
        
        n = 1
        if type(val) == list:
            n = len(val)
            val = val[0]
        
        if type(val) == str: 
            self._control_signal['n_bytes'] = n*1
            self._control_signal['decode'] = lambda d: [d.decode(self.encoding)]
        elif type(val) == int: 
            self._control_signal['n_bytes'] = n*4
            self._control_signal['decode'] = lambda d: list(struct.unpack(self.format+str(n)+'i',d))
        elif type(val) == float: 
            self._control_signal['n_bytes'] = n*4
            self._control_signal['decode'] = lambda d: list(struct.unpack(self.format+str(n)+'f',d))

    def __init__(self,IP='127.0.0.1',port=1234,encoding='UTF-8',control_signal='',timeout=20):
        super().__init__()
        
        self.IP = IP
        self.port = port
        self.encoding = encoding
        self.control_signal = control_signal
        self.timeout = timeout

        if sys.byteorder == 'little': self.format = '<'
        elif sys.byteorder == 'big': self.format = '>'

        self.sending_time_stamp = False
        self.wait_for_controlsignal = False
        self.quiet = False

        self._socket = None
        self._status = 0 # 0 - closed; -1 - open for receiving; 1 - open for sending
        self._is_IP_confirmed = False
    
    def __del__(self):
        self.close()
    
    def info(self):
        print(self.__class__.__name__.upper(), "connection")
        print("\tIP:\t\t", self.IP)
        print("\tport:\t\t", self.port)
        print("\tTime out:\t", self.timeout)
        print("\tstatus:\t\t", self.status)
        print("Transfer")
        print("\tEncoding:\t\t", self.encoding)
        print("\tControl signal:\t", self.control_signal)
    
    def close(self,send_control_signal=True):
        if self.is_open:
            if len(self.control_signal) and send_control_signal: 
                self.sending_time_stamp = False
                self.send_data(self.control_signal)
            
            if self.wait_for_controlsignal: pass
        
            self._socket.close()
            self._status = 0
            self.log('Connection closed with {:s}'.format(self.remote_address))
    
    def ready_to_receive(self):
        return len(select([self._socket],[],[],0.001)[0]) > 0

    def send_data(self,dat):
        if not(self.status_for_sending):
            self.log('ERROR - Connection with {:s} is not ready for sending!'.format(self.remote_address))
            return
    
        if type(dat) != list: dat = [dat]
        
        t = datetime.now()
        if self.sending_time_stamp: dat.insert(0,t.timestamp())
        
        for d in dat:
            if type(d) == str: self._socket.send(bytes(d,'UTF-8'))
            elif type(d) == int: self._socket.send(struct.pack(self.format+'i',d))
            elif type(d) == float: self._socket.send(struct.pack(self.format+'f',d))
            
        return t, len(dat)-self.sending_time_stamp

    def flush(self):
        try:
            self._socket.recv(1024000000000)
        except:
            pass

    def log(self,msg):
        if ~self.quiet | any([msg.find(s) != -1 for s in ['ERROR','WARNING','USER']]):
            print('[{:.3f}s] {:s}'.format(self.clock, msg))


class Udp(__Connect):
    
    @property
    def status(self):
        if self._status == -1:
            return 'ready for receiving'
        elif self._status == 1:
            return 'ready for sending'
        else: # 0
            return 'closed'

    @property
    def status_for_sending(self):
        return self.status == 'ready for sending'

    @property
    def status_for_receiving(self):
        return self.status == 'ready for receiving'

    def __init__(self,IP='127.0.0.1',port=1234,encoding='UTF-8',control_signal='#',timeout=20):
        super().__init__(IP,port,encoding,control_signal,timeout)

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def connect_for_receiving(self):
        self._socket.bind((self.IP, self.port))

        if len(self.control_signal):
            data = [0]
            while chr(data[0]) != self.control_signal[0]:
                while not(self.ready_to_receive()): pass
                data, addr= self._socket.recvfrom(16)
                self._is_IP_confirmed = addr[0] == self.IP
        self.IP = addr[0]
        self._status = -1
        self.log('Connection with {:s} is {:s}'.format(self.remote_address,self.status))
    
    def connect_for_sending(self):
        err = self._socket.connect_ex(((self.IP, self.port)))
        if not(err):
            self._status = 1
            self._is_IP_confirmed = True
        else:
            self.log('Establishing connection for sending with {:s} failed with error: {:s}'.format(self.remote_address,err))
            return

        if len(self.control_signal): 
            self.sending_time_stamp = False
            self.send_data(self.control_signal)
        self.log('Connection with {:s} is {:s}'.format(self.remote_address,self.status))

    def reopen(self,operation='receiving'):
        if not(self.is_open):
            if operation == 'receiving':
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.connect_for_receiving()
            elif operation == 'sending':
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.connect_for_sending()
            else:
                self.log('ERROR - Unknown operation:{:s}'.format(operation))

    def receive_data(self,n=0,dtype='str'):
        if not(self.status_for_receiving):
            self.log('ERROR - Connection with {:s} is not ready for receiving!'.format(self.remote_address))
            return
    
        dat = []
        while not(n) or len(dat) < (n+self.sending_time_stamp):
            if self.ready_to_receive():

                # check for closing signal
                try:
                    if self._control_signal['decode'](self._socket.recv(self._control_signal['n_bytes'], socket.MSG_PEEK)) == self.control_signal:
                        self.close(self.wait_for_controlsignal)
                        return dat
                except: pass


                if self.sending_time_stamp and not(len(dat)):
                    dat += [datetime.fromtimestamp(struct.unpack(self.format+'1f',self._socket.recv(4))[0])]
           
                d = self._socket.recv(1024)
                if len(d) % 4: dtype = 'str' # Cave: No 4(-8-12-16-...)-char-long string is allowed
                
                if dtype == 'str': dat += [d.decode(self.encoding)]
                elif dtype == 'int': dat += list(struct.unpack(self.format+str(n)+'i',d))
                elif dtype == 'float': dat += list(struct.unpack(self.format+str(n)+'f',d))

            else:
                t0 = datetime.now()
                while not(self.ready_to_receive()) and ((datetime.now() - t0).total_seconds() < self.timeout): pass
                if not(self.ready_to_receive()): break
        return dat

class Tcp(__Connect):

    @property
    def status(self):
        if self._status == -1:
            return 'open as server'
        elif self._status == 1:
            return 'open as client'
        else: # 0
            return 'closed'

    @property
    def status_for_sending(self):
        return self.status.find('open') != -1

    @property
    def status_for_receiving(self):
        return self.status.find('open') != -1

    def __init__(self,IP=None,port=1234,encoding='UTF-8',control_signal='',timeout=20):
        super().__init__(IP,port,encoding,control_signal,timeout)

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
    def open_as_server(self):
        self._socket.bind(('', self.port))
        self._socket.listen(1)
        self._socket, addr = self._socket.accept()
        self._status = -1
        if not(self.IP is None):
            self._is_IP_confirmed = addr[0] == self.IP
        self.IP = addr[0]
        self.log('{:s}; connected with client at {:s}:{:d}'.format(self.status,self.IP,addr[1]))

    def open_as_client(self):
        self._socket.connect((self.IP, self.port))
        self._status = 1
        self._is_IP_confirmed = True
        self.log('{:s}; connected to server at {:s}:{:d}'.format(self.status,self.IP,self.port))
    
    def receive_data(self,n=0,dtype='str'):
        if not(self.status_for_receiving):
            self.log('ERROR - Connection with {:s} is not ready for receiving!'.format(self.remote_address))
            return
    
        if dtype == 'str': dat = ''
        else: dat = []
        n_received = 0
        while not(n) or n_received < (n+self.sending_time_stamp):
            if self.ready_to_receive():

                # check for closing signal
                try:
                    if self._control_signal['decode'](self._socket.recv(self._control_signal['n_bytes'], socket.MSG_PEEK)) == self.control_signal:
                        self.close(self.wait_for_controlsignal)
                        return dat
                except: pass


                if self.sending_time_stamp and not(len(dat)):
                    dat += [datetime.fromtimestamp(struct.unpack(self.format+'1f',self._socket.recv(4))[0])]; n_received += 1
           
                if dtype == 'str': dat += self._socket.recv(1).decode(self.encoding)
                elif dtype == 'uint16': dat += list(struct.unpack(self.format+'H',self._socket.recv(2)))
                elif dtype == 'int32': dat += list(struct.unpack(self.format+'i',self._socket.recv(4)))
                elif dtype == 'uint32': dat += list(struct.unpack(self.format+'I',self._socket.recv(4)))
                elif dtype == 'float': dat += list(struct.unpack(self.format+'f',self._socket.recv(4)))
                else: dat += [self._socket.recv(1)]
                n_received += 1
            else:
                t0 = datetime.now()
                while not(self.ready_to_receive()) and ((datetime.now() - t0).total_seconds() < self.timeout): pass
                if not(self.ready_to_receive()): break
        
        return dat