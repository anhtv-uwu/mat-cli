#!/usr/bin/env python3
"""Native smoke checks against a relocated, checksummed release archive."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import bundle


def main():
    target = sys.argv[1]
    assert target == bundle.host_platform(), (target, bundle.host_platform())
    plugin, = (bundle.BUILD / 'plugin').glob('CliMatPlugin_*.jar')
    output = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else bundle.BUILD
    archive = bundle.assemble(target, output, plugin)
    with tempfile.TemporaryDirectory(prefix='mat cli relocated ') as temporary:
        staging = Path(temporary)
        bundle.extract(archive, staging / 'unpacked')
        runtime = staging / 'unpacked' / ('mat-cli-' + target)
        for line in (runtime / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
            expected, name = line.split('  ', 1)
            assert bundle.digest(runtime / name) == expected, name
        cache = runtime / 'mat/configuration/org.eclipse.osgi'
        if cache.exists():
            shutil.rmtree(cache)
        cli = runtime / ('mat-cli.ps1' if os.name == 'nt' else 'mat-cli')
        subprocess.run([sys.executable, str(bundle.ROOT / 'scripts/smoke.py'), str(cli)], check=True)
    print(f'Native archive/relocation verification passed: {target}')


if __name__ == '__main__':
    main()
