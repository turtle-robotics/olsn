import numpy as np
import pandas as pd

data_path = 'zbs_2secfist.csv'  # Path to the data file
data = pd.read_csv(data_path)

# Define a function to determine the class based on the maximum EMG value in a row
def label_class(row):
    max_value = row.max()
    return 'Fist' if max_value > 65 else 'Rest'

# Apply the function to each row (excluding the Class column itself)
data['Class'] = data.iloc[:, :-1].apply(label_class, axis=1)

# Display the updated dataset to verify changes
data.head()
