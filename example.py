from pyniexp import scannersynch

## Initialise
# SSO = scannersynch.ScannerSynchClass()
# SSO = scannersynch.ScannerSynchClass(True)   % emulate scanner synch pulse
# SSO = scannersynch.ScannerSynchClass(False,True) % emulate button box
# SSO = scannersynch.ScannerSynchClass(True,True) % emulate scanner synch pulse and button box

## Example for scanner synch pulse #1: - Simple case
def example_scanner_wait():
    SSO = scannersynch.ScannerSynch(True)
    SSO.SetSynchReadoutTime(0.5)
    SSO.TR = 2                 # allows detecting missing pulses
    SSO.ResetSynchCount()
    while SSO.SynchCount < 10: # polls 10 pulses
        SSO.WaitForSynch()
        print('Pulse {}: {:.3f}. Measured TR = {:.3f}s'.format(
            SSO.SynchCount,
            SSO.TimeOfLastPulse,
            SSO.MeasuredTR))

## Example for scanner synch pulse #2 - Background check
def example_scanner_check():
    import time
    import random

    SSO = scannersynch.ScannerSynch(True)
    SSO.SetSynchReadoutTime(0.5)
    SSO.TR = 2                                   # allows detecting missing pulses
    SSO.ResetSynchCount()
    while SSO.SynchCount < 10:                   # until 10 pulses
        time.sleep(random.randrange(0,2000)/1000) # in every 0-100 ms ...
        if SSO.CheckSynch(0.01):                 # ... waits for 10 ms for a pulse
            print('Pulse {}: {:.3f}. Measured TR = {:.3f}s. {} synch pulses has/have been missed'.format(
                SSO.SynchCount,
                SSO.TimeOfLastPulse,
                SSO.MeasuredTR,
                SSO.MissedSynch))

## Example for buttons:
def example_buttons():
    SSO = scannersynch.ScannerSynch(True, True)
    SSO.SetButtonReadoutTime(0.5)    # block individual buttons
    # SSO.SetButtonBoxReadoutTime(0.5) # block the whole buttonbox
    SSO.Keys = ['1','2','3','4']       # emulation Buttons #1-#4 with "1"-"4"
    n = 0
    # SSO.BBoxTimeout = 1.5;           # Wait for button press for 1.5s
    # SSO.BBoxTimeout = -1.5;          # Wait for button press for 1.5s even in case of response
    SSO.ResetClock()
    while n != 10:                   # polls 10 button presses
        print('Press a button!')
        SSO.WaitForButtonPress()     # Wait for any button to be pressed
        # SSO.WaitForButtonRelease()   # Wait for any button to be released
        # SSO.WaitForButtonPress([],2) # Wait for Button #3 (=zero-indexed 2)
        # SSO.WaitForButtonPress(2)    # Wait for any button for 2s (overrides SSO.BBoxTimeout only for this event)
        # SSO.WaitForButtonPress(-2)   # Wait for any (number of) button(s) for 2s even in case of response (overrides SSO.BBoxTimeout only for this event)
        # SSO.WaitForButtonPress(2,2)  # Wait for Button #3 (=zero-indexed 2) for 2s (overrides SSO.BBoxTimeout only for this event)
        # SSO.WaitForButtonPress(-2,2) # Wait for (any number of presses of) Button #3 (=zero-indexed 2) for 2s even in case of response (overrides SSO.BBoxTimeout only for this event)
        n = n + 1
        for b in range(0,len(SSO.ButtonPresses)):
            print('#{} Button {} pressed at {:.3f}s'.format(b,SSO.ButtonPresses[b],SSO.TimeOfButtonPresses[b]))
        print('Last: Button {} pressed at {:.3f}s'.format(SSO.LastButtonPress,SSO.TimeOfLastButtonPress))

# example_scanner_wait()
example_scanner_check()
# example_buttons()