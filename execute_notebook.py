"""Execute with a project-local kernel spec; leave global Jupyter settings alone."""
from pathlib import Path
import os
import sys
import json
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent
kernel_dir = ROOT / '.jupyter' / 'kernels' / 'pump_reference'
kernel_dir.mkdir(parents=True, exist_ok=True)
(kernel_dir / 'kernel.json').write_text(json.dumps({
    'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
    'display_name': 'Pump reference project environment', 'language': 'python'}))
os.environ['JUPYTER_PATH'] = str(ROOT / '.jupyter')
os.environ['JUPYTER_RUNTIME_DIR'] = str(ROOT / '.jupyter' / 'runtime')
os.environ['IPYTHONDIR'] = str(ROOT / '.ipython')
path = ROOT / 'Pump_it_Up_课程样例.ipynb'
nb = nbformat.read(path, as_version=4)
NotebookClient(nb, timeout=7200, kernel_name='pump_reference',
               resources={'metadata': {'path': str(ROOT)}}, allow_errors=False).execute()
nb.metadata.kernelspec = {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}
nbformat.validate(nb)
nbformat.write(nb, path)
print('EXECUTED', path, len(nb.cells), 'cells', flush=True)
