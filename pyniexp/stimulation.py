import nidaqmx, serial, json, sys
from numpy import concatenate, vstack, arange, linspace, cos, pi, ones
from nidaqmx.stream_writers import AnalogMultiChannelWriter
import matplotlib.pyplot as plt
from loguru import logger
from time import sleep
from pyniexp.utils import Status

class Waveform:
    SCALING = 2 # actual intensity (peak to trough) = amplitude * 2

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
        envelope = concatenate((rampup,self.amplitude*ones(int(stimDuration*self.samplingRate)),rampdown))

        return envelope * waveform

    def show(self):
        fig, ax = plt.subplots()
        ax.plot(arange(0,self.duration,1/self.samplingRate) , self.signal, label='Waveform')
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
        self.stop()
        self._DAQ.close()
        self._DAQ = None

    @property
    def status(self):
        if self._DAQ is None: return Status.DISCONNECTED
        elif len(self.waves) == 0: return Status.CONNECTED
        elif self._DAQ.is_task_done(): return Status.STOPPED
        else: return Status.RUNNING

    def loadWaveform(self,waveList=None,waitUntilFinished=False):
        if waveList is None: 
            waveList = self.waves
        else:
            assert (type(waveList) == list) & (type(waveList[0]) == Waveform), "Input MUST be a list of Waveforms"
            assert len(waveList) == self.nChannels, "Number of waves ({}) is not equal with number of channels ({})".format(len(waveList),self.nChannels)
            assert all([d == waveList[0].duration for d in [w.duration for w in waveList]]) & \
                all([d == waveList[0].samplingRate for d in [w.samplingRate for w in waveList]]), "Waves MUST have the same duration and sampling rate"
            self.waves = waveList

        if self.status == Status.RUNNING:
            if waitUntilFinished: self._DAQ.wait_until_done()
            else: self.initialize()
        else: self._DAQ.stop()

        self._DAQ.timing.cfg_samp_clk_timing(
            rate = self.waves[0].samplingRate,
            sample_mode = nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan = int(self.waves[0].duration * self.waves[0].samplingRate))
        writer = AnalogMultiChannelWriter(self._DAQ.out_stream,auto_start=False)  
        writer.write_many_sample(vstack([w.signal for w in self.waves]))
    
    def stimulate(self):
        if self.status == Status.CONFIGURED: self._DAQ.start()

    def stop(self):
        if self.status == Status.RUNNING: self._DAQ.stop()

class TI:

    __config = None
    _serial = None
    status = Status.DISCONNECTED
    wait = 1 #s, wait after commands
    verbose = True
    emulate = False

    @property
    def amplitude(self):
        return [ch['Amplitutde'] for ch in self.channels]

    @amplitude.setter
    def amplitude(self,val):
        self.channels[0]['Amplitutde'] = val[0]
        self.channels[1]['Amplitutde'] = val[1]

    def __init__(self,configFile='config_TI.json'):
        with open(configFile) as config:
            self.__config = json.load(config)
        self.port = self.__config['Port']
        self.channels = self.__config['Channels']

    def __del__(self):
        self.stop()
        self.unload()
        self._serial.close()
        logger.info('TI stimulator is disconnected')

    def connect(self):
        self._serial = serial.Serial(port=self.port,baudrate=self.__config['BaudRate'])

        if self._serial.isOpen():
            logger.info('TI stimulator is connected (port = {}, BaudRate = {:d})'.format(self.__config['Port'],self.__config['BaudRate']))
            self.status = Status.CONNECTED
        else:
            logger.error('Conneciton failed on {}, check port!'.format(self.__config['Port']))
            self.status = Status.DISCONNECTED

    def load(self):
        logger.info('Uploading device parameters')
        self.sendCommand('DDS 0 {}'.format(self.channels[0]['Freqency']))
        self.sendCommand('DDS 1 {}'.format(self.channels[1]['Freqency']))
        self.sendCommand('ChConfig {:d} {:d} {:d} {:d} {:02d} {:02d} {:02d} {:02d}'.format(
            self.channels[0]['loadA'],self.channels[0]['loadB'],self.channels[1]['loadA'],self.channels[1]['loadB'],
            self.channels[0]['pinA'],self.channels[0]['pinB'],self.channels[1]['pinA'],self.channels[1]['pinB']
            ))
        self.status = Status.CONFIGURED

    def unload(self):
        if self.status != Status.CONFIGURED:
            logger.warning('TI is not loaded')
            return
        
        logger.info('Unloading device')
        self.sendCommand('ChConfig 00 00 00 00 08 09 10 11')
        self.status = Status.UNCONFIGURED

    def start(self,nowait=False,verbose=None):
        if self.amplitude == [0,0]:
            self.amplitude = [ch['Amplitutde'] for ch in self.__config['Channels']]
        logger.info('Stimulation started...')
        self.sendCommand('RampWfm mA 0 {} 0 {} {}'.format(*self.amplitude,self.__config['rampUp']),nowait=nowait,verbose=verbose)
        self.status = Status.RUNNING

    def stop(self,nowait=False,verbose=None):
        if self.status != Status.RUNNING: 
            logger.warning('Stimulation is not running')
            return
        logger.info('Stimulation stopped')
        self.sendCommand('RampWfm mA {} 0 {} 0 {}'.format(*self.amplitude,self.__config['rampDown']),nowait=nowait,verbose=verbose)
        self.status = Status.STOPPED

    def sendCommand(self,cmd,nowait=False,verbose=None):
        if verbose is None: verbose = self.verbose
        if verbose: logger.info(cmd)
        if not(self.emulate): self._serial.write((cmd+'\r').encode())
        if not(nowait): sleep(self.wait)