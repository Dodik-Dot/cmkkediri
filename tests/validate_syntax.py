"""Validate source according to its shebang, without executing host checks."""
import ast
from pathlib import Path
import subprocess

root = Path(__file__).parents[1]
paths = [root / 'linux/install.sh', *sorted((root / 'linux/local_checks').glob('*.sh')),
         root / 'linux/plugins/mk_inventory.linux']
for path in paths:
    source = path.read_text()
    if 'python' in source.splitlines()[0]:
        ast.parse(source, filename=str(path))
    else:
        subprocess.run(['bash', '-n', str(path)], check=True)
print(f'Syntax: {len(paths)} Linux sources passed (shebang-aware)')
