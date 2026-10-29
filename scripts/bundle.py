#!/usr/bin/env python3
"""Assemble a Linux x86_64 offline runtime from pinned official archives."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / 'build'
LOCK = json.loads((ROOT / 'bundle-lock.json').read_text())

def download(name, spec):
    cache = BUILD / 'downloads' / name
    cache.parent.mkdir(parents=True, exist_ok=True)
    algorithm = 'sha512' if 'sha512' in spec else 'sha256'
    if not cache.exists():
        temporary = cache.with_suffix('.part')
        with urllib.request.urlopen(spec['url'], timeout=120) as src, temporary.open('wb') as dst:
            shutil.copyfileobj(src, dst)
        temporary.replace(cache)
    digest = hashlib.new(algorithm)
    with cache.open('rb') as src:
        for block in iter(lambda: src.read(1024 * 1024), b''):
            digest.update(block)
    if digest.hexdigest() != spec[algorithm]:
        raise SystemExit(f'Checksum mismatch: {cache}; remove it and retry')
    return cache

def main():
    repository = ROOT / 'CliMatRepository/target/repository'
    if not (repository / 'content.jar').exists() and not (repository / 'content.xml').exists():
        raise SystemExit('Run mvn verify before bundling')
    mat = download('mat.zip', LOCK['mat'])
    jre = download('jre.tar.gz', LOCK['jre'])
    bundle = BUILD / 'mat-cli-linux-x86_64'
    if bundle.exists():
        raise SystemExit(f'{bundle} already exists; move it away before rebuilding')
    bundle.mkdir(parents=True)
    with zipfile.ZipFile(mat) as archive:
        for member in archive.infolist():
            target = (bundle / member.filename).resolve()
            if not target.is_relative_to(bundle.resolve()):
                raise SystemExit('Unsafe ZIP path')
        archive.extractall(bundle)
    jre_stage = bundle / 'jre-stage'
    jre_stage.mkdir()
    with tarfile.open(jre) as archive:
        archive.extractall(jre_stage, filter='data')
    extracted = list(jre_stage.iterdir())
    if len(extracted) != 1 or not (extracted[0] / 'bin/java').is_file():
        raise SystemExit('Unexpected JRE archive layout')
    extracted[0].rename(bundle / 'jre')
    jre_stage.rmdir()
    launcher, = (bundle / 'mat/plugins').glob('org.eclipse.equinox.launcher_*.jar')
    subprocess.run([str(bundle / 'jre/bin/java'), '-jar', str(launcher), '-nosplash',
        '-application', 'org.eclipse.equinox.p2.director', '-repository', repository.as_uri(),
        '-installIU', 'CliMatFeature.feature.group', '-destination', str(bundle / 'mat'),
        '-bundlepool', str(bundle / 'mat'), '-roaming',
        '-configuration', str(bundle / 'mat/configuration')], check=True)
    # Local p2 repositories may be referenced through an OSGi cache. Keep our
    # runtime plugin in the stable plugins directory so cache cleanup is safe.
    config = bundle / 'mat/configuration/org.eclipse.equinox.simpleconfigurator/bundles.info'
    lines = config.read_text().splitlines()
    for index, line in enumerate(lines):
        if line.startswith('CliMatPlugin,'):
            fields = line.split(',')
            source = bundle / 'mat' / fields[2]
            destination = bundle / 'mat/plugins' / source.name
            if source != destination:
                shutil.copy2(source, destination)
            fields[2] = 'plugins/' + destination.name
            lines[index] = ','.join(fields)
    config.write_text('\n'.join(lines) + '\n')
    shutil.copy2(ROOT / 'scripts/mat-cli', bundle / 'mat-cli')
    for name in ('README.md', 'LICENSE', 'NOTICE', 'SECURITY.md', 'bundle-lock.json'):
        shutil.copy2(ROOT / name, bundle / name)
    shutil.copytree(ROOT / 'docs', bundle / 'docs')
    # Include auditable inventory; no heap dumps, tests or Maven caches.
    inventory = []
    for path in sorted(bundle.rglob('*')):
        if path.is_file():
            inventory.append(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(bundle)}')
    (bundle / 'SHA256SUMS').write_text('\n'.join(inventory) + '\n')
    archive_path = BUILD / 'mat-cli-linux-x86_64.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as archive:
        archive.add(bundle, arcname=bundle.name)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    archive_path.with_suffix(archive_path.suffix + '.sha256').write_text(f'{digest}  {archive_path.name}\n')
    print(archive_path)

if __name__ == '__main__':
    main()
