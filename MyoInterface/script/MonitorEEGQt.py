from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import concurrent.futures
from MyoInterface.MyoInterface import MyoInterface
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
import time

async def function(interface):
    await interface.stream_raw_emg()

interface = MyoInterface()
interface.lines = []
interface.nsamples_displayed = 1000

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
    err_detect = executor.submit(interface.connect_and_run_function, function)
    while not hasattr(interface,'client'):
        time.sleep(1)
        print('waiting for connection')

    def update():
         if hasattr(interface,'client'):
            for i in range(8):
                ydata = interface.emg_data_stream[i]
                if len(ydata) < interface.nsamples_displayed:
                    ydata = np.pad(ydata,[0,interface.nsamples_displayed-len(ydata)])
                else:
                    ydata = ydata[-interface.nsamples_displayed:]
                curves[i].setData(ydata)
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(30)
    QtGui.QApplication.instance().exec_()