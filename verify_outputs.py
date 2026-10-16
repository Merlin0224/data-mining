"""Audit label alignment, holdout integrity, metrics, hashes and test predictions."""
from pathlib import Path
import hashlib
import json
import tempfile
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split
from pump_model import ROOT, LABELS, SEED, load_data, PumpFeatures, write_submission


def main():
    out = ROOT / 'results'
    raw = ROOT / 'data/raw'
    X, y, test = load_data(raw)
    manifest = json.loads((raw / 'manifest.json').read_text())
    for item in manifest['files']:
        assert hashlib.sha256((raw / item['name']).read_bytes()).hexdigest() == item['sha256']
    # Shuffled label rows must leave feature/label alignment unchanged.
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        tmp = Path(tmp)
        X.to_csv(tmp / 'train_values.csv', index=False)
        pd.read_csv(raw / 'train_labels.csv').sample(frac=1, random_state=19).to_csv(
            tmp / 'train_labels.csv', index=False)
        test.to_csv(tmp / 'test_values.csv', index=False)
        _, y_shuffled, _ = load_data(tmp)
        assert y.equals(y_shuffled)
    train_idx, valid_idx = train_test_split(np.arange(len(X)), test_size=0.2,
                                           stratify=y, random_state=SEED)
    assignment = pd.read_csv(out / 'split_assignment.csv')
    assert set(assignment.loc[assignment.split == 'validation', 'id']) == set(X.iloc[valid_idx].id)
    assert not set(X.iloc[train_idx].id) & set(X.iloc[valid_idx].id)
    predictions = pd.read_csv(out / 'validation_predictions.csv')
    assert predictions.id.tolist() == X.iloc[valid_idx].id.tolist()
    assert predictions.actual.tolist() == y.iloc[valid_idx].tolist()
    metadata = json.loads((out / 'run_metadata.json').read_text())
    comparison = pd.read_csv(out / 'model_comparison.csv').set_index('model')
    best = metadata['selected_model']
    assert best == comparison.cv_accuracy_mean.idxmax()
    actual_accuracy = accuracy_score(predictions.actual, predictions.prediction)
    actual_f1 = f1_score(predictions.actual, predictions.prediction, average='macro')
    assert np.isclose(actual_accuracy, comparison.loc[best, 'validation_accuracy'])
    assert np.isclose(actual_f1, comparison.loc[best, 'validation_macro_f1'])
    cm = pd.read_csv(out / 'confusion_matrix.csv', index_col=0)
    assert np.array_equal(cm.to_numpy(), confusion_matrix(predictions.actual, predictions.prediction, labels=LABELS))
    assert cm.to_numpy().sum() == len(valid_idx)
    folds = pd.read_csv(out / 'cv_folds.csv')
    for name, group in folds.groupby('model'):
        assert len(group) == 3
        assert np.isclose(group.accuracy.mean(), comparison.loc[name, 'cv_accuracy_mean'])
    submission = pd.read_csv(out / 'submission.csv')
    assert submission.columns.tolist() == ['id', 'status_group']
    official_template = pd.read_csv(raw / 'SubmissionFormat.csv')
    assert submission.id.tolist() == official_template.id.tolist()
    assert len(submission) == 14850 and not submission.isna().any().any()
    assert set(submission.status_group) <= set(LABELS)
    assert hashlib.sha256((out / 'submission.csv').read_bytes()).hexdigest() == metadata['submission_sha256']
    if 'catboost' in best:
        model = CatBoostClassifier().load_model(str(out / 'final_model.cbm'))
        reproduced = model.predict(PumpFeatures().fit_transform(test), thread_count=4).ravel()
        by_test_order = submission.set_index('id').loc[test.id, 'status_group'].to_numpy()
        assert np.array_equal(reproduced, by_test_order)
    # Verify predictions still bind to IDs when a differently ordered template is used.
    class FixedPredictor:
        def predict(self, rows):
            return np.asarray([LABELS[i % 3] for i in range(len(rows))])
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        tmp = Path(tmp)
        template = test[['id']].head(9).sample(frac=1, random_state=7)
        template.to_csv(tmp / 'template.csv', index=False)
        reordered = write_submission(FixedPredictor(), test.head(9), tmp / 'out.csv', tmp / 'template.csv')
        expected = dict(zip(test.id.head(9), [LABELS[i % 3] for i in range(9)]))
        assert reordered.id.tolist() == template.id.tolist()
        assert reordered.status_group.tolist() == [expected[i] for i in template.id]
    mutated = X.head(3).copy()
    mutated.loc[mutated.index[0], ['construction_year', 'longitude']] = [2099, 0]
    f = PumpFeatures().fit_transform(mutated)
    assert 'id' not in f and 'status_group' not in f
    assert pd.isna(f.iloc[0].construction_year) and pd.isna(f.iloc[0].longitude)
    audit = {'status': 'PASS', 'checks': ['raw SHA-256', 'shuffled label alignment',
        'holdout split IDs', 'prediction-to-label alignment', 'CV-only model selection',
        'recomputed Accuracy and Macro-F1', 'confusion counts', 'per-fold score means',
        'submission schema/order/hash', 'native final model prediction reproduction',
        'shuffled template alignment', 'missing year and coordinate rules'],
        'validation_accuracy': actual_accuracy, 'validation_macro_f1': actual_f1,
        'all_label_counts': y.value_counts().to_dict(), 'clean_feature_count': len(f.columns)}
    (out / 'audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit, indent=2), flush=True)


if __name__ == '__main__':
    main()
