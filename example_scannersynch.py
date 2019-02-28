from pyniexp import scannersynch
from time import sleep

## Initialise
# SSO = scannersynch.scanner_synch()
# SSO = scannersynch.scanner_synch(emul_synch=True)   % emulate scanner synch pulse
# SSO = scannersynch.scanner_synch(emul_buttons=True) % emulate button box
# SSO = scannersynch.scanner_synch(emul_synch=True,emul_buttons=True) % emulate scanner synch pulse and button box


## Example for scanner synch pulse #1: - Simple case
def example_scanner_wait(emul_synch=False):
    SSO = scannersynch.scanner_synch(emul_synch=emul_synch)
    SSO.set_synch_readout_time(0.5)
    SSO.TR = 2
    SSO.start_process()
    
    while SSO.synch_count < 10: # polls 10 pulses
        SSO.wait_for_synch()
        print('[{:.3f}] Pulse {}: {:.3f}. Measured TR = {:.3f}s'.format(
            SSO.clock,
            SSO.synch_count,
            SSO.time_of_last_pulse,
            SSO.measured_TR))

    SSO = None
    
## Example for scanner synch pulse #2 - Background check
def example_scanner_check(emul_synch=False):
    from random import randrange

    SSO = scannersynch.scanner_synch(emul_synch=emul_synch)
    SSO.set_synch_readout_time(0.5)
    SSO.TR = 2
    SSO.start_process()
    
    prevSS = 0
    while SSO.synch_count < 10:         # until 10 pulses
        sleep(randrange(250,350)/1000)  # run code for 250-350 ms ...
        if SSO.synch_count > prevSS:
            print('[{:.3f}] Pulse {}: {:.3f}. Measured TR = {:.3f}s. {} synch pulses has/have been missed'.format(
                SSO.clock,
                SSO.synch_count,
                SSO.time_of_last_pulse,
                SSO.measured_TR,
                SSO.synch_count - prevSS - 1))
            prevSS = SSO.synch_count

    SSO = None

if __name__ == '__main__':
#    example_scanner_wait(False)    
    example_scanner_check(False)