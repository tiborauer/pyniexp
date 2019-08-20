import numpy as np
from multiprocessing import Process, Value, RawArray
from loguru import logger

SIG_NOTSTARTED = -1
SIG_RUNNING = 1
SIG_STOPPED = 0
SIG_NEWIMAGE = 10

class imageProcess:
    __process = Process()
    _image_dimension = None

    def __init__(self,image_dimension):
        self._image_dimension = image_dimension
        self._buffer = RawArray('d',[0]*np.prod(self._image_dimension))
        self._signal = Value('b',SIG_NOTSTARTED)

        logger.info('Starting process')
        self.__process = Process(target=self._run)
        self.__process.start()

    def __del__(self):
        if self._signal.value != SIG_STOPPED:
            logger.info('Stopping process')
            self._signal.value = SIG_STOPPED

    # Processing
    def process(self,image):
        """Image processing method to overwrite"""
        return NotImplemented
    
    # Mechanism
    def load_image(self,mlImage):
        if not(self.__process.is_alive()):
            logger.exception('Process is not running')
            return

        for l in range(0,len(self._buffer)): self._buffer[l] = mlImage[l]
        self._signal.value = SIG_NEWIMAGE
    
    def _run(self):
        while self._signal.value != SIG_STOPPED:
            if self._signal.value == SIG_NOTSTARTED: 
                logger.info('Process is running')
                self._signal.value = SIG_RUNNING
            if self._signal.value == SIG_NEWIMAGE:
                img = np.array(self._buffer).reshape(np.flip(self._image_dimension,0)).transpose(2,1,0) 
                logger.info('New image')
                self.process(img)
                self._signal.value = SIG_RUNNING
        logger.info('Process is stopped')