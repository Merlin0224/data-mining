"""Run the entire measured experiment, notebook and output audit."""
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import subprocess
import sys

root = Path(__file__).resolve().parent
env = os.environ.copy()
env.update({name: '4' for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                  'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']})
env['MPLCONFIGDIR'] = str(root / '.mplconfig')
status = {'started_utc': datetime.now(timezone.utc).isoformat(), 'completed': []}
for script in ['pump_model.py', 'execute_notebook.py', 'verify_outputs.py']:
    status['current'] = script
    (root / 'pipeline_status.json').write_text(json.dumps(status, indent=2))
    print('START', script, flush=True)
    result = subprocess.run([sys.executable, '-u', str(root / script)], cwd=root, env=env)
    if result.returncode:
        status.update({'status': 'FAILED', 'returncode': result.returncode})
        (root / 'pipeline_status.json').write_text(json.dumps(status, indent=2))
        raise SystemExit(result.returncode)
    status['completed'].append(script)
status.update({'status': 'PASS', 'finished_utc': datetime.now(timezone.utc).isoformat()})
(root / 'pipeline_status.json').write_text(json.dumps(status, indent=2))
with (root / 'requirements-lock.txt').open('w') as f:
    subprocess.run(['/usr/bin/pip', '--python', sys.executable, 'freeze'], stdout=f, check=True)
print('ALL COMPLETE', flush=True)
