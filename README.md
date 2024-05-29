# PyNIExp
Python interfaces for neuroimaging experiments (and how to import them)
 - Interface to National Instruments cards (with digital and analogue I/O) for 
   - scanner pulse and button presses (with simulation mode)
      ```python
      from pyniexp.scanner import BrainVisionTrigger, ScannerSynch
      ```
   - stimulation devices
      ```python
      from pyniexp.stimulator import Waveform, TES, TI, StimulatorApp
      ```
 - UDP transfer
    ```python
    from pyniexp.network import Tcp, Udp
    ```
 - Interface to acquire 3D volumes from MATLAB engine
    ```python
    from pyniexp.mlplugin import dataProcess, imageProcess
    ```


 ## Install
`pip install PyNIExp`
