import numpy as np
import pandas as pd
import tensorflow as tf
import tensorflow_decision_forests as tfdf
from sklearn.model_selection import train_test_split, ParameterGrid, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

training_data_path = '/home/zachary/Downloads/TURTLE/OLSN/olsn/Compiled and Labelled - Sheet1.csv'  # Change this path to wherever you keep your data
df = pd.read_csv(training_data_path)
df = df.dropna() # drops all N/A data in the set (if there is any)

# Feature Selection
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['Class'])
train_ds = tfdf.keras.pd_dataframe_to_tf_dataset(train_df, label="Class")
test_ds = tfdf.keras.pd_dataframe_to_tf_dataset(test_df, label="Class") 

initial_model = tfdf.keras.RandomForestModel()
initial_model.fit(train_ds)
feature_importances = initial_model.make_inspector().variable_importances()


# Re-split the data and take into account feature under representation
train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df['Class'])

X = train_df.drop('Class', axis=1)
y = train_df['Class']
rus = RandomUnderSampler(random_state=42)
X_resampled, y_resampled = rus.fit_resample(X, y)
train_df = pd.concat([pd.DataFrame(X_resampled, columns=X.columns), pd.Series(y_resampled, name='Class')], axis=1)

# Convert to TF-DF datasets
train_ds = tfdf.keras.pd_dataframe_to_tf_dataset(train_df, label="Class")
test_ds = tfdf.keras.pd_dataframe_to_tf_dataset(test_df, label="Class")

# pretty much guessed on these, still a place where optimization can occur but with a 99.95% success rate I think we are good, will test on other data
param_grid = {
    "num_trees": [50, 100, 200],
    "max_depth": [10, 20, None],
    "min_examples": [2, 5, 10],
    "split_strategy": ["AUTO", "BEST"]
}

kf = KFold(n_splits=5, shuffle=True, random_state=42)
best_score = -np.inf
best_params = None

for params in ParameterGrid(param_grid):
    fold_scores = []
    for train_index, val_index in kf.split(train_df):
        train_fold = train_df.iloc[train_index]
        val_fold = train_df.iloc[val_index]
        
        train_fold_ds = tfdf.keras.pd_dataframe_to_tf_dataset(train_fold, label="Class")
        val_fold_ds = tfdf.keras.pd_dataframe_to_tf_dataset(val_fold, label="Class")
        
        model = tfdf.keras.RandomForestModel(**params)
        model.fit(train_fold_ds)
        
        evaluation = model.evaluate(val_fold_ds, return_dict=True)
        fold_scores.append(evaluation['accuracy'])
    
    avg_score = np.mean(fold_scores)
    print(f"Params: {params}, CV Accuracy: {avg_score}")
    
    if avg_score > best_score:
        best_score = avg_score
        best_params = params

print(f"Best Params: {best_params}, Best CV Accuracy: {best_score}")

# Train Final Model with Best Hyperparameters
final_model = tfdf.keras.RandomForestModel(**best_params)
final_model.fit(train_ds)

# Evaluate the Model
evaluation = final_model.evaluate(test_ds, return_dict=True)
print("Final Model Evaluation Metrics:")
for metric, value in evaluation.items():
    print(f"{metric}: {value}")

# Confusion Matrix
true_labels = test_df['Class'].values
predictions = final_model.predict(test_ds)
pred_labels = np.array([pred["predictions"][0].decode("utf-8") for pred in predictions])

cm = confusion_matrix(true_labels, pred_labels)
disp = ConfusionMatrixDisplay(confusion_matrix=cm)
disp.plot(cmap=plt.cm.Blues)
plt.title("Confusion Matrix")
plt.show()


model_save_path = '/home/zachary/Downloads/TURTLE/OLSN/olsn/random_forest_model'
final_model.save(model_save_path)

# Train scikit-learn RandomForestClassifier
X_train = train_df.drop('Class', axis=1).values
y_train = train_df['Class'].values
X_test = test_df.drop('Class', axis=1).values
y_test = test_df['Class'].values

clf = RandomForestClassifier(
    n_estimators=best_params['num_trees'],
    max_depth=best_params['max_depth'],
    min_samples_split=best_params['min_examples'],
    random_state=42
)
clf.fit(X_train, y_train)

# Evaluate
accuracy = clf.score(X_test, y_test)
print(f"Scikit-learn RandomForest Accuracy: {accuracy}")


