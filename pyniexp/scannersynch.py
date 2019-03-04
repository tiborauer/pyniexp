from math import inf
import sys, json
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

#### Main class
class scanner_synch:
    
    ## Properties 
    # Private properties
    __config = None
    __buttonbox_readout = False
    __process = Process()

    __isDAQ = 'nidaqmx' in sys.modules
    __isKb = 'pyniexp.kbutils' in sys.modules # Button emulation (keyboard)

    # Public properties
    buttonbox_timeout = inf # second (timeout for WaitForButtonPress)
    is_inverted = False

    # Public read-only properties
    __emul_synch = 0
    @property
    def emul_synch(self):
        return self.__emul_synch   
    __emul_buttons = 0
    @property
    def emul_buttons(self):
        return self.__emul_buttons   

    __readout_time = [0.5, 0.5] # sec to store data before refresh 1*n (default 0.5)
    @property
    def readout_time(self):
        return self.__readout_time

    # Dependent properties
    @property
    def is_valid(self):
        valid = True
        valid = valid and (self.__isDAQ or (self.emul_buttons and self.emul_buttons))
        if (self.emul_synch == 1) and not(self.TR):
            print('Emulation: Scanner synch pulse is not in use --> ', end='')
            print('You need to set TR!')
            valid = valid and False
        if (self.emul_buttons == 1) and not(len(self.buttons)):
            print('Emulation: Buttonbox is not in use           --> ', end='')
            print('You need to set Buttons!')
            valid = valid and False
        if (self.emul_buttons == 0) and not(len(self.__buttonbox)):
            print('Buttonbox: none is configured                --> ', end='')
            print('You need to add at least one buttonbox!')
            valid = valid and False
        
        if not(valid): print('Validation: FAILED!')

        return valid

    ## Constructor
    def __init__(self,config=None,emul_synch=False,emul_buttons=False):
        self.__buttonbox = []

        print('Initialising Scanner Synch...')
        if not(config is None):
            with open(config) as fid:
                self.__config = json.load(fid)
        else:
            if emul_synch != -1: emul_synch = 1
            if emul_buttons != -1: emul_buttons = 1
            self.__isDAQ = False

        self.__emul_synch = emul_synch
        self.__emul_buttons = emul_buttons

        # test environment
        if (self.emul_synch == 0) or (self.emul_buttons == 0):
            try:
                D = nidaqmx.system.System.local().devices
                D = [d for d in D if d.name == self.__config['DAQ']['Hardware']]
                D = D[0]
                D.self_test_device()
            except:
                print('WARNING - DAQ card is not available:', sys.exc_info()[0])
                self.__isDAQ = False
                if self.__emul_synch != -1: self.__emul_synch = 1
                if self.__emul_buttons != -1: self.__emul_buttons = 1
        else: self.__isDAQ = False

        self._t0 = Value('d',time())      # internal timer
        self._keep_running = Value('b',-1) # internal signal (-1: not started, 1: running)
        self.start_process()

    ## Destructor
    def __del__(self):
        if self._keep_running.value:
            self._keep_running.value = 0

    ## Utils
    # Process
    def start_process(self,max_pulses=None):
        if self.__process.is_alive(): 
            print('Process is already running')
            return

        if max_pulses is None: max_pulses = self.__config['DAQ']['BufferLength']

        print('Starting process...')

        if not(self.is_valid): 
            print('You have to start the process manually by calling <object>.start_process()!')
            return
        self._synchpulsetimes = RawArray('d', [-1]*max_pulses)
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

    # Clock
    @property
    def clock(self):
        return time() - self._t0.value

    def reset_clock(self):
        self._t0.value = time()

    # TR
    __TR = None    # emulated pulse frequency
    @property
    def TR(self):
        return self.__TR

    @TR.setter
    def TR(self,val):
        if self.__process.is_alive():
            self.__process.terminate()
        
        self.__TR = val

    # Buttons
    def add_buttonbox(self,name='Nata'):
        conf = [bbconf for bbconf in self.__config['ButtonBox'] if bbconf['Name'] == name]
        if not(len(conf)): print('ERROR: no configuration found for \'{}\''.format(name)); return
        elif len(conf) > 1:  print('ERROR: multiple matching configurations found {}'.format([c['Name'] for c in conf])); return
        self.__buttonbox.append(conf[0])

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
        else: return sum([len(c['ButtonCode']) for c in self.__buttonbox])

    ## Scanner Pulse
    @property
    def synch_count(self):
        return sum([i > -1 for i in self._synchpulsetimes])

    def reset_synch_count(self):
        for n in range(0,len(self._synchpulsetimes)):
            self._synchpulsetimes[n] = -1
    
    @property
    def synch_readout_time(self):
        return self.__readout_time[0]

    def set_synch_readout_time(self,t):
        self.__readout_time[0] = t
    
    def wait_for_synch(self):
        if not(self.__process.is_alive()): 
            print('Process is not running')
            return

        synch_count0 = self.synch_count
        while not(self.synch_count > synch_count0): pass
    
    @property
    def time_of_last_pulse(self):
        return self._synchpulsetimes[self.synch_count-1]
    
    @property
    def measured_TR(self):
        if self.synch_count > 1: return self.time_of_last_pulse - self._synchpulsetimes[self.synch_count-2] 
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
        if not(self.__process.is_alive()): 
            print('Process is not running')
            return

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
        DAQ = []
        if self.__isDAQ:            
            DAQ.append(nidaqmx.Task())
            # Add channels for scanner pulse
            DAQ[0].di_channels.add_di_chan(self.__config['DAQ']['Hardware'] + '/' + self.__config['SynchPulse']['Channel_Manual']) # manual
            DAQ[0].di_channels.add_di_chan(self.__config['DAQ']['Hardware'] + '/' + self.__config['SynchPulse']['Channel_Scanner']) # scanner

            # Add channels for buttonbox(es)
            for bb in self.__buttonbox:
                DAQ.append(nidaqmx.Task())
                for ch in bb['Channels']:
                    DAQ[-1].di_channels.add_di_chan(self.__config['DAQ']['Hardware'] + '/' + ch)
        
        # Start KB
        if self.emul_buttons: Kb = kbutils.Kb()
    
        self.reset_clock()
        t0 = self.clock
        while self._keep_running.value:
            t = self.clock
            self.rate = t - t0; t0 = t # update rate (for self-diagnostics)

            # Synch pulse
            if self.emul_synch != -1:
                # - data
                if self.emul_synch == 0:
                    synch = any([d^self.is_inverted for d in DAQ[0].read()])
                elif self.emul_synch == 1:
                    synch = not(self.synch_count) or (t-self.time_of_last_pulse >= self.TR)
                # - process
                if not(self.synch_count) or (t-self.time_of_last_pulse >= self.synch_readout_time):
                    if synch: self._synchpulsetimes[self.synch_count] = t
            
            # Buttons
            if self.emul_buttons != -1:
                # - data
                b_data = []
                if self.emul_buttons == 0:
                    for bb_ind in range(0,len(self.__buttonbox)):
                        bb_code = utils.binvec2dec([d^self.is_inverted for d in DAQ[bb_ind+1].read()])
                        if any([bb_code == ign for ign in self.__buttonbox[bb_ind]['Ignore']]): bb_code = -1 # ignore faulty signal
                        b_data += utils.ismember(self.__buttonbox[bb_ind]['ButtonCode'],[bb_code])
                elif self.emul_buttons == 1:
                    kb_data = Kb.kbCheck(); key_code = [k[0] for k in kb_data if k[1] == 'down']
                    b_data = utils.ismember(self.buttons,key_code)
                # -process
                if t >= self._button_record_period[0] and t <= self._button_record_period[1]:
                    ToBp = self._time_of_last_buttonpresses
                    if self.__buttonbox_readout: ToBp = [max(ToBp)]*self.number_of_buttons
                    for n in range(0,self.number_of_buttons):
                        buttonstates0 = self._buttonstates[:]
                        self._buttonstates[n] = b_data[n]*self._select_buttons[n]
                        if self._buttonstates[n] and not(buttonstates0[n]) and (t-ToBp[n] > self.readout_time[n+1]):
                            self._buttonpresstimes[n][self._last_button_indices[n]+1] = t

            if self._keep_running.value == -1: self._keep_running.value = 1

        print('Scanner Synch is closing...')
        if self.__isDAQ:
            [d.close() for d in DAQ]
        if self.emul_buttons: 
            Kb.stop()
        print('Done')
        print('Process rate (last iteration): {:.3f}s'.format(self.rate))