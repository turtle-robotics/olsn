#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import logging

from myo import AggregatedData, MyoClient
from myo.types import (
    ClassifierEvent,
    ClassifierMode,
    EMGData,
    EMGMode,
    FVData,
    IMUData,
    IMUMode,
    MotionEvent,
    VibrationType,
)
from myo.constants import RGB_PINK
import pandas as pd
import numpy as np
# from csv_logger import CsvLogger

global df

df = pd.DataFrame(columns=['channel 1', 'channel 2', 'channel 3', 'channel 4', 'channel 5', 'channel 6', 'channel 7',
                           'channel 8', 'channel 9', 'channel 10', 'channel 11', 'channel 12', 'channel 13', 'channel 14', 'channel 15',
                           'channel 16','channel 17','channel 18'])

class SampleClient(MyoClient):

    # global df
    # df = pd.DataFrame(columns=['channel 1', 'channel 2', 'channel 3', 'channel 4', 'channel 5', 'channel 6', 'channel 7',
    #                        'channel 8', 'channel 9', 'channel 10', 'channel 11', 'channel 12', 'channel 13', 'channel 14', 'channel 15','channel 16'])
    
    global i
    i = 0

    global array
    
    async def on_classifier_event(self, ce: ClassifierEvent):
        # logging.info(ce.json())
        print(1)
        pass

    async def on_aggregated_data(self, ad: AggregatedData):
        # logging.info(ad)
        #
        print(2)
        global df
        string = str(ad)
        array = string.split(',')
        array = np.array(array).reshape(1,18)
        print(array)
        try:
            df = df.append(pd.DataFrame(array, columns=df.columns), ignore_index=False)
        except:
            df = pd.DataFrame(array)

        # print(np.size(array))
        # print(string_thing)
        # global i, df, array


        # if (i == 0):
        #     array = np.array(ad)
        # else:
        #     temp = np.array(ad)
        #     np.concatenate((array,temp), axis = 0)
        # print(array)
        # # self.df[i] = array.tolist()
        # # df[i] = array.tolist()
        # i += 1
        # print(i)


    async def on_emg_data(self, emg: EMGData):
        # logging.info(emg)
        print(3)
        pass

    async def on_fv_data(self, fvd: FVData):
        # logging.info(fvd.json())
        print(4)
        pass

    async def on_imu_data(self, imu: IMUData):
        # logging.info(imu.json())
        print(5)
        pass

    async def on_motion_event(self, me: MotionEvent):
        # logging.info(me.json())
        print(6)


async def main(args: argparse.Namespace):

    # global df
    #
    # df = pd.DataFrame(columns=['channel 1', 'channel 2', 'channel 3', 'channel 4', 'channel 5', 'channel 6', 'channel 7',
    #                        'channel 8', 'channel 9', 'channel 10', 'channel 11', 'channel 12', 'channel 13', 'channel 14', 'channel 15',
    #                        'channel 16'])


    logging.info("scanning for a Myo device...")

    sc = await SampleClient.with_device(mac=args.mac, aggregate_all=True)

    # get the available services on the myo device
    info = await sc.get_services()
    logging.info(info)

    # setup the MyoClient
    await sc.setup(
        classifier_mode=ClassifierMode.ENABLED,
        emg_mode=EMGMode.SEND_FILT,  # for aggregate_all
        imu_mode=IMUMode.SEND_ALL,  # for aggregate_all
    )

    # start the indicate/notify
    await sc.start()

    # receive notifications for 5 seconds
    await asyncio.sleep(3)
    # await asyncio.Future()

    df.to_csv('file_name4.csv')

    # stop the indicate/notify
    await sc.stop()

    logging.info("bye bye!")
    await sc.vibrate(VibrationType.LONG)
    await sc.led(RGB_PINK)
    await sc.disconnect()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="sets the log level to debug",
    )
    parser.add_argument(
        "--mac",
        default="",
        help="the mac address to connect to",
        metavar="<mac-address>",
    )
    parser.add_argument(
        "--seconds",
        default=10,
        help="seconds to read data",
        metavar="<seconds>",
        type=int,
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )

    asyncio.run(main(args))
