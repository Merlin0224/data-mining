"""Reproducible Pump it Up coursework reference. CPU only; at most 4 threads."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import time
import warnings

import numpy as np
import pandas as pd
import sklearn
from catboost import CatBoostClassifier
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent
LABELS = ['functional', 'functional needs repair', 'non functional']
SEED = 42


class PumpFeatures(BaseEstimator, TransformerMixin):
    """Row-wise transformations only; no target or dataset-wide statistics."""
    DROP = ['id', 'status_group', 'date_recorded', 'recorded_by', 'wpt_name',
            'scheme_name', 'num_private', 'extraction_type_group',
            'extraction_type_class', 'payment_type', 'quality_group',
            'quantity_group', 'source_type', 'source_class', 'waterpoint_type_group']

    def fit(self, X, y=None):
        self.feature_names_in_ = np.asarray(X.columns, dtype=object)
        return self

    def transform(self, X):
        x = X.copy()
        dates = pd.to_datetime(x['date_recorded'], errors='coerce')
        year = pd.to_numeric(x['construction_year'], errors='coerce')
        year = year.mask((year <= 0) | (year > dates.dt.year))
        x['construction_year'] = year
        x['pump_age'] = dates.dt.year - year
        x['recorded_year'] = dates.dt.year.astype(float)
        x['recorded_month'] = dates.dt.month.astype(float)
        for col in ['longitude', 'latitude']:
            values = pd.to_numeric(x[col], errors='coerce')
            # Near-zero coordinates in this Tanzania dataset are missing markers.
            x[col] = values.mask(values.abs() < 0.1)
        for col in ['amount_tsh', 'population', 'gps_height']:
            values = pd.to_numeric(x[col], errors='coerce')
            x[col] = values
            x[col + '_is_zero'] = (values == 0).astype(float)
            if col != 'gps_height':
                x['log1p_' + col] = np.log1p(values.clip(lower=0))
        # These are identifiers, not ordinal measurements.
        for col in ['region_code', 'district_code', 'public_meeting', 'permit']:
            x[col] = x[col].astype('string')
        x['district_key'] = x['region_code'] + '_' + x['district_code']
        x = x.drop(columns=self.DROP, errors='ignore')
        for col in x.select_dtypes(exclude=np.number).columns:
            values = x[col].astype('string').str.strip().str.lower()
            x[col] = values.replace('', pd.NA).fillna('__missing__').astype(str)
        return x.replace([np.inf, -np.inf], np.nan)


def load_data(data_dir=ROOT / 'data' / 'raw'):
    data_dir = Path(data_dir)
    X = pd.read_csv(data_dir / 'train_values.csv')
    labels = pd.read_csv(data_dir / 'train_labels.csv')
    test = pd.read_csv(data_dir / 'test_values.csv')
    for name, frame in [('train', X), ('labels', labels), ('test', test)]:
        if 'id' not in frame or frame['id'].isna().any() or not frame['id'].is_unique:
            raise ValueError(f'{name}: missing/duplicate IDs')
    if set(X.id) != set(labels.id):
        raise ValueError('Training feature IDs do not match label IDs')
    if set(X.id) & set(test.id):
        raise ValueError('Training and test IDs overlap')
    if set(X.columns) != set(test.columns) or 'status_group' in X:
        raise ValueError('Feature schema mismatch or target in feature data')
    y = labels.set_index('id').loc[X.id, 'status_group'].reset_index(drop=True)
    if y.isna().any() or set(y) != set(LABELS):
        raise ValueError('Unexpected or missing target labels')
    return X, y, test.loc[:, X.columns]


def sklearn_preprocessor():
    return ColumnTransformer([
        ('numeric', Pipeline([
            ('impute', SimpleImputer(strategy='median', add_indicator=True,
                                     keep_empty_features=True)),
            ('scale', StandardScaler()),
        ]), make_column_selector(dtype_include=np.number)),
        ('category', OneHotEncoder(handle_unknown='infrequent_if_exist',
                                  min_frequency=10, max_categories=200,
                                  sparse_output=True),
         make_column_selector(dtype_exclude=np.number)),
    ], sparse_threshold=1.0)


def build_models(X, threads=4):
    cleaned = PumpFeatures().fit_transform(X)
    cats = cleaned.select_dtypes(exclude=np.number).columns.tolist()
    models = {
        'majority': Pipeline([('features', PumpFeatures()),
                             ('model', DummyClassifier(strategy='most_frequent'))]),
        'logistic': Pipeline([('features', PumpFeatures()),
                              ('encode', sklearn_preprocessor()),
                              ('model', LogisticRegression(C=1.0, max_iter=1500,
                                                           solver='lbfgs', random_state=SEED))]),
        'random_forest': Pipeline([('features', PumpFeatures()),
                                   ('encode', sklearn_preprocessor()),
                                   ('model', RandomForestClassifier(
                                       n_estimators=240, max_depth=None,
                                       min_samples_leaf=2, max_features='sqrt',
                                       n_jobs=threads, random_state=SEED))]),
    }
    for depth, iterations in [(6, 650), (8, 850)]:
        models[f'catboost_depth{depth}'] = Pipeline([
            ('features', PumpFeatures()),
            ('model', CatBoostClassifier(
                iterations=iterations, depth=depth, learning_rate=0.07,
                loss_function='MultiClass', eval_metric='Accuracy',
                cat_features=cats, random_seed=SEED, thread_count=threads,
                verbose=False, allow_writing_files=False)),
        ])
    return models


def fit_and_evaluate(X_train, y_train, X_valid, y_valid, out_dir, threads=4):
    """Model selection uses training CV only. Holdout scores never select models."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    models = build_models(X_train, threads)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
    rows, fold_rows, fitted = [], [], {}
    for name, pipeline in models.items():
        started = time.perf_counter()
        print('CV', name, flush=True)
        scores = cross_validate(pipeline, X_train, y_train, cv=cv, n_jobs=1,
                                scoring={'accuracy': 'accuracy', 'macro_f1': 'f1_macro'},
                                error_score='raise')
        for fold in range(3):
            fold_rows.append({'model': name, 'fold': fold + 1,
                              'accuracy': scores['test_accuracy'][fold],
                              'macro_f1': scores['test_macro_f1'][fold]})
        pipeline.fit(X_train, y_train)
        pred = np.asarray(pipeline.predict(X_valid)).ravel()
        train_pred = np.asarray(pipeline.predict(X_train)).ravel()
        row = {'model': name, 'cv_accuracy_mean': float(scores['test_accuracy'].mean()),
               'cv_accuracy_std': float(scores['test_accuracy'].std(ddof=1)),
               'cv_macro_f1_mean': float(scores['test_macro_f1'].mean()),
               'train_accuracy': accuracy_score(y_train, train_pred),
               'validation_accuracy': accuracy_score(y_valid, pred),
               'validation_macro_f1': f1_score(y_valid, pred, average='macro'),
               'seconds': time.perf_counter() - started}
        rows.append(row)
        fitted[name] = pipeline
        # Checkpoint results so interrupted runs leave inspectable progress.
        pd.DataFrame(rows).to_csv(out_dir / 'model_comparison.csv', index=False)
        pd.DataFrame(fold_rows).to_csv(out_dir / 'cv_folds.csv', index=False)
        print(json.dumps(row), flush=True)
    comparison = pd.DataFrame(rows).sort_values('cv_accuracy_mean', ascending=False)
    comparison.to_csv(out_dir / 'model_comparison.csv', index=False)
    best_name = str(comparison.iloc[0]['model'])
    best = fitted[best_name]
    pred = np.asarray(best.predict(X_valid)).ravel()
    report = classification_report(y_valid, pred, labels=LABELS, output_dict=True,
                                   zero_division=0)
    (out_dir / 'classification_report.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    pd.DataFrame(confusion_matrix(y_valid, pred, labels=LABELS),
                 index=LABELS, columns=LABELS).to_csv(out_dir / 'confusion_matrix.csv')
    predictions = pd.DataFrame({'id': X_valid.id.to_numpy(), 'actual': y_valid.to_numpy(),
                                'prediction': pred})
    predictions.to_csv(out_dir / 'validation_predictions.csv', index=False)
    errors = X_valid.reset_index(drop=True).copy()
    errors['actual'] = y_valid.to_numpy()
    errors['prediction'] = pred
    errors.loc[errors.actual != errors.prediction].to_csv(out_dir / 'errors.csv', index=False)
    # Native CatBoost importance describes associations, not causal effects.
    if 'catboost' in best_name:
        importance = pd.DataFrame({
            'feature': best.named_steps['features'].transform(X_train).columns,
            'importance': best.named_steps['model'].get_feature_importance()})
        importance.sort_values('importance', ascending=False).to_csv(
            out_dir / 'feature_importance.csv', index=False)
    return comparison, best_name, best


def write_submission(model, X_test, output_path, template_path=None):
    pred = np.asarray(model.predict(X_test)).ravel()
    submission = pd.DataFrame({'id': X_test.id.to_numpy(), 'status_group': pred})
    if template_path is not None:
        template = pd.read_csv(template_path)
        if not template.id.is_unique or set(template.id) != set(X_test.id):
            raise ValueError('Submission template IDs mismatch')
        submission = submission.set_index('id').loc[template.id].reset_index()
    if submission.status_group.isna().any() or not set(submission.status_group) <= set(LABELS):
        raise ValueError('Invalid predictions')
    if len(submission) != len(X_test) or not submission.id.is_unique:
        raise ValueError('Invalid submission shape')
    submission.to_csv(output_path, index=False, encoding='utf-8')
    return submission


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data' / 'raw')
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'results')
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    X, y, test = load_data(args.data_dir)
    # The untouched 20% holdout is separated BEFORE any fitting or model search.
    train_ids, valid_ids = train_test_split(np.arange(len(X)), test_size=0.2,
                                           stratify=y, random_state=SEED)
    pd.DataFrame({'id': X.id, 'split': np.where(np.isin(np.arange(len(X)), valid_ids),
                                               'validation', 'train')}).to_csv(
        out / 'split_assignment.csv', index=False)
    comparison, best_name, best = fit_and_evaluate(
        X.iloc[train_ids], y.iloc[train_ids], X.iloc[valid_ids], y.iloc[valid_ids], out,
        threads=max(1, min(args.threads, 4)))
    # Parameters are now fixed. Refit on all labeled examples for test prediction.
    final = clone(best).fit(X, y)
    official_template = args.data_dir / 'SubmissionFormat.csv'
    template = official_template if official_template.exists() else args.data_dir / 'submission_format_derived.csv'
    submission = write_submission(final, test, out / 'submission.csv', template)
    # Save only the native CatBoost estimator plus explicit cleaning recipe.
    if 'catboost' in best_name:
        final.named_steps['model'].save_model(str(out / 'final_model.cbm'))
    metadata = {'seed': SEED, 'train_rows': len(train_ids), 'validation_rows': len(valid_ids),
                'all_labeled_rows': len(X), 'test_rows': len(test),
                'selected_model': best_name, 'selection_rule': 'highest training-only 3-fold CV accuracy',
                'platform': platform.platform(), 'python': platform.python_version(),
                'pandas': pd.__version__, 'numpy': np.__version__, 'sklearn': sklearn.__version__,
                'submission_sha256': hashlib.sha256((out / 'submission.csv').read_bytes()).hexdigest(),
                'submission_template': str(template.name), 'online_score': None}
    import catboost
    metadata['catboost'] = catboost.__version__
    (out / 'run_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print('SELECTED', best_name, flush=True)
    print(comparison.to_string(index=False), flush=True)
    print('SUBMISSION', submission.shape, flush=True)


if __name__ == '__main__':
    main()
