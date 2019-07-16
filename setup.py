from setuptools import setup

setup(
    name='PyNIExp',
    url='https://github.com/tiborauer/pyniexp',
    author='Tibor Auer',
    author_email='tibor.auer@gmail.com',
    
    packages=['pyniexp'],
    install_requires=['keyboard','nidaqmx'],
    
    version='0.13.11',
    license='GPL-3.0',
    description='Python interface for neuroimaging experiments',
    
    long_description=open('README.md').read(),
)
