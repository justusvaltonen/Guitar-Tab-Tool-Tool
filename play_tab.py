#!/usr/bin/env python3
"""Play guitar ASCII tab files by converting to MIDI and synthesizing via FluidSynth."""

import sys
import os
import tempfile
import subprocess
import urllib.request
import shutil

try:
    import mido
    from mido import Message, MidiFile, MidiTrack, MetaMessage
except ImportError:
    print("Error: mido package not installed. Run: pip install mido")
    sys.exit(1)

# SoundFont URL (FluidR3_GM.sf2 - free General MIDI soundfont)
SOUNDFONT_URL = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
SOUNDFONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "FluidR3_GM.sf2")

# Guitar tuning: E A D G B E (6 strings, low E = string 6, high E = string 1)
STRING_TUNING = [40, 45, 49, 52, 55, 59]  # MIDI note numbers for E2, A2, D3, G3, B3, E4

# Nylon Guitar program in GM (program 25 = Nylon Guitar)
GUITAR_PROGRAM = 25

def download_soundfont(url=SOUNDFONT_URL, path=SOUNDFONT_PATH):
    """Download soundfont if it doesn't exist or is invalid."""
    # Determine if source is a URL or local path
    if url.startswith(('http://', 'https://')):
        # Remote URL
        if os.path.exists(path) and os.path.getsize(path) > 100000:
            print(f"SoundFont found at: {path}")
            return path
        print(f"Downloading SoundFont from {url}...")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            urllib.request.urlretrieve(url, path)
            print(f"SoundFont downloaded to: {path}")
            return path
        except Exception as e:
            print(f"Error downloading SoundFont: {e}")
            sys.exit(1)
    else:
        # Local file path
        if os.path.isfile(url):
            if os.path.getsize(url) > 100000:
                # Already valid
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if not os.path.exists(path) or os.path.getsize(path) <= 100000:
                    shutil.copy(url, path)
                print(f"SoundFont found at: {path}")
                return path
            else:
                # Copy from source to assets path
                os.makedirs(os.path.dirname(path), exist_ok=True)
                shutil.copy(url, path)
                print(f"SoundFont copied from {url} to {path}")
                return path
        else:
            # Source does not exist; treat as URL? but not http(s) -> error
            print(f"Error: SoundFont source file not found: {url}")
            sys.exit(1)

def parse_ascii_tab(lines):
    """Parse simple ASCII guitar tab (6 lines). Returns a dict mapping string index (0-5, low E to high E) to list of (position, fret) tuples."""
    if len(lines) < 6:
        raise ValueError("Tab must have at least 6 lines")
    # Find the actual tab lines (skip headers like "e|--0-2-3-")
    tab_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip empty lines and comment/header lines
        if not stripped or stripped.startswith('#'):
            continue
        # Look for lines that have the pipe character (standard tab format)
        if '|' in stripped:
            # Extract the part after the pipe
            parts = stripped.split('|', 1)
            if len(parts) > 1:
                tab_lines.append(parts[1])
        else:
            # Could be a simple tab line without pipe
            tab_lines.append(stripped)
    # Take first 6 lines as strings
    if len(tab_lines) < 6:
        raise ValueError(f"Expected 6 tab lines, got {len(tab_lines)}")
    tab_lines = tab_lines[:6]
    # Parse each string
    result = {}
    for string_idx, line in enumerate(tab_lines):
        notes = []
        i = 0
        while i < len(line):
            char = line[i]
            if char == '-':
                # Empty string, skip
                i += 1
            elif char.isdigit():
                # Found a fret number
                fret = int(char)
                # Find position by counting dashes before this note
                pos = 0
                j = 0
                while j < i and line[j] != '|':
                    if line[j] == '-':
                        pos += 1
                    j += 1
                notes.append((pos, fret))
                i += 1
            elif char == '|':
                # Bar line, skip
                i += 1
            else:
                i += 1
        # Map string index: 0 = low E (6th string), 5 = high E (1st string)
        result[5 - string_idx] = notes
    return result

def tab_to_midi(tab_data, output_path, tempo=120, note_duration=0.5):
    """Convert parsed tab data to a MIDI file."""
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    # Set tempo (mido.tempo2bpm converts BPM to microseconds per beat, we need the reverse)
    track.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo)))
    # Time signature
    track.append(MetaMessage('time_signature', numerator=4, denominator=4))
    # Program change for Nylon Guitar
    track.append(Message('program_change', program=GUITAR_PROGRAM, time=0))
    # Collect all notes with their positions
    all_notes = []
    for string_idx in range(6):
        notes = tab_data.get(string_idx, [])
        base_note = STRING_TUNING[string_idx]
        for pos, fret in notes:
            if fret == 0:
                # Open string - use the base note
                note_num = base_note
            else:
                # Calculate MIDI note for the fret
                note_num = base_note + fret
            all_notes.append((pos, note_num))
    # Sort notes by position for proper delta timing
    all_notes.sort(key=lambda x: x[0])
    # MIDI ticks per beat
    ticks_per_beat = mid.ticks_per_beat
    last_pos = 0
    # Process each note with proper delta timing
    for pos, note_num in all_notes:
        # Delta time from previous note
        delta_pos = pos - last_pos
        delta_time = int(delta_pos * (ticks_per_beat / 4))  # 4 positions per beat
        # Add note on
        track.append(Message('note_on', note=note_num, velocity=64, time=delta_time))
        # Add note off after duration
        track.append(Message('note_off', note=note_num, velocity=64, time=int(note_duration * ticks_per_beat)))
        last_pos = pos
    # Write MIDI file
    mid.save(output_path)
    return output_path

def render_wav(midi_path, soundfont_path, output_wav):
    """Render MIDI to WAV using FluidSynth."""
    try:
        result = subprocess.run(
            ['fluidsynth', '-ni', '-F', output_wav, '-r', '44100', soundfont_path, midi_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"FluidSynth error: {result.stderr}")
            return False
        print(f"WAV rendered to: {output_wav}")
        return output_wav
    except FileNotFoundError:
        print("Error: fluidsynth not found. Install it with: sudo apt-get install fluidsynth")
        return False

def play_tab_file(tab_path, output_wav=None):
    """Main function to process a tab file and produce a WAV."""
    # Read the tab file
    with open(tab_path, 'r') as f:
        lines = f.readlines()
    print(f"Parsing tab file: {tab_path}")
    print(f"Lines read: {len(lines)}")
    # Parse the tab
    try:
        tab_data = parse_ascii_tab(lines)
    except ValueError as e:
        print(f"Error parsing tab: {e}")
        sys.exit(1)
    print(f"Parsed {len(tab_data)} strings")
    for string_idx, notes in tab_data.items():
        if notes:
            print(f"  String {string_idx + 1}: {len(notes)} notes")
    # Download soundfont if needed
    soundfont = download_soundfont()
    # Create temporary MIDI file
    with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
        midi_path = tmp.name
    try:
        # Convert to MIDI
        print("Creating MIDI file...")
        tab_to_midi(tab_data, midi_path)
        print(f"MIDI file created: {midi_path}")
        # Determine output WAV path
        if output_wav:
            wav_path = output_wav
        else:
            wav_path = os.path.join(os.path.dirname(tab_path), os.path.splitext(os.path.basename(tab_path))[0] + '.wav')
        # Render WAV
        render_wav(midi_path, soundfont, wav_path)
    finally:
        # Clean up temporary MIDI file
        if os.path.exists(midi_path):
            os.unlink(midi_path)

def main():
    if len(sys.argv) < 2:
        print("Usage: python play_tab.py <tab_file> [output.wav]")
        print("Example: python play_tab.py my_song.txt")
        sys.exit(1)
    tab_file = sys.argv[1]
    if not os.path.exists(tab_file):
        print(f"Error: File not found: {tab_file}")
        sys.exit(1)
    # Determine output WAV path
    if len(sys.argv) >= 3:
        output_wav = sys.argv[2]
    else:
        output_wav = os.path.join(os.path.dirname(tab_file), os.path.splitext(os.path.basename(tab_file))[0] + '.wav')
    play_tab_file(tab_file, output_wav)

if __name__ == "__main__":
    main()