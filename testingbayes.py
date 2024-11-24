import numpy as np
import pandas as pd
import pickle
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import cross_val_score


# Load the dataset
training_data_path = 'Compiled and Labelled - Sheet1.csv'  # Path to the data file
ds = pd.read_csv(training_data_path)

# Separate features and target labels
X = ds[["channel 1", "channel 2", "channel 3", "channel 4", 
        "channel 5", "channel 6", "channel 7", "channel 8"]]
y = ds["Class"]

# Check for highly similar samples between train and test sets
def check_similarity(X_train, X_test, threshold=0.95):
    # Compute cosine similarity matrix between training and testing sets
    similarity_matrix = cosine_similarity(X_train, X_test)
    high_similarity_pairs = (similarity_matrix > threshold).sum()
    print("Number of highly similar samples between train and test:", high_similarity_pairs)
    if high_similarity_pairs > 0:
        print(f"Warning: Found {high_similarity_pairs} samples with similarity over {threshold}. This may indicate data leakage.")

# Split the data into training and testing sets, ensuring random state for reproducibility
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

# Check for similar samples
check_similarity(X_train, X_test)

# Verify class distribution to avoid bias between training and test sets
print("\nTraining set class distribution:")
print(y_train.value_counts(normalize=True))
print("\nTesting set class distribution:")
print(y_test.value_counts(normalize=True))

# Initialize and train the model with cross-validation to avoid overfitting and assess performance more reliably
model = RandomForestClassifier(n_estimators=100, max_depth=4)

# Using Stratified K-Fold cross-validation
skf = StratifiedKFold(n_splits=5)
cross_val_scores = cross_val_score(model, X, y, cv=skf)
print("\nCross-validation scores across folds:", cross_val_scores)
print("Mean cross-validation score:", cross_val_scores.mean())

# Fit the model on the training set
model.fit(X_train, y_train)

# Evaluate on the test set to check generalization
y_pred = model.predict(X_test)
print("\nTest accuracy of the model:", metrics.accuracy_score(y_test, y_pred))

# Save the model for future use
filename = 'model.pkl'
pickle.dump(model, open(filename, 'wb'))
