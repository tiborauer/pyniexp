from pyniexp import scannersynch
import time

## Initialise
# SSO = scannersynch.ScannerSynch()
# SSO = scannersynch.ScannerSynch(emulSynch=True)   % emulate scanner synch pulse
# SSO = scannersynch.ScannerSynch(emulButtons=True) % emulate button box
# SSO = scannersynch.ScannerSynch(emulSynch=True,emulButtons=True) % emulate scanner synch pulse and button box

## Example for scanner synch pulse #1: - Simple case
def example_scanner_wait(emulSynch=False):
    SSO = scannersynch.ScannerSynch(emulSynch=emulSynch)
    SSO.SetSynchReadoutTime(0.5)
    SSO.TR = 2                 # allows detecting missing pulses

    SSO.ResetSynchCount()
    while SSO.SynchCount < 10: # polls 10 pulses
        SSO.WaitForSynch()
        print('[{:.3f}] Pulse {}: {:.3f}. Measured TR = {:.3f}s'.format(
            SSO.Clock,
            SSO.SynchCount,
            SSO.TimeOfLastPulse,
            SSO.MeasuredTR))

## Example for scanner synch pulse #2 - Background check
def example_scanner_daemon(emulSynch=False):
    import time
    import random

    SSO = scannersynch.ScannerSynch(emulSynch=emulSynch)
    SSO.SetSynchReadoutTime(0.5)
    SSO.TR = 2                                      # allows detecting missing pulses
    SSO.doCorrection = True                        # allow correction of emulated TR for execution time

    prevSS = 0
    SSO.ResetSynchCount()
    SSO.StartSynchDaemon()                          # start background monitor
    while SSO.SynchCount < 10:                      # until 10 pulses
        time.sleep(random.randrange(250,350)/1000)  # run code for 250-350 ms ...
        if SSO.SynchCount > prevSS:
            print('[{:.3f}] Pulse {}: {:.3f}. Measured TR = {:.3f}s. {} synch pulses has/have been missed'.format(
                SSO.Clock,
                SSO.SynchCount,
                SSO.TimeOfLastPulse,
                SSO.MeasuredTR,
                SSO.MissedSynch))
            prevSS = SSO.SynchCount

## Example for buttons:
def example_buttons(emulButtons=False):
    SSO = scannersynch.ScannerSynch(emulButtons=emulButtons)
    SSO.SetButtonReadoutTime(0.25)    # block individual buttons
    # SSO.SetButtonBoxReadoutTime(0.5) # block the whole buttonbox
    if emulButtons: SSO.Keys = ['1','2','3','4']     # emulation Buttons #1-#4 with "1"-"4"
    n = 0
    # SSO.BBoxTimeout = 1.5;           # Wait for button press for 1.5s
    # SSO.BBoxTimeout = -1.5;          # Wait for button press for 1.5s even in case of response
    SSO.ResetClock()
    while n != 10:                   # polls 10 button presses
        print('\n[{:.3f}s] - Press a button of {}!'.format(SSO.Clock,SSO.Keys))
        SSO.WaitForButtonPress()     # Wait for any button to be pressed
        # SSO.WaitForButtonRelease()   # Wait for any button to be released
        # SSO.WaitForButtonPress(indButton=[2]) # Wait for Button #3 (=zero-indexed 2)
        # SSO.WaitForButtonPress(timeout=2)     # Wait for any button for 2s (overrides SSO.BBoxTimeout only for this event)
        # SSO.WaitForButtonPress(timeout=-2)    # Wait for any (number of) button(s) for 2s even in case of response (overrides SSO.BBoxTimeout only for this event)
        # SSO.WaitForButtonPress(timeout=2,indButton=[2])   # Wait for Button #3 (=zero-indexed 2) for 2s (overrides SSO.BBoxTimeout only for this event)
        # SSO.WaitForButtonPress(timeout=-2,indButton=[2])  # Wait for (any number of presses of) Button #3 (=zero-indexed 2) for 2s even in case of response (overrides SSO.BBoxTimeout only for this event)
        # SSO.WaitForButtonPressInBackground(timeout=-2,indButton=[0,2]); time.sleep(4)   # Wait for any (number of) buttons #1 and #3 (=zero-indexed 0 and 2) for 2s even in case of response (overrides SSO.BBoxTimeout only for this event) in the background
        n = n + 1
        for b in range(0,len(SSO.ButtonPresses)):
            print('#{} Button {} pressed at {:.3f}s'.format(b,SSO.ButtonPresses[b],SSO.TimeOfButtonPresses[b]))
        if emulButtons: print('[{:.3f}s] - Last: Button {} pressed at {:.3f}s'.format(SSO.Clock,[SSO.Keys[i] for i in SSO.LastButtonPress],SSO.TimeOfLastButtonPress))
        else: print('[{:.3f}s] - Last: Button {} pressed at {:.3f}s'.format(SSO.Clock,SSO.LastButtonPress,SSO.TimeOfLastButtonPress))

#example_scanner_wait()
example_scanner_daemon()
#example_buttons()
