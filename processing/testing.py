import joblib
from pathlib import Path

script_dir = Path(__file__).resolve().parent
model_path = script_dir / 'safety_model.joblib'
model = joblib.load(model_path)

# Test with "Hours Since Event" (e.g., 6 hours after an event)
# The double brackets [[6]] mean: 1 sample, 1 feature
test_data = [[6]] 
prediction = model.predict(test_data)

print(f"Prediction for 6 hours after event: {prediction[0]:.2f}")