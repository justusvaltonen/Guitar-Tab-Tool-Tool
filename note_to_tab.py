import itertools
from typing import List, Tuple, Dict

# Mapping of standard notes to MIDI numbers (C0 = 12)
NOTE_TO_MIDI = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
    'A': 9, 'A#': 10, 'Bb': 10, 'B': 11,
}

# Standard guitar tuning (E2 A2 D3 G3 B3 E4) as MIDI numbers
STRING_TUNING = [40, 45, 50, 55, 59, 64]  # low E to high E


def note_to_midi(note: str) -> int:
    """Convert a note like C4 or D#5 to a MIDI number."""
    # Split letter+accidentals from octave
    if len(note) < 2:
        raise ValueError(f'Invalid note: {note}')
    if note[1] in ('#', 'b'):
        name = note[:2]
        octave = int(note[2:])
    else:
        name = note[0]
        octave = int(note[1:])
    base = NOTE_TO_MIDI[name]
    return base + 12 * (octave + 1)  # MIDI C-1 = 0, so C0 = 12


def possible_frets(midi: int) -> List[Tuple[int, int]]:
    """Return list of (string_index, fret) that can play the given MIDI note.
    string_index: 0 = low E, 5 = high E.
    Only frets 0‑24 are considered (typical guitar range)."""
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
    """
    result: List[Tuple[int, int]] = []
    prev_string, prev_fret = None, None
    for midi in midi_sequence:
        cand = possible_frets(midi)
        if not cand:
            raise ValueError(f'No guitar position for MIDI {midi}')
        if prev_string is None:
            # start with the lowest string option
            choice = min(cand, key=lambda x: (x[0], x[1]))
        else:
            # pick candidate with minimal fret distance from previous
            choice = min(cand,
                         key=lambda x: abs(x[1] - prev_fret) + 0.1 * x[0])
        result.append(choice)
        prev_string, prev_fret = choice
    return result


def notes_to_tab(notes: List[str]) -> str:
    """Convert a list of note strings (e.g., ['E4', 'G4', 'B4']) to an ASCII tab.
    The tab is a simple 6‑line representation with dashes and fret numbers.
    """
    midi_seq = [note_to_midi(n) for n in notes]
    fingering = choose_fingering(midi_seq)
    # Build empty tab lines
    lines = [['-'] * len(notes) for _ in range(6)]
    for idx, (string_idx, fret) in enumerate(fingering):
        # Convert fret number to string (single digit or two digits)
        fret_str = str(fret)
        # Place on the appropriate string line (0 = low E, 5 = high E)
        line = lines[5 - string_idx]  # high E at top of output
        # If two‑digit fret, we need to expand the column width
        if len(fret_str) == 2:
            # replace current column with first digit, and insert second digit as next column
            line[idx] = fret_str[0]
            # shift everything right for subsequent columns
            for l in lines:
                l.insert(idx + 1, fret_str[1])
            # also extend note list for visual alignment (add placeholder)
            notes.insert(idx + 1, '')
        else:
            line[idx] = fret_str
    # Join each line
    tab_lines = [''.join(l) for l in lines]
    header = '  '.join([n if n else '--' for n in notes])
    return '\n'.join(tab_lines) + '\n' + header


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: note_to_tab.py NOTE1 NOTE2 ... (e.g., C4 D4 E4)')
        sys.exit(1)
    notes = sys.argv[1:]
    print(notes_to_tab(notes))
