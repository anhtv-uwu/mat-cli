# MAT CLI for agents

A source-based fork of [Appian CLIMAT](https://github.com/appian/cli-mat-plugin),
with the original interactive analysis plus a non-interactive JSON interface.
The Linux x86_64 all-in-one bundle includes **Eclipse MAT 1.17.0** and
**Temurin JRE 21.0.13+9**. After extraction, no system Java, Maven, GUI or network
is required. Other platforms are not bundled/tested yet.

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

Requirements: Linux x86_64, JDK 21, Maven 3.9.16, Python 3.12+, network for build.

```bash
mvn -B verify
python3 scripts/bundle.py
python3 scripts/smoke.py build/mat-cli-linux-x86_64/mat-cli
```

The bundle and archive appear under `build/`. The bundler refuses to overwrite
an existing bundle. Cached downloads are checked against [bundle-lock.json](bundle-lock.json).
Building does not install into or delete files from an existing MAT installation.
The original cleanup script and build-time automatic installation were removed.
Test frameworks are excluded from shipped dependencies. Maven uses the fixed
Eclipse 2026-06 and MAT 1.17 update sites rather than a moving `latest` site.
The bundle includes license files and a per-file SHA256SUMS inventory.

See [security scope](SECURITY.md) and [validation](docs/VALIDATION.md).
