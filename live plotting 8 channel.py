import concurrent.futures
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import numpy as np
import csv
import pandas as pd
import sys

sys.path.insert(0,
                '/Users/icfar/Documents/GitHub/olsn/MyoInterface/build/lib/MyoInterface')  # change address as appropriate
# from build.lib.MyoInterface import MyoInterface
import MyoInterface
# import MyoInterface

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
import time

# parameters customizing plot
x_axis_size = 500  # sets how many data points are kept for plotting
time_between_updates = 1  # sets how often the plots update function is called, in ms

df = pd.DataFrame(columns=['channel 1', 'channel 2', 'channel 3', 'channel 4', 'channel 5', 'channel 6', 'channel 7',
                           'channel 8', ])  # start of creating dataframe to record data; WIP
data_count = 1


async def function(interface):
    global df
    await interface.stream_raw_emg(action=lambda x: print())
    df = df.append(interface.emg_data_stream[:][-1])


interface = MyoInterface.MyoInterface()
interface.lines = []

# vectors holding data being plotted
sensor_vectors = np.zeros((8, x_axis_size,))  # different sensor_vectors for each sensor

# Create a PyQtGraph application
app = QApplication([])

# Create a PyQtGraph plot window
win = pg.GraphicsLayoutWidget(show=True)
win.setWindowTitle('Live Vector Plot')

# Create a list to store PlotItem objects for each vector
plots = []

# Initialize the plots with the initial data
colorList = ["#fa9189", "#fcae7c",
             "#ffe699", "#f9ffb5", "#b3f5bc", "#d6f6ff", "#e2cbf7", "#d1bdf1"]
plot = '1'
plot_position_iterator = 1  # used to determine when to create new row or column
for vector in sensor_vectors:
    plot = win.addPlot(title=f"Channel {plot_position_iterator}")
    plot.setXRange(0, x_axis_size)
    curve = plot.plot(vector, pen=colorList[plot_position_iterator - 1])
    plots.append({'plot': plot, 'curve': curve})
    if plot_position_iterator % 2 == 0:
        win.nextRow()
    elif plot_position_iterator % 2 == 1:
        win.nextCol()
    plot_position_iterator += 1

with concurrent.futures.ThreadPoolExecutor() as executor:
    err_detect = executor.submit(interface.connect_and_run_function, function)
    while not hasattr(interface, 'client'):
        time.sleep(1)
        print('waiting for connection')


    def update_plots():
        global data_count
        if hasattr(interface, 'client'):
            for i in range(8):
                sensor_vectors[i] = np.roll(sensor_vectors[i], -1)  # shift data to the left
                sensor_vectors[i][-1] = interface.emg_data_stream[i][-1]  # add new data point to end
                plots[i]['curve'].setData(sensor_vectors[i])  # update plot
            print("DC: ", data_count)
            data_count += 1

            # commented out from original library code; keeping in case useful to better understand library function later
            # for i in range(8):
            #     ydata = interface.emg_data_stream[i]
            #     if len(ydata) < interface.nsamples_displayed:
            #         ydata = np.pad(ydata,[0,interface.nsamples_displayed-len(ydata)])
            #     else:
            #         ydata = ydata[-interface.nsamples_displayed:]
            #     interface.lines[i].set_ydata(ydata)


    # Create a QTimer to periodically update the plots (e.g., every 100 ms)
    timer = QTimer()
    timer.timeout.connect(update_plots)
    timer.start(time_between_updates)

    # Start the PyQtGraph application event loop
    app.exec_()

