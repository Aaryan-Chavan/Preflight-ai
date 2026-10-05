import json
import os
import numpy as np
import xgboost as xgb
from preflight.risk.feature_extractor import FeatureExtractor

class MLRiskAnalyzer:
    def __init__(self, models_dir="src/preflight/risk/models"):
        self.extractor = FeatureExtractor(models_dir)
        
        # 1. Load the lightweight XGBoost model directly from JSON
        self.model = xgb.Booster()
        self.model.load_model(os.path.join(models_dir, "xgboost_model.json"))
        
        # 2. Load the calibration curve for instant numpy interpolation
        with open(os.path.join(models_dir, "calibration.json"), "r") as f:
            calib = json.load(f)
            self.calib_x = np.array(calib["x"])
            self.calib_y = np.array(calib["y"])
            
        # 3. Load thresholds
        with open(os.path.join(models_dir, "thresholds.json"), "r") as f:
            self.thresholds = json.load(f)
            
        # 4. Load schema to guarantee strict column ordering
        with open(os.path.join(models_dir, "feature_schema.json"), "r") as f:
            self.schema = json.load(f)

    def analyze(self, old_ref: str, new_ref: str) -> dict:
        """Scores a Git commit and returns the calibrated risk."""
        # 1. Extract and process features
        processed_features, raw_features = self.extractor.extract(old_ref, new_ref)
        
        # 2. Convert to XGBoost DMatrix, guaranteeing the exact schema order
        feature_vector = [processed_features[f] for f in self.schema["features"]]
        dmatrix = xgb.DMatrix([feature_vector], feature_names=self.schema["features"])
        
        # 3. Predict raw probability
        raw_prob = self.model.predict(dmatrix)[0]
        
        # 4. Calibrate to a true percentage
        calibrated_prob = np.interp(raw_prob, self.calib_x, self.calib_y)
        
        # 5. Apply thresholds
        if calibrated_prob >= self.thresholds["HIGH"]:
            risk_level = "HIGH"
        elif calibrated_prob >= self.thresholds["MEDIUM"]:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
            
        return {
            "risk_level": risk_level,
            "confidence_percent": round(float(calibrated_prob) * 100, 1),
            "raw_features": raw_features
        }