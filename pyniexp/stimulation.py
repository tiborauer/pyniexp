import nidaqmx, json, sys
from numpy import concatenate, vstack, arange, linspace, cos, pi, ones
from nidaqmx.stream_writers import AnalogMultiChannelWriter
import matplotlib.pyplot as plt

class Waveform:
    SCALING = 2 # actual intensity = amplitude (V) * SCALE (2mA/V)

    def __init__(self,amplitude = 1, frequency = 10, phase=0, duration = 20, rampUp = 4, rampDown = 4, samplingRate = 1000):
        
        self.amplitude = amplitude/self.SCALING 
        self.frequency = frequency
        self.phase = phase
        self.rampUp = rampUp
        self.rampDown = rampDown
        self.duration = duration
        self.samplingRate = samplingRate
    
    @property
    def duration(self): return self._duration

    @duration.setter
    def duration(self,val):
        assert val > self.rampUp + self.rampDown, "duration {} is smaller than rampup + rampdown = {}".format(val, self.rupDuration + self.rdownDuration)
        self._duration = val

    @property
    def signal(self):
        stimDuration = self.duration-(self.rampUp+self.rampDown)
        dt = 1/self.samplingRate    # seconds per sample
        
        t = arange(0,self.duration,dt)   # timesteps
        lag = self.phase*(pi/180)        # calculate into phase

        waveform = cos(2*pi*self.frequency*t-lag)

        rampup = linspace(0,self.amplitude,self.rampUp*self.samplingRate)
        rampdown = linspace(self.amplitude,0,self.rampDown*self.samplingRate)
        envelope = concatenate((rampup,self.amplitude*ones(stimDuration*self.samplingRate),rampdown))

        return envelope * waveform

    def show(self):
        fig, ax = plt.subplots()
        ax.plot(arange(0,self.duration,1/self.samplingRate) , self.signal*self.SCALING, label='Waveform')
        ax.set(xlabel='time [s]', ylabel='intensity [mA]')
        ax.grid()
        ax.legend()

        plt.show()

class Stimulator:
    isDAQ = False
    _DAQ = None

    @property
    def nChannels(self):
        if self.isDAQ:
            return len(self.__config['Channels'])
        else: return 0

    def __init__(self,configFile='config_stimulation.json'):
        with open(configFile) as config:
            self.__config = json.load(config)

        try:
            D = nidaqmx.system.System.local().devices
            D = [d for d in D if d.name == self.__config['DAQ']['Hardware']]
            D = D[0]
            D.self_test_device()
            self.isDAQ = True
        except:
            print('WARNING - DAQ card {} is not available'.format(self.__config['DAQ']['Hardware']), sys.exc_info()[0])

        if self.isDAQ:
            self.initialize()
            self.waves = []


    def __del__(self):
        if self.isDAQ: 
            self.close()

    def initialize(self):
        if not(self._DAQ is None): self.close()
        self._DAQ = nidaqmx.Task()

        for ch in self.__config['Channels']:
            self._DAQ.ao_channels.add_ao_voltage_chan(self.__config['DAQ']['Hardware'] + '/' + ch)

        self._DAQ.timing.samp_quant_samp_mode = nidaqmx.constants.AcquisitionType['CONTINUOUS']

        if not(self.__config['ControlSignal'] is None):
            self._DAQ.write([self.__config['ControlSignal']]*self.nChannels)

    def close(self):
        if self._DAQ is None: return
        if self.isRunning: self._DAQ.stop()
        self._DAQ.close()
        self._DAQ = None

    @property
    def isRunning(self):
        return not(self._DAQ.is_task_done())

    def loadWaveform(self,waveList=None,waitUntilFinished=False):
        if waveList is None: 
            waveList = self.waves
        else:
            assert (type(waveList) == list) & (type(waveList[0]) == Waveform), "Input MUST be a list of Waveforms"
            assert len(waveList) == self.nChannels, "Number of waves ({}) is not equal with number of channels ({})".format(len(waveList),self.nChannels)
            assert all([d == waveList[0].duration for d in [w.duration for w in waveList]]) & \
                all([d == waveList[0].samplingRate for d in [w.samplingRate for w in waveList]]), "Waves MUST have the same duration and sampling rate"
            self.waves = waveList

        if self.isRunning:
            if waitUntilFinished: self._DAQ.wait_until_done()
            else: self.initialize()
        else: self._DAQ.stop()

        self._DAQ.timing.cfg_samp_clk_timing(
            rate = self.waves[0].samplingRate,
            sample_mode = nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan = self.waves[0].duration * self.waves[0].samplingRate)
        writer = AnalogMultiChannelWriter(self._DAQ.out_stream,auto_start=False)  
        writer.write_many_sample(vstack([w.signal for w in self.waves]))
    
    def stimulate(self):
        self._DAQ.start()
