from math import inf
import sys
from time import time
from multiprocessing import Process, Value, RawValue, RawArray

import pyniexp.utils as utils

try:
    import nidaqmx
except ImportError:
    print('WARNING: nidaqmx module is not available --> ', end='')
    print('You can run ScannerSynch only in emulation mode')

try:
    import pyniexp.kbutils as kbutils
except ImportError:
    print('WARNING: kbutils module is not available --> ', end='')
    print('You cannot emulate buttons')

DEV = 'Dev1'
MAX_SIGNAL = 1000

#### Emulation class for DAQ
class simDAQ:

    ## Properies
    di_channels = []

#### Main class
class scanner_synch:
    
    ## Properties 
    # Private constants
    _button_list_LT = (1, 2, 4, 8) # Lumitouch Photon Control (1 hand, 4 buttons)
    _button_list_NATA = (3, 7, 11, 15, 19, 23, 27, 31, 35, 39) # NATA (2 hands, 10 buttons)

    # Public properties
    buttonbox_timeout = inf # second (timeout for WaitForButtonPress)
    is_inverted = False

    # Public read-only properties
    __emul_synch = False
    @property
    def emul_synch(self):
        return self.__emul_synch   
    __emul_buttons = False
    @property
    def emul_buttons(self):
        return self.__emul_buttons   

    # Private properties
    __buttonbox_readout = False
    __process = Process()
    
    __readout_time = [0.5, 0.5] # sec to store data before refresh 1*n (default 0.5)
    @property
    def readout_time(self):
        return self.__readout_time
        
    __isDAQ = 'nidaqmx' in sys.modules
    __isKb = 'pyniexp.kbutils' in sys.modules # Button emulation (keyboard)

    # Dependent properties
    @property
    def is_valid(self):
        valid = True
        valid = valid and (self.__isDAQ or (self.emul_buttons and self.emul_buttons))
        if self.emul_synch and not(self.TR):
            print('Emulation: Scanner synch pulse is not in use --> ', end='')
            print('You need to set TR!')
            valid = valid and False
        if self.emul_buttons and not(len(self.buttons)):
            print('Emulation: Buttonbox is not in use           --> ', end='')
            print('You need to set Buttons!')
            valid = valid and False
        
        if not(valid): print('WARNING: Scanner Synch is not open!')

        return valid

    ## Constructor
    def __init__(self,emul_synch=False,emul_buttons=False):
        print('Initialising Scanner Synch...')
        self.__emul_synch = emul_synch
        self.__emul_buttons = emul_buttons

        # test environment
        if self.emul_synch or self.emul_buttons:
            try:
                D = nidaqmx.system.System.local().devices
                D = [d for d in D if d.name == DEV]
                D = D[0]
                D.self_test_device()
            except:
                print('WARNING - DAQ card is not available:', sys.exc_info()[0])
                self.__isDAQ = False
                self.__emul_synch = True
                self.__emul_buttons = True
        else: self.__isDAQ = False

        self._t0 = Value('d',time())      # internal timer
        self._keep_running = Value('b',-1) # internal signal (-1: not started, 1: running)
        self.start_process()

    ## Destructor
    def __del__(self):
        if self._keep_running.value:
            self._keep_running.value = 0

    ## Utils
    def start_process(self,max_pulses=MAX_SIGNAL):
        print('Starting process...')
        if not(self.is_valid): 
            print('You have to start the process manually by calling <object>.start_process()!')
            return
        if self.__process.is_alive():
            self.__process.terminate()
        self._synchpulstimes = RawArray('d', [-1]*max_pulses)
        self._buttonstates = RawArray('b', [0]*self.number_of_buttons)
        self._buttonpresstimes = [RawArray('d', [-1]*max_pulses) for n in range(0,self.number_of_buttons)]
        self._select_buttons = RawArray('b',[1]*self.number_of_buttons) # record only selected buttons
        self._button_record_period = RawArray('d',[0, inf])               # record buttons only in this period
        self.__readout_time = [self.__readout_time[0]] + [self.__readout_time[1]]*self.number_of_buttons
        self.__process = Process(target=self._run)
        self.__process.start()
        while not(self.is_alive): pass
        print('[{:.3f}s] - Process is running'.format(self.clock))

    @property
    def is_alive(self):
        return self._keep_running.value == 1

    @property
    def clock(self):
        return time() - self._t0.value

    def reset_clock(self):
        self._t0.value = time()

    __TR = 2    # emulated pulse frequency (default 2)
    @property
    def TR(self):
        return self.__TR

    @TR.setter
    def TR(self,val):
        if self.__process.is_alive():
            self.__process.terminate()
        
        self.__TR = val

    __buttons = []
    @property
    def buttons(self):
        return self.__buttons

    @buttons.setter
    def buttons(self,val):
        if self.__isKb:
            if self.__process.is_alive():
                self.__process.terminate()
                
            kbutils.kbLayout
            if not all(utils.ismember(val,kbutils.kbLayout)):
                print('WARNING: Some buttons are not recognised in...')
                print(kbutils.kbLayout)
                return

            self.__buttons = val
            self.__readout_time = [self.__readout_time[0]] + [self.__readout_time[1]]*(self.number_of_buttons)

        else:
            print('WARNING: "kbutils" is not available')
    
    @property
    def number_of_buttons(self):
        if self.emul_buttons: return len(self.buttons)
        else: return len(self._button_list_LT)+len(self._button_list_NATA)

    ## Scanner Pulse
    @property
    def synch_count(self):
        return sum([i > -1 for i in self._synchpulstimes])

    def reset_synch_count(self):
        for n in range(0,len(self._synchpulstimes)):
            self._synchpulstimes[n] = -1
    
    @property
    def synch_readout_time(self):
        return self.__readout_time[0]

    def set_synch_readout_time(self,t):
        self.__readout_time[0] = t
    
    def wait_for_synch(self):
        synch_count0 = self.synch_count
        while not(self.synch_count > synch_count0): pass
    
    @property
    def time_of_last_pulse(self):
        return self._synchpulstimes[self.synch_count-1]
    
    @property
    def measured_TR(self):
        if self.synch_count > 1: return self.time_of_last_pulse - self._synchpulstimes[self.synch_count-2] 
        else: return 0
    
    ## Buttons
    def set_button_readout_time(self,t):
        self.__readout_time = [self.__readout_time[0]] + [t]*(len(self.__readout_time)-1)
        self.__buttonbox_readout = False
    
    def set_buttonbox_readout_time(self,t):
        self.__readout_time = [self.__readout_time[0]] + [t]*(len(self.__readout_time)-1)
        self.__buttonbox_readout = True
    
    @property
    def _last_button_indices(self):
        return [sum([n > -1 for n in self._buttonpresstimes[b]])-1 for b in range(0,self.number_of_buttons)]

    @property
    def _time_of_last_buttonpresses(self):
        return [self._buttonpresstimes[b][self._last_button_indices[b]] for b in range(0,self.number_of_buttons)]

    @property
    def buttonpresses(self):
        e = [(b,n) for b in range(0,self.number_of_buttons) for n in self._buttonpresstimes[b] if n > self._button_record_period[0]]
        return sorted(e, key=lambda e: e[1])

    def wait_for_button(self,timeout=None,ind_button=None,no_block=False,event_type='press'):
        BBoxQuery = self.clock

        # Onset
        self._button_record_period[0] = BBoxQuery

        # Offset
        if timeout is None: timeout = self.buttonbox_timeout
        wait = timeout < 0 # wait until timeout even in case of response
        timeout = abs(timeout)
        self._button_record_period[1] = self._button_record_period[0]+timeout

        # Select buttons
        if type(ind_button) != list: ind_button = range(0,self.number_of_buttons)
        for b in range(0,self.number_of_buttons):
            self._select_buttons[b] = any([b == n for n in ind_button])

        if no_block: return

        while self.clock - BBoxQuery < timeout:
            if wait: continue
            if event_type == 'press' and any([e[1] > self._button_record_period[0] for e in self.buttonpresses]): break # (selected) button pressed
            if event_type == 'release' and any([not(self._buttonstates[b]) 
                for b in [e[0] for e in self.buttonpresses if e[1] > self._button_record_period[0]]]): break # (selected) button released                
        
        self._button_record_period[1] = self.clock # stop recording

    ## Low level methods
    def _run(self):
        # Start DAQ
        if self.__isDAQ:
            DAQ = nidaqmx.Task()
            # Add channels for scanner pulse
            DAQ.di_channels.add_di_chan(DEV + '/port0/line0') # manual
            DAQ.di_channels.add_di_chan(DEV + '/port0/line1') # scanner
            # Add channels for Lumitouch
            DAQ.di_channels.add_di_chan(DEV + '/port0/line2')
            DAQ.di_channels.add_di_chan(DEV + '/port0/line3')
            DAQ.di_channels.add_di_chan(DEV + '/port0/line4')
            DAQ.di_channels.add_di_chan(DEV + '/port0/line5')
            # Add channels for NATA
            DAQ.di_channels.add_di_chan(DEV + '/port1/line0')
            DAQ.di_channels.add_di_chan(DEV + '/port1/line1')
            DAQ.di_channels.add_di_chan(DEV + '/port1/line2')
            DAQ.di_channels.add_di_chan(DEV + '/port1/line3')
            DAQ.di_channels.add_di_chan(DEV + '/port1/line4')
            DAQ.di_channels.add_di_chan(DEV + '/port1/line5')
        else:
            DAQ = simDAQ()
            DAQ.di_channels = range(1, 1+len(self.__buttons) +1)
        
        # Start KB
        if self.emul_buttons: Kb = kbutils.Kb()
    
        self.reset_clock()
        t0 = self.clock
        while self._keep_running.value:
            t = self.clock
            self.rate = t - t0; t0 = t # update rate (for self-diagnostics)

            # get data
            if self.__isDAQ:
                data = [self.is_inverted^d for d in DAQ.read()]
                data[0] = any(data[0:2]); del(data[1])
                data[2] = False # CAVE - Lumitouch: button two is not working
                if all([data[i] for i in [1, 3, 4]]): # CAVE - Lumitouch: random signal on all channels
                    for i in range(1,5): data[i] = False
    #             for i in range(1,5): data[i] = False # TEMP: Lumitouch not connected
    #             for i in range(5,11): data[i] = False # TEMP: NATA not connected
            else:
                data = [0] * len(DAQ.di_channels)

            data = [data[0]] + [utils.binvec2dec(data[1:5]) == b for b in self._button_list_LT] + [utils.binvec2dec(data[5:11]) == b for b in self._button_list_NATA]

            # - scanner synch pulse emulation
            if self.emul_synch and self.TR:
                data[0] = not(self.synch_count) or (t-self.time_of_last_pulse >= self.TR)
    
            # - button press emulation (keyboard)
            if self.emul_buttons:
                kbdata = Kb.kbCheck(); keyCode = [k[0] for k in kbdata if k[1] == 'down']
                data = [data[0]] + utils.ismember(self.buttons,keyCode)

            # synch pulse
            if not(self.synch_count) or (t-self.time_of_last_pulse >= self.synch_readout_time):
                if data[0]:
                    self._synchpulstimes[self.synch_count] = t
            del(data[0])
           
            # buttons
            if t >= self._button_record_period[0] and t <= self._button_record_period[1]:
                ToBp = self._time_of_last_buttonpresses
                if self.__buttonbox_readout: ToBp = [max(ToBp)]*self.number_of_buttons
                for n in range(0,self.number_of_buttons):
                    buttonstates0 = self._buttonstates[:]
                    self._buttonstates[n] = data[n]*self._select_buttons[n]
                    if self._buttonstates[n] and not(buttonstates0[n]) and (t-ToBp[n] > self.readout_time[n+1]):
                        self._buttonpresstimes[n][self._last_button_indices[n]+1] = t

            if self._keep_running.value == -1: self._keep_running.value = 1

        print('Scanner Synch is closing...')
        if self.__isDAQ:
            DAQ.close()
        if self.emul_buttons: 
            Kb.stop()
        print('Done')
        print('Process rate (last iteration): {:.3f}s'.format(self.rate))