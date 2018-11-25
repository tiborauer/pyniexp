import math
import sys
import time

try:
    import nidaqmx
except ImportError:
    print('WARNING: nidaqmx module is not available --> ', end='')
    print('You can run ScannerSynch only in emulation mode')

try:
    import keyboard
except ImportError:
    print('WARNING: keyboard module is not available --> ', end='')
    print('You cannot emulate buttons')

#### Emulation class for DAQ

class DAQClass:

    ## Properies

    di_channels = None

#### Main class

class ScannerSynchClass:
    
    ## Properties 

    # Private constants
    __buttList_LT = (1, 2, 4, 8) # Lumitouch Photon Control (1 hand, 4 buttons)
    __buttList_NATA = (3, 7, 11, 15, 19, 23, 27, 31, 35, 39) # NATA (2 hands, 10 buttons)

    # Public properties
    TR = 0 # emulated pulse frequency
    PulseWidth = 0.005 # emulated pulse width 

    __Keys = []
    @property
    def Keys(self):
        return self.__Keys

    BBoxTimeout = math.inf # second (timeout for WaitForButtonPress)
    isInverted = False

    # Public read-only properties
    __SynchCount = 0
    @property
    def SynchCount(self):
        return self.__SynchCount
    __MissedSynch = 0
    @property
    def MissedSynch(self):
        return self.__MissedSynch

    __ButtonPresses = []
    @property
    def ButtonPresses(self):
        return self.__ButtonPresses   
    __TimeOfButtonPresses = 0
    @property
    def TimeOfButtonPresses(self):
        return self.__TimeOfButtonPresses   

    __LastButtonPress = 0
    @property
    def LastButtonPress(self):
        return self.__LastButtonPress   
        
    __EmulSynch = False
    @property
    def EmulSynch(self):
        return self.__EmulSynch   
    __EmulButtons = False
    @property
    def EmulButtons(self):
        return self.__EmulButtons   

    # Private properties
    __DAQ = None
    __nChannels = 0
        
    __t0 = None # internal timer
        
    __KBList = []
    __Data = [] # current data
    __Datap = []# previous data
    __TOA = [] # time of access 1*n
    __TOAp = []# previous time of access 1*n
    __ReadoutTime = [0] # sec to store data before refresh 1*n
    __BBoxReadout = False
    __BBoxWaitForRealease = False # wait for release instead of press
        
    __isDAQ = 'nidaqmx' in sys.modules
    __isKB = 'keyboard' in sys.modules # Button emulation (keyboard)

    # Dependent properties
    @property
    def IsValid(self):
        return (not self.__DAQ == None) and (not self.__EmulButtons or (self.__EmulButtons and self.__isKB))

    @property
    def Clock(self):
        return time.time() - self.__t0
            
    @property
    def Synch(self):
        return []
    @property
    def TimeOfLastPulse(self):
        return []
    @property
    def MeasuredTR(self):
        return []

    @property
    def Buttons(self):
        return []
    @property
    def TimeOfLastButtonPress(self):
        return []

    ## Constructor

    def __init__(self,*args):
        DEV = 'SimDev1'  # ToDo: switch for Dev1

        print('Initialising Scanner Synch...')
        # test environment
        try:
            D = nidaqmx.system.System.local().devices
            D = [d for d in D if d.name == DEV]
            D = D[0]
            D.self_test_device()
        except:
            print('WARNING: ', sys.exc_info()[0])
            self.__isDAQ = False

        if (len(args)<2 or not args[0] or not args[1]) and self.__isDAQ:
            self.__DAQ = nidaqmx.Task()
            # Add channels for scanner pulse
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line0') # manual
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line1') # scanner
            # Add channels for Lumitouch
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line2')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line3')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line4')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port0/line5')
            # Add channels for NATA
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line0')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line1')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line2')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line3')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line4')
            self.__DAQ.di_channels.add_di_chan(DEV + '/port1/line5')

            if len(args) == 2:
                self.__EmulSynch = args[0]
                self.__EmulButtons = args[1]
            elif len(args) == 1:
                self.__EmulSynch = args[0]
                self.__EmulButtons = False
            elif len(args) == 0:
                self.__EmulSynch = False
                self.__EmulButtons = False
        else:
            self.__isDAQ = False
            self.__EmulSynch = True
            self.__EmulButtons = True
                
            self.__DAQ = DAQClass()
            self.__DAQ.di_channels = range(1, 1+len(self.__buttList_LT)+len(self.__buttList_NATA) +1)

            print('')
            print('WARNING: DAQ card is not in use!')

        if not self.IsValid:
            print('WARNING: Scanner Synch is not open!')
            self.__del__()
            return

        if self.__EmulSynch:
            print('Emulation: Scanner synch pulse is not in use --> ', end='')
            print('You may need to set TR!')

        if self.__EmulButtons:
            print('Emulation: ButtonBox is not in use           --> ', end='')
            print('You may need to set Keys!')

        self.nChannels = 1+len(self.__buttList_LT)+len(self.__buttList_NATA)

        self.__Data = [0] * self.nChannels
        self.__Datap = [0] * self.nChannels
        self.__ReadoutTime = self.__ReadoutTime * self.nChannels
        self.ResetClock()

        print('Done')

    ## Destructor

    def __del__(self):
        print('Scanner Synch is closing...')
        if self.__isDAQ:
            self.__DAQ.close()
        
        if self.__isKB:
            keyboard.unhook_all()

        print('Done')

    ## Utils

    def ResetClock(self):
        self.__t0 = time.time()
        self.__TOA = [0] * self.nChannels
        self.__TOAp = [0] * self.nChannels

    @Keys.setter
    def Keys(self,val):
        self.__Keys = val
        self.__KBList = []
        keyboard.hook(self.__store_keys)

    ## Low level methods
    def Refresh(self):
        t = self.Clock

        # get data
        if self.__isDAQ:
            data = [self.isInverted^d for d in self.__DAQ.read()]
            data[0] = any(data[0:2]); del(data[1])
            data[2] = False # CAVE - Lumitouch: button two is not working
        else:
            data = [0] * len(self.__DAQ.di_channels)

    #            if all(data([2 4 5])), data(2:5) = 0; end % CAVE - Lumitouch: random signal on all channels
#%                 data(2:5) = 0; % TEMP: Lumitouch not connected
#%                 data(6:11) = 0; % TEMP: NATA not connected
    
    def __store_keys(self,e):
        self.__KBList.append(e)
