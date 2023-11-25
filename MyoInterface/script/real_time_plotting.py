
import concurrent.futures

import sys
sys.path.insert(0, '/Users/icfar/Documents/OLSN/NoDongleTesting/MyoInterface/build/lib/MyoInterface')
# from build.lib.MyoInterface import MyoInterface
import name
# import MyoInterface

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
import time
async def function(interface):
    await interface.stream_raw_emg(action = lambda x : print('inside',interface.emg_data_stream))

interface = name.MyoInterface()
interface.lines = []
interface.nsamples_displayed = 1000
interface.figure = plt.figure(figsize=[15,15])
for i in range(8):
    ax = plt.subplot(8,1,i+1)
    line, = ax.plot(np.zeros(interface.nsamples_displayed))
    ax.set_ylim(-50,50)
    interface.lines.append(line)
with concurrent.futures.ThreadPoolExecutor() as executor:
    err_detect = executor.submit(interface.connect_and_run_function, function)
    while not hasattr(interface,'client'):
        # time.sleep(1)
        print('waiting for connection')

    def update(t):
        if hasattr(interface,'client'):
            for i in range(8):
                ydata = interface.emg_data_stream[i]
                if len(ydata) < interface.nsamples_displayed:
                    ydata = np.pad(ydata,[0,interface.nsamples_displayed-len(ydata)])
                else:
                    ydata = ydata[-interface.nsamples_displayed:]
                interface.lines[i].set_ydata(ydata)
    ani = FuncAnimation(interface.figure, update, interval=100)
    plt.show()
