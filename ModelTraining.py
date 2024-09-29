import numpy as np
import pandas as pd
import tensorflow as tf
import tensorflow_decision_forests as tfdf
from sklearn.model_selection import train_test_split
import ydf

training_data_path = '/home/zachary/Downloads/TURTLE/OLSN/olsn/Compiled and Labelled - Sheet1.csv'
df = pd.read_csv(training_data_path)

train_df = df.sample(frac = 0.8)
test_df = df.drop(train_df.index)

# does this need to be changed?
train_df.size / 9 #number of elements split into training
test_df.size / 9 #number of elements split into testing
(train_df.size / 9) + (test_df.size / 9) #total number of elements

train_ds = tfdf.keras.pd_dataframe_to_tf_dataset(train_df, label="Class")
test_ds = tfdf.keras.pd_dataframe_to_tf_dataset(test_df, label="Class")

model = tfdf.keras.RandomForestModel()
model.fit(train_ds)

model.evaluate(test_ds)

model.predict(test_ds)

results = model.evaluate(test_ds)

model.save_weights('/home/zachary/Downloads/TURTLE/OLSN/olsn/model_weights.keras')




"""
porting model to harware below

from sklearn.datasets import load_iris
from everywhereml.sklearn.ensemble import RandomForestClassifier

X, y = load_iris(return_X_y=True) # replace this with your own data!
clf = RandomForestClassifier(n_estimators=5).fit(X, y)

'''
  Now we convert the classifier to C++ with a single line of code
  - instance_name will create an instance of the classifier in the produced code
    (you will use this name later)
'''
print(clf.to_arduino(instance_name='irisClassifier'))
"""
