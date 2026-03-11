import pandas as pd
import numpy as np
import pickle

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


# -----------------------------
# 1️⃣ Load Dataset
# -----------------------------
df = pd.read_excel("Complete_Dataframe_def.xlsx")

# Remove ID column if exists
if "Sub" in df.columns:
    df = df.drop("Sub", axis=1)


# -----------------------------
# 2️⃣ Select Simplified Features
# -----------------------------
X = df[[
    "Mean_ACC_ANS",
    "Mean_RTs_ANS",
    "wm_K",
    "Accuracy_SymbolicComp",
    "RTs_SymbolicComp"
]]

y = df["group"]


# -----------------------------
# 3️⃣ Encode Target Labels
# -----------------------------
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)


# -----------------------------
# 4️⃣ Split Dataset (80/20)
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded,
    test_size=0.2,
    random_state=42
)


# -----------------------------
# 5️⃣ Train Random Forest Model
# -----------------------------
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)


# -----------------------------
# 6️⃣ Evaluate Model
# -----------------------------
y_pred = model.predict(X_test)

print("Model Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))
print("\nConfusion Matrix:\n")
print(confusion_matrix(y_test, y_pred))


# -----------------------------
# 7️⃣ Save Model & Encoder
# -----------------------------
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)

with open("label_encoder.pkl", "wb") as f:
    pickle.dump(label_encoder, f)

print("\nModel saved successfully as model.pkl")
print("Label encoder saved as label_encoder.pkl")

