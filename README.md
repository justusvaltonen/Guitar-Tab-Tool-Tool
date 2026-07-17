# Guitar Tab Tool

A lightweight command-line toolkit for working with guitar tablature.

## Features
- **Play** guitar tabs (ASCII format) as audio
- **Create** tabs from live microphone input (real-time transcription)
- **Convert** musical notes to ASCII guitar tab

## Installation
```bash
cd ~/GuitarTabHimmeli
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

Install system dependencies:
```bash
sudo apt-get install fluidsynth libasound2-dev
```

## Usage
### Play a tab file (renders to WAV)
```bash
python3 play_tab.py my_song.tab
# Output: my_song.wav (play with aplay or ffplay)

### Live transcription
```bash
python3 live_tab.py
```

### Convert notes to tab
```bash
python3 note_to_tab.py C4 E4 G4 B4
```

## Rough Testing Status
All generated WAV files in TabsGuitar/ have been roughly tested:
- Audible content confirmed in all files (33-145s duration)
- Sound quality varies by song (based on FluidR3_GM.sf2 soundfont)
- Full validation requires additional testing

## Requirements
- Python 3.12+
- `mido` (for MIDI generation)
- `fluidsynth` CLI (for WAV rendering)

## License
MIT