"""Download original data and the template from DrivenData's public sources."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import base64
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
URLS = {
    'train_values.csv': 'https://s3.amazonaws.com/drivendata/data/7/public/4910797b-ee55-40a7-8668-10efd5c1b960.csv',
    'train_labels.csv': 'https://s3.amazonaws.com/drivendata/data/7/public/0bf8bc6e-30d0-4c50-956a-603fc693d966.csv',
    'test_values.csv': 'https://s3.amazonaws.com/drivendata/data/7/public/702ddfc5-68cd-4d1d-a0de-f5f566f76d91.csv',
    'SubmissionFormat.csv': 'https://api.github.com/repos/drivendataorg/pump-it-up/contents/data/submission_format.csv?ref=master',
}


def download():
    raw = ROOT / 'data' / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    manifest = {'downloaded_utc': datetime.now(timezone.utc).isoformat(), 'files': []}
    for name, url in URLS.items():
        path = raw / name
        if not path.exists():
            tmp = path.with_suffix('.part')
            request = urllib.request.Request(url, headers={'User-Agent': 'Pump-coursework-reference'})
            with urllib.request.urlopen(request, timeout=90) as response, tmp.open('wb') as f:
                if response.status != 200:
                    raise RuntimeError(f'Download failed: {url}')
                if name == 'SubmissionFormat.csv':
                    f.write(base64.b64decode(json.load(response)['content']))
                else:
                    while chunk := response.read(1024 * 1024):
                        f.write(chunk)
            tmp.replace(path)
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames
            rows = sum(1 for _ in reader)
        expected = 59400 if name.startswith('train_') else 14850
        if rows != expected or 'id' not in columns:
            raise ValueError(f'Unexpected schema/row count in {name}: {rows}')
        record = {'name': name, 'url': url, 'rows': rows, 'columns': columns,
                  'bytes': path.stat().st_size,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        manifest['files'].append(record)
        print(name, rows, 'rows', record['sha256'], flush=True)
    with (raw / 'test_values.csv').open(encoding='utf-8-sig', newline='') as f:
        ids = [int(row['id']) for row in csv.DictReader(f)]
    with (raw / 'SubmissionFormat.csv').open(encoding='utf-8-sig', newline='') as f:
        template_ids = [int(row['id']) for row in csv.DictReader(f)]
    if len(template_ids) != len(set(template_ids)) or set(ids) != set(template_ids):
        raise ValueError('Official template IDs do not match test data')
    manifest['submission_template'] = 'Official template published in drivendataorg/pump-it-up/data/submission_format.csv.'
    manifest['test_id_order_matches_official_template'] = ids == template_ids
    (raw / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    download()
