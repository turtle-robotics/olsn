#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, asyncio, logging, pickle, time
import pandas as pd
import numpy as np
from collections import Counter
from threading import Thread
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from myo import AggregatedData, MyoClient
from myo.types import (
    ClassifierMode,
    EMGMode,
    IMUMode,
    VibrationType,
)
from myo.constants import RGB_PINK

# Load the model
filename = 'dl-myo/examples/rf_model.pkl'
model = pickle.load(open(filename, 'rb'))

# Initialize variables for prediction aggregation
prediction_buffer = []
start_time = time.time()

# Dataframe for incoming data
df = pd.DataFrame(columns=[
    'channel 1', 'channel 2', 'channel 3', 'channel 4',
    'channel 5', 'channel 6', 'channel 7', 'channel 8'
])

# Gesture-to-Image Mapping
gesture_images = {
    "Fist": "dl-myo/examples/fist.png",           # Replace with your fist image file path
    "Rest": "dl-myo/examples/rest.png",           # Replace with your rest image file path
    "One-Finger-Pinch": "dl-myo/examples/one_finger_pinch.png",  # Replace with your pinch image file path
    "Two-Finger-Pinch": "dl-myo/examples/two_finger_pinch.png",  # Replace with your pinch image file path
    "Extension": "dl-myo/examples/extension.png",  # Replace with your extension image file path
}

# Initialize the GUI
gesture_label = None
gesture_image_label = None


def run_gui():
    """Runs the enhanced GUI in a separate thread."""
    global gesture_label, gesture_image_label

    # Create the main window
    root = tk.Tk()
    root.title("Texas A&M | MEEN 423 | Project 2")
    root.geometry("900x700")
    root.configure(bg="#500000")  # Texas A&M maroon color

    # Title label
    title_label = tk.Label(
        root,
        text="Real-Time Gesture Recognition for Dynamic Prosthetic Devices",
        font=("Helvetica", 16, "bold"),
        fg="white",
        bg="#500000",
        wraplength=850,
    )
    title_label.pack(pady=10)

    # Prediction Display (Main Focus)
    prediction_frame = tk.Frame(root, bg="#500000")
    prediction_frame.pack(pady=20)

    prediction_label = tk.Label(
        prediction_frame,
        text="Prediction:",
        font=("Helvetica", 28, "bold"),
        fg="white",
        bg="#500000",
    )
    prediction_label.grid(row=0, column=0, padx=10)

    gesture_label = tk.Label(
        prediction_frame,
        text="Waiting...",
        font=("Helvetica", 48, "bold"),
        fg="#FFD700",  # Gold
        bg="#500000",
    )
    gesture_label.grid(row=0, column=1, padx=10)

    # Image Display (Centralized)
    gesture_image_label = tk.Label(root, bg="#500000")
    gesture_image_label.pack(pady=40)

    # Footer Frame for Logo and Text
    footer_frame = tk.Frame(root, bg="#500000")
    footer_frame.pack(side="bottom", pady=10)

    footer_label = tk.Label(
        footer_frame,
        text="© 2024 Texas A&M University | All Rights Reserved",
        font=("Helvetica", 10, "italic"),
        fg="white",
        bg="#500000",
    )
    footer_label.grid(row=0, column=0, padx=5)

    # Minimal MEEN Stack Logo
    logo_path = "dl-myo/examples/MEEN_stack.png"
    try:
        logo = Image.open(logo_path)
        logo = logo.resize((80, 80))  # Resize logo to be minimal
        logo_tk = ImageTk.PhotoImage(logo)
        logo_label = tk.Label(footer_frame, image=logo_tk, bg="#500000")
        logo_label.image = logo_tk  # Keep a reference to avoid garbage collection
        logo_label.grid(row=0, column=1, padx=5)
    except Exception as e:
        logging.warning(f"Unable to load logo image: {e}")

    root.mainloop()


def update_gesture_image(prediction):
    """Update the gesture image based on the prediction."""
    global gesture_image_label, gesture_images

    if prediction in gesture_images:
        try:
            # Load the image
            img_path = gesture_images[prediction]
            img = Image.open(img_path)
            img = img.resize((300, 300))  # Larger images for central focus
            img_tk = ImageTk.PhotoImage(img)

            # Update the label
            gesture_image_label.config(image=img_tk)
            gesture_image_label.image = img_tk  # Keep a reference to avoid garbage collection
        except Exception as e:
            logging.warning(f"Unable to load gesture image: {e}")


class SampleClient(MyoClient):
    async def on_aggregated_data(self, ad: AggregatedData):
        global prediction_buffer, start_time, df, gesture_label

        # Parse incoming data
        string = str(ad)
        array = string.split(',')
        array = np.array(array).reshape(1, 18)
        df = pd.DataFrame(array, columns=[
            'channel 1', 'channel 2', 'channel 3', 'channel 4',
            'channel 5', 'channel 6', 'channel 7', 'channel 8',
            'channel 9', 'channel 10', 'channel 11', 'channel 12',
            'channel 13', 'channel 14', 'channel 15', 'channel 16',
            'channel 17', 'channel 18'
        ])
        df = df.iloc[:, :8]  # Keep only the first 8 channels

        # Make prediction
        prediction = model.predict(df)[0]
        prediction_buffer.append(prediction)

        # Check if 0.25 seconds have passed
        if time.time() - start_time >= 0.25:
            # Determine the most frequent prediction
            most_common_prediction = Counter(prediction_buffer).most_common(1)[0][0]
            print(f"Prediction: {most_common_prediction}")
            prediction_buffer = []  # Clear the buffer
            start_time = time.time()  # Reset the timer

            # Update GUI with the prediction
            if gesture_label:
                gesture_label.config(text=most_common_prediction)

            # Update the gesture image
            update_gesture_image(most_common_prediction)


async def main(args: argparse.Namespace):
    logging.info("scanning for a Myo device...")
    sc = await SampleClient.with_device(mac=args.mac, aggregate_all=True)

    # Get available services on the Myo device
    info = await sc.get_services()
    logging.info(info)

    # Setup the MyoClient
    await sc.setup(
        classifier_mode=ClassifierMode.ENABLED,
        emg_mode=EMGMode.SEND_FILT,
        imu_mode=IMUMode.SEND_ALL,
    )

    # Start the client
    await sc.start()

    # Keep the MyoClient running
    await asyncio.Future()

    # Stop the client
    await sc.stop()
    logging.info("Exiting Myo client.")
    await sc.vibrate(VibrationType.LONG)
    await sc.led(RGB_PINK)
    await sc.disconnect()


if __name__ == "__main__":
    # Start the GUI in a separate thread
    gui_thread = Thread(target=run_gui, daemon=True)
    gui_thread.start()

    # Parse arguments for the Myo client
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

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)-15s %(name)-8s %(levelname)s: %(message)s",
    )

    # Run the Myo client
    asyncio.run(main(args))


