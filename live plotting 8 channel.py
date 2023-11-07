import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import numpy as np

#vectors holding data being plotted
x_axis_size = 100 # sets how many data points are kept for plotting
time_between_updates = 100 # sets how often the plots update function is called, in ms

sensor_vectors = np.zeros((8,x_axis_size,)) # different sensor_vectors for each sensor

# Create a PyQtGraph application
app = QApplication([])

# Create a PyQtGraph plot window
win = pg.GraphicsLayoutWidget(show=True)
win.setWindowTitle('Live Vector Plot')

# Create a list to store PlotItem objects for each vector
plots = []

# Initialize the plots with the initial data
plot = '1'
plot_position_iterator = 0 # used to determine when to create new row or column
for vector in sensor_vectors:
    plot_position_iterator += 1
    plot = win.addPlot(title=f"Vector Plot {plot}")
    curve = plot.plot(vector, pen='g')
    plots.append({'plot': plot, 'curve': curve})
    if plot_position_iterator % 2 == 0:
        win.nextRow()
    elif plot_position_iterator % 2 == 1:
        win.nextCol()

# Function to update the plots with new data
def update_plots():
    fake_data = np.random.rand(1, 8) #creates fake data in place of sensor data
    for i, vector in enumerate(sensor_vectors):
        sensor_vectors[i] = np.roll(sensor_vectors[i], -1)  # shift data to the left
        sensor_vectors[i][-1] = fake_data[0][i]  # add new data point to end
        plots[i]['curve'].setData(vector) # update plot

# Create a QTimer to periodically update the plots (e.g., every 100 ms)
timer = QTimer()
timer.timeout.connect(update_plots)
timer.start(time_between_updates)

# Start the PyQtGraph application event loop
app.exec_()
