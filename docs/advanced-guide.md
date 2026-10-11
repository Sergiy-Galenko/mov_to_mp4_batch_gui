# Technical guide

## CLI mode

Run commands using the project's Python environment:

```sh
python main.py --cli --help
python main.py --cli -i input.mov -o ./converted --profile Balanced
python main.py --cli -i input.mov -o ./converted --target-size-mb 8 --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe
```

A target-size limit is decimal MB (1,000,000 bytes). Video target encoding uses CPU H.264, two passes, a container reserve, and verification before publishing. Oversized temporary outputs are discarded and retried at a lower bitrate; at most three complete attempts are made. Selecting an incompatible codec is a preflight error. Existing results are retained when an encode fails.

## Encoding and hardware

Outside Target size, available FFmpeg encoders and the selected hardware preference determine CPU or hardware encoding. Filters and resizing require re-encoding; compatible Fast Copy operations remux existing streams. ProRes uses MOV or MKV and does not support Target size.

## Whisper devices

OpenAI Whisper supports the available CPU, CUDA and MPS devices. Faster Whisper uses CPU/CUDA. The application can run Whisper in a managed isolated Python environment. Device choices come from that environment's verification report when it is active; otherwise the local runtime is queried. MPS with Faster Whisper is rejected explicitly.

## Portable data and configuration

Set `MEDIA_CONVERTER_PORTABLE_DIR` to use an isolated writable data root. Packaged portable builds use `portable.ini` and their adjacent `data` directory. Keep the settings, presets and history together when making a backup. JSON preset imports validate field names, types and allowed values; name collisions require an explicit policy.

## Troubleshooting

Check the selected interpreter, FFmpeg/FFprobe paths and logs first. A missing optional encoder or Whisper engine does not imply that the basic application dependencies are missing. For rendering problems, see [QML diagnostics](development.md#qml).
