import numpy as np
import tensorflow as tf
import tensorflow_decision_forests as tfdf
import pandas as pd
import ydf


training_data_path = 'Compiled and Labelled - Sheet1.csv'  # Change this path to wherever you keep your data
ds = pd.read_csv(training_data_path)


train_ds, test_ds = tf.keras.utils.split_dataset(ds, left_size=0.75)

init_model = tfdf.keras.RandomForestModel()

train_ds.head(5)
