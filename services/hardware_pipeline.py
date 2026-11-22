"""Hardware frame paths with explicit CPU-filter bridges and reversible fallback."""

from __future__ import annotations

import glob
import re
import sys


def vaapi_device() -> str | None:
    devices = sorted(glob.glob("/dev/dri/renderD*")) if sys.platform.startswith("linux") else []
    return devices[0] if devices else None


def configure_pipeline(command: list[str], encoder: str, info, filters: set[str], *, device: str | None = None) -> list[str]:
    result = list(command)
    is_vaapi = encoder.endswith("_vaapi")
    device = device or vaapi_device() if is_vaapi else None
    if is_vaapi and not device:
        raise ValueError("VA-API render device is unavailable")
    # Generic complex graphs continue on CPU; VA-API still needs an output upload.
    complex_graph = "-filter_complex" in result
    chain = result[result.index("-vf") + 1] if "-vf" in result else ""
    simple_scale = re.fullmatch(r"scale=(-?\d+):(-?\d+)", chain)
    compatible = bool(
        info
        and info.vcodec in {"h264", "hevc", "vp9", "av1", "mpeg2video"}
        and info.pix_fmt in {"yuv420p", "nv12"}
        and info.rotation in {None, 0}
        and info.dynamic_range != "HDR"
        and not complex_graph
        and (not chain or simple_scale)
    )
    if encoder.endswith("_nvenc"):
        backend, scaler, pixel = "cuda", "scale_cuda", "cuda"
    elif encoder.endswith("_qsv"):
        backend, scaler, pixel = "qsv", "scale_qsv", "qsv"
    elif is_vaapi:
        backend, scaler, pixel = "vaapi", "scale_vaapi", "vaapi"
    else:
        # VideoToolbox/AMF retain their verified encoding paths; no unsupported
        # claim that arbitrary software filters can consume their hardware frames.
        return result
    accelerated = compatible and (not chain or scaler in filters)
    if accelerated:
        options = ["-hwaccel", backend, "-hwaccel_output_format", pixel]
        if is_vaapi:
            options += ["-hwaccel_device", device]
        position = result.index("-i")
        result[position:position] = options
        if simple_scale:
            result[result.index("-vf") + 1] = f"{scaler}={simple_scale[1]}:{simple_scale[2]}:format=nv12"
        elif is_vaapi and "scale_vaapi" in filters:
            result[-1:-1] = ["-vf", "scale_vaapi=format=nv12"]
        if "-pix_fmt" in result:
            result[result.index("-pix_fmt") + 1] = pixel
    elif is_vaapi:
        result[2:2] = ["-vaapi_device", device]
        upload = "format=nv12,hwupload"
        if complex_graph:
            index = result.index("-map") + 1
            label = result[index]
            if not label.startswith("["):
                raise ValueError("VA-API complex filter output is missing")
            graph_index = result.index("-filter_complex") + 1
            result[graph_index] += f";{label}{upload}[hardware_output]"
            result[index] = "[hardware_output]"
        elif "-vf" in result:
            result[result.index("-vf") + 1] += "," + upload
        else:
            result[-1:-1] = ["-vf", upload]
        if "-pix_fmt" in result:
            result[result.index("-pix_fmt") + 1] = "vaapi"
        else:
            result[-1:-1] = ["-pix_fmt", "vaapi"]
    return result


def software_pipeline(command: list[str]) -> list[str]:
    """Strip device options and turn supported hardware graphs into software graphs."""
    result = []
    skip = False
    for argument in command:
        if skip:
            skip = False
            continue
        if argument in {"-hwaccel", "-hwaccel_output_format", "-hwaccel_device", "-vaapi_device", "-filter_hw_device", "-init_hw_device"}:
            skip = True
            continue
        result.append(argument)
    for flag in ("-vf", "-filter_complex"):
        if flag not in result:
            continue
        index = result.index(flag) + 1
        graph = result[index]
        graph = re.sub(r"scale_(?:cuda|qsv|vaapi)=(-?\d+):(-?\d+):format=nv12", r"scale=\1:\2", graph)
        graph = graph.replace("scale_vaapi=format=nv12", "format=yuv420p")
        graph = graph.replace("format=nv12,hwupload", "format=yuv420p")
        result[index] = graph
    if "-pix_fmt" in result and result[result.index("-pix_fmt") + 1] in {"vaapi", "cuda", "qsv"}:
        result[result.index("-pix_fmt") + 1] = "yuv420p"
    return result
