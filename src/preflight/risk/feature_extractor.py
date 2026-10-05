import subprocess
import json
import os
import numpy as np

class FeatureExtractor:
    def __init__(self, models_dir="src/preflight/risk/models"):
        # Load the schema exported during training
        schema_path = os.path.join(models_dir, "feature_schema.json")
        with open(schema_path, "r") as f:
            self.schema = json.load(f)

    def extract(self, old_ref: str, new_ref: str) -> tuple[dict, dict]:
        """Extracts features from Git and formats them for the ML model."""
        
        # 1. Run git diff to get size metrics
        cmd = ["git", "diff", "--numstat", f"{old_ref}..{new_ref}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        la, ld, nf = 0, 0, 0
        for line in result.stdout.strip().split('\n'):
            if not line: 
                continue
            added, deleted, _ = line.split('\t', 2)
            # Binary files show up as '-' in numstat, so we skip them for line counts
            if added != '-': la += int(added)
            if deleted != '-': ld += int(deleted)
            nf += 1

        # 2. Build the raw feature dictionary
        raw_features = {
            "la": la,
            "ld": ld,
            "nf": nf
        }

        # The ApacheJIT schema expects other history features (entropy, author experience).
        # We temporarily safely pad missing features with 0 until we build the git log parser.
        for feat in self.schema["features"]:
            if feat not in raw_features:
                raw_features[feat] = 0

        # 3. Apply transformations exactly as defined in the training schema
        processed_features = {}
        for feat in self.schema["features"]:
            val = raw_features[feat]
            if feat in self.schema["log1p_transforms"]:
                processed_features[feat] = np.log1p(val)
            else:
                processed_features[feat] = val

        return processed_features, raw_features