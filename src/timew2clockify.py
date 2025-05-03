#!/usr/bin/env python3
"""
Timewarrior to Clockify Migration Tool

This script helps migrate time entries from Timewarrior to Clockify using the clockify-cli tool.
It uses the second tag in each Timewarrior entry to map to a Clockify client/project.
The first tag is used as the description for the Clockify task.
"""

import argparse
import json
import subprocess
import sys
import os
from datetime import datetime, timedelta

# Config file for mapping timewarrior tags to clockify projects
DEFAULT_CONFIG_FILE = os.path.expanduser("~/.config/timew2clockify/mapping.conf")

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
    parser.add_argument(
        '--no-interactive',
        action='store_true',
        help='Skip interactive prompt for unmapped tags'
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

def save_mapping_to_config(config_file, tag, client, project):
    """Save a new tag mapping to the config file."""
    with open(config_file, 'a') as f:
        f.write(f"\n{tag}={client}/{project}")
    print(f"Added mapping for tag '{tag}' to config file: {client}/{project}")

def get_clockify_clients():
    """Get list of active clients from Clockify using JSON output."""
    try:
        result = subprocess.run(
            ["clockify-cli", "client", "list", "--not-archived", "--json"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Parse the JSON output
        clients = []
        client_data = json.loads(result.stdout)
        
        for client in client_data:
            clients.append({
                "id": client["id"],
                "name": client["name"]
            })
        
        return clients
    except subprocess.CalledProcessError as e:
        print(f"Error getting Clockify clients: {e.stderr}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing Clockify clients JSON: {e}")
        return []

def get_clockify_projects(client_id):
    """Get list of projects for a client from Clockify using JSON output."""
    try:
        result = subprocess.run(
            ["clockify-cli", "project", "list", "--clients", client_id, "--json"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Parse the JSON output
        projects = []
        project_data = json.loads(result.stdout)
        
        for project in project_data:
            projects.append({
                "id": project["id"],
                "name": project["name"]
            })
        
        return projects
    except subprocess.CalledProcessError as e:
        print(f"Error getting Clockify projects: {e.stderr}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing Clockify projects JSON: {e}")
        return []

def prompt_for_client_project(tag, config_file):
    """Prompt user to select a client and project for an unmapped tag."""
    print(f"\nTag '{tag}' is not mapped to any Clockify client/project.")
    print("Let's create a mapping for it.")
    
    # Get list of clients
    print("\nFetching available clients...")
    clients = get_clockify_clients()
    
    if not clients:
        print("No active clients found in Clockify.")
        return None, None
    
    # Display clients and let user choose
    print("\nAvailable clients:")
    for i, client in enumerate(clients, 1):
        print(f"{i}. {client['name']}")
    
    client_choice = input("\nSelect a client (enter number): ")
    try:
        client_index = int(client_choice) - 1
        if client_index < 0 or client_index >= len(clients):
            print("Invalid selection.")
            return None, None
        selected_client = clients[client_index]
    except ValueError:
        print("Invalid input, please enter a number.")
        return None, None
    
    # Get list of projects for the selected client
    print(f"\nFetching projects for client '{selected_client['name']}'...")
    projects = get_clockify_projects(selected_client['id'])
    
    if not projects:
        print(f"No active projects found for client '{selected_client['name']}'.")
        return None, None
    
    # Display projects and let user choose
    print("\nAvailable projects:")
    for i, project in enumerate(projects, 1):
        print(f"{i}. {project['name']}")
    
    project_choice = input("\nSelect a project (enter number): ")
    try:
        project_index = int(project_choice) - 1
        if project_index < 0 or project_index >= len(projects):
            print("Invalid selection.")
            return None, None
        selected_project = projects[project_index]
    except ValueError:
        print("Invalid input, please enter a number.")
        return None, None
    
    # Ask if user wants to save this mapping
    save_choice = input(f"\nSave this mapping ({tag}={selected_client['name']}/{selected_project['name']}) for future use? (y/n): ")
    if save_choice.lower() == 'y':
        save_mapping_to_config(config_file, tag, selected_client['name'], selected_project['name'])
    
    return selected_client['name'], selected_project['name']

def get_timewarrior_entries(start_date=None, end_date=None):
    """Get time entries from Timewarrior."""
    cmd = ["timew", "export"]
    
    if start_date:
        cmd.extend(["from", start_date])
    if end_date:
        cmd.extend(["-", end_date])
    
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

def migrate_to_clockify(entries, mapping, config_file, dry_run=False, interactive=True):
    """Migrate Timewarrior entries to Clockify."""
    if not entries:
        print("No Timewarrior entries found to migrate.")
        return
    
    success_count = 0
    skipped_count = 0
    
    # Cache for interactive selections
    interactive_cache = {}
    
    for entry in entries:
        # Skip entries without tags or with fewer than 2 tags
        if not entry.get('tags') or len(entry.get('tags', [])) < 2:
            print(f"Skipping entry with insufficient tags: {entry.get('start')} - {entry.get('end', 'ongoing')}")
            skipped_count += 1
            continue
        
        # Get the first tag for description
        description = entry['tags'][0]
        
        # Get the second tag for client/project mapping
        second_tag = entry['tags'][1]
        
        # Look up the client/project in the mapping
        if second_tag in mapping:
            client, project = mapping[second_tag]
        elif second_tag in interactive_cache:
            client, project = interactive_cache[second_tag]
        elif interactive:
            print(f"\nProcessing entry: {entry.get('start')} - {entry.get('end', 'ongoing')}")
            print(f"Tags: {', '.join(entry['tags'])}")
            
            client, project = prompt_for_client_project(second_tag, config_file)
            if client and project:
                interactive_cache[second_tag] = (client, project)
            else:
                print(f"Skipping entry with unmapped tag '{second_tag}'")
                skipped_count += 1
                continue
        else:
            print(f"Skipping entry with unmapped tag '{second_tag}': {entry.get('start')} - {entry.get('end', 'ongoing')}")
            skipped_count += 1
            continue
        
        # Parse start and end times
        start_time = datetime.fromisoformat(entry['start'].replace('Z', '+00:00'))
        
        if 'end' in entry:
            end_time = datetime.fromisoformat(entry['end'].replace('Z', '+00:00'))
        else:
            # If no end time, skip the entry
            print(f"Skipping ongoing entry: {entry.get('start')} - {', '.join(entry['tags'])}")
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
            "--when-to-close", end_str
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
    
    # Check if clockify-cli is available
    try:
        subprocess.run(["clockify-cli", "version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
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
        print(f"Warning: No valid mappings found in {args.config}")
        print("You'll be prompted to create mappings for unmapped tags.")
    
    # Get timewarrior entries
    entries = get_timewarrior_entries(args.start, args.end)
    
    # Migrate entries to clockify
    migrate_to_clockify(entries, mapping, args.config, args.dry_run, not args.no_interactive)

if __name__ == "__main__":
    main()