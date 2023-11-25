# MyoInterface

A way to connect and control Myo Armband without the bluetooth dongle.

This is a python library built on bleak and uses the published bluetooth protocol.

Based on BLE protocals published by Thalmic Labs: https://github.com/thalmiclabs/myo-bluetooth 

work done by PerlinWarp : https://github.com/PerlinWarp/pyomyo 

Open-Myo: https://github.com/Alvipe/Open-Myo

and FreeMyo.py https://github.com/jshahbazi/FreeMyo.py



This library is very similar to FreeMyo.py, but with more modular functions that offers flexibility to shape the tool towards different purposes.



### setup:

do`pip install -r req.txt`

use [Scanning_for_mac_address.py](https://github.com/madwilliam/MyoInterface/blob/main/script/Scanning_for_mac_address.py) to scan for myoband mac address, mine showed up as DIUxMyo

change the default address in [MyoInterface](https://github.com/madwilliam/MyoInterface/blob/main/build/lib/MyoInterface/MyoInterface.py)

### Examples:

[Live EMG visualization](https://github.com/madwilliam/MyoInterface/blob/main/script/MonitorEEGQt.py)

[Printing EMG reading](https://github.com/madwilliam/MyoInterface/blob/main/script/print_emg.py)

[recording Emg data ](https://github.com/madwilliam/MyoInterface/blob/main/script/record_emg.py)

