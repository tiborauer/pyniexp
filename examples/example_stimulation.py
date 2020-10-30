from pyniexp.stimulation import Waveform, Stimulator
from time import sleep

stim = Stimulator(configFile=r'D:\Projects\pyniexp\examples\config_stimulation_sim.json')

# Output Signal Parameters
phase=0
freqs = [0, 5, 10, 15, 30, 60]

wave1 = Waveform(amplitude = 1, frequency = 10, phase=0, duration = 10.0, rampUp = 3, rampDown = 3, samplingRate = 1000)
wave2 = Waveform(amplitude = 1, frequency = 10, phase=phase, duration = 10.0, rampUp = 3, rampDown = 3, samplingRate = 1000)

# wave1.show()
# wave2.show()

for f in freqs:
    print(f)
    wave1.frequency = f
    wave2.frequency = f
    stim.loadWaveform([wave1, wave2])
    stim.stimulate()
    sleep(15)

stim = None