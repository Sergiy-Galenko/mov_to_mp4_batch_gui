# Development and verification

## Setup

Use Python 3.12+ and an isolated environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
```

On Windows, use `.venv\Scripts\python.exe`.

## Architecture

- `app/`: models, settings, preset validation and shared target-size units.
- `services/`: encoding, preflight, persistent stores and background work.
- `ui/backend_components/`: ordinary feature mixins, with a QObject facade in `impl.py`. Its explicit Qt interface exposes properties and slots to QML; runtime source assembly and `exec` are not used.
- `ui/qml/Main.qml`: window, navigation and screen integration.
- `ui/qml/components/SettingsPanel.qml`: persistent settings form.
- `ui/qml/components/PresetManagerPanel.qml`: shared preset controls.
- `tests/`: unit, QML and real FFmpeg integration tests.

Preserve signal notifications when refactoring the Qt interface. Keep controls alive across settings-page navigation so user values are retained.

## Checks

```sh
.venv/bin/python -m ruff check app services ui utils tests cli.py main.py
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app services ui utils tests
```

Tests use a temporary portable data root to avoid reading or writing personal configuration. Real encoder tests look for FFmpeg in PATH or `MEDIA_CONVERTER_TEST_FFMPEG`. Set `MEDIA_CONVERTER_REQUIRE_FFMPEG_TESTS=1` to fail if FFmpeg is missing; CI enables this on Linux, macOS and Windows. Integration tests cover two-pass progress, actual byte limits and bitrate correction after an oversized result.

## QML

Read the first error in a `QQmlApplicationEngine` failure chain: a later failure often follows an unresolved component or property. Run `tests/test_qml_load.py` to verify loading, navigation and property notifications. Run `tests/test_i18n.py` after changing translatable strings; all four dictionaries must contain each key.

## Screenshots

Existing screenshots live in `docs/images`. Use `scripts/capture_readme.py` with demonstration files; inspect the generated images before replacing published screenshots. Avoid personal file paths or media in screenshots. The README only references checked-in assets.

## Packaging

`scripts/build_pyinstaller.py` creates packaged builds. Its `--portable --ffmpeg-dir PATH` options include FFmpeg and enable portable data. Windows CI builds and checks a portable artifact. macOS CI currently runs lint, compilation and tests; it does not sign or notarize a distribution.
