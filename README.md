# timew2clockify

A Python command-line tool that migrates time entries from Timewarrior to Clockify.

## Dependencies

This tool requires two external CLI tools:

1. **Timewarrior** (`timew`) - for exporting time entries
2. **clockify-cli** - for submitting entries to Clockify

### Installing clockify-cli

Download and install the latest clockify-cli release:

```bash
# Download the latest release for Linux x86_64
wget https://github.com/lucassabreu/clockify-cli/releases/download/v0.55.2/clockify-cli_Linux_x86_64.tar.gz

# Extract the binary
tar -xzf clockify-cli_Linux_x86_64.tar.gz

# Install to user bin directory (add ~/.local/bin to your PATH)
mkdir -p ~/.local/bin
cp clockify-cli ~/.local/bin/

# Or install system-wide (requires sudo)
sudo cp clockify-cli /usr/local/bin/

# Verify installation
clockify-cli version
```

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
```

2. Activate the virtual environment:

- On macOS/Linux:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Project


Run with dry run first - this lets you map projects to clockify and make sure it's all set up correctly. This will interactively ask you how timewarrior projects should be mapped to clockify.


```bash
python src/timew2clockify.py --dry-run --start 2025-05-01 --end 2025-05-31
```

To run the project, execute:

```bash
python src/timew2clockify.py --start 2025-05-01 --end 2025-05-31
```