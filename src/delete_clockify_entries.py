#!/usr/bin/env python3
"""
Clockify Entry Deletion Tool

This script helps delete time entries from Clockify within a specified date range.
It uses the clockify-cli tool to list and delete entries.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Delete Clockify time entries within a date range')
    parser.add_argument(
        '--start', 
        required=True,
        help='Start date for deletion (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end', 
        required=True,
        help='End date for deletion (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Ask for confirmation before deleting each entry'
    )
    return parser.parse_args()

def get_clockify_entries(start_date, end_date):
    """Get time entries from Clockify within the specified date range."""
    try:
        # Add one day to end_date to make the range inclusive
        # since clockify-cli's date range appears to be exclusive of the end date
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            inclusive_end = (end_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        except ValueError:
            # If date parsing fails, use the original end_date
            inclusive_end = end_date
        
        # Use clockify-cli report with JSON output to get entries
        result = subprocess.run(
            ["clockify-cli", "report", start_date, inclusive_end, "--json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the JSON output
        entries = json.loads(result.stdout)
        return entries
    except subprocess.CalledProcessError as e:
        print(f"Error getting Clockify entries: {e.stderr}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing Clockify entries JSON: {e}")
        return []

def format_entry_info(entry):
    """Format entry information for display."""
    start_time = entry.get('timeInterval', {}).get('start', 'Unknown')
    end_time = entry.get('timeInterval', {}).get('end', 'Ongoing')
    duration = entry.get('timeInterval', {}).get('duration', 'Unknown')
    description = entry.get('description', 'No description')
    project = entry.get('project', {}).get('name', 'No project')
    
    # Format start and end times for display
    if start_time != 'Unknown':
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            start_formatted = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            start_formatted = start_time
    else:
        start_formatted = start_time
    
    if end_time != 'Ongoing' and end_time != 'Unknown':
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            end_formatted = end_dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            end_formatted = end_time
    else:
        end_formatted = end_time
    
    return f"{start_formatted} - {end_formatted} ({duration}) | {project} | {description}"

def delete_clockify_entries(entries, dry_run=False, interactive=False):
    """Delete Clockify entries."""
    if not entries:
        print("No entries found to delete.")
        return
    
    success_count = 0
    skipped_count = 0
    
    print(f"Found {len(entries)} entries in the specified date range:")
    
    for entry in entries:
        entry_id = entry.get('id')
        if not entry_id:
            print("Skipping entry without ID")
            skipped_count += 1
            continue
        
        entry_info = format_entry_info(entry)
        
        if dry_run:
            print(f"Would delete: {entry_info}")
            success_count += 1
            continue
        
        if interactive:
            print(f"\nEntry: {entry_info}")
            confirm = input("Delete this entry? (y/N): ").lower().strip()
            if confirm != 'y':
                print("Skipped.")
                skipped_count += 1
                continue
        
        # Delete the entry
        try:
            print(f"Deleting: {entry_info}")
            result = subprocess.run(
                ["clockify-cli", "delete", entry_id, "-i=0"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"  Success: Entry deleted")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"  Error deleting entry {entry_id}: {e.stderr.strip()}")
            skipped_count += 1
    
    print(f"\nDeletion summary:")
    print(f"  Successfully {'processed' if dry_run else 'deleted'}: {success_count}")
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
    
    # Validate date formats
    try:
        datetime.strptime(args.start, '%Y-%m-%d')
        datetime.strptime(args.end, '%Y-%m-%d')
    except ValueError as e:
        print(f"Error: Invalid date format. Use YYYY-MM-DD format. {e}")
        sys.exit(1)
    
    # Get entries from Clockify
    print(f"Fetching entries from {args.start} to {args.end}...")
    entries = get_clockify_entries(args.start, args.end)
    
    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
    
    # Delete entries
    delete_clockify_entries(entries, args.dry_run, args.interactive)
    
    if not args.dry_run and not args.interactive:
        print("\nWarning: All entries in the date range have been permanently deleted!")

if __name__ == "__main__":
    main()