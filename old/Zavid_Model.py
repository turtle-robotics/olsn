"""
import numpy as np 
import tensorflow as tf # currently unused
import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.model_selection import cross_val_score

import tensorflow_decision_forests as tfdf # currently unused
import ydf # currently unused
from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics

# Load the dataset
training_data_path = 'Compiled and Labelled - Sheet1.csv'  # Change this path to wherever you keep your data
ds = pd.read_csv(training_data_path)
train_ds = ds.sample(frac = .75)
test_ds = ds.drop(train_ds.index)

print(train_ds)
print(test_ds)

# Create and train the model
model = RandomForestClassifier(n_estimators=10, max_depth=10)
model.fit(train_ds)

model.evaluate()

# Make predictions and evaluate
y_pred = model.predict(test_ds)


filename = 'model.pkl'
pickle.dump(model, open(filename, 'wb'))
"""

import numpy as np 
import pandas as pd
import pickle, sys
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics
from sklearn.model_selection import cross_val_score

# Load the dataset
training_data_path = 'Compiled and Labelled - Sheet1.csv'  # Path to the data file
ds = pd.read_csv(training_data_path)


X = ds[["channel 1", "channel 2", "channel 3", "channel 4", 
        "channel 5", "channel 6", "channel 7", "channel 8"]]
y = ds["Class"]
# print(y)

# Further split into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

# Find duplicate rows in training and test sets
duplicates_in_train_test = pd.merge(X_train, X_test, how='inner')
print("Number of duplicate samples between train and test:", len(duplicates_in_train_test))


model = RandomForestClassifier(n_estimators=10, max_depth=10)
model.fit(X_train, y_train)

cv_scores = cross_val_score(model, X_train, y_train, cv=5) # cross validate
print("Cross-validation scores:", cv_scores)
print("Mean cross-validation score:", cv_scores.mean())

y_pred = model.predict(X_test)
print("Test accuracy of the model:", metrics.accuracy_score(y_test, y_pred))


filename = 'model.pkl' # save model
pickle.dump(model, open(filename, 'wb'))
