import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

def train_and_save_model():
    # Define the static decay logic
    X_train = np.array([[0], [12], [24], [48], [72], [168]])
    y_train = np.array([1.0, 0.78, 0.62, 0.38, 0.24, 0.05])

    # Train the model
    ml_model = RandomForestRegressor(n_estimators=50, random_state=42)
    ml_model.fit(X_train, y_train)

    # Save the model
    joblib.dump(ml_model, 'safety_model.joblib')
    print("✅ Model brain created and saved as 'safety_model.joblib'.")

if __name__ == "__main__":
    train_and_save_model()