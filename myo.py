#!/usr/bin/env python3

import multiprocessing
from pyomyo import Myo, emg_mode
import csv
from bokeh.plotting import figure, curdoc
from bokeh.models import ColumnDataSource
from bokeh.layouts import gridplot
from bokeh.io import push_notebook
import time

worker_q = multiprocessing.Queue()
csv_q = multiprocessing.Queue()
graph_q = multiprocessing.Queue()

emg_plots = [figure(title=f'EMG Channel {i+1}', width=400, height=200, 
                    tools='', toolbar_location=None) for i in range(8)]

emg_sources = [ColumnDataSource(data=dict(x=[], y=[])) for _ in range(8)]

for i, plot in enumerate(emg_plots):
    plot.line('x', 'y', source=emg_sources[i], line_width=2)
    plot.x_range.follow = "end"
    plot.x_range.follow_interval = 100  # Adjust as needed for your data rate

grid = gridplot(emg_plots, ncols=4)

curdoc().add_root(grid)
curdoc().title = "Real-time EMG Data"

def worker(q):
    m = Myo(mode=emg_mode.FILTERED)
    m.connect()

    def add_to_queue(emg, movement):
        q.put(emg)

    m.add_emg_handler(add_to_queue)

    def print_battery(bat):
        print('Battery level:', bat)

    m.add_battery_handler(print_battery)

    m.set_leds([128, 0, 0], [128, 0, 0])

    m.vibrate(1)

    while True:
        m.run()

    print('Worker Stopped')

def process_to_csv(q, csvfile):
    writer = csv.writer(csvfile)
    while True:
        while not q.empty():
            emg = list(q.get())
            writer.writerow(emg)


def process_to_graph(q):
    # Initialize data dictionary for each channel
    emg_data = {i: {'x': [], 'y': []} for i in range(8)}
    line_indices = [emg_sources[i].data['x'] for i in range(8)]

    while True:
        while not q.empty():
            emg = list(q.get())

            for i in range(8):
                emg_data[i]['x'].append(len(emg_data[i]['x']) + 1)
                emg_data[i]['y'].append(emg[i])

                # Trim data to keep a fixed window size
                if len(emg_data[i]['x']) > 100:  # Adjust window size as needed
                    emg_data[i]['x'] = emg_data[i]['x'][1:]
                    emg_data[i]['y'] = emg_data[i]['y'][1:]

                # Update the data source for the Bokeh plot
                emg_sources[i].data = emg_data[i]

            time.sleep(0.01)  # Adjust the sleep duration based on your data rate

if __name__ == '__main__':
    csvfile = open('myo_emg_data.csv', 'w+', newline='')

    p = multiprocessing.Process(target=worker, args=(worker_q,))
    p.start()

    p2 = multiprocessing.Process(target=process_to_csv, args=(csv_q, csvfile,))
    p2.start()

    p3 = multiprocessing.Process(target=process_to_graph, args=(graph_q,))
    p3.start()


    try:
        while True:
            while not worker_q.empty():
                emg = list(worker_q.get())
                csv_q.put(emg)
                graph_q.put(emg)
                print(emg)

    except KeyboardInterrupt:
        csvfile.close()
        print('Quitting')
        quit()
