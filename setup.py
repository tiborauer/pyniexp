from setuptools import setup

setup(
    name='ScannerSynch',
    url='https://github.com/tiborauer/ScannerSynch-python',
    author='Tibor Auer',
    author_email='tibor.auer@gmail.com',
    
    packages=['scannersynch'],
    install_requires=['keyboard','nidaqmx'],
    
    version='0.1',
    license='GPL-3.0',
    description='Interface for National Instruments PCI 6503 card',
    
    long_description=open('README.md').read(),
)