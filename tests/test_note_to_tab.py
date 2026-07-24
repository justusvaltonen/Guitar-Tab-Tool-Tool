#!/usr/bin/env python3
"""Unit tests for note_to_tab.py module."""

import unittest
from note_to_tab import note_to_midi, possible_frets, choose_fingering, notes_to_tab


class TestNoteToMidi(unittest.TestCase):
    """Test note to MIDI number conversion."""
    
    def test_c4(self):
        """C4 should be MIDI note 60."""
        self.assertEqual(note_to_midi('C4'), 60)
    
    def test_a4(self):
        """A4 should be MIDI note 69."""
        self.assertEqual(note_to_midi('A4'), 69)
    
    def test_e2(self):
        """E2 (low E string open) should be MIDI note 40."""
        self.assertEqual(note_to_midi('E2'), 40)
    
    def test_e4(self):
        """E4 (high E string open) should be MIDI note 64."""
        self.assertEqual(note_to_midi('E4'), 64)
    
    def test_sharps(self):
        """Test sharp notes."""
        self.assertEqual(note_to_midi('D#3'), 51)
        self.assertEqual(note_to_midi('F#4'), 66)
    
    def test_flats(self):
        """Test flat notes."""
        self.assertEqual(note_to_midi('Bb2'), 46)
        self.assertEqual(note_to_midi('Gb3'), 54)
    
    def test_invalid_note(self):
        """Test invalid note raises error."""
        with self.assertRaises(ValueError):
            note_to_midi('X4')
        with self.assertRaises(ValueError):
            note_to_midi('C')


class TestPossibleFrets(unittest.TestCase):
    """Test finding possible fret positions for notes."""
    
    def test_e2_open_string(self):
        """E2 should have fret 0 on low E string."""
        result = possible_frets(40)
        self.assertTrue(len(result) > 0)
        self.assertTrue(any(s == 0 and f == 0 for s, f in result))
    
    def test_e4_open_string(self):
        """E4 should have fret 0 on high E string."""
        result = possible_frets(64)
        self.assertTrue(len(result) > 0)
        self.assertTrue(any(s == 5 and f == 0 for s, f in result))
    
    def test_a4_multiple_positions(self):
        """A4 can be played on multiple strings."""
        result = possible_frets(69)  # A4
        self.assertTrue(len(result) >= 2)
    
    def test_high_note_no_position(self):
        """Very high notes may not be playable on guitar."""
        result = possible_frets(120)  # Very high C
        self.assertEqual(len(result), 0)


class TestChooseFingering(unittest.TestCase):
    """Test fingering selection algorithm."""
    
    def test_single_note(self):
        """Single note should return one position."""
        result = choose_fingering([40])  # E2
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], (0, 0))  # Low E string, open
    
    def test_two_notes_same_string(self):
        """Two notes on same string should stay on same string."""
        # E2 and F2 on low E string
        result = choose_fingering([40, 41])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], 0)  # Both on string 0
        self.assertEqual(result[1][0], 0)
    
    def test_chord(self):
        """Chord notes should be distributed across strings."""
        # C major chord: C3, E3, G3
        result = choose_fingering([48, 52, 55])
        self.assertEqual(len(result), 3)
        # All should be on different strings
        strings = [pos[0] for pos in result]
        self.assertEqual(len(set(strings)), 3)


class TestNotesToTab(unittest.TestCase):
    """Test full note to tab conversion."""
    
    def test_returns_string(self):
        """Should return a non-empty string."""
        result = notes_to_tab(['E4', 'G4', 'B4'])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
    
    def test_contains_six_lines(self):
        """Tab should have 6 lines for 6 strings."""
        result = notes_to_tab(['E4'])
        lines = result.split('\n')
        # 6 string lines + 1 header line
        self.assertGreaterEqual(len(lines), 7)
    
    def test_empty_input(self):
        """Empty input should return empty string."""
        result = notes_to_tab([])
        self.assertEqual(result, "")
    
    def test_single_note(self):
        """Single note should produce valid tab with string names."""
        result = notes_to_tab(['E4'])
        # Check that all string names are present
        self.assertIn('E|', result)  # Low E string line
        self.assertIn('A|', result)  # A string line
        self.assertIn('D|', result)  # D string line
        self.assertIn('G|', result)  # G string line
        self.assertIn('B|', result)  # B string line
        self.assertIn('e|', result)  # High E string line
        self.assertIn('E4', result)  # Note name in header
    
    def test_multiple_notes(self):
        """Multiple notes should be spaced correctly."""
        result = notes_to_tab(['E4', 'F4', 'G4'])
        self.assertIn('E4', result)
        self.assertIn('F4', result)
        self.assertIn('G4', result)
    
    def test_tab_format(self):
        """Test that tab has correct format with pipes."""
        result = notes_to_tab(['E4'])
        lines = result.split('\n')
        # Each string line should have format like "E|...|"
        for line in lines[:-1]:  # Skip header
            self.assertTrue(line.startswith('E|') or line.startswith('A|') or 
                           line.startswith('D|') or line.startswith('G|') or 
                           line.startswith('B|') or line.startswith('e|'))
            self.assertTrue(line.endswith('|'))


if __name__ == '__main__':
    unittest.main()
