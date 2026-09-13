"""Optional Rust extension; source checkouts remain usable without a compiler."""

import os
from contextlib import suppress

native = None
if os.environ.get("MEDIA_CONVERTER_DISABLE_NATIVE", "").lower() not in {"1", "true", "yes"}:
    # Missing wheel, unsupported architecture, or an unavailable shared runtime.
    with suppress(ImportError, OSError):
        import media_converter_native as native

NATIVE_AVAILABLE = native is not None
