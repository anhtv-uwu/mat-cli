# MAT CLI for agents

A source-based fork of [Appian CLIMAT](https://github.com/appian/cli-mat-plugin),
with the original interactive analysis plus a non-interactive JSON interface.
All-in-one bundles include **Eclipse MAT 1.17.0** and a pinned **Temurin JRE 21**
for the selected OS/CPU. After extraction, no system Java, Maven, GUI or runtime
network download is required.

| Platform | Bundle | Launcher |
| --- | --- | --- |
| Linux x86_64 (glibc) | `mat-cli-linux-x86_64.tar.gz` | `./mat-cli` |
| Linux ARM64 (glibc) | `mat-cli-linux-aarch64.tar.gz` | `./mat-cli` |
| macOS Intel | `mat-cli-macos-x86_64.tar.gz` | `./mat-cli` |
| macOS Apple Silicon | `mat-cli-macos-aarch64.tar.gz` | `./mat-cli` |
| Windows x64 | `mat-cli-windows-x86_64.zip` | `mat-cli.cmd` or `mat-cli.ps1` |

Each target has a native CI job that tests its extracted archive, including a
bundle directory and heap filename with spaces, JSON, Unicode, quoted OQL and
error exit codes. Check the workflow result for the release commit: configured
matrix entries alone are not evidence of a passing native test. See
[platform validation](docs/PLATFORMS.md). Windows ARM64, Linux musl/Alpine and
other architectures are not covered by these bundles.

Download the archive and checksum from [GitHub Releases](https://github.com/anhtv-uwu/mat-cli/releases).

## Use the bundle

```bash
tar -xzf mat-cli-linux-x86_64.tar.gz
cd mat-cli-linux-x86_64
./mat-cli --help
./mat-cli info /absolute/path/app.hprof
./mat-cli histogram /absolute/path/app.hprof --limit 20
./mat-cli dominators /absolute/path/app.hprof --offset 0 --limit 20
./mat-cli object /absolute/path/app.hprof 0x12345678
./mat-cli references /absolute/path/app.hprof 0x12345678 --incoming
./mat-cli gc-roots /absolute/path/app.hprof 0x12345678
./mat-cli threads /absolute/path/app.hprof --limit 20
./mat-cli oql /absolute/path/app.hprof 'SELECT * FROM java.lang.String' --limit 10
./mat-cli query /absolute/path/app.hprof 'histogram' --limit 20
MAT_CLI_HEAP=4g ./mat-cli info /absolute/path/app.hprof
```

Stdout contains a JSON envelope: `{"ok":true,"command":"info","result":...}`.
Progress goes to stderr. Exit codes: `0` success, `2` invalid arguments,
`1` analysis failure. Pages contain `rows`, `total`, `offset`, `limit`.
Default limit 100; maximum 10000. Histogram sorts by shallow heap descending;
dominators returns MAT's root-level dominators; tree queries return top-level
rows. GC roots returns the first shortest path in object-to-root order.
Generic MAT query results that are not tables/trees/lists use a text fallback.
Each invocation opens/disposes one snapshot; indexes speed up later calls.
Use a process timeout and increase MAT_CLI_HEAP for large dumps.

## Original CLIMAT interface

```bash
./mat-cli legacy /absolute/path/app.hprof -c  # interactive menu
./mat-cli legacy /absolute/path/app.hprof     # full report beside heap
./mat-cli legacy /absolute/path/app.hprof -i 0x12345678
```

Includes leak suspects, histogram, dominator tree, OQL, object/class reference
navigation, arrays/collections/strings, thread analysis and extension points.
See [upstream documentation](docs/UPSTREAM.md) for the original feature guide.
Legacy output is text and preserves upstream behavior, including error handling;
use the new commands when an agent needs reliable JSON and exit codes.

## Build

Requirements: JDK 21, Maven 3.9.16, Python 3.12+, network for build.
The Java plugin is built once and shared across platforms. Bundling works on
Linux, macOS and Windows and defaults to the host OS/architecture.

```bash
mvn -B verify
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 scripts/bundle.py --list-platforms
python3 scripts/bundle.py                       # auto-detect host
python3 scripts/bundle.py --platform macos-aarch64  # cross-package, no target JVM execution
# Supply --output-dir for a separate build directory, or --plugin for a prebuilt plugin JAR.
# Smoke-test on the native target, using its launcher:
python3 scripts/smoke.py build/mat-cli-linux-x86_64/mat-cli
```

The bundle and archive appear under `build/`. The bundler refuses to overwrite
an existing bundle. Cached downloads are checked against [bundle-lock.json](bundle-lock.json).
Building does not install into or delete files from an existing MAT installation.
The original cleanup script and build-time automatic installation were removed.
Test frameworks are excluded from shipped dependencies. Maven uses the fixed
Eclipse 2026-06 and MAT 1.17 update sites rather than a moving `latest` site.
The bundle includes license files and a per-file SHA256SUMS inventory.

On Windows, extract the ZIP and run from PowerShell or Command Prompt:

```powershell
.\mat-cli.cmd info 'C:\heap dumps\app.hprof'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\mat-cli.ps1 histogram 'C:\heap dumps\app.hprof' --limit 20
$env:MAT_CLI_HEAP = '4g'
```

JSON strings use standard Unicode escapes so Windows console code pages cannot
change the returned data. The Windows launcher transports Unicode arguments as
UTF-8/Base64, then the application decodes them before normal option parsing and
resolves relative heap paths against the caller's working directory. No script
or expression is evaluated by that transport. Extract the Windows bundle into
an ASCII-only installation path to avoid Java 21 native launcher path limitations;
heap paths and OQL values can contain Unicode.

The CMD wrapper uses the Windows-provided PowerShell, with a process-local
execution policy; it does not change the machine policy. The PowerShell launcher
quotes native JVM arguments explicitly, including embedded quotes in OQL.
macOS archives are CLI bundles, not signed/notarized application installers.

The bundler registers the self-contained plugin in MAT's bundle list without
running a target JVM or modifying a separate MAT installation. These CLI bundles
are not p2-managed feature installations. Build jobs still produce a p2 repository
for users who want to manage a plugin separately.

See [security scope](SECURITY.md) and [validation](docs/VALIDATION.md).
