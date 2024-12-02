import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pickle
from sklearn.metrics import confusion_matrix, classification_report, ConfusionMatrixDisplay
from sklearn.metrics import roc_curve, auc
from sklearn.model_selection import cross_val_score, train_test_split, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics

# Load the dataset
training_data_path = 'ZBS_Data_Compiled_and_Labelled.csv'  # Path to the data file
ds = pd.read_csv(training_data_path)

# Separate features and target labels
X = ds[["channel 1", "channel 2", "channel 3", "channel 4", 
        "channel 5", "channel 6", "channel 7", "channel 8"]]
y = ds["Class"]

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

# Initialize the Random Forest model
rf_model = RandomForestClassifier(random_state=42)

# Cross-validation scores
cross_val_scores = cross_val_score(rf_model, X, y, cv=StratifiedKFold(n_splits=5))
print("\nCross-validation scores across folds:", cross_val_scores)
print("Mean cross-validation score:", cross_val_scores.mean())

# Fit the model on the training set
rf_model.fit(X_train, y_train)

# Evaluate on the test set
y_pred_rf = rf_model.predict(X_test)
test_accuracy = metrics.accuracy_score(y_test, y_pred_rf)
print("\nTest accuracy of the Random Forest model:", test_accuracy)

# Classification report
print("\nClassification Report:")
print(classification_report(y_test, y_pred_rf))

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred_rf)

# Enhanced Confusion Matrix Visualization
fig, ax = plt.subplots(figsize=(12, 10))  # Larger size for better visibility
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=rf_model.classes_)
disp.plot(cmap="Blues", ax=ax, values_format='')  # No default values displayed

# Manually add black text annotations for matrix values
for i in range(cm.shape[0]):
    for j in range(cm.shape[1]):
        ax.text(j, i, f'{cm[i, j]}', ha='center', va='center', color="black", fontsize=16)

# Title and Labels
ax.set_title("Confusion Matrix", fontsize=24, pad=20, color="black")
ax.set_xlabel("Predicted Labels", fontsize=18, labelpad=15)
ax.set_ylabel("True Labels", fontsize=18, labelpad=15)

# Adjust tick labels for clarity
ax.tick_params(axis='both', which='major', labelsize=14)

# Disable gridlines for a cleaner appearance
ax.grid(False)

# Save the improved confusion matrix
plt.tight_layout()
plt.savefig("confusion_matrix_cleaned.png", dpi=300)  # High resolution for printing
plt.show()



# Feature Importance
feature_importances = rf_model.feature_importances_
features = X.columns
plt.figure(figsize=(10, 6))
plt.barh(features, feature_importances, color='blue', edgecolor='black')
plt.title("Feature Importances")
plt.xlabel("Importance Score")
plt.ylabel("Features")
plt.grid(axis='x', linestyle='--', alpha=0.7)
plt.savefig("feature_importances.png")  # Save for the poster
plt.show()

# ROC Curve (for binary classification or multi-class one-vs-all)
if len(rf_model.classes_) == 2:  # Binary classification
    y_prob = rf_model.predict_proba(X_test)[:, 1]
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='blue', label=f'ROC curve (AUC = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='gray', linestyle='--', label="Random Guess")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.legend(loc="lower right")
    plt.grid(linestyle='--', alpha=0.7)
    plt.savefig("roc_curve.png")  # Save for the poster
    plt.show()

# Data Distribution: Plot each feature histogram
# for col in X.columns:
#     plt.figure(figsize=(6, 4))
#     plt.hist(X[col], bins=20, color='blue', edgecolor='black', alpha=0.7)
#     plt.title(f"Distribution of {col}")
#     plt.xlabel(col)
#     plt.ylabel("Frequency")
#     plt.grid(linestyle='--', alpha=0.7)
#     plt.savefig(f"{col}_distribution.png")  # Save for the poster
#     plt.show()

filename = 'rf_model.pkl' # save model
pickle.dump(rf_model, open(filename, 'wb'))
