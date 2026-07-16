#!/usr/bin/env python3
import unittest
from note_to_tab import note_to_midi, possible_frets, notes_to_tab


class TestNoteToTab(unittest.TestCase):
    def test_note_to_midi(self):
        self.assertEqual(note_to_midi('C4'), 60)
        self.assertEqual(note_to_midi('A4'), 69)
        self.assertEqual(note_to_midi('D#3'), 51)
        self.assertEqual(note_to_midi('Bb2'), 46)
        self.assertEqual(note_to_midi('E2'), 40)  # Standard low E

    def test_possible_frets(self):
        # E2 should have fret 0 on low E string (string 0)
        result = possible_frets(40)
        self.assertTrue(len(result) > 0)
        self.assertTrue(any(s == 0 and f == 0 for s, f in result))

    def test_notes_to_tab_returns_string(self):
        result = notes_to_tab(['E4', 'G4', 'B4'])
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


if __name__ == '__main__':
    unittest.main()
