#!/usr/bin/env python3
"""
Timewarrior to Clockify Migration Tool

This script helps migrate time entries from Timewarrior to Clockify using the clockify-cli tool.
It uses the first tag in each Timewarrior entry to map to a Clockify client/project.
"""

import argparse
import json
import subprocess
import sys
import os
from datetime import datetime, timedelta

# Config file for mapping timewarrior tags to clockify projects
DEFAULT_CONFIG_FILE = os.path.expanduser("~/.config/timew2clockify/mapping.conf")

def execute_command(command):
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        print(f"Command output: {output}")
        return output
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Command failed with output: {e.output}")
        print(f"Error executing command: {e}")
        return None

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Migrate Timewarrior entries to Clockify')
    parser.add_argument(
        '--config', 
        default=DEFAULT_CONFIG_FILE,
        help=f'Path to the mapping configuration file (default: {DEFAULT_CONFIG_FILE})'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be migrated without actually migrating'
    )
    parser.add_argument(
        '--start', 
        help='Start date for migration (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end', 
        help='End date for migration (YYYY-MM-DD)'
    )
    return parser.parse_args()

def load_mapping_config(config_file):
    """Load the mapping configuration from the config file."""
    mapping = {}
    
    # Create config directory if it doesn't exist
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    
    # Create config file with example if it doesn't exist
    if not os.path.exists(config_file):
        with open(config_file, 'w') as f:
            f.write("# Timewarrior tag to Clockify client/project mapping\n")
            f.write("# Format: tag=client/project\n")
            f.write("# Example:\n")
            f.write("# development=MyClient/WebApp\n")
            f.write("# meetings=Internal/Meetings\n")
        print(f"Created example config file at {config_file}")
        print("Please edit this file to define your tag mappings and run the script again.")
        sys.exit(1)
    
    # Load the mapping
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            parts = line.split('=', 1)
            if len(parts) != 2:
                print(f"Warning: Ignoring invalid mapping line: {line}")
                continue
                
            tag, project = parts
            client, proj = project.split('/', 1) if '/' in project else (project, "")
            mapping[tag.strip()] = (client.strip(), proj.strip())
    
    return mapping

def get_timewarrior_entries(start_date=None, end_date=None):
    """Get time entries from Timewarrior."""
    cmd = ["timew", "export"]
    
    if start_date:
        cmd.extend(["from", start_date])
    if end_date:
        cmd.extend(["to", end_date])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        entries = json.loads(result.stdout)
        return entries
    except subprocess.CalledProcessError as e:
        print(f"Error running Timewarrior export: {e}")
        print(f"Output: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing Timewarrior output: {e}")
        sys.exit(1)

def migrate_to_clockify(entries, mapping, dry_run=False):
    """Migrate Timewarrior entries to Clockify."""
    if not entries:
        print("No Timewarrior entries found to migrate.")
        return
    
    success_count = 0
    skipped_count = 0
    
    for entry in entries:
        # Skip entries without tags
        if not entry.get('tags'):
            print(f"Skipping entry without tags: {entry.get('start')} - {entry.get('end', 'ongoing')}")
            skipped_count += 1
            continue
        
        # Get the first tag
        first_tag = entry['tags'][0]
        
        # Look up the client/project in the mapping
        if first_tag not in mapping:
            print(f"Skipping entry with unmapped tag '{first_tag}': {entry.get('start')} - {entry.get('end', 'ongoing')}")
            skipped_count += 1
            continue
        
        client, project = mapping[first_tag]
        
        # Format the description (using all tags except the first one)
        description = " ".join(entry['tags'][1:]) if len(entry['tags']) > 1 else first_tag
        
        # Parse start and end times
        start_time = datetime.fromisoformat(entry['start'].replace('Z', '+00:00'))
        
        if 'end' in entry:
            end_time = datetime.fromisoformat(entry['end'].replace('Z', '+00:00'))
        else:
            # If no end time, skip the entry
            print(f"Skipping ongoing entry: {entry.get('start')} - {first_tag}")
            skipped_count += 1
            continue
        
        # Format times for clockify-cli
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S%z")
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S%z")
        
        # Build the clockify-cli command
        cmd = [
            "clockify-cli", "manual",
            "--client", client,
            "--project", project,
            "--description", description,
            "--when", start_str,
            "--when-to", end_str
        ]
        
        if dry_run:
            duration = end_time - start_time
            hours = duration.total_seconds() / 3600
            print(f"Would add: {start_time} - {end_time} ({hours:.2f}h) to {client}/{project}: {description}")
            success_count += 1
        else:
            try:
                print(f"Adding: {start_time} - {end_time} to {client}/{project}: {description}")
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print(f"  Success: {result.stdout.strip()}")
                success_count += 1
            except subprocess.CalledProcessError as e:
                print(f"  Error: {e.stderr.strip()}")
                skipped_count += 1
    
    print(f"\nMigration summary:")
    print(f"  Successfully {'processed' if dry_run else 'migrated'}: {success_count}")
    print(f"  Skipped: {skipped_count}")

def main():
    """Main function."""
    args = parse_arguments()

    clockify_check = execute_command("clockify-cli version")
    if clockify_check is None:
        print("Error: clockify-cli not found or not working properly.")
        print("Please install it from: https://github.com/lucassabreu/clockify-cli")
        sys.exit(1)
    
    # Check if timewarrior is available
    try:
        subprocess.run(["timew", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Timewarrior (timew) not found or not working properly.")
        print("Please install it from: https://github.com/GothenburgBitFactory/timewarrior")
        sys.exit(1)

    # Load mapping configuration
    mapping = load_mapping_config(args.config)
    if not mapping:
        print(f"Error: No valid mappings found in {args.config}")
        print("Please add at least one mapping in the format: tag=client/project")
        sys.exit(1)
    
    # Get timewarrior entries
    entries = get_timewarrior_entries(args.start, args.end)
    
    # Migrate entries to clockify
    migrate_to_clockify(entries, mapping, args.dry_run)

if __name__ == "__main__":
    main()