from MyoInterface.lib.MyoInterface import MyoInterface
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
def plot_real_time(interface:MyoInterface):
    interface.lines = []
    interface.nsamples_displayed = 1000
    interface.figure = plt.figure(figsize=[15,15])
    for i in range(8):
        ax = plt.subplot(8,1,i+1)
        line, = ax.plot(np.zeros(interface.nsamples_displayed))
        ax.set_ylim(-50,50)
        interface.lines.append(line)
    async def update(t):
        for i in range(8):
            ydata = interface.emg_data_stream[i]
            if len(ydata) < interface.nsamples_displayed:
                ydata = np.pad(ydata,[0,interface.nsamples_displayed-len(ydata)])
            interface.lines[i].set_ydata(ydata)
            await interface.process_queued_emg_data()
    ani = FuncAnimation(interface.figure, update, interval=1)
    plt.show()
