# Guitar Tab Tool

A lightweight command-line toolkit for working with guitar tablature.

## Features
- **Play** guitar tabs (ASCII format) as audio via MIDI synthesis
- **Create** tabs from live microphone input (real-time pitch detection)
- **Convert** musical notes to ASCII guitar tab

## Installation

### Prerequisites
- Python 3.8+
- FluidSynth (for audio rendering)
- A SoundFont file (e.g., FluidR3_GM.sf2)

### Setup

```bash
# Clone the repository
git clone https://github.com/justusvaltonen/Guitar-Tab-Tool-Tool.git
cd Guitar-Tab-Tool-Tool

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install fluidsynth fluid-soundfont-gm portaudio19-dev

# Install system dependencies (macOS)
brew install fluidsynth

# Install system dependencies (Windows)
# Download FluidSynth from https://www.fluidsynth.org/
# Install pyaudio: pip install pipwin && pipwin install pyaudio
```

## Usage

### Play a tab file (renders to WAV)
```bash
python play_tab.py my_song.txt
# Output: my_song.wav (play with aplay, ffplay, or any audio player)

python play_tab.py my_song.txt output.wav
```

### Live transcription
```bash
python live_tab.py
# Shows real-time tab as you play your guitar
# Press Ctrl+C to stop
```

### Convert notes to tab
```bash
python note_to_tab.py C4 E4 G4 B4
# Output: ASCII tab showing the notes on the guitar fretboard
```

## Project Structure
```
Guitar-Tab-Tool-Tool/
├── play_tab.py      # Tab file to WAV converter
├── live_tab.py      # Real-time audio to tab transcriber
├── note_to_tab.py   # Note to tab converter
├── tests/           # Unit tests
├── TabsGuitar/      # Example guitar tab files
├── TabsBass/        # Example bass tab files
└── requirements.txt # Python dependencies
```

## Testing

Run the unit tests:
```bash
python -m unittest discover tests/
```

Run the live tab tests (without microphone):
```bash
python test_live_tab.py
```

## Requirements
- Python 3.8+
- `mido` (for MIDI generation)
- `numpy` (for audio processing)
- `librosa` (for pitch detection)
- `pretty_midi` (for MIDI manipulation)
- `pyaudio` (for audio input)
- `fluidsynth` CLI (for WAV rendering)

## Troubleshooting

### "No module named 'mido'"
Run: `pip install -r requirements.txt`

### "fluidsynth not found"
Install FluidSynth:
- Ubuntu: `sudo apt-get install fluidsynth`
- macOS: `brew install fluidsynth`
- Windows: Download from https://www.fluidsynth.org/

### "SoundFont not found"
Install a SoundFont:
- Ubuntu: `sudo apt-get install fluid-soundfont-gm`
- Or download FluidR3_GM.sf2 and place it in the assets/ directory

### "pyaudio not found"
Install pyaudio:
- Linux: `sudo apt-get install portaudio19-dev && pip install pyaudio`
- macOS: `brew install portaudio && pip install pyaudio`
- Windows: `pip install pipwin && pipwin install pyaudio`

## License
MIT
