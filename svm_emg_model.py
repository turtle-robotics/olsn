from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score
import pandas as pd

# Load the dataset
training_data_path = 'ZBS_Data_Compiled_and_Labelled.csvIan_Static_Data_v2.csv'  # Path to the data file
ds = pd.read_csv(training_data_path)

# Separate features and target labels
X = ds[["channel 1", "channel 2", "channel 3", "channel 4", 
        "channel 5", "channel 6", "channel 7", "channel 8"]].values
y = ds["Class"].values


# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)


# Create a pipeline with scaling and SVM
svm_model = Pipeline([
    ('scaler', StandardScaler()),  # SVMs are sensitive to feature scaling
    ('svc', SVC(kernel='rbf', random_state=42, probability=True))  # RBF kernel for non-linear classification
])

# Fit the model
svm_model.fit(X_train, y_train)

# Cross-validation scores
cross_val_scores = cross_val_score(svm_model, X, y, cv=StratifiedKFold(n_splits=5))
print("\nSVM - Cross-validation scores:", cross_val_scores)
print("Mean cross-validation score:", cross_val_scores.mean())

# Test accuracy
y_pred = svm_model.predict(X_test)
print("\nSVM - Test accuracy:", accuracy_score(y_test, y_pred))
