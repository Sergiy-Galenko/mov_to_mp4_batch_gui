"""Subtitle editing and source/output time mapping. All operations return new values."""

from __future__ import annotations

import math
import re
import uuid
from itertools import pairwise


def seconds(value) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Time must be a finite, non-negative number")
    return round(result, 3)


def normalize_cues(cues: list, duration: float | None = None) -> list[dict]:
    result = []
    for cue in cues:
        start, end = seconds(cue["start"]), seconds(cue["end"])
        if duration is not None:
            end = min(end, seconds(duration))
        if end <= start:
            raise ValueError("Subtitle end must be after its start and within the video")
        entry = {
            "id": str(cue.get("id") or uuid.uuid4().hex),
            "start": start,
            "end": end,
            "text": str(cue.get("text", "")).replace("\x00", ""),
        }
        if cue.get("words"):
            entry["words"] = [
                {"start": seconds(word["start"]), "end": seconds(word["end"]), "word": str(word["word"])} for word in cue["words"]
            ]
        result.append(entry)
    return sorted(result, key=lambda cue: (cue["start"], cue["end"]))


def timestamp(value: float, separator=",") -> str:
    millis = round(seconds(value) * 1000)
    hours, remainder = divmod(millis, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    sec, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{sec:02}{separator}{millis:03}"


def parse_timestamp(text: str) -> float:
    parts = text.strip().replace(",", ".").split(":")
    if len(parts) not in {2, 3}:
        raise ValueError("Invalid subtitle timestamp")
    values = [seconds(part) for part in parts]
    if values[-1] >= 60 or values[-2] >= 60:
        raise ValueError("Invalid subtitle timestamp")
    return sum(value * 60**index for index, value in enumerate(reversed(values)))


def parse_subtitles(text: str) -> list[dict]:
    cues = []
    for block in re.split(r"\n\s*\n", text.lstrip("\ufeff").replace("\r\n", "\n").strip()):
        lines = block.splitlines()
        if not lines or lines[0].startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        for index, line in enumerate(lines):
            if "-->" in line:
                start, end = line.split("-->", 1)
                cues.append(
                    {"start": parse_timestamp(start), "end": parse_timestamp(end.strip().split()[0]), "text": "\n".join(lines[index + 1 :])}
                )
                break
    if not cues:
        raise ValueError("No valid SRT/VTT subtitles found")
    return normalize_cues(cues)


def serialize_subtitles(cues: list, fmt="srt") -> str:
    if fmt not in {"srt", "vtt"}:
        raise ValueError("Choose SRT or VTT")
    blocks = []
    for index, cue in enumerate(normalize_cues(cues), 1):
        separator = "." if fmt == "vtt" else ","
        blocks.append(f"{index}\n{timestamp(cue['start'], separator)} --> {timestamp(cue['end'], separator)}\n{cue['text']}")
    return ("WEBVTT\n\n" if fmt == "vtt" else "") + "\n\n".join(blocks) + "\n"


def split_cue(cues: list, cue_id: str, at: float, cursor: int) -> list[dict]:
    result = normalize_cues(cues)
    cue = next(item for item in result if item["id"] == cue_id)
    at = seconds(at)
    if not cue["start"] < at < cue["end"]:
        raise ValueError("Place the playhead inside the selected subtitle")
    # QML TextEdit cursor positions count UTF-16 code units, not Python code points.
    encoded = cue["text"].encode("utf-16-le")
    left = encoded[: cursor * 2].decode("utf-16-le", errors="ignore").strip()
    right = encoded[cursor * 2 :].decode("utf-16-le", errors="ignore").strip()
    if not left or not right:
        raise ValueError("Place the text cursor between the words to split")
    result.remove(cue)
    cue.pop("words", None)
    result.extend([{**cue, "end": at, "text": left}, {**cue, "id": uuid.uuid4().hex, "start": at, "text": right}])
    return normalize_cues(result)


def merge_cues(cues: list, cue_id: str) -> list[dict]:
    result = normalize_cues(cues)
    index = next(i for i, item in enumerate(result) if item["id"] == cue_id)
    if index + 1 >= len(result):
        raise ValueError("Select a subtitle with a following cue")
    first, second = result[index : index + 2]
    result[index : index + 2] = [
        {**first, "end": max(first["end"], second["end"]), "text": first["text"].rstrip() + " " + second["text"].lstrip()}
    ]
    result[index].pop("words", None)
    return result


def kept_ranges(duration: float, removed: list, start=0.0, end=None) -> list[list[float]]:
    limit = seconds(duration)
    start = min(seconds(start), limit)
    end = min(seconds(end), limit) if end is not None else limit
    if end <= start:
        raise ValueError("The selected video range is empty")
    cuts = sorted((max(start, seconds(pair[0])), min(end, seconds(pair[1]))) for pair in removed)
    result, cursor = [], start
    for left, right in cuts:
        if right <= left:
            continue
        if left > cursor:
            result.append([cursor, left])
        cursor = max(cursor, right)
    if cursor < end:
        result.append([cursor, end])
    return result


def word_cut(words: list, first: int, last: int) -> list[float]:
    if not 0 <= first <= last < len(words):
        raise ValueError("Select one or more timed words")
    selected = words[first : last + 1]
    start = min(seconds(word["start"]) for word in selected)
    end = max(seconds(word["end"]) for word in selected)
    if end <= start:
        raise ValueError("The selected words have no valid timing")
    return [start, end]


def retime_cues(cues: list, ranges: list) -> list[dict]:
    result, offset = [], 0.0
    for start, end in ranges:
        for cue in normalize_cues(cues):
            left, right = max(start, cue["start"]), min(end, cue["end"])
            if right > left:
                text = cue["text"]
                if cue.get("words"):
                    text = " ".join(word["word"].strip() for word in cue["words"] if left <= (word["start"] + word["end"]) / 2 < right)
                    if not text:
                        continue
                result.append(
                    {
                        **cue,
                        "id": uuid.uuid4().hex,
                        "start": round(offset + left - start, 3),
                        "end": round(offset + right - start, 3),
                        "text": text,
                    }
                )
        offset += end - start
    return result


def scenes_from_timestamps(timestamps: list, duration: float, minimum=0.5) -> list[dict]:
    duration = seconds(duration)
    minimum = max(0.1, seconds(minimum))
    boundaries = [0.0]
    for time in sorted(set(seconds(value) for value in timestamps)):
        if time - boundaries[-1] >= minimum and duration - time >= minimum:
            boundaries.append(time)
    boundaries.append(duration)
    return [{"start": a, "end": b, "selected": True} for a, b in pairwise(boundaries) if b > a]
