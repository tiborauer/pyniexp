import nidaqmx
import math

class ScannerSynchClass:
    
    __buttList_LT = [1, 2, 4, 8] # Lumitouch Photon Control (1 hand, 4 buttons)
    __buttList_NATA = [3, 7, 11, 15, 19, 23, 27, 31, 35, 39] # NATA (2 hands, 10 buttons)

    TR = 0 # emulated pulse frequency
    PulseWidth = 0.005 # emulated pulse width 

    Keys = []
    BBoxTimeout = math.inf # second (timeout for WaitForButtonPress)
    isInverted = False

    isDAQ = True

    def __init__(self,emulSynch,emulButtons):
        print('Initialising Scanner Synch...')
        # test environment
        

        print('Done')