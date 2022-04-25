from setuptools import setup
import pathlib

ROOT_DIR = pathlib.Path(__file__).parent

def long_description():
    readme = ROOT_DIR / 'README.md'
    with readme.open(encoding='utf-8') as f:
        return '\n' + f.read()

setup(
    name='PyNIExp',
    url='https://github.com/tiborauer/pyniexp',
    author='Tibor Auer',
    author_email='tibor.auer@gmail.com',
    
    packages=['pyniexp'],
    install_requires=['keyboard','nidaqmx','loguru','matplotlib','pyserial','pyqt5','pyqtgraph'],
    
    package_data={'pyniexp': ['stimulatordlg.ui']},
    include_package_data=True,

    version='0.27.3',
    license='GPL-3.0',
    description='Python interface for neuroimaging experiments',
    
    long_description=long_description(),
    long_description_content_type='text/markdown',
)
