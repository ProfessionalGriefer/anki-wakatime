# Anki Wakatime

[![wakatime](https://wakatime.com/badge/github/ProfessionalGriefer/ankiWakatime.svg)](https://wakatime.com/badge/github/ProfessionalGriefer/ankiWakatime)

A time tracking extension for Anki.
Perfect for other programmers who already use WakaTime.

## Contribute

### Getting started

Install Python 3.9 as Anki uses Python version 3.9

```bash
conda create -n ankiWakatime python=3.9
```

Install the code and the requirements

```bash
git clone https://github.com/ProfessionalGriefer/ankiWakatime.git
cd ankiWakatime
python -m pip install -r ./requirements.txt
ln -s . /Users/vincent/Library/Application Support/Anki2/addons21 # Only on MacOS
```

The last command creates a softlink from the current directory to the Anki's addon folder

To run Anki in Debug mode run the following commands for MacOS:

```bash
/Applications/Anki.app/Contents/MacOS/anki
```

Refer to the official [Anki Docs](https://addon-docs.ankiweb.net/console-output.html) for Linux or Windows.

### Understanding the directory

- `config.json`: To retrieve the WakaTime API key
- `config.md`: Short Addon Description under `Tools>Add-ons>Anki Wakatime`
- `__init__.py`: Entry file required for Anki
- `cli.py`: Functions to manage `wakatime-cli`
- `customTypes.py`: Type annotations for Mypy
- `download.py`: To download the [`wakatime-cli`](https://github.com/wakatime/wakatime-cli) tool
- `globals.py`: Constants and settings accessed by other files
- `helpers.py`: Helper functions
- `wakaType.py`: Calls the `wakatime-cli` tool with the necessary parameters
- `requirements.txt`: Lists all the required Python dependencies

Found my add-on useful? Consider buying me a coffee!
<a href="https://www.buymeacoffee.com/vincentnahn"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=☕&slug=vincentnahn&button_colour=800020&font_colour=ffffff&font_family=Inter&outline_colour=ffffff&coffee_colour=FFDD00" /></a>
