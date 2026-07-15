#!/usr/bin/env python3
"""Render chord symbols to a piano-like WAV and/or General MIDI file."""

from __future__ import annotations

import argparse
from array import array
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import wave


NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ALTERATIONS = {
    "b5": 6,
    "#5": 8,
    "b9": 13,
    "9": 14,
    "#9": 15,
    "b11": 16,
    "11": 17,
    "#11": 18,
    "b13": 20,
    "13": 21,
    "#13": 22,
}
RESTS = {"n.c.", "n.c", "nc", "rest", "r", "-"}


class ChordError(ValueError):
    pass


def note_pc(letter: str, accidental: str = "") -> int:
    pc = NOTE_PC[letter.upper()]
    if accidental in ("#", "♯"):
        pc += 1
    elif accidental in ("b", "♭"):
        pc -= 1
    return pc % 12


def normalize_symbol(symbol: str) -> str:
    return (
        symbol.strip()
        .replace("♭", "b")
        .replace("♯", "#")
        .replace("−", "-")
        .replace("–", "-")
        .replace("△", "Δ")
    )


def replace_degree(intervals: list[int], old: tuple[int, ...], new: int) -> None:
    for value in old:
        while value in intervals:
            intervals.remove(value)
    intervals.append(new)


def parse_chord(symbol: str) -> dict:
    raw = normalize_symbol(symbol)
    if raw.lower() in RESTS:
        return {"symbol": symbol, "rest": True, "intervals": [], "root_pc": 0, "bass_pc": None}

    match = re.fullmatch(r"([A-Ga-g])([#b]?)([^/]*?)(?:/([A-Ga-g])([#b]?))?", raw)
    if not match:
        raise ChordError(f"无法解析和弦：{symbol}")

    letter, accidental, quality, bass_letter, bass_accidental = match.groups()
    root = note_pc(letter, accidental)
    bass = note_pc(bass_letter, bass_accidental or "") if bass_letter else None
    quality = quality.strip()
    compact = quality.replace(" ", "")
    lower = compact.lower()
    base_quality = re.sub(r"\([^)]*\)", "", compact)
    base_lower = base_quality.lower()

    half_dim = "ø" in compact or "m7-5" in lower or "m7b5" in lower
    diminished = ("dim" in base_lower or "°" in base_quality) and not half_dim
    augmented = "aug" in base_lower or base_quality.startswith("+")
    sus2 = "sus2" in base_lower
    sus4 = "sus4" in base_lower or ("sus" in base_lower and not sus2)
    minor = (
        (base_quality.startswith("m") and not base_quality.startswith("maj"))
        or base_lower.startswith("min")
    ) and not half_dim

    if half_dim:
        intervals = [0, 3, 6, 10]
    elif diminished:
        intervals = [0, 3, 6]
    elif augmented:
        intervals = [0, 4, 8]
    elif sus2:
        intervals = [0, 2, 7]
    elif sus4:
        intervals = [0, 5, 7]
    elif minor:
        intervals = [0, 3, 7]
    else:
        intervals = [0, 4, 7]

    minor_major = bool(re.search(r"m(?:maj|M|Δ)7", compact))
    major_seven = (
        minor_major
        or "maj7" in base_lower
        or "maj9" in base_lower
        or "maj11" in base_lower
        or "maj13" in base_lower
        or "M7" in base_quality
        or "M9" in base_quality
        or "Δ" in base_quality
    )
    add9 = "add9" in base_lower

    if "dim7" in base_lower or "°7" in base_quality:
        intervals.append(9)
    elif major_seven:
        intervals.append(11)
    elif re.search(r"(?<!add)(7|9|11|13)", base_lower) and not half_dim:
        intervals.append(10)

    if re.search(r"(?:^|[^0-9])6(?![0-9])", base_lower) and "13" not in base_lower:
        intervals.append(9)
    if add9:
        intervals.append(14)
    elif "13" in base_lower:
        intervals.extend([14, 17, 21])
    elif "11" in base_lower:
        intervals.extend([14, 17])
    elif "9" in base_lower:
        intervals.append(14)

    for group in re.findall(r"\(([^)]*)\)", compact):
        for item in group.split(","):
            item = item.strip()
            if item in ALTERATIONS:
                degree = item.lstrip("b#")
                if degree == "5":
                    replace_degree(intervals, (6, 7, 8), ALTERATIONS[item])
                elif degree == "9":
                    replace_degree(intervals, (13, 14, 15), ALTERATIONS[item])
                elif degree == "11":
                    replace_degree(intervals, (16, 17, 18), ALTERATIONS[item])
                elif degree == "13":
                    replace_degree(intervals, (20, 21, 22), ALTERATIONS[item])

    intervals = sorted(set(intervals))
    if len(intervals) > 6:
        removable = [7, 17, 14]
        for tone in removable:
            if len(intervals) <= 6:
                break
            if tone in intervals:
                intervals.remove(tone)

    return {
        "symbol": symbol,
        "rest": False,
        "root_pc": root,
        "bass_pc": bass,
        "intervals": intervals,
    }


