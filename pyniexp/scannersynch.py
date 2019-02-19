import math
import sys
import time
import threading

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

#### Emulation class for DAQ

class simDAQ:

    ## Properies

    di_channels = None

#### Main class

class ScannerSynch:
    
    ## Properties 

    # Private constants
    __buttList_LT = (1, 2, 4, 8) # Lumitouch Photon Control (1 hand, 4 buttons)
    __buttList_NATA = (3, 7, 11, 15, 19, 23, 27, 31, 35, 39) # NATA (2 hands, 10 buttons)

    # Public properties
    TR = 0 # emulated pulse frequency
    doCorrection = False # Correct emulated TR based on measurement (counter execution time)

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
        return self.__SynchCount + self.MissedSynch
    @property
    def MissedSynch(self):
        if self.__SynchCount:
            return max(round((self.Clock - self.__TOAp[0])/self.TR)-1,0) if self.TR else 0
        else: return 0

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
    __TR = 0    # original/target TR
        
    __Data = [] # current data
    __Datap = []# previous data
    __TOA = [] # time of access 1*n
    __TOAp = []# previous time of access 1*n
    __threadSynch = None
    __threadButtons = None
    __ReadoutTime = [0] # sec to store data before refresh 1*n
    __BBoxReadout = False
    __BBoxWaitForRealease = False # wait for release instead of press
        
    __isDAQ = 'nidaqmx' in sys.modules
    __isKb = 'pyniexp.kbutils' in sys.modules # Button emulation (keyboard)

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
        mTR = (self.__TOA[0] - self.__TOAp[0])/(self.MissedSynch + 1)
        if mTR and self.doCorrection:
            if not self.__TR: self.__TR = self.TR # save target TR
            self.TR = self.TR - (mTR - self.__TR)
        return mTR

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

    def __init__(self,emulSynch=False,emulButtons=False):
        DEV = 'Dev1'

        print('Initialising Scanner Synch...')
        self.__EmulSynch = emulSynch
        self.__EmulButtons = emulButtons

        # test environment
        try:
            D = nidaqmx.system.System.local().devices
            D = [d for d in D if d.name == DEV]
            D = D[0]
            D.self_test_device()
        except:
            print('WARNING: ', sys.exc_info()[0])
            self.__isDAQ = False

        if not(self.__EmulSynch) and self.__isDAQ:
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
        else:
            self.__isDAQ = False
            self.__EmulSynch = True
            self.__EmulButtons = True
                
            self.__DAQ = simDAQ()
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
        self.__UpdateSynch()
    
    def SynchDaemon(self):
        while True:
            self.WaitForSynch()

    def StartSynchDaemon(self):
        self.__threadSynch = threading.Thread(target=self.SynchDaemon, args=())
        self.__threadSynch.daemon = True
        self.__threadSynch.start()

    ## Buttons
    def SetButtonReadoutTime(self,t):
        self.__ReadoutTime = [self.__ReadoutTime[0]] + [t]*(len(self.__ReadoutTime)-1)
        self.__BBoxReadout = False
        
    def SetButtonBoxReadoutTime(self,t):
        self.__ReadoutTime = [self.__ReadoutTime[0]] + [t]*(len(self.__ReadoutTime)-1)
        self.__BBoxReadout = True

    def WaitForButtonPress(self,timeOut=None,indButton=None):
        BBoxQuery = self.Clock

        # Reset indicator
        self.__ButtonPresses = []
        self.__TimeOfButtonPresses = []
        self.__LastButtonPress = []    

        # timeout
        if type(timeOut) == int: timeout = timeOut
        else: timeout = self.BBoxTimeout
        wait = timeout < 0 # wait until timeout even in case of response
        timeout = abs(timeout)

        while ((not self.Buttons or # button pressed
            wait or
            (type(indButton) == list and not any([any([bp == i for i in indButton]) for bp in self.LastButtonPress]))) and # correct button pressed
            self.Clock - BBoxQuery < timeout):
            if len(self.LastButtonPress):
                if type(indButton) == list and not any([any([bp == i for i in indButton]) for bp in self.LastButtonPress]): # incorrect button
                    self.__LastButtonPress = []
                    continue
                if len(self.TimeOfButtonPresses) and (self.TimeOfButtonPresses[len(self.TimeOfButtonPresses)-1] == self.TimeOfLastButtonPress): continue # same event
                self.__ButtonPresses = self.__ButtonPresses + self.LastButtonPress
                self.__TimeOfButtonPresses = self.__TimeOfButtonPresses + [self.TimeOfLastButtonPress]*len(self.LastButtonPress)

    def WaitForButtonRelease(self,timeOut=None,indButton=None):
        # backup settings
        rot = self.__ReadoutTime[1:len(self.__ReadoutTime)] 
        bbro = self.__BBoxReadout 

        # config for release
        self.__BBoxWaitForRealease = True
        self.SetButtonBoxReadoutTime(0)

        self.WaitForButtonPress(timeOut, indButton)
            
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
        return b,t

    def WaitForButtonPressInBackground(self,timeout=None,indButton=None):
        if not(self.__threadButtons is None) and self.__threadButtons.isAlive: self.__threadButtons._delete()

        self.__threadButtons = threading.Thread(target=self.WaitForButtonPress, args=(timeout,indButton))
        self.__threadButtons.daemon = True
        self.__threadButtons.start()

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
            data[0] = (not self.__SynchCount) or (t-self.__TOA[0] >= self.TR)
 
        # button press emulation (keyboard)
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
        self.__TOA = [t if self.__Data[i] else self.__TOA[i] for i in range(0,len(self.__TOA))]

    def __UpdateSynch(self):
        if not self.__SynchCount:
            self.ResetClock()
            self.__SynchCount = 1
        else:
            self.__SynchCount = self.__SynchCount + 1