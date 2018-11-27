import scannersynch

## Initialise
SSO = scannersynch.ScannerSynchClass()
# SSO = scannersynch.ScannerSynchClass(True)   % emulate scanner synch pulse
# SSO = scannersynch.ScannerSynchClass(False,True) % emulate button box
# SSO = scannersynch.ScannerSynchClass(True,True) % emulate scanner synch pulse and button box

## Example for scanner synch pulse #1: - Simple case
SSO.SetSynchReadoutTime(0.5)
# SSO.TR = 2                # allows detecting missing pulses
SSO.ResetSynchCount()
while SSO.SynchCount < 10:  # polls 10 pulses
    SSO.WaitForSynch()
    print('Pulse {}: {:.3f}. Measured TR = {:.3f}s\n'.format(
        SSO.SynchCount,
        SSO.TimeOfLastPulse,
        SSO.MeasuredTR))