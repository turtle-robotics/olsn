# import random
# from bokeh.driving import count
# from bokeh.models import ColumnDataSource
# from bokeh.plotting import curdoc, figure

# update_interval = 100
# roll_over = 1000

# source = ColumnDataSource({'x':[], 'y':[]})

# @count()
# def update(x):
#     y = random.random()
#     source.Stream({'x':[], 'y':[]}, rollover=roll_over)

# plot = figure()
# plot.line('x', 'y', source = source)
# plot.xaxis.axis_label = 'x'
# plot.yaxis.axis_label = 'y'

# doc = curdoc()
# doc.add_root(plot)
# doc.add_periodic_callback(update, update_interval)
import sys
from math import sin
from threading import Thread
from time import sleep

from PyQt6.QtWidgets import QApplication

from pglive.sources.data_connector import DataConnector
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget

"""
Line plot is displayed in this example.
"""
app = QApplication(sys.argv)
running = True

plot_widget = LivePlotWidget(title="Line Plot @ 100Hz")
plot_curve = LiveLinePlot()
plot_widget.addItem(plot_curve)
# DataConnector holding 600 points and plots @ 100Hz
data_connector = DataConnector(plot_curve, max_points=600, update_rate=100)


def sin_wave_generator(connector):
    """Sine wave generator"""
    x = 0
    while running:
        x += 1
        data_point = sin(x * 0.01)
        # Callback to plot new data point
        connector.cb_append_data_point(data_point, x)

        sleep(0.01)


plot_widget.show()
Thread(target=sin_wave_generator, args=(data_connector,)).start()
app.exec()
running = False