def parse_progression(text: str, default_beats: float) -> list[tuple[dict, float]]:
    tokens = [token for token in re.split(r"[|\s]+", text.strip()) if token]
    if not tokens:
        raise ChordError("和弦进行不能为空")
    result = []
    for token in tokens:
        beats = default_beats
        duration_match = re.fullmatch(r"(.+):([0-9]+(?:\.[0-9]+)?)", token)
        if duration_match:
            token, beats_text = duration_match.groups()
            beats = float(beats_text)
        if beats <= 0:
            raise ChordError(f"持续拍数必须大于零：{token}")
        result.append((parse_chord(token), beats))
    return result


def midi_for_pc(pc: int, octave: int) -> int:
    return 12 * (octave + 1) + pc


def root_position(chord: dict, octave: int) -> list[int]:
    root = midi_for_pc(chord["root_pc"], octave)
    return [root + interval for interval in chord["intervals"]]


def candidate_voicings(chord: dict, octave: int) -> list[list[int]]:
    base = root_position(chord, octave)
    candidates = []
    for inversion in range(len(base)):
        inverted = base[inversion:] + [note + 12 for note in base[:inversion]]
        for shift in (-12, 0, 12):
            candidate = sorted(note + shift for note in inverted)
            if min(candidate) >= 48 and max(candidate) <= 84:
                candidates.append(candidate)
    return candidates or [base]


def voicing_cost(candidate: list[int], previous: list[int] | None) -> float:
    center_penalty = abs(sum(candidate) / len(candidate) - 64) * 0.25
    span_penalty = max(0, candidate[-1] - candidate[0] - 19) * 0.6
    if not previous:
        return center_penalty + span_penalty
    a = candidate
    b = previous
    movement = 0.0
    for index, note in enumerate(a):
        ref = b[min(index, len(b) - 1)]
        movement += abs(note - ref)
    movement += abs(len(a) - len(b)) * 3
    return movement + center_penalty + span_penalty


def choose_voicing(chord: dict, style: str, octave: int, previous: list[int] | None) -> list[int]:
    if style == "root":
        return root_position(chord, octave)
    if style == "spread":
        notes = root_position(chord, octave)
        if len(notes) >= 3:
            notes[0] -= 12
            notes[2] += 12
        return sorted(notes)
    return min(candidate_voicings(chord, octave), key=lambda item: voicing_cost(item, previous))


def bass_note(chord: dict, bass_octave: int) -> int:
    pc = chord["bass_pc"] if chord["bass_pc"] is not None else chord["root_pc"]
    return midi_for_pc(pc, bass_octave)


