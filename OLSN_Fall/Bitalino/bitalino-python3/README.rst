===================
BITalino Python API
===================

BITalino is a low-cost toolkit that allows anyone to create projects and applications with body signals.
Out of the box, BITalino has easy-to-use hardware with sensors for ECG, EMG, EDA, Motion and Light.

This package provides the tools to interface with the BITalino hardware from Python.

Get your BITalino, accessories, tools and support at `bitalino.com <http://www.bitalino.com/>`_.

Dependencies
------------

- numpy

  - Source: https://pypi.python.org/pypi/numpy
  - Windows binaries: http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy

- pySerial

  - Source: https://pypi.python.org/pypi/pyserial
  - Windows binaries: http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyserial

- pybluez (optional)

  - Source: https://code.google.com/p/pybluez/downloads/list
  - Windows binaries: http://www.lfd.uci.edu/~gohlke/pythonlibs/#pybluez

Release Notes
-------------

Version 0.6

- Serial Baud rate was incorrectly set as 9600, instead of 115200
- Known issues:

  - *version* method hangs

Version 0.5

- Included GPL license file
- Known issues:

  - *version* method hangs

Version 0.4

- The API now supports using serial ports to communicate with the BITalino device;
  this removes the dependency on pybluez and enhances cross-platform compatibility (e.g. Mac OS)
- Removed inconsistent scaling of analog channels A4 and A5 (6 bit channels)
- Code style normalization
- Improved type checks of analog and digital channels masks (*start* and *trigger* methods)
- Known issues:

  - *version* method hangs

Disclaimer
----------

Copyright (C) 2014 Team BIT

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see
<http://www.gnu.org/licenses/>.

Usage Example
-------------

>>> import bitalino
>>> device = bitalino.BITalino()
>>> 
>>> macAddress = "00:13:01:04:04:15"
>>> SamplingRate = 1000
>>> device.open(macAddress, SamplingRate) # Set MAC address and sampling rate
>>> 
>>> th = device.battery(20) # Set battery threshold
>>> 
>>> BITversion = device.version() # Get BITalino firmware version
>>> print "version: ", BITversion
>>> 
>>> device.start([0,3]) # Start Acquisition in Analog Channels 0 and 3
>>> 
>>> dataAcquired = device.read(1000) # Read 1000 samples
>>> 
>>> device.trigger([0,0,1,0]) # Turn on BITalino LED
>>> 
>>> device.stop() # Stop acquisition
>>> device.close()
>>> 
>>> SeqN = dataAcquired[0,:]
>>> D0 = dataAcquired[1,:]
>>> D1 = dataAcquired[2,:]
>>> D2 = dataAcquired[3,:]
>>> D3 = dataAcquired[4,:]
>>> A0 = dataAcquired[5,:]
>>> A3 = dataAcquired[6,:]
>>> print SeqN
