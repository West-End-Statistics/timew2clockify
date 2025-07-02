# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python command-line tool that migrates time entries from Timewarrior to Clockify. The tool:
- Extracts time entries from Timewarrior using `timew export`
- Maps Timewarrior tags to Clockify client/project combinations via a configuration file
- Uses the first tag as the task description and second tag for client/project mapping
- Submits entries to Clockify via the `clockify-cli` tool

## Dependencies

The project requires two external CLI tools:
- `timew` (Timewarrior) - for exporting time entries
- `clockify-cli` - for submitting entries to Clockify

## Development Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Tool

Basic usage:
```bash
python src/timew2clockify.py --start 2025-05-01 --end 2025-05-31
```

Key command-line options:
- `--dry-run`: Preview what would be migrated without actually doing it
- `--config`: Path to mapping configuration file (default: `~/.config/timew2clockify/mapping.conf`)
- `--no-interactive`: Skip interactive prompts for unmapped tags
- `--start`/`--end`: Date range for migration (YYYY-MM-DD format)

## Architecture

The tool follows a linear workflow:
1. **Configuration Loading** (`load_mapping_config`): Loads tag-to-client/project mappings from config file
2. **Data Extraction** (`get_timewarrior_entries`): Exports time entries from Timewarrior as JSON
3. **Interactive Mapping** (`prompt_for_client_project`): Handles unmapped tags by querying Clockify API for available clients/projects
4. **Migration** (`migrate_to_clockify`): Submits entries to Clockify using `clockify-cli`

Key design decisions:
- Uses subprocess calls to external tools rather than direct API integration
- Maintains a simple text-based configuration file for tag mappings
- Supports both interactive and non-interactive modes
- Caches interactive selections within a single run to avoid repeated prompts