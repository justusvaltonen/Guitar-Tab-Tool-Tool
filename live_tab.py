#!/usr/bin/env python3
"""
Live Audio to Guitar Tab Transcriber
Records from microphone, detects pitches, maps to guitar strings/frets, outputs ASCII tab.
"""

import sys
import numpy as np
import librosa
import pretty_midi
from collections import deque
import threading
import time

# Guitar standard tuning (E2, A2, D3, G3, B3, E4) - low to high
# String indices: 0=low E (6th string), 5=high E (1st string)
GUITAR_TUNING = [
    ("E", 82.41),   # String 0 (low E, 6th string)
    ("A", 110.00),  # String 1 (5th string)
    ("D", 146.83),  # String 2 (4th string)
    ("G", 196.00),  # String 3 (3rd string)
    ("B", 246.94),  # String 4 (2nd string)
    ("E", 329.63),  # String 5 (high E, 1st string)
]

# String names for display (high to low, as shown in tab)
STRING_NAMES_DISPLAY = ['e', 'B', 'G', 'D', 'A', 'E']  # high E to low E

# Fret frequencies relative to open string (12-EDO)
FRET_RATIOS = [2 ** (i / 12) for i in range(25)]  # 0-24 frets

SAMPLE_RATE = 44100
CHUNK_SIZE = 2048  # ~46ms at 44.1kHz
FORMAT = None  # Will be set based on availability
CHANNELS = 1

# Audio buffer for pitch detection
audio_buffer = deque(maxlen=int(SAMPLE_RATE * 2))  # 2 second buffer
buffer_lock = threading.Lock()

# Pitch detection state
last_pitch = None
last_note_time = 0
note_cooldown = 0.3  # seconds between note outputs

# Try to import pyaudio, but make it optional
try:
    import pyaudio
    HAS_PYAUDIO = True
    FORMAT = pyaudio.paFloat32
except ImportError:
    HAS_PYAUDIO = False
    print("Warning: pyaudio not available. Audio input will not work.")


def freq_to_midi(freq):
    """Convert frequency to MIDI note number.
    
    MIDI note 69 = A4 = 440Hz
    Formula: midi = 12 * log2(freq / 440) + 69
    """
    if freq <= 0:
        return None
    return round(12 * np.log2(freq / 440.0) + 69)


def midi_to_freq(midi):
    """Convert MIDI note to frequency.
    
    Formula: freq = 440 * 2^((midi - 69) / 12)
    """
    return 440.0 * (2 ** ((midi - 69) / 12))


def find_closest_string_fret(target_freq):
    """Find the closest guitar string/fret combination for a given frequency.
    
    Returns:
        Tuple of (string_idx, fret, note_name, matched_freq) or None if no match
        string_idx: 0-5 (0=low E, 5=high E)
        fret: 0-24
    """
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
    """Detect fundamental frequency using librosa's pyin.
    
    Args:
        y: Audio signal (numpy array)
        sr: Sample rate
    
    Returns:
        Fundamental frequency in Hz, or None if not detected
    """
    try:
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=librosa.note_to_hz('E2'), fmax=librosa.note_to_hz('E6'),
            sr=sr, frame_length=2048, hop_length=512
        )
        # Get median of voiced frames
        voiced_f0 = f0[voiced_flag]
        if len(voiced_f0) > 0:
            return float(np.median(voiced_f0))
    except Exception:
        pass
    return None


def detect_pitch_autocorr(y, sr):
    """Fallback pitch detection using autocorrelation.
    
    Args:
        y: Audio signal (numpy array)
        sr: Sample rate
    
    Returns:
        Fundamental frequency in Hz, or None if not detected
    """
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
    """Process audio buffer and detect notes.
    
    Returns:
        Dict with note info or None if no note detected
    """
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
            'string': string_idx,  # 0-5 (0=low E, 5=high E)
            'fret': fret,
            'note': note_name,
            'freq': pitch,
            'matched_freq': matched_freq,
        }
    return None


def format_tab_line(note_info):
    """Format a single note as ASCII tab line.
    
    Args:
        note_info: Dict with 'string', 'fret', 'note', 'freq', 'matched_freq'
    
    Returns:
        Formatted string with tab representation
    """
    if note_info is None:
        return ""
    
    string_idx = note_info['string']  # 0-5 (0=low E, 5=high E)
    fret = note_info['fret']
    note_name = note_info['note']
    
    # Create tab representation
    # In tab notation: top line = high E (string 5), bottom line = low E (string 0)
    # So we need to reverse the string order for display
    lines = []
    for i, s in enumerate(STRING_NAMES_DISPLAY):
        # i=0 is 'e' (high E, string 5), i=5 is 'E' (low E, string 0)
        # display_string_idx = 5 - i (5=high E, 0=low E)
        display_string_idx = 5 - i
        if string_idx == display_string_idx:
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


def list_audio_devices():
    """List available audio input devices.
    
    Returns:
        List of (index, name) tuples for input devices
    """
    if not HAS_PYAUDIO:
        return []
    
    p = pyaudio.PyAudio()
    devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            devices.append((i, info['name']))
    p.terminate()
    return devices


def main():
    """Main entry point for live transcription."""
    if not HAS_PYAUDIO:
        print("Error: pyaudio is required for live audio input.")
        print("Install it with: pip install pyaudio")
        print("Note: On Linux, you may need: sudo apt-get install portaudio19-dev")
        sys.exit(1)
    
    print("=" * 50)
    print("  Live Audio -> Guitar Tab Transcriber")
    print("=" * 50)
    print("  Press Ctrl+C to stop\n")
    print("  Standard tuning: E A D G B E (low to high)")
    print("  String 1 = high E, String 6 = low E\n")
    
    # List input devices
    devices = list_audio_devices()
    print("Available input devices:")
    for idx, name in devices:
        print(f"  [{idx}] {name}")
    
    device_index = None
    try:
        choice = input("\nSelect device index (Enter for default): ").strip()
        if choice:
            device_index = int(choice)
    except (ValueError, KeyboardInterrupt):
        pass
    
    p = pyaudio.PyAudio()
    
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
