#!/usr/bin/env python3

import multiprocessing
from pyomyo import Myo, emg_mode
import csv
from serial.tools.list_ports import comports

worker_q = multiprocessing.Queue()
csv_q = multiprocessing.Queue()
graph_q = multiprocessing.Queue()


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
    while True:
        while not q.empty():
            emg = list(q.get())
            # do something

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
