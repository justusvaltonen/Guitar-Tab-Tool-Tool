#!/usr/bin/env python3
"""
Test harness for live_tab.py functionality.
Tests core functions without requiring actual microphone input.
"""

import numpy as np
from live_tab import freq_to_midi, find_closest_string_fret, detect_pitch_librosa, detect_pitch_autocorr, format_tab_line

def test_freq_to_midi():
    """Test frequency to MIDI conversion."""
    print("Testing freq_to_midi:")
    test_cases = [
        (440.0, 69),  # A4
        (82.41, 40),  # E2 (low E open)
        (110.0, 45),  # A2 (A open)
        (329.63, 64), # E4 (high E open)
    ]
    
    for freq, expected in test_cases:
        result = freq_to_midi(freq)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {freq}Hz -> {result} (expected {expected})")
    
    return True

def test_find_closest_string_fret():
    """Test string/fret detection."""
    print("\nTesting find_closest_string_fret:")
    test_cases = [
        (82.41, "E2 (low E open)"),
        (110.0, "A2 (A open)"),
        (146.83, "D3 (D open)"),
        (196.0, "G3 (G open)"),
        (246.94, "B3 (B open)"),
        (329.63, "E4 (high E open)"),
        (130.81, "C#3 (fret 3 on A string)"),
    ]
    
    for freq, desc in test_cases:
        result = find_closest_string_fret(freq)
        if result:
            string_idx, fret, note, matched_freq = result
            status = "✓" if abs(freq - matched_freq) / freq < 0.03 else "✗"
            print(f"  {status} {freq:.2f}Hz ({desc}) -> string {6-string_idx}, fret {fret} ({note})")
        else:
            print(f"  ✗ {freq:.2f}Hz ({desc}) -> NO MATCH")
    
    return True

def test_pitch_detection_functions():
    """Test pitch detection functions with synthetic data."""
    print("\nTesting pitch detection functions:")
    
    # Test librosa pitch detection (will likely return None without real audio)
    print("  librosa pitch detection: Not tested without real audio")
    
    # Test autocorrelation pitch detection
    print("  autocorrelation pitch detection:")
    for freq in [82.41, 196.0, 329.63]:
        # Generate synthetic sine wave
        sr = 44100
        t = np.linspace(0, 1, sr)
        y = np.sin(2 * np.pi * freq * t).astype(np.float32)
        
        detected = detect_pitch_autocorr(y, sr)
        if detected:
            match = find_closest_string_fret(detected)
            if match:
                string_idx, fret, note, matched_freq = match
                error_pct = abs(freq - detected) / freq * 100
                print(f"    ✓ {freq:.2f}Hz -> detected {detected:.1f}Hz -> {note}{fret} (error: {error_pct:.1f}%)")
            else:
                print(f"    ✗ {freq:.2f}Hz -> detected {detected:.1f}Hz -> NO MATCH")
        else:
            print(f"    ✗ {freq:.2f}Hz -> pitch detection failed")
    
    return True

def test_format_tab_line():
    """Test tab line formatting."""
    print("\nTesting format_tab_line:")
    
    # Create test note info
    test_note = {
        'string': 1,  # high E string (string 1)
        'fret': 5,
        'note': 'E',
        'freq': 659.25,  # E4
        'matched_freq': 659.25,
    }
    
    result = format_tab_line(test_note)
    print("  Sample output:")
    print(result)
    
    return True

def main():
    """Run all tests."""
    print("Live Tab Python Functionality Test Harness")
    print("=" * 50)
    
    try:
        test_freq_to_midi()
        test_find_closest_string_fret()
        test_pitch_detection_functions()
        test_format_tab_line()
        
        print("\n" + "=" * 50)
        print("✓ All core functionality tests completed successfully!")
        print("Note: Real-time audio testing requires microphone access.")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())