import math
import sys
import time

import scannersynch.utils as utils

try:
    import nidaqmx
except ImportError:
    print('WARNING: nidaqmx module is not available --> ', end='')
    print('You can run ScannerSynch only in emulation mode')

try:
    import scannersynch.kbutils as kbutils
except ImportError:
    print('WARNING: kbutils module is not available --> ', end='')
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

    __LastButtonPress = []
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
    __Kb = None
    __nChannels = 0
        
    __t0 = None # internal timer
        
    __Data = [] # current data
    __Datap = []# previous data
    __TOA = [] # time of access 1*n
    __TOAp = []# previous time of access 1*n
    __ReadoutTime = [0] # sec to store data before refresh 1*n
    __BBoxReadout = False
    __BBoxWaitForRealease = False # wait for release instead of press
        
    __isDAQ = 'nidaqmx' in sys.modules
    __isKb = 'scannersynch.kbutils' in sys.modules # Button emulation (keyboard)

    # Dependent properties
    @property
    def IsValid(self):
        print(self.__isKb)
        return (not self.__DAQ == None) and (not self.__EmulButtons or (self.__EmulButtons and self.__isKb))

    @property
    def Clock(self):
        return time.time() - self.__t0
            
    @property
    def Synch(self):
        val = False
        self.__Refresh()
        if self.__Data[0]:
            self.__Data[0] = False
            val = True
        return val
    @property
    def TimeOfLastPulse(self):
        return self.__TOA[0]
    @property
    def MeasuredTR(self):
        return (self.__TOA[0] - self.__TOAp[0])/(self.MissedSynch + 1)

    @property
    def Buttons(self):
        val = False
        self.__Refresh()
        if self.__BBoxWaitForRealease:
            if any(self.__Datap[1:len(self.__Datap)]) and all([not(self.__Data[i] and self.__Datap[i]) for i in range(0,len(self.__Datap))]):
                self.__LastButtonPress = [i-1 for i in range(1,len(self.__Datap)) if self.__Datap[i]]
                self.__Datap = [self.__Datap[0]] + [False] * (len(self.__Datap)-1)
                val = True
        else:
            if any(self.__Data[1:len(self.__Data)]):
                self.__LastButtonPress = [i-1 for i in range(1,len(self.__Data)) if self.__Data[i]]
                self.__Data = [self.__Data[0]] + [False] * (len(self.__Data)-1)
                val = True
        return val
    @property
    def TimeOfLastButtonPress(self):
        return max(self.__TOA[1:len(self.__TOA)]) * (len(self.LastButtonPress) > 0)

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
        
        if self.__Kb:
            self.__Kb.stop()

        print('Done')

    ## Utils

    def ResetClock(self):
        self.__t0 = time.time()
        self.__TOA = [0] * self.nChannels
        self.__TOAp = [0] * self.nChannels

    @Keys.setter
    def Keys(self,val):
        if self.__isKb:
            kbutils.kbLayout
            if not all(utils.ismember(val,kbutils.kbLayout)):
                print('WARNING: Some keys are not recognised in...')
                print(kbutils.kbLayout)
                return

            self.__Keys = val
            self.__DAQ.di_channels = range(1, 1+len(self.__Keys) +1)
            self.nChannels = 1+len(self.__Keys)
            self.__Data = [0] * self.nChannels
            self.__Datap = [0] * self.nChannels
            self.__ReadoutTime = [self.__ReadoutTime[0]] + [self.__ReadoutTime[1]]*(self.nChannels-1)

            if type(self.__Kb) != kbutils.Kb:
                self.__Kb = kbutils.Kb()
        else:
            print('WARNING: "kbutils" is not available')

    ## Scanner Pulse
    def ResetSynchCount(self):
        self.__SynchCount = 0

    def SetSynchReadoutTime(self,t):
        self.__ReadoutTime[0] = t
    
    def WaitForSynch(self):
        while not self.Synch:
            pass
        self.__NewSynch()
    
    def CheckSynch(self,timeout):
        SynchQuery = self.Clock

        val = False

        while (self.Clock - SynchQuery) < timeout:
            if self.Synch:
                self.__NewSynch()
                val = True
                break            

        return val

    ## Buttons
    def SetButtonReadoutTime(self,t):
        self.__ReadoutTime = [self.__ReadoutTime[0]] + [t]*(len(self.__ReadoutTime)-1)
        self.__BBoxReadout = False
        
    def SetButtonBoxReadoutTime(self,t):
        self.__ReadoutTime = [self.__ReadoutTime[0]] + [t]*(len(self.__ReadoutTime)-1)
        self.__BBoxReadout = True

    def WaitForButtonPress(self,*args): # timeout, ind
        BBoxQuery = self.Clock

        # Reset indicator
        self.__ButtonPresses = []
        self.__TimeOfButtonPresses = []
        self.__LastButtonPress = []    

        # timeout
        if len(args) >= 1 and type(args[0]) == int: timeout = args[0]
        else: timeout = self.BBoxTimeout
        wait = timeout < 0 # wait until timeout even in case of response
        timeout = abs(timeout)

        while ((not self.Buttons or # button pressed
            wait or
            (len(args) >= 2 and type(args[1]) == int and not any([bp == args[1] for bp in self.LastButtonPress]))) and # corrrct button pressed
            self.Clock - BBoxQuery < timeout):
            if len(self.LastButtonPress):
                if len(args) >= 2 and type(args[1]) == int and not any([bp == args[1] for bp in self.LastButtonPress]): continue # incorrect button
                if len(self.TimeOfButtonPresses) and (self.TimeOfButtonPresses[len(self.TimeOfButtonPresses)-1] == self.TimeOfLastButtonPress): continue # same event
                self.__ButtonPresses = self.__ButtonPresses + self.LastButtonPress
                self.__TimeOfButtonPresses = self.__TimeOfButtonPresses + [self.TimeOfLastButtonPress]*len(self.LastButtonPress)

    def WaitForButtonRelease(self,*args):
        # backup settings
        rot = self.__ReadoutTime[1:len(self.__ReadoutTime)] 
        bbro = self.__BBoxReadout 

        # config for release
        self.__BBoxWaitForRealease = True
        self.SetButtonBoxReadoutTime(0)

        self.WaitForButtonPress(*args)
            
        # restore settings
        self.__BBoxWaitForRealease = False
        self.__ReadoutTime = [self.__ReadoutTime[0]] + rot
        self.__BBoxReadout = bbro

    def ReadButton(self):
        b = self.LastButtonPress
        t = self.TimeOfLastButtonPress
        self.__LastButtonPress = []
        self.__ButtonPresses = []
        self.__TimeOfButtonPresses = []
        return (b,t)

    ## Low level methods
    def __Refresh(self):
        t = self.Clock

        # get data
        if self.__isDAQ:
            data = [self.isInverted^d for d in self.__DAQ.read()]
            data[0] = any(data[0:2]); del(data[1])
            data[2] = False # CAVE - Lumitouch: button two is not working
            if all([data[i] for i in [1, 3, 4]]): # CAVE - Lumitouch: random signal on all channels
                for i in range(1,5): data[i] = False
#             for i in range(1,5): data[i] = False # TEMP: Lumitouch not connected
#             for i in range(5,11): data[i] = False # TEMP: NATA not connected
        else:
            data = [0] * len(self.__DAQ.di_channels)
        
        data = [data[0]] + [utils.binvec2dec(data[1:5]) == b for b in self.__buttList_LT] + [utils.binvec2dec(data[5:11]) == b for b in self.__buttList_NATA]

        # scanner synch pulse emulation
        if self.EmulSynch and self.TR:
            data[0] = (not self.__SynchCount) or ((t-self.__TOA[0] >= self.TR) and ((t-self.__TOA[0]) % self.TR <= self.PulseWidth))
 
        # button press emulation (keyboard) via PTB
        if self.EmulButtons:
            nKeys = len(self.Keys)
            if self.__isKb and nKeys:
                kbdata = self.__Kb.kbCheck(); keyCode = [k[0] for k in kbdata if k[1] == 'down']
                data = [data[0]] + utils.ismember(self.Keys,keyCode)

        if self.__BBoxReadout: 
            self.__TOA = [self.__TOA[0]] + [max(self.__TOA[1:len(self.__TOA)])] * (len(self.__TOA)-1)
        ind = [t-self.__TOA[i] > self.__ReadoutTime[i] for i in range(0,len(self.__ReadoutTime))]
        self.__Datap = self.__Data
        self.__Data = [data[i] if ind[i] else self.__Data[i] for i in range(0,len(self.__Data))]
        self.__TOAp = self.__TOA
        self.__TOA = [t if self.__Data[i] else self.__TOA[i] for i in range(0,len(self.__Data))]

    def __NewSynch(self):
        if not self.SynchCount:
            self.ResetClock()
            self.__SynchCount = 1
        else:
            if self.TR:
                self.__MissedSynch = 0
                self.__MissedSynch = round(self.MeasuredTR/self.TR)-1
            self.__SynchCount = self.SynchCount + 1 + self.MissedSynch