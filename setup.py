from setuptools import setup

setup(
    name='PyNIExp',
    url='https://github.com/tiborauer/pyniexp',
    author='Tibor Auer',
    author_email='tibor.auer@gmail.com',
    
    packages=['pyniexp'],
    install_requires=['keyboard','nidaqmx','loguru','matplotlib','pyserial','pyqt5','pyqtgraph'],
    
    package_data={'pyniexp': ['stimulatordlg.ui']},
    include_package_data=True,

    version='0.27.1',
    license='GPL-3.0',
    description='Python interface for neuroimaging experiments',
    
    long_description=open('README.md').read(),
)
