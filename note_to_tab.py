#!/usr/bin/env python3
"""Convert musical notes to ASCII guitar tablature."""

import itertools
from typing import List, Tuple, Dict

# Mapping of standard notes to semitone offsets (C = 0)
NOTE_TO_MIDI = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
    'A': 9, 'A#': 10, 'Bb': 10, 'B': 11,
}

# Standard guitar tuning (E2 A2 D3 G3 B3 E4) as MIDI numbers
# E2=40, A2=45, D3=50, G3=55, B3=59, E4=64
STRING_TUNING = [40, 45, 50, 55, 59, 64]  # low E to high E
# String names for display (high to low): e, B, G, D, A, E
STRING_NAMES_DISPLAY = ['e', 'B', 'G', 'D', 'A', 'E']


def note_to_midi(note: str) -> int:
    """Convert a note like C4 or D#5 to a MIDI number.
    
    MIDI note numbering: C-1 = 0, C0 = 12, C#0 = 13, ..., A4 = 69, C8 = 108
    
    Args:
        note: Note string like 'C4', 'D#3', 'Bb2'
    
    Returns:
        MIDI note number (0-127)
    
    Raises:
        ValueError: If the note string is invalid
    """
    # Split letter+accidentals from octave
    if len(note) < 2:
        raise ValueError(f'Invalid note: {note}')
    
    # Handle notes with accidentals (2 chars for note name)
    if note[1] in ('#', 'b'):
        name = note[:2]
        octave_str = note[2:]
    else:
        name = note[0]
        octave_str = note[1:]
    
    # Validate note name
    if name not in NOTE_TO_MIDI:
        raise ValueError(f'Invalid note name: {name}. Valid names are: {list(NOTE_TO_MIDI.keys())}')
    
    # Validate octave
    try:
        octave = int(octave_str)
    except ValueError:
        raise ValueError(f'Invalid octave in note: {note}')
    
    base = NOTE_TO_MIDI[name]
    # MIDI formula: note_number = 12 * (octave + 1) + semitone
    # For C4: 12 * (4 + 1) + 0 = 60 ✓
    # For E2: 12 * (2 + 1) + 4 = 40 ✓
    return base + 12 * (octave + 1)


def possible_frets(midi: int) -> List[Tuple[int, int]]:
    """Return list of (string_index, fret) that can play the given MIDI note.
    
    string_index: 0 = low E, 5 = high E.
    Only frets 0-24 are considered (typical guitar range).
    
    Args:
        midi: MIDI note number
    
    Returns:
        List of (string_index, fret) tuples
    """
    possibilities = []
    for s, open_midi in enumerate(STRING_TUNING):
        fret = midi - open_midi
        if 0 <= fret <= 24:
            possibilities.append((s, fret))
    return possibilities


def choose_fingering(midi_sequence: List[int]) -> List[Tuple[int, int]]:
    """Choose a fingering that minimizes hand movement.
    
    Simple greedy algorithm: for each note pick the position that is
    closest (in fret distance) to the previous note's fret on any string.
    For the first note, prefer the highest string (lowest string index) 
    with the lowest fret number for better playability.
    
    Args:
        midi_sequence: List of MIDI note numbers
    
    Returns:
        List of (string_index, fret) tuples
    """
    result: List[Tuple[int, int]] = []
    prev_string, prev_fret = None, None
    
    for midi in midi_sequence:
        cand = possible_frets(midi)
        if not cand:
            raise ValueError(f'No guitar position for MIDI {midi}')
        
        if prev_string is None:
            # For first note, prefer highest string (string 5) with lowest fret
            # Sort by: fret ascending, then string descending (higher strings first)
            choice = min(cand, key=lambda x: (x[1], -x[0]))
        else:
            # Pick candidate with minimal fret distance from previous
            # Add small penalty for string changes (0.1 * string difference)
            choice = min(cand,
                         key=lambda x: abs(x[1] - prev_fret) + 0.1 * abs(x[0] - prev_string))
        result.append(choice)
        prev_string, prev_fret = choice
    return result


def notes_to_tab(notes: List[str]) -> str:
    """Convert a list of note strings (e.g., ['E4', 'G4', 'B4']) to an ASCII tab.
    
    The tab is a simple 6-line representation with dashes and fret numbers.
    
    Args:
        notes: List of note strings
    
    Returns:
        ASCII tab string
    """
    if not notes:
        return ""
    
    midi_seq = [note_to_midi(n) for n in notes]
    fingering = choose_fingering(midi_seq)
    
    # Build empty tab lines (6 strings: high E at top, low E at bottom)
    # Each line represents one string, with positions for each note
    lines = [['-'] * len(notes) for _ in range(6)]
    
    for idx, (string_idx, fret) in enumerate(fingering):
        # Convert fret number to string
        fret_str = str(fret)
        
        # Place on the appropriate string line (0 = low E, 5 = high E)
        # In output: line 0 = high E (string 5), line 5 = low E (string 0)
        line_idx = 5 - string_idx
        
        if len(fret_str) == 2:
            # Two-digit fret: replace current column with first digit
            # and insert second digit as next column
            lines[line_idx][idx] = fret_str[0]
            # Shift everything right for subsequent columns
            for l in lines:
                l.insert(idx + 1, fret_str[1])
            # Also extend note list for visual alignment
            notes.insert(idx + 1, '')
        else:
            lines[line_idx][idx] = fret_str
    
    # Join each line with string names
    tab_lines = []
    for i, line in enumerate(lines):
        string_name = STRING_NAMES_DISPLAY[i]  # high E to low E
        tab_lines.append(f"{string_name}|{''.join(line)}|")
    
    # Create header with note names
    header_notes = []
    for n in notes:
        if n:
            header_notes.append(n)
        else:
            header_notes.append('--')
    header = '  '.join(header_notes)
    
    return '\n'.join(tab_lines) + '\n' + header


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python note_to_tab.py NOTE1 NOTE2 ... (e.g., C4 D4 E4)')
        print('Example: python note_to_tab.py E4 G4 B4')
        sys.exit(1)
    
    notes = sys.argv[1:]
    try:
        result = notes_to_tab(notes)
        print(result)
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)