def schedule_chord(
    events: list[tuple[float, float, int, int]],
    chord: dict,
    start: float,
    beats: float,
    upper: list[int],
    pattern: str,
    velocity: int,
    use_bass: bool,
    bass_octave: int,
) -> None:
    if chord["rest"]:
        return
    bass = bass_note(chord, bass_octave)
    upper_velocity = max(1, velocity)
    bass_velocity = max(1, velocity - 8)

    if pattern == "block":
        notes = ([bass] if use_bass else []) + upper
        for note in notes:
            events.append((start, beats * 0.90, note, bass_velocity if note == bass else upper_velocity))
    elif pattern == "arpeggio":
        notes = ([bass] if use_bass else []) + upper
        step = 0.5
        count = max(1, int(math.ceil(beats / step)))
        for index in range(count):
            when = start + index * step
            if when >= start + beats:
                break
            events.append((when, min(step * 1.7, start + beats - when), notes[index % len(notes)], upper_velocity))
    elif pattern == "broken":
        for beat in range(int(math.ceil(beats))):
            when = start + beat
            if when >= start + beats:
                break
            if use_bass:
                events.append((when, min(0.8, start + beats - when), bass, bass_velocity))
            chord_when = when + 0.5
            if chord_when < start + beats:
                for note in upper:
                    events.append((chord_when, min(0.45, start + beats - chord_when), note, upper_velocity))
    elif pattern == "bossa":
        position = 0.0
        while position < beats:
            if use_bass and int(position) % 2 == 0:
                events.append((start + position, min(0.75, beats - position), bass, bass_velocity))
            offbeat = position + 0.5
            if offbeat < beats:
                for note in upper:
                    events.append((start + offbeat, min(0.38, beats - offbeat), note, upper_velocity))
            position += 1.0


def build_events(
    progression: list[tuple[dict, float]],
    repeat: int,
    voicing: str,
    pattern: str,
    octave: int,
    bass_octave: int,
    velocity: int,
    use_bass: bool,
) -> tuple[list[tuple[float, float, int, int]], float, list[str]]:
    events = []
    beat = 0.0
    previous = None
    summary = []
    for _ in range(repeat):
        for chord, duration in progression:
            if chord["rest"]:
                summary.append(f"{chord['symbol']}: rest ({duration:g} beats)")
                beat += duration
                continue
            upper = choose_voicing(chord, voicing, octave, previous)
            schedule_chord(events, chord, beat, duration, upper, pattern, velocity, use_bass, bass_octave)
            summary.append(f"{chord['symbol']}: {' '.join(midi_note_name(n) for n in upper)} ({duration:g} beats)")
            previous = upper
            beat += duration
    return events, beat, summary


def midi_note_name(note: int) -> str:
    names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    return f"{names[note % 12]}{note // 12 - 1}"


def vlq(value: int) -> bytes:
    buffer = value & 0x7F
    output = bytearray([buffer])
    while value >> 7:
        value >>= 7
        buffer = (value & 0x7F) | 0x80
        output.insert(0, buffer)
    return bytes(output)


def write_midi(path: Path, events: list[tuple[float, float, int, int]], tempo: float, ticks: int = 480) -> None:
    timed = []
    for start, duration, note, velocity in events:
        timed.append((round(start * ticks), 1, bytes([0x90, note, velocity])))
        timed.append((round((start + duration) * ticks), 0, bytes([0x80, note, 0])))
    timed.sort(key=lambda item: (item[0], item[1]))

    track = bytearray()
    microseconds = round(60_000_000 / tempo)
    track.extend(vlq(0) + b"\xff\x51\x03" + microseconds.to_bytes(3, "big"))
    track.extend(vlq(0) + bytes([0xC0, 0]))
    last_tick = 0
    for tick, _, message in timed:
        track.extend(vlq(tick - last_tick) + message)
        last_tick = tick
    track.extend(vlq(0) + b"\xff\x2f\x00")

    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, ticks)
    payload = b"MTrk" + struct.pack(">I", len(track)) + track
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + payload)


def note_wave(note: int, velocity: int, duration: float, sample_rate: int) -> tuple[array, array]:
    release = 0.65
    length = max(1, int((duration + release) * sample_rate))
    left = array("f", [0.0]) * length
    right = array("f", [0.0]) * length
    frequency = 440.0 * (2.0 ** ((note - 69) / 12.0))
    brightness = max(0.55, min(1.15, 1.0 - (note - 60) * 0.008))
    decay_time = max(0.65, 2.7 - (note - 48) * 0.025)
    velocity_gain = (velocity / 127.0) ** 1.35
    pan = max(-0.45, min(0.45, (note - 60) / 48.0))
    left_gain = math.sqrt((1.0 - pan) / 2.0)
    right_gain = math.sqrt((1.0 + pan) / 2.0)
    harmonic_amps = (1.0, 0.43, 0.22, 0.13, 0.075, 0.045)
    detunes = (-0.75, 0.0, 0.9) if note >= 45 else (0.0,)
    detune_gain = 1.0 / len(detunes)
    inharmonicity = 0.00010 + max(0, note - 48) * 0.000004

    for index in range(length):
        t = index / sample_rate
        attack = min(1.0, t / 0.006)
        natural = math.exp(-t / decay_time)
        if t <= duration:
            envelope = attack * natural
        else:
            envelope = attack * natural * math.exp(-(t - duration) / 0.18)

        value = 0.0
        for detune in detunes:
            base = frequency * (2.0 ** (detune / 1200.0))
            subtotal = 0.0
            for harmonic, amplitude in enumerate(harmonic_amps, start=1):
                partial = harmonic * math.sqrt(1.0 + inharmonicity * harmonic * harmonic)
                partial_decay = math.exp(-t * (harmonic - 1) * 0.34)
                subtotal += amplitude * partial_decay * math.sin(2.0 * math.pi * base * partial * t)
            value += subtotal * detune_gain

        hammer = 0.16 * math.exp(-t / 0.025) * math.sin(2.0 * math.pi * frequency * 7.3 * t)
        value = (value * 0.44 * brightness + hammer) * envelope * velocity_gain
        left[index] = value * left_gain
        right[index] = value * right_gain
    return left, right


def render_synth_wav(
    path: Path,
    events: list[tuple[float, float, int, int]],
    tempo: float,
    total_beats: float,
    sample_rate: int,
    reverb: float,
) -> None:
    seconds_per_beat = 60.0 / tempo
    total_seconds = total_beats * seconds_per_beat + 1.2
    length = max(1, int(total_seconds * sample_rate))
    left = array("f", [0.0]) * length
    right = array("f", [0.0]) * length
    cache = {}

    for start, duration, note, velocity in events:
        start_sample = int(start * seconds_per_beat * sample_rate)
        seconds = duration * seconds_per_beat
        key = (note, velocity, round(seconds, 4), sample_rate)
        if key not in cache:
            cache[key] = note_wave(note, velocity, seconds, sample_rate)
        note_left, note_right = cache[key]
        available = min(len(note_left), length - start_sample)
        for index in range(max(0, available)):
            left[start_sample + index] += note_left[index]
            right[start_sample + index] += note_right[index]

    if reverb > 0:
        dry_left = array("f", left)
        dry_right = array("f", right)
        for delay_seconds, gain in ((0.071, 0.16), (0.113, 0.11), (0.173, 0.07)):
            delay = int(delay_seconds * sample_rate)
            wet_gain = gain * reverb
            for index in range(delay, length):
                left[index] += dry_right[index - delay] * wet_gain
                right[index] += dry_left[index - delay] * wet_gain

    peak = max(max((abs(x) for x in left), default=0.0), max((abs(x) for x in right), default=0.0), 1e-9)
    scale = 0.92 / peak
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        chunk = array("h")
        for l_sample, r_sample in zip(left, right):
            chunk.append(max(-32768, min(32767, round(l_sample * scale * 32767))))
            chunk.append(max(-32768, min(32767, round(r_sample * scale * 32767))))
            if len(chunk) >= 16384:
                if sys.byteorder == "big":
                    chunk.byteswap()
                output.writeframesraw(chunk.tobytes())
                chunk = array("h")
        if chunk:
            if sys.byteorder == "big":
                chunk.byteswap()
            output.writeframesraw(chunk.tobytes())


def render_fluidsynth(soundfont: Path, midi_path: Path, output: Path, sample_rate: int) -> None:
    executable = shutil.which("fluidsynth")
    if not executable:
        raise RuntimeError("未找到 FluidSynth；请先安装，或移除 --soundfont 使用内置合成音色")
    if not soundfont.exists():
        raise FileNotFoundError(f"SoundFont 不存在：{soundfont}")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [executable, "-ni", str(soundfont), str(midi_path), "-F", str(output), "-r", str(sample_rate)]
    subprocess.run(command, check=True)


def inspect_wav(path: Path) -> None:
    with wave.open(str(path), "rb") as audio:
        channels = audio.getnchannels()
        sample_rate = audio.getframerate()
        frames = audio.getnframes()
        width = audio.getsampwidth()
        raw = audio.readframes(frames)
    if width != 2:
        peak_text = "n/a"
    else:
        samples = array("h")
        samples.frombytes(raw)
        if sys.byteorder == "big":
            samples.byteswap()
        peak_text = f"{max((abs(v) for v in samples), default=0) / 32767.0:.4f}"
    print(f"path={path}")
    print(f"channels={channels}")
    print(f"sample_rate={sample_rate}")
    print(f"sample_width_bits={width * 8}")
    print(f"duration_seconds={frames / sample_rate:.3f}")
    print(f"peak={peak_text}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把和弦符号渲染为钢琴 WAV/MIDI 试听文件")
    parser.add_argument("--progression", help='和弦进行，例如 "Dm7 | G7 | Cmaj7"')
    parser.add_argument("--output", type=Path, help="WAV 输出路径")
    parser.add_argument("--midi-out", type=Path, help="可选 MIDI 输出路径")
    parser.add_argument("--tempo", type=float, default=100.0, help="每分钟拍数，默认 100")
    parser.add_argument("--beats", type=float, default=4.0, help="每个和弦默认持续拍数")
    parser.add_argument("--repeat", type=int, default=1, help="整段重复次数")
    parser.add_argument("--pattern", choices=("block", "arpeggio", "broken", "bossa"), default="block")
    parser.add_argument("--voicing", choices=("smooth", "root", "spread"), default="smooth")
    parser.add_argument("--octave", type=int, default=4, help="右手基准八度")
    parser.add_argument("--bass-octave", type=int, default=2, help="左手低音八度")
    parser.add_argument("--velocity", type=int, default=86, help="MIDI 力度 1-127")
    parser.add_argument("--no-bass", action="store_true", help="不添加独立左手低音")
    parser.add_argument("--sample-rate", type=int, default=32000)
    parser.add_argument("--reverb", type=float, default=0.75, help="混响强度 0-1.5")
    parser.add_argument("--soundfont", type=Path, help="使用 FluidSynth 与指定 .sf2/.sf3")
    parser.add_argument("--print-notes", action="store_true", help="打印实际采用的右手音符")
    parser.add_argument("--inspect", type=Path, help="检查现有 WAV 后退出")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.inspect:
        inspect_wav(args.inspect)
        return 0
    if not args.progression or not args.output:
        raise SystemExit("生成音频必须同时提供 --progression 与 --output")
    if args.tempo <= 0 or args.beats <= 0 or args.repeat < 1:
        raise SystemExit("tempo、beats 必须大于 0，repeat 必须至少为 1")
    if not 1 <= args.velocity <= 127:
        raise SystemExit("velocity 必须在 1-127 之间")
    if not 8000 <= args.sample_rate <= 96000:
        raise SystemExit("sample-rate 必须在 8000-96000 之间")

    try:
        progression = parse_progression(args.progression, args.beats)
        events, total_beats, summary = build_events(
            progression,
            args.repeat,
            args.voicing,
            args.pattern,
            args.octave,
            args.bass_octave,
            args.velocity,
            not args.no_bass,
        )
    except ChordError as error:
        raise SystemExit(str(error)) from error

    temp_midi = None
    midi_path = args.midi_out
    if args.soundfont and midi_path is None:
        handle = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
        handle.close()
        temp_midi = Path(handle.name)
        midi_path = temp_midi
    if midi_path:
        write_midi(midi_path, events, args.tempo)

    try:
        if args.soundfont:
            render_fluidsynth(args.soundfont, midi_path, args.output, args.sample_rate)
        else:
            render_synth_wav(args.output, events, args.tempo, total_beats, args.sample_rate, args.reverb)
    finally:
        if temp_midi and temp_midi.exists():
            temp_midi.unlink()

    if args.print_notes:
        print("\n".join(summary))
    print(f"WAV: {args.output.resolve()}")
    if args.midi_out:
        print(f"MIDI: {args.midi_out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
