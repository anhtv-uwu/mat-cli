#!/usr/bin/env python3
"""Build offline MAT bundles for any platform in bundle-lock.json."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / 'build'
LOCK = json.loads((ROOT / 'bundle-lock.json').read_text(encoding='utf-8'))


def host_platform(system=None, machine=None):
    system = (system or platform.system()).lower()
    machine = (machine or platform.machine()).lower()
    os_name = {'linux': 'linux', 'darwin': 'macos', 'windows': 'windows'}.get(system)
    arch = {'x86_64': 'x86_64', 'amd64': 'x86_64', 'aarch64': 'aarch64', 'arm64': 'aarch64'}.get(machine)
    name = f'{os_name}-{arch}'
    if name not in LOCK['platforms']:
        raise ValueError(f'Unsupported host {system}/{machine}; choose --platform explicitly for cross-packaging')
    return name


def digest(path, algorithm='sha256'):
    result = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def download(name, spec, target):
    suffix = '.zip' if spec['url'].endswith('.zip') else '.tar.gz'
    cache = BUILD / 'downloads' / target / (name + suffix)
    cache.parent.mkdir(parents=True, exist_ok=True)
    algorithm = 'sha512' if 'sha512' in spec else 'sha256'
    if not cache.exists():
        temporary = cache.with_suffix(cache.suffix + '.part')
        with urllib.request.urlopen(spec['url'], timeout=120) as src, temporary.open('wb') as dst:
            shutil.copyfileobj(src, dst)
        temporary.replace(cache)
    if digest(cache, algorithm) != spec[algorithm]:
        raise ValueError(f'Checksum mismatch: {cache}; remove it and retry')
    return cache


def extract_zip(path, destination):
    """Preserve Unix execute bits and links, without allowing paths outside staging."""
    destination = destination.resolve()
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError(f'Unsafe ZIP path: {member.filename}')
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                link = archive.read(member).decode('utf-8')
                if not (target.parent / link).resolve().is_relative_to(destination):
                    raise ValueError(f'Unsafe ZIP symlink: {member.filename}')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(link)
            else:
                archive.extract(member, destination)
                if mode & 0o777 and not member.is_dir():
                    permissions = mode & 0o777
                    # Unix archive modes can mark files read-only on Windows,
                    # preventing normal cleanup even when the user owns them.
                    if os.name == 'nt':
                        permissions |= stat.S_IWRITE
                    target.chmod(permissions)


def extract(path, destination):
    destination.mkdir(parents=True)
    if zipfile.is_zipfile(path):
        extract_zip(path, destination)
    else:
        with tarfile.open(path) as archive:
            archive.extractall(destination, filter='data')


def locate_mat(staging):
    candidates = [p.parent for p in staging.rglob('plugins')
                  if p.is_dir() and list(p.glob('org.eclipse.equinox.launcher_*.jar'))
                  and (p.parent / 'configuration/org.eclipse.equinox.simpleconfigurator/bundles.info').is_file()]
    if len(candidates) != 1:
        raise ValueError(f'Expected one MAT runtime, found {len(candidates)}')
    return candidates[0]


def locate_jre(staging, target):
    java_name = 'java.exe' if target.startswith('windows-') else 'java'
    candidates = [p.parent.parent for p in staging.rglob(java_name) if p.parent.name == 'bin']
    if len(candidates) != 1:
        raise ValueError(f'Expected one JRE runtime, found {len(candidates)}')
    return candidates[0]


def install_plugin(runtime, plugin):
    """Register the self-contained plugin without executing a target JVM.

    This is a standalone CLI bundle, not a p2-managed feature installation.
    The plugin's MAT version range is still enforced by OSGi when it starts.
    """
    config = runtime / 'configuration/org.eclipse.equinox.simpleconfigurator/bundles.info'
    with zipfile.ZipFile(plugin) as jar:
        manifest = jar.read('META-INF/MANIFEST.MF').decode('utf-8')
    version = next(line.split(': ', 1)[1].strip() for line in manifest.splitlines()
                   if line.startswith('Bundle-Version: '))
    filename = f'CliMatPlugin_{version}.jar'
    destination = runtime / 'plugins' / filename
    shutil.copy2(plugin, destination)
    lines = [line for line in config.read_text(encoding='utf-8').splitlines()
             if not line.startswith('CliMatPlugin,')]
    lines.append(f'CliMatPlugin,{version},plugins/{filename},4,false')
    config.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def inventory(bundle):
    rows = []
    for path in sorted(bundle.rglob('*')):
        if path.is_file() and path.name != 'SHA256SUMS':
            rows.append(f'{digest(path)}  {path.relative_to(bundle).as_posix()}')
    (bundle / 'SHA256SUMS').write_text('\n'.join(rows) + '\n', encoding='utf-8')


def package(bundle, target):
    if target.startswith('windows-'):
        archive = Path(shutil.make_archive(str(bundle), 'zip', bundle.parent, bundle.name))
    else:
        archive = bundle.with_suffix('.tar.gz')
        with tarfile.open(archive, 'w:gz') as stream:
            stream.add(bundle, arcname=bundle.name)
    archive.with_suffix(archive.suffix + '.sha256').write_text(
        f'{digest(archive)}  {archive.name}\n', encoding='utf-8')
    return archive


def assemble(target, output_dir, plugin):
    spec = LOCK['platforms'][target]
    bundle = output_dir / ('mat-cli-' + target)
    staging = output_dir / ('.staging-' + target)
    if bundle.exists() or staging.exists():
        raise ValueError(f'Output/staging already exists for {target}; move it away before rebuilding')
    mat = download('mat', spec['mat'], target)
    jre = download('jre', spec['jre'], target)
    extract(mat, staging / 'mat')
    extract(jre, staging / 'jre')
    runtime = locate_mat(staging / 'mat')
    java = locate_jre(staging / 'jre', target)
    bundle.mkdir(parents=True)
    shutil.copytree(runtime, bundle / 'mat', symlinks=True)
    shutil.copytree(java, bundle / 'jre', symlinks=True)
    install_plugin(bundle / 'mat', plugin)
    launchers = ('mat-cli.ps1', 'mat-cli.cmd') if target.startswith('windows-') else ('mat-cli',)
    for launcher in launchers:
        shutil.copy2(ROOT / 'scripts' / launcher, bundle / launcher)
    for name in ('README.md', 'LICENSE', 'NOTICE', 'SECURITY.md', 'bundle-lock.json'):
        shutil.copy2(ROOT / name, bundle / name)
    shutil.copytree(ROOT / 'docs', bundle / 'docs')
    (bundle / 'platform.json').write_text(json.dumps({'platform': target,
        'mat': LOCK['mat_version'], 'java': spec['jre']['version']}, indent=2) + '\n', encoding='utf-8')
    inventory(bundle)
    archive = package(bundle, target)
    shutil.rmtree(staging)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=sorted(LOCK['platforms']), help='Defaults to the host OS/architecture; cross-packaging is supported')
    parser.add_argument('--list-platforms', action='store_true')
    parser.add_argument('--output-dir', type=Path, default=BUILD)
    parser.add_argument('--plugin', type=Path, help='Built CliMatPlugin JAR; defaults to the Maven p2 repository output')
    args = parser.parse_args()
    if args.list_platforms:
        print('\n'.join(sorted(LOCK['platforms'])))
        return
    target = args.platform or host_platform()
    plugin = args.plugin
    if plugin is None:
        candidates = list((ROOT / 'CliMatRepository/target/repository/plugins').glob('CliMatPlugin_*.jar'))
        if len(candidates) != 1:
            parser.error('Run mvn verify first or supply exactly one --plugin JAR')
        plugin = candidates[0]
    if not plugin.is_file():
        parser.error(f'Plugin does not exist: {plugin}')
    try:
        print(assemble(target, args.output_dir.resolve(), plugin.resolve()))
    except ValueError as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
