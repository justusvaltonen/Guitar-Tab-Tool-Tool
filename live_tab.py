#!/usr/bin/env python3
"""
Live Audio to Guitar Tab Transcriber
Records from microphone, detects pitches, maps to guitar strings/frets, outputs ASCII tab.
"""

import numpy as np
import pyaudio
import librosa
import pretty_midi
from collections import deque
import threading
import time
import sys

# Guitar standard tuning (E2, A2, D3, G3, B3, E4) - low to high
GUITAR_TUNING = [
    ("E", 82.41),   # String 6 (low E)
    ("A", 110.00),  # String 5
    ("D", 146.83),  # String 4
    ("G", 196.00),  # String 3
    ("B", 246.94),  # String 2
    ("E", 329.63),  # String 1 (high E)
]

# Fret frequencies relative to open string (12-EDO)
FRET_RATIOS = [2 ** (i / 12) for i in range(25)]  # 0-24 frets

SAMPLE_RATE = 44100
CHUNK_SIZE = 2048  # ~46ms at 44.1kHz
FORMAT = pyaudio.paFloat32
CHANNELS = 1

# Audio buffer for pitch detection
audio_buffer = deque(maxlen=int(SAMPLE_RATE * 2))  # 2 second buffer
buffer_lock = threading.Lock()

# Pitch detection state
last_pitch = None
last_note_time = 0
note_cooldown = 0.3  # seconds between note outputs


def freq_to_midi(freq):
    """Convert frequency to MIDI note number."""
    if freq <= 0:
        return None
    return round(12 * np.log2(freq / 440.0) + 69)


def midi_to_freq(midi):
    """Convert MIDI note to frequency."""
    return 440.0 * (2 ** ((midi - 69) / 12))


def find_closest_string_fret(target_freq):
    """Find the closest guitar string/fret combination for a given frequency."""
    best_match = None
    best_error = float('inf')
    
    for string_idx, (note_name, open_freq) in enumerate(GUITAR_TUNING):
        for fret in range(25):
            freq = open_freq * FRET_RATIOS[fret]
            error = abs(freq - target_freq) / target_freq
            if error < best_error:
                best_error = error
                best_match = (string_idx, fret, note_name, freq)
    
    # Only return if error is within reasonable range (quarter tone ~ 3%)
    if best_error < 0.03:
        return best_match
    return None


def detect_pitch_librosa(y, sr):
    """Detect fundamental frequency using librosa's pyin."""
    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=librosa.note_to_hz('E2'), fmax=librosa.note_to_hz('E6'),
            sr=sr, frame_length=2048, hop_length=512
        )
        # Get median of voiced frames
        voiced_f0 = f0[voiced_flag]
        if len(voiced_f0) > 0:
            return np.median(voiced_f0)
    except Exception:
        pass
    return None


def detect_pitch_autocorr(y, sr):
    """Fallback pitch detection using autocorrelation."""
    # Normalize
    y = y - np.mean(y)
    if np.max(np.abs(y)) > 0:
        y = y / np.max(np.abs(y))
    
    # Autocorrelation
    corr = np.correlate(y, y, mode='full')
    corr = corr[len(corr)//2:]
    
    # Find first peak after zero lag
    # Search in range corresponding to E2 (82Hz) to E6 (1318Hz)
    min_lag = int(sr / 1318)
    max_lag = int(sr / 82)
    
    if max_lag < len(corr):
        peak_idx = np.argmax(corr[min_lag:max_lag]) + min_lag
        if peak_idx > 0:
            return sr / peak_idx
    return None


def audio_callback(in_data, frame_count, time_info, status):
    """PyAudio callback to fill audio buffer."""
    audio_data = np.frombuffer(in_data, dtype=np.float32)
    with buffer_lock:
        audio_buffer.extend(audio_data)
    return (in_data, pyaudio.paContinue)


def process_audio():
    """Process audio buffer and detect notes."""
    global last_pitch, last_note_time
    
    with buffer_lock:
        if len(audio_buffer) < CHUNK_SIZE:
            return None
        # Get recent audio
        y = np.array(list(audio_buffer)[-CHUNK_SIZE:])
    
    # Detect pitch
    pitch = detect_pitch_librosa(y, SAMPLE_RATE)
    if pitch is None or np.isnan(pitch):
        pitch = detect_pitch_autocorr(y, SAMPLE_RATE)
    
    if pitch is None or pitch <= 0:
        return None
    
    # Debounce: only output if pitch changed significantly or enough time passed
    now = time.time()
    if last_pitch is not None:
        pitch_diff = abs(pitch - last_pitch) / last_pitch
        if pitch_diff < 0.02 and (now - last_note_time) < note_cooldown:
            return None
    
    last_pitch = pitch
    last_note_time = now
    
    # Map to guitar
    match = find_closest_string_fret(pitch)
    if match:
        string_idx, fret, note_name, matched_freq = match
        return {
            'string': 6 - string_idx,  # 1=high E, 6=low E
            'fret': fret,
            'note': note_name,
            'freq': pitch,
            'matched_freq': matched_freq,
        }
    return None


def format_tab_line(note_info):
    """Format a single note as ASCII tab line."""
    if note_info is None:
        return ""
    
    string_num = note_info['string']
    fret = note_info['fret']
    note_name = note_info['note']
    
    # Create tab representation
    # Strings: e B G D A E (high to low)
    strings = ['e', 'B', 'G', 'D', 'A', 'E']
    
    lines = []
    for i, s in enumerate(strings):
        string_idx = i + 1  # top 'e' (high E) = string 1, bottom 'E' (low E) = string 6
        if string_idx == string_num:
            fret_str = str(fret).rjust(2)
            lines.append(f"{s}|---{fret_str}---|")
        else:
            lines.append(f"{s}|---------|")
    
    # Add note info
    freq = note_info['freq']
    matched = note_info['matched_freq']
    diff_cents = 1200 * np.log2(freq / matched)
    lines.append(f"\n  Note: {note_name}{fret}  Freq: {freq:.1f}Hz  Match: {matched:.1f}Hz  Diff: {diff_cents:+.1f}¢")
    
    return "\n".join(lines)


def clear_screen():
    """Clear terminal screen."""
    print("\033[2J\033[H", end="")


def main():
    print("=" * 50)
    print("  Live Audio -> Guitar Tab Transcriber")
    print("=" * 50)
    print("  Press Ctrl+C to stop\n")
    print("  Standard tuning: E A D G B E (low to high)")
    print("  String 1 = high E, String 6 = low E\n")
    
    p = pyaudio.PyAudio()
    
    # List input devices
    print("Available input devices:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"  [{i}] {info['name']}")
    
    device_index = None
    try:
        choice = input("\nSelect device index (Enter for default): ").strip()
        if choice:
            device_index = int(choice)
    except (ValueError, KeyboardInterrupt):
        pass
    
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=CHUNK_SIZE,
        stream_callback=audio_callback,
    )
    
    print("\n[Recording... Play your guitar]\n")
    
    stream.start_stream()
    
    try:
        while stream.is_active():
            note = process_audio()
            if note:
                clear_screen()
                print(format_tab_line(note))
            time.sleep(0.05)  # 20 FPS update
    except KeyboardInterrupt:
        print("\n\nStopping...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        print("Done.")


if __name__ == "__main__":
    main()