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
    if url.startswith(('http://', 'https://')):
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
        if os.path.isfile(url):
            if os.path.getsize(url) > 100000:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if not os.path.exists(path) or os.path.getsize(path) <= 100000:
                    shutil.copy(url, path)
                print(f"SoundFont found at: {path}")
                return path
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                shutil.copy(url, path)
                print(f"SoundFont copied from {url} to {path}")
                return path
        else:
            print(f"Error: SoundFont source file not found: {url}")
            sys.exit(1)

def parse_tab_lines(lines):
    """Parse ASCII tab into valid note positions.
    
    Uses a robust regex-based approach to extract notes from guitar tabs.
    Handles multi-section tabs, mixed formats, and various annotations.
    Returns a dict mapping string index (0-5, low E to high E) to list of (position, fret) tuples.
    """
    import re
    
    if len(lines) == 0:
        raise ValueError("Tab must have at least one line")
    
    # Find all lines that look like tab strings (start with string letter or pipe)
    # Standard format: e|--0-1-2--| or just |--0-1-2--|
    tab_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # Check if this looks like a tab line
        if '|' in stripped or re.match(r'^[eBgDaEsS]|[-0-9]', stripped):
            if '|' in stripped:
                tab_content = stripped.split('|', 1)[1]
            else:
                tab_content = stripped
            tab_lines.append(tab_content)
    
    if not tab_lines:
        raise ValueError("No valid tab content found")
    
    # Parse each tab line - they should be in order e, B, G, D, A, E (high to low)
    # For multi-measure tabs, the same 6 strings repeat
    result = {i: [] for i in range(6)}  # 0=low E, 5=high E
    
    # Process lines in groups of 6
    for group_start in range(0, len(tab_lines), 6):
        group = tab_lines[group_start:group_start + 6]
        if len(group) < 6:
            # Handle incomplete groups - still process what we have
            pass
        
        for line_idx, line_content in enumerate(group):
            if line_idx >= 6:
                break
            
            # String mapping: group[0] = e (high E, string 5), group[5] = E (low E, string 0)
            string_idx = 5 - line_idx
            
            # Extract fret numbers with their positions
            notes = []
            pos = 0
            i = 0
            while i < len(line_content):
                char = line_content[i]
                if char == '-':
                    pos += 1
                    i += 1
                elif char.isdigit():
                    # Read all consecutive digits for multi-digit fret numbers
                    start = i
                    while i < len(line_content) and line_content[i].isdigit():
                        i += 1
                    fret = int(line_content[start:i])
                    # Only record valid frets (0-24 for guitar)
                    if 0 <= fret <= 24:
                        notes.append((pos, fret))
                elif char == '|':
                    i += 1
                else:
                    i += 1
            
            result[string_idx].extend(notes)
    
    return result

def tab_to_midi(tab_data, output_path, tempo=120, note_duration=0.5):
    """Convert parsed tab data to a MIDI file."""
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo)))
    track.append(MetaMessage('time_signature', numerator=4, denominator=4))
    track.append(Message('program_change', program=GUITAR_PROGRAM, time=0))
    
    all_notes = []
    for string_idx in range(6):
        notes = tab_data.get(string_idx, [])
        base_note = STRING_TUNING[string_idx]
        for pos, fret in notes:
            if fret == 0:
                note_num = base_note
            else:
                note_num = base_note + fret
            # Validate MIDI note number (0-127)
            if 0 <= note_num <= 127:
                all_notes.append((pos, note_num))
    
    all_notes.sort(key=lambda x: x[0])
    ticks_per_beat = mid.ticks_per_beat
    last_pos = 0
    
    for pos, note_num in all_notes:
        delta_pos = pos - last_pos
        delta_time = max(0, int(delta_pos * (ticks_per_beat / 4)))
        track.append(Message('note_on', note=note_num, velocity=80, time=delta_time))
        track.append(Message('note_off', note=note_num, velocity=64, time=int(note_duration * ticks_per_beat)))
        last_pos = pos
    
    mid.save(output_path)
    return output_path

def render_wav(midi_path, soundfont_path, output_wav):
    """Render MIDI to WAV using FluidSynth."""
    try:
        result = subprocess.run(
            ['fluidsynth', '-ni', '-F', output_wav, '-r', '44100', '-g', '2.0', soundfont_path, midi_path],
            capture_output=True,
            text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"FluidSynth error: {result.stderr}")
            return False
        print(f"WAV rendered to: {output_wav}")
        return output_wav
    except FileNotFoundError:
        print("Error: fluidsynth not found. Install it with: sudo apt-get install fluidsynth")
        return False
    except subprocess.TimeoutExpired:
        print("Error: FluidSynth timed out")
        return False

def play_tab_file(tab_path, output_wav=None):
    """Main function to process a tab file and produce a WAV."""
    with open(tab_path, 'r') as f:
        lines = f.readlines()
    print(f"Parsing tab file: {tab_path}")
    
    try:
        tab_data = parse_tab_lines(lines)
    except ValueError as e:
        print(f"Error parsing tab: {e}")
        sys.exit(1)
    
    total_notes = sum(len(notes) for notes in tab_data.values())
    print(f"Parsed {total_notes} total notes across all strings")
    for string_idx, notes in tab_data.items():
        if notes:
            print(f"  String {string_idx + 1} ({'E2ADEF'[string_idx]}): {len(notes)} notes")
    
    soundfont = download_soundfont()
    
    with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
        midi_path = tmp.name
    
    try:
        print("Creating MIDI file...")
        tab_to_midi(tab_data, midi_path)
        print(f"MIDI file created: {midi_path}")
        
        if output_wav:
            wav_path = output_wav
        else:
            wav_path = os.path.join(os.path.dirname(tab_path), os.path.splitext(os.path.basename(tab_path))[0] + '.wav')
        
        render_wav(midi_path, soundfont, wav_path)
    finally:
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
    
    if len(sys.argv) >= 3:
        output_wav = sys.argv[2]
    else:
        output_wav = os.path.join(os.path.dirname(tab_file), os.path.splitext(os.path.basename(tab_file))[0] + '.wav')
    
    play_tab_file(tab_file, output_wav)

if __name__ == "__main__":
    main()