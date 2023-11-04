import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import numpy as np

# Create an array of 1x8 vectors (simulated data for demonstration)
n = 100  # Number of vectors
vectors = [np.random.rand(8) for _ in range(n)]

# Create a PyQtGraph application
app = QApplication([])

# Create a PyQtGraph plot window
win = pg.GraphicsLayoutWidget(show=True)
win.setWindowTitle('Live Vector Plot')

# Create a list to store PlotItem objects for each vector
plots = []

# Initialize the plots with the initial data
plot = '1'
for vector in vectors:
    plot = win.addPlot(title=f"Vector Plot {plot}")
    curve = plot.plot(vector, pen='g')
    plots.append({'plot': plot, 'curve': curve})

# Function to update the plots with new data
def update_plots():
    for i, vector in enumerate(vectors):
        plots[i]['curve'].setData(vector)

# Create a QTimer to periodically update the plots (e.g., every 100 ms)
timer = QTimer()
timer.timeout.connect(update_plots)
timer.start(100)

# Start the PyQtGraph application event loop
app.exec_()
