from time import time
from multiprocessing import Value
from enum import Enum
from serial.tools import list_ports
import logging
from sys import stdout


class Status(Enum):
    DISCONNECTED = 0
    CONNECTED = 1
    UNCONFIGURED = 1
    CONFIGURED = 2
    STOPPED = 2
    RUNNING = 3


## Clock
class clock:

    def __init__(self):
        self._t0 = Value("d", time())

    # Clock
    @property
    def clock(self):
        return time() - self._t0.value

    def reset_clock(self):
        self._t0.value = time()


## Logger
logLevel = logging.DEBUG
logFormat = logging.Formatter(
    "[ %(asctime)s | %(levelname)10s ] - ( %(filename)s:%(lineno)s ) - %(message)s"
)


def getLogger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logLevel)
    logger.handlers.clear()

    # stdout
    stdoutHandler = logging.StreamHandler(stdout)
    stdoutHandler.setLevel(logLevel)
    stdoutHandler.setFormatter(logFormat)
    logger.addHandler(stdoutHandler)

    return logger


def binvec2dec(binvec):
    return sum([binvec[i] * (2**i) for i in range(0, len(binvec))])


def ismember(list1, list2):
    return [any([kb == kp for kp in list2]) for kb in list1]


def list_find(str_list, pattern):
    return [i for i in range(0, len(str_list)) if str_list[i].find(pattern) != -1]


def listSerial():
    return [p.device for p in list_ports.comports()]
