# -*- coding: utf-8 -*-

"""
BITalino API

Defines the BITalino class.

Created on Tue Jun 25 13:44:28 2013

@author: Priscila Alves, José Guerreiro, Carlos Carreiras, Hugo Silva

"""


try:
    import bluetooth
    from bluetooth import discover_devices
except ImportError:
    bluetooth = None
    discover_devices = None
import serial
from serial.tools import list_ports
import time
import math
import numpy


def _byte_at(buf, index):
    """Byte0–255 at index (Py2 str / Py3 bytes / bytearray)."""
    b = buf[index]
    if isinstance(b, int):
        return b
    return ord(b)


class BITalino(object):
    
    def __init__(self):
        """
        BITalino class: interface to the BITalino hardware.
        
        """
        self.socket = None
        self.analogChannels = []
        self.number_bytes = None
        self.macAddress = None
        self.serial = False
    
    def find(self, serial=False):
        """
        Search for bluetooth devices nearby
        
        Output: tuple with name and mac address of each device found
        """
        
        try:
            if serial:
                return [
                    (port.device, port.description or "")
                    for port in list_ports.comports()
                    if port.device
                ]
            if discover_devices is None:
                return -1
            nearby_devices = discover_devices(lookup_names=True)
            return nearby_devices
        except Exception:
            return -1
    
    def open(self, macAddress=None, SamplingRate=1000, serial_timeout=None):
        """
        Connect to bluetooth device with the mac address provided. 
        Configure the sampling Rate. 
        
        Kwargs:
            
            macAddress (string): MAC address of the bluetooth device
            SamplingRate(int): Sampling frequency (Hz); values available: 1000, 100, 10 and 1
            serial_timeout (float or None): pySerial read timeout in seconds for COM/USB
                connections only; None keeps blocking reads (default).
        
        Output: True or -1 (error)
        """
        
        Setup = True
        while Setup:
            if macAddress != None:
                try:
                    if ":" in macAddress and len(macAddress) == 17:
                        if bluetooth is None:
                            raise ImportError(
                                "PyBluez (bluetooth package) is required for RFCOMM MAC connections"
                            )
                        self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                        self.socket.connect((macAddress, 1))
                        self._serial_timeout = None
                    else:
                        if serial_timeout is not None:
                            self.socket = serial.Serial(
                                macAddress, 115200, timeout=serial_timeout
                            )
                        else:
                            self.socket = serial.Serial(macAddress, 115200)
                        self.serial = True
                        self._serial_timeout = serial_timeout
                    time.sleep(2)
                    
                    # Configure sampling rate
                    if SamplingRate == 1000:
                        variableToSend = 0x03
                    elif SamplingRate == 100:
                        variableToSend = 0x02
                    elif SamplingRate == 10:
                        variableToSend = 0x01
                    elif SamplingRate == 1:
                        variableToSend = 0x00
                    else:
                        self.socket.close()
                        raise TypeError("The Sampling Rate %s cannot be set in BITalino. Choose 1000, 100, 10 or 1." % SamplingRate)
                        return -1
                        
                    variableToSend = int((variableToSend<<6)|0x03)
                    self.write(variableToSend)
                    Setup = False
                    
                except Exception as e:
                    print(e)
                    return -1
            else:
                raise TypeError("A MAC address or serial port is needed to connect")
                return -1
        else:
            self.macAddress = macAddress
            return True

    def start(self, analogChannels=[0, 1, 2, 3, 4, 5]):
        """
        Starts Acquisition in the analog channels set.
        
        Kwargs:
            
            analogChannels (array of int): channels to be acquired (from 0 to 5)
        
        Output: True
        """
        
        # check type of list of analog channels
        if isinstance(analogChannels, list):
            self.analogChannels = analogChannels
        elif isinstance(analogChannels, tuple):
            self.analogChannels = list(analogChannels)
        elif isinstance(analogChannels, numpy.ndarray):
            self.analogChannels = analogChannels.astype(int).tolist()
        else:
            raise TypeError("Unsupported analog channels list type.")
        
        # remove repeats
        self.analogChannels = list(set(self.analogChannels))
        
        # check items
        nb = len(self.analogChannels)
        pValues = range(6)
        if nb == 0 or nb > 6 or any([item not in pValues for item in self.analogChannels]):
            raise TypeError("Analog channels set not valid.")
        
        if self.socket is None:
            raise TypeError("An input connection is needed.")
        bit = 1
        # setting channels mask (use stored list; order matches acquisition layout)
        for i in sorted(self.analogChannels):
            bit = bit | 1 << (2 + i)
        #start acquisition
        self.write(bit)
        return True
    
    def stop(self):
        """
        Sends state value 0 to stop BITalino acquisition.
        
        Output: True
        """
        
        if self.socket is None:
            raise TypeError("An input connection is needed.")
        
        # Send stop mode
        self.write(0)
        
        return True
    
    def close(self):
        """
        Closes bluetooth socket
        
        Output: True
        """
        
        # Check
        if self.socket is None:
            raise TypeError("An input connection is needed.")
        
        self.socket.close()
        
        return True
    
    def write(self, data=0):
        """
        Send a command to BITalino
        
        Output: True
        """
        if self.socket is None:
            raise TypeError("An input connection is needed.")

        # Send Mode (bytes for pyserial / bluetooth in Python 3)
        payload = bytes((data & 0xFF,))
        if self.serial:
            self.socket.write(payload)
        else:
            self.socket.send(payload)
        return True
    
    def battery(self, value=0):
        """
        Set the battery threshold of BITalino
        Works only in idle mode
        
        Kwargs:
            
            value (int): threshold value from 0 to 63
                0  -> 3.4V
                63 -> 3.8V
                
        Output: True
        """
        
        if self.socket is None:
            raise TypeError("An input connection is needed.")
        
        # Send Mode
        if 0 <= value <= 63:
            Mode = value << 2
            self.write(Mode)
        else:
            raise TypeError("The threshold value must be between 0 and 63.")
        
        return True
    
    def trigger(self, digitalArray=[0, 0, 0, 0]):
        """
        Act on digital output channels of BITalino
        Works only during acquisition mode
        
        Kwargs:
            
            digitalArray (array): array of size 4 which act on digital outputs according to the value: 0 or 1
                Each position of the array corresponds to a digital output, in ascending order.
                
                Example:
                    digitalArray =[1,0,1,0] -> Digital 0 and 2 will be set to one and Digital 1 and 3 to zero
        
        Output: True
        """
        
        if self.socket is None:
            raise TypeError("An input connection is needed.")
        
        # check type of digital array
        if isinstance(digitalArray, list):
            pass
        elif isinstance(digitalArray, tuple):
            digitalArray = list(digitalArray)
        elif isinstance(digitalArray, numpy.ndarray):
            digitalArray = digitalArray.astype(int).tolist()
        else:
            raise TypeError("Unsupported digital channels list type.")
        
        # check items
        pValues = [0, 1]
        if len(digitalArray) != 4 or any([item not in pValues for item in digitalArray]):
            raise TypeError("Digital channels set not valid.")
        
        data = 3
        for i,j in enumerate(digitalArray):
            data = data | j<<(2+i)
        
        self.write(data)
        return True
    
    def version(self):
        """
        Get BITalino version
        Works only in idle mode
        
        Output: Version (string)
        """
        
        if self.socket is None:
            raise TypeError("An input connection is needed.")
        
        self.write(7)
        buf = bytearray()
        
        # choose serial or socket
        if self.serial:
            reader = self.socket.read
        else:
            reader = self.socket.recv
        
        while True:
            chunk = reader(1)
            if not chunk:
                break
            if isinstance(chunk, str):
                buf.extend(bytearray(chunk))
            else:
                buf.extend(chunk)
            if buf and buf[-1] == 0x0A:
                break
        return bytes(buf[:-1]).decode("ascii", errors="replace")
    
    def read(self, nSamples=100):
        """
        Acquire defined number of samples from BITalino
        
        Kwargs: 
            nSamples (int): number of samples

        Output:
            dataAcquired (array): the data acquired is organized in a matrix; The columns correspond to the sequence number, 4 digital channels and analog channels, as configured previously on the start method; 
                                Each line correspond to a sample.

                                The organization of the array is as follows:
                                --  Always included --
                                Column 0 - Sequence Number
                                Column 1 - Digital 0
                                Column 2 - Digital 1
                                Column 3 - Digital 2
                                Column 4 - Digital 3
                                -- Variable with the analog channels set on start method --
                                Column 5  - analogChannels[0]
                                Column 6  - analogChannels[1]
                                Column 7  - analogChannels[2]
                                Column 8  - analogChannels[3]
                                Column 9  - analogChannels[4]
                                Column 10 - analogChannels[5]
        """
        
        if self.socket is None:
            raise TypeError("An input connection is needed.")
        
        nChannels = len(self.analogChannels)
        
        if nChannels <=4 :
            self.number_bytes = int(math.ceil((12.+10.*nChannels)/8.))
        else:
            self.number_bytes = int(math.ceil((52.+6.*(nChannels-4))/8.))
        
        # choose serial or socket
        if self.serial:
            reader = self.socket.read
        else:
            reader = self.socket.recv
        
        # get data according to the value nSamples set
        dataAcquired = numpy.zeros((5 + nChannels, nSamples))
        Data = bytearray()
        sampleIndex = 0
        bad_frames = 0
        max_bad_frames = max(200, nSamples * self.number_bytes * 4)
        while sampleIndex < nSamples:
            while len(Data) < self.number_bytes:
                chunk = reader(1)
                if not chunk:
                    if getattr(self, "_serial_timeout", None) is not None:
                        raise IOError(
                            "Serial read timed out (wrong COM port or no data)"
                        )
                    continue
                if isinstance(chunk, str):
                    Data.extend(bytearray(chunk))
                else:
                    Data.extend(chunk)
            else:
                decoded = self.decode(Data)
                if isinstance(decoded, numpy.ndarray) and decoded.size > 0: 
                    dataAcquired[:, sampleIndex] = decoded.T
                    Data = bytearray()
                    sampleIndex += 1
                else:
                    bad_frames += 1
                    if bad_frames > max_bad_frames:
                        raise IOError(
                            "Excess CRC/decode failures (wrong COM port or corrupt stream)"
                        )
                    chunk = reader(1)
                    if not chunk:
                        if getattr(self, "_serial_timeout", None) is not None:
                            raise IOError(
                                "Serial read timed out (wrong COM port or no data)"
                            )
                        continue
                    if isinstance(chunk, str):
                        Data.extend(bytearray(chunk))
                    else:
                        Data.extend(chunk)
                    Data = Data[1:] 
                    print("ERROR DECODING")
        else:
            return dataAcquired
    
    def decode(self, data, nAnalog=None):
        """
        Unpack data samples.
        
        Kwargs:
            
            data (array): received data
            nAnalog (int): number of analog channels contained in data
        
        Output:
            res(array): data unpacked
        """
        
        if nAnalog == None: nAnalog = len(self.analogChannels)
        if nAnalog <= 4:
            number_bytes = int(math.ceil((12. + 10. * nAnalog) / 8.))
        else:
            number_bytes = int(math.ceil((52. + 6. * (nAnalog - 4)) / 8.))
        
        nSamples = len(data) // number_bytes
        res = numpy.zeros(((nAnalog + 5), nSamples))
        
        j, x0, x1, x2, x3, out, inp, col, line = 0, 0, 0, 0, 0, 0, 0, 0, 0
        encode0F = 0x0F
        encode01 = 0x01
        encode03 = 0x03
        encodeFC = 0xFC
        encodeFF = 0xFF
        encodeC0 = 0xC0
        encode3F = 0x3F
        encodeF0 = 0xF0
        
        #CRC check
        CRC = _byte_at(data, j + number_bytes - 1) & encode0F
        for byte in range(number_bytes):
            for bit in range(7, -1, -1):
                inp = _byte_at(data, byte)>>bit & encode01
                if byte == (number_bytes - 1) and bit < 4:
                    inp = 0
                out = x3
                x3 = x2
                x2 = x1
                x1 = out^x0
                x0 = inp^out
        
        if CRC == int((x3<<3)|(x2<<2)|(x1<<1)|x0):
            try:
                # Seq Number
                SeqN = _byte_at(data, j + number_bytes - 1) >> 4 & encode0F
                res[line, col] = SeqN
                line += 1
                
                # Digital 0
                Digital0 = _byte_at(data, j + number_bytes - 2) >> 7 & encode01
                res[line, col] = Digital0
                line += 1
                
                # Digital 1
                Digital1 = _byte_at(data, j + number_bytes - 2) >> 6 & encode01
                res[line, col] = Digital1
                line += 1
                
                # Digital 2
                Digital2 = _byte_at(data, j + number_bytes - 2) >> 5 & encode01
                res[line, col] = Digital2
                line += 1
                
                # Digital 3
                Digital3 = _byte_at(data, j + number_bytes - 2) >> 4 & encode01
                res[line, col] = Digital3
                line += 1
                
                if number_bytes >= 3:
                    # Analog 0
                    Analog0 = (_byte_at(data, j + number_bytes - 2) & encode0F) << 6 | (_byte_at(data, j + number_bytes - 3) & encodeFC) >> 2
                    res[line, col] = Analog0
                    line += 1
                    
                if number_bytes >= 4:
                    # Analog 1
                    Analog1 = (_byte_at(data, j + number_bytes - 3) & encode03) << 8 | (_byte_at(data, j + number_bytes - 4) & encodeFF)
                    res[line, col] = Analog1
                    line += 1
                    
                if number_bytes >= 6:
                    # Analog 2
                    Analog2 = (_byte_at(data, j + number_bytes - 5) & encodeFF) << 2 | (_byte_at(data, j + number_bytes - 6) & encodeC0) >> 6
                    res[line, col] = Analog2
                    line += 1
                    
                if number_bytes >= 7:
                    # Analog 3
                    Analog3 = (_byte_at(data, j + number_bytes - 6) & encode3F) << 4 | (_byte_at(data, j + number_bytes - 7) & encodeF0) >> 4
                    res[line, col] = Analog3
                    line += 1
                    
                if number_bytes >= 8:
                    # Analog 4
                    Analog4 = (_byte_at(data, j + number_bytes - 7) & encode0F) << 2 | (_byte_at(data, j + number_bytes - 8) & encodeC0) >> 6
                    res[line, col] =Analog4
                    line += 1
                    
                    # Analog 5
                    if numpy.shape(res)[0] == 11:
                        Analog5 = _byte_at(data, j + number_bytes - 8) & encode3F
                        res[line, col] = Analog5
                
            except Exception:
                print("exception decode")
            return res
        else:
            return []



if __name__ == '__main__':
    
    #Example
    device = BITalino()
    
    # macAddress = "00:13:01:04:02:16"
    macAddress = "COM7"
    SamplingRate = 1000
    nSamples = 10
    
    # Connect to bluetooth device and set Sampling Rate
    device.open(macAddress, SamplingRate)
    
    #set battery threshold
    th = device.battery(20)
    
    #get BITalino version
    BITversion = device.version()
    print("version: ", BITversion)
    
    #Start Acquisition in Analog Channels 0 and 3
    device.start([0, 3])
    
    #Read 1000 samples
    dataAcquired = device.read(nSamples)
    
    # turn BITalino led on
    device.trigger([0, 0, 1, 0])
    
    #stop acquisition
    device.stop()
    device.close()
    
    SeqN = dataAcquired[0, :]
    D0 = dataAcquired[1, :]
    D1 = dataAcquired[2, :]
    D2 = dataAcquired[3, :]
    D3 = dataAcquired[4, :]
    A0 = dataAcquired[5, :]
    A3 = dataAcquired[6, :]  
    print(SeqN)
    
