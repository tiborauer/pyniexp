from numpy import array, prod, flip
from multiprocessing import Process, Value, RawArray
from loguru import logger
from matlab import double

SIG_NOTSTARTED = -1
SIG_RUNNING = 1
SIG_STOPPED = 0
SIG_NEWIMAGE = 10

class dataProcess:
    __process = Process()

    def __init__(self,data_size,autostart=True):
        self._buffer = RawArray('d',[0]*data_size)
        self._signal = Value('b',SIG_NOTSTARTED)
        if autostart: self.start_process()

    def __del__(self):
        if self._signal.value != SIG_STOPPED:
            logger.info('Stopping process')
            self._signal.value = SIG_STOPPED

    # Processing
    def process(self,data):
        """Data processing method to overwrite"""
        return NotImplemented
    
    # Mechanism
    def start_process(self):
        logger.info('Starting process')
        self.__process = Process(target=self._run)
        self.__process.start()

    def load_data(self,mlData):
        if not(self.__process.is_alive()):
            logger.exception('Process is not running')
            return

        if type(mlData) == double: # matlab array
            mlData = mlData._data.tolist()
        elif type(mlData) == float: # single value
            mlData = [mlData]

        for l in range(0,len(self._buffer)): self._buffer[l] = mlData[l]
        self._signal.value = SIG_NEWIMAGE
    
    def _run(self):
        while self._signal.value != SIG_STOPPED:
            if self._signal.value == SIG_NOTSTARTED: 
                logger.info('Process is running')
                self._signal.value = SIG_RUNNING
            if self._signal.value == SIG_NEWIMAGE:
                logger.info('New data')
                self.process(self._buffer)
                self._signal.value = SIG_RUNNING
        logger.info('Process is stopped')

class imageProcess(dataProcess):
    _image_dimension = None

    def __init__(self,image_dimension,autostart=True):
        self._image_dimension = image_dimension
        super().__init__(prod(self._image_dimension),autostart)
    
    def _run(self):
        while self._signal.value != SIG_STOPPED:
            if self._signal.value == SIG_NOTSTARTED: 
                logger.info('Process is running')
                self._signal.value = SIG_RUNNING
            if self._signal.value == SIG_NEWIMAGE:
                img = array(self._buffer).reshape(flip(self._image_dimension,0)).transpose(2,1,0) 
                logger.info('New image')
                self.process(img)
                self._signal.value = SIG_RUNNING
        logger.info('Process is stopped')