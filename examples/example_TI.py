from pyniexp.stimulator import TI

stim = TI()
stim.connect()

stim.load()

stim.start()
stim.stop()

stim = None