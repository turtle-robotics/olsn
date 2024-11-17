import numpy as np
import tensorflow as tf
import tensorflow_decision_forests as tfdf
import pandas as pd
import ydf


training_data_path = 'Compiled and Labelled - Sheet1.csv'  # Change this path to wherever you keep your data
ds = pd.read_csv(training_data_path)
batch_size = 12

df = pd.DataFrame({
                   "feature_1" : ds['channel 1'], 
                   "feature_2" : ds['channel 2'], 
                   "feature_3" : ds['channel 3'], 
                   "feature_4" : ds['channel 4'], 
                   "feature_5" : ds['channel 5'],
                   "feature_6" : ds['channel 6'], 
                   "feature_7" : ds['channel 7'], 
                   "feature_8" : ds['channel 8'], 
                   "class"     : ds['Class']
                   })


features = df[["feature_1", "feature_2", "feature_3", "feature_4", "feature_5", "feature_6", "feature_7", "feature_8"]]
labels = df["class"]
# Split the data into training and testing sets
train_size = int(0.75 * len(df))
train_features = features[:train_size]
train_labels = labels[:train_size]
test_features = features[train_size:]
test_labels = labels[train_size:]

# Convert to TensorFlow datasets
train_ds = (tf.data.Dataset.from_tensor_slices((dict(train_features), train_labels)).batch(batch_size))
test_ds = (tf.data.Dataset.from_tensor_slices((dict(test_features), test_labels)).batch(batch_size))

model = ydf.RandomForestLearner(label="class").train(train_ds)

analysis = model.analyze(test_ds)
print(analysis)


# df = pd.DataFrame({'channel 1': [0], 
#                    'channel 2': [1], 
#                    'channel 3': [2], 
#                    'channel 4': [3], 
#                    'channel 5': [4],
#                    'channel 6': [5], 
#                    'channel 7': [6], 
#                    'channel 8': [7], 
#                    'Class': [8]})
# print(df.head)
# dataset = tf.data.Dataset.from_tensor_slices((df[['feature1', 'feature2']].values, df['label'].values))


# # Evaluate a model (e.g. roc, accuracy, confusion matrix, confidence intervals)
# model.evaluate(test_ds)

# # Generate predictions
# model.predict(test_ds)

# # Analyse a model (e.g. partial dependence plot, variable importance)

# # Benchmark the inference speed of a model
# model.benchmark(test_ds)

# model.describe()
