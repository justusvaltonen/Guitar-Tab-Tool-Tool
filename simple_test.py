#!/usr/bin/env python3
"""Quick syntax and import test for live_tab."""
try:
    from live_tab import find_closest_string_fret, freq_to_midi
    print("✓ Imports successful")
    
    # Test freq_to_midi
    result = freq_to_midi(82.41)  # E2 frequency
    print(f"✓ freq_to_midi(82.41) = {result}")
    
    # Test find_closest_string_fret
    match = find_closest_string_fret(82.41)
    if match:
        string_idx, fret, note, matched_freq = match
        print(f"✓ find_closest_string_fret(82.41) -> {note}{fret} (string {6-string_idx})")
    else:
        print("✗ find_closest_string_fret returned None")
        
    print("✓ All tests passed successfully")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
