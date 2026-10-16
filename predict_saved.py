"""Predict original-schema features with the saved, fully trained CatBoost model."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from pump_model import ROOT, PumpFeatures, write_submission


class SavedPumpModel:
    def __init__(self, path):
        self.model = CatBoostClassifier().load_model(str(path))

    def predict(self, X):
        return np.asarray(self.model.predict(PumpFeatures().fit_transform(X), thread_count=4)).ravel()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, default=ROOT / 'data/raw/test_values.csv')
    parser.add_argument('--model', type=Path, default=ROOT / 'results/final_model.cbm')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/submission_reproduced.csv')
    args = parser.parse_args()
    features = pd.read_csv(args.features)
    if not features.id.is_unique or features.id.isna().any():
        raise ValueError('Duplicate or missing IDs')
    submission = write_submission(SavedPumpModel(args.model), features, args.output)
    print('Saved', args.output, submission.shape)
