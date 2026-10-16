"""Package the reference without virtual environments, caches or preview files."""
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parent
required = ['Pump_it_Up_课程样例.ipynb', 'output/pdf/Pump_it_Up_课程参考报告.pdf',
            '课程参考报告.html', 'results/submission.csv', 'results/audit.json',
            'results/model_comparison.csv', 'data/raw/manifest.json', 'requirements-lock.txt']
for name in required:
    if not (ROOT / name).is_file():
        raise FileNotFoundError(name)
if json.loads((ROOT / 'results/audit.json').read_text())['status'] != 'PASS':
    raise ValueError('Output audit did not pass')
nb = json.loads((ROOT / 'Pump_it_Up_课程样例.ipynb').read_text(encoding='utf-8'))
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        assert cell['execution_count'] is not None
        assert not any(o.get('output_type') == 'error' for o in cell['outputs'])
target = ROOT.parent / 'Pump_it_Up_课程参考样例.zip'
exclude = {'.git', '.venv', '.runtime', '.jupyter', '.ipython', '.mplconfig', '__pycache__', 'tmp'}
allowed_suffixes = {'.py', '.txt', '.md', '.ipynb', '.json', '.csv', '.png', '.pdf', '.html', '.cbm', '.log'}
with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT)
        if not path.is_file() or set(rel.parts) & exclude:
            continue
        if path.name == 'setup.log' or path.suffix not in allowed_suffixes:
            continue
        z.write(path, str(Path(ROOT.name) / rel))
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    print('PACKAGED', len(z.namelist()), 'files;', target.stat().st_size, 'bytes')
print(target)
