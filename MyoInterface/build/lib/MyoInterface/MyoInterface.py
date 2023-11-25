import numpy as np
import asyncio
from bleak import BleakClient
import struct
# from MyoInterface.command_codes import *
from command_codes import *
import os
from pyqtgraph.Qt import QtGui, QtCore
import time
import concurrent.futures
import pyqtgraph as pg
class MyoInterface:
    def __init__(self,address = "E2:1A:C4:73:B3:0C"):
        self.address = address
        self.code = CommandCode()
        self.loop = asyncio.get_event_loop()
        self.emg_data_queue = asyncio.Queue()

    def construct_uuid(self,command_code):
        return f'd506{command_code}-a904-deb9-4748-2c7f4a124842'
    
    async def set_mode(self,emg_mode = EmgMode.record_raw_emg, imu_mode = ImuMode.off, classifier_mode = ClassifierMode.disabled):
        print('Setting Myo Recording Mode')
        command = struct.pack('<5B', Commands.set_mode, 3, emg_mode, imu_mode, classifier_mode)
        await self.run_command(command)
    
    async def unlock_device(self,unlock_mode = UnlockModes.remain_unlocked_until_lock_command):
        print('Setting Myo Unlock Mode')
        command = struct.pack('<3B', Commands.unlock, 1, unlock_mode)
        await self.run_command(command)
    
    async def set_sleep_mode(self,sleep_mode = SleepModes.never_sleep):
        print('Setting Myo Sleep Mode')
        command = struct.pack('<3B', Commands.unlock, 1, sleep_mode)
        await self.run_command(command)
    
    async def run_command(self,command):
        uuid = self.construct_uuid(self.code.command)
        await self.client.write_gatt_char(uuid,command)
    
    async def read_data(self,uuid):
        return await self.client.read_gatt_char(uuid)

    async def start_subscription(self,codes,callback=None):
        if callback is None:
            def callback(sender: int, data: bytearray):
                print(f"{sender}: {data}")
        for code in codes:
            uuid = self.construct_uuid(code)
            await self.client.start_notify(uuid, callback)
    
    async def subscribe(self,codes,callback=None,run_time = 120,stream_funtion = None):
        await self.start_subscription(codes,callback)
        if stream_funtion is not None:
            await stream_funtion()
        else:
            await asyncio.sleep(run_time)
        print('Stopping Data Stream')
        for code in codes:
            uuid = self.construct_uuid(code)
            await self.client.stop_notify(uuid)
    
    async def raw_emgg_callback(self,sender, data):
        # id = self.code.emg_handles.index(sender)
        emg = struct.unpack('<16b', data)
        await self.emg_data_queue.put((id,emg))

    async def start_raw_eeg_data_stream(self):
        await self.unlock_device()
        await self.set_sleep_mode()
        await self.set_mode()
        await self.start_subscription(self.code.emg_data,callback=self.self.raw_emgg_callback)
        self.process_emg_data()
    
    async def subscribe_raw_eeg(self,raw_emgg_callback=None,stream_funtion = None,set_up_function = None):
        if set_up_function is not None:
            set_up_function()
        await self.unlock_device()
        await self.set_sleep_mode()
        await self.set_mode()
        await self.subscribe(self.code.emg_data,callback=raw_emgg_callback,stream_funtion=stream_funtion)
    
    async def stream_raw_emg(self,set_up_function = None,action=None,stream_function=None):
        print('Starting Emg Stream')
        self.emg_data_stream = [[] for _ in range(8)]
        if action is None:
            action = lambda self:print(self.emg_data_stream)
        if stream_function is None:
            stream_function = lambda : self.process_emg_data(action)
        await self.subscribe_raw_eeg(self.raw_emgg_callback,stream_funtion = stream_function,set_up_function=set_up_function)
    
    def set_up_recording_file(self,path):
        if os.path.exists(path):
            print('file exists, aborting')
            exit()
        self.path = os.path.dirname(path) 
        self.file_name = os.path.basename(path) 
        if not os.path.exists(self.path):
            os.mkdir(self.path)
        with open(os.path.join(self.path,self.file_name),'a') as fd:
            fd.write(','.join([f'channel{i}' for i in range(8)]))
    
    def update_recording_file(obj,self):
        newydata = []
        for i in range(8):
            newydata.append(self.emg_data_stream[i][-2:])
        with open(os.path.join(self.path,self.file_name),'a') as fd:
            fd.write(f'\n'+','.join([str(i[0]) for i in newydata]))  
            fd.write(f'\n'+','.join([str(i[1]) for i in newydata]))  

    async def record_raw_emg(self,path):
        self.set_up_recording_file(path)
        await self.stream_raw_emg(action = self.update_recording_file)
    
    async def connect(self):
        print("Connecting to device...")
        self.client = BleakClient(self.address)
        await self.client.connect()
    
    async def disconnect(self):
        print("Disconnecting")
        await self.client.disconnect()

    async def async_connect_and_run_function(self,function):
        print("Connecting to device...")
        async with BleakClient(self.address) as self.client:
            print('Connected')
            result = await function(self)
        return result
    
    def connect_and_run_function(self,function):
        result = asyncio.run(self.async_connect_and_run_function(function))
        return result
    
    async def read_basic_info(self):
        uuid = self.construct_uuid(self.code.basic_info)
        r = await self.read_data(uuid)
        serial_number = r[:6]
        unlock_pose = r[6:8]
        classifier_type = r[8:9]
        classifier_index = r[9:10]
        has_custom_classifier = r[10:11]
        stream_indicating = r[11:12]
        sku = r[12:13]
        reserved = r[13:]
    
    async def read_firmware_version(self):
        uuid = self.construct_uuid(self.code.firmware_version)
        r = await self.read_data(uuid)
        major = int.from_bytes(r[:2],'big')
        minor = int.from_bytes(r[2:4],'big') 
        patch = int.from_bytes(r[4:6],'big') 
        hardware_rev = int.from_bytes(r[6:],'big') 
    
    async def process_emg_data(self,action=None):
        i=0
        while True:
            if self.emg_data_queue.qsize() > 0:
                recv_characteristic,emg = await self.emg_data_queue.get()
                emg1 = emg[:8]
                emg2 = emg[8:16]
                #print(emg)
                # progression = (recv_characteristic - last_recv_characteristic) % 4
                # if progression > 1:
                #     for i in range(1,progression):
                #         for _ in range(0,8):
                #             self.emg_data_stream[i].append(0)
                # last_recv_characteristic = recv_characteristic
                for i in range(0,8):
                    self.emg_data_stream[i].append(emg1[i])
                    self.emg_data_stream[i].append(emg2[i])
                if not action == None:
                    action(self)
            else:
                await asyncio.sleep(0.0001)
            # if i>1000:
            #     print('connected')
            #     i=0
            # print(i)
            # i+=1

    def run_and_display_eeg(self,function,nsamples_displayed = 1000,connected=False):
        self.nsamples_displayed = nsamples_displayed
        win = pg.GraphicsWindow(title="Sample process")
        win.resize(1000,600)
        win.setWindowTitle('Myo Emg Monitor')
        pg.setConfigOptions(antialias=True)
        plots = []
        curves = []
        for i in range(8):
            plot = win.addPlot(title=f"EMG channel {i}",row=i,col = 0)
            curve = plot.plot(pen='y')
            plots.append(plot)
            curves.append(curve)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            if connected:
                executor.submit(self.connect_and_run_function,function)
            else:
                def run():
                    # asyncio.set_event_loop(asyncio.ProactorEventLoop())
                    # loop = asyncio.get_event_loop()
                    # loop.run_until_complete(function(self))
                    # loop.close()
                    asyncio.run(function(self))
                executor.submit(run)
            while not hasattr(self,'client'):
                time.sleep(1)
                print('waiting for connection')
            def update():
                if hasattr(self,'emg_data_stream'):
                    for i in range(8):
                        ydata = self.emg_data_stream[i]
                        if len(ydata) < self.nsamples_displayed:
                            ydata = np.pad(ydata,[0,self.nsamples_displayed-len(ydata)])
                        else:
                            ydata = ydata[-self.nsamples_displayed:]
                        curves[i].setData(ydata)
            timer = QtCore.QTimer()
            timer.timeout.connect(update)
            timer.start(30)
            QtGui.QApplication.instance().exec_()

class CommandCode:
    def __init__(self):
        self.basic_info='0101'
        self.firmware_version='0201'
        self.imu_data='0402'
        self.emg_data=['0105','0205','0305','0405']
        self.emg_handles = [42,45,48,51]
        self.battery_level='2a19'
        self.device_name='2a00'
        self.command = '0401'
