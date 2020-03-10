from pyniexp.stimulation import Waveform, Stimulator

stim = Stimulator()

# Output Signal Parameters
phase=0

wave1 = Waveform(amplitude = 0, frequency = 10, phase=0, duration = 20.0, rampUp = 4, rampDown = 4, samplingRate = 1000)
wave2 = Waveform(amplitude = 0, frequency = 10, phase=phase, duration = 20.0, rampUp = 4, rampDown = 4, samplingRate = 1000)

# wave1.show()
# wave2.show()

stim.loadWaveform([wave1, wave2])

stim.stimulate()

stim = None