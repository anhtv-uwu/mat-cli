#!/usr/bin/env python3
"""Integration checks against a genuine, locally generated HPROF, never mocks."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

CLI = Path(sys.argv[1]).resolve()
ROOT = Path(__file__).resolve().parent.parent
checks = 0

def invoke(*args, status=0):
    global checks
    p = subprocess.run([str(CLI), *map(str, args)], capture_output=True, text=True, timeout=120)
    assert p.returncode == status, (args, p.returncode, p.stdout, p.stderr)
    result = json.loads(p.stdout)
    assert result['ok'] == (status == 0), result
    checks += 1
    return result.get('result')

with tempfile.TemporaryDirectory(prefix='mat cli smoke ') as work:
    heap = Path(work) / 'fixture with spaces.hprof'
    subprocess.run(['java', str(ROOT / 'scripts/HeapFixture.java'), str(heap)], check=True, timeout=60)
    info = invoke('info', heap)
    assert info['objects'] > 256 and info['usedHeapBytes'] > 128 * 4096
    hist = invoke('histogram', heap, '--limit', 3)
    assert len(hist['rows']) == 3 and hist['total'] > 3
    assert hist['rows'][0]['shallowBytes'] >= hist['rows'][1]['shallowBytes']
    second = invoke('histogram', heap, '--limit', 3, '--offset', 3)
    assert second['offset'] == 3 and second['rows'] != hist['rows']
    assert invoke('histogram', heap, '--offset', 2147483647)['rows'] == []
    objects = invoke('oql', heap, 'SELECT * FROM java.lang.String', '--limit', 2)
    assert len(objects['rows']) == 2
    addr = objects['rows'][0]['address']
    assert invoke('object', heap, addr)['address'] == addr
    invoke('references', heap, addr)
    invoke('references', heap, addr, '--incoming')
    invoke('gc-roots', heap, addr, '--limit', 5)
    assert invoke('dominators', heap, '--limit', 3)['rows']
    assert invoke('threads', heap, '--limit', 3)['rows']
    assert invoke('query', heap, 'histogram', '--limit', 3)['rows']
    assert invoke('oql', heap, 'SELECT s.toString() FROM java.lang.String s', '--limit', 2)['rows']
    invoke('info', heap, '--limit', 0, status=2)
    invoke('info', heap, '--offset', -1, status=2)
    invoke('info', heap, '--limit', status=2)
    invoke('info', heap, '--wat', status=2)
    invoke('object', heap, 'wat', status=2)
    invoke('object', heap, status=2)
    invoke('info', Path(work) / 'missing.hprof', status=2)
    invoke('wat', heap, status=2)
    invoke('query', heap, 'not_a_real_mat_query', status=1)
    invoke('oql', heap, 'not oql', status=1)
    broken = Path(work) / 'broken.hprof'
    broken.write_bytes(b'not an hprof')
    invoke('info', broken, status=1)
    help_run = subprocess.run([str(CLI), '--help'], capture_output=True, text=True, timeout=30)
    assert help_run.returncode == 0 and 'histogram' in help_run.stdout
    checks += 1
    # EOF must exit the original menu without hanging or a stack trace.
    legacy = subprocess.run([str(CLI), 'legacy', str(heap), '-c'], input='', capture_output=True, text=True, timeout=120)
    assert legacy.returncode == 0 and 'NoSuchElementException' not in legacy.stderr, legacy.stderr
    checks += 1
    report = subprocess.run([str(CLI), 'legacy', str(heap)], capture_output=True, text=True, timeout=120)
    reports = list(Path(work).glob('climat_results_*.txt'))
    assert report.returncode == 0 and reports and reports[0].stat().st_size > 0, (report.stdout, report.stderr)
    checks += 1
print(f'{checks} integration checks passed on MAT 1.17')
