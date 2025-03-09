#!/usr/bin/env python3
"""
Script to find and clean up duplicate messages in the database
"""
import sqlite3
import argparse
from datetime import datetime

def connect_to_db(db_path):
    """Connect to the SQLite database"""
    return sqlite3.connect(db_path)

def find_duplicate_messages(conn):
    """Find messages that have the same content, user_id, and conversation_id within a short time window"""
    cursor = conn.cursor()
    
    # Find potential duplicates by grouping by content, user_id, conversation_id, and role
    cursor.execute("""
    SELECT content, user_id, conversation_id, role, COUNT(*) as count
    FROM messages
    GROUP BY content, user_id, conversation_id, role
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
    """)
    
    potential_duplicates = cursor.fetchall()
    
    duplicates = []
    for content, user_id, conversation_id, role, count in potential_duplicates:
        # Get the specific message instances
        cursor.execute("""
        SELECT id, timestamp
        FROM messages
        WHERE content = ? AND user_id = ? AND conversation_id = ? AND role = ?
        ORDER BY timestamp
        """, (content, user_id, conversation_id, role))
        
        instances = cursor.fetchall()
        
        # Group instances that are within 5 seconds of each other
        for i in range(len(instances) - 1):
            id1, timestamp1 = instances[i]
            id2, timestamp2 = instances[i + 1]
            
            # Parse timestamps
            time1 = datetime.fromisoformat(timestamp1)
            time2 = datetime.fromisoformat(timestamp2)
            
            # Calculate time difference in seconds
            diff_seconds = (time2 - time1).total_seconds()
            
            # If less than 5 seconds apart, consider them duplicates
            if diff_seconds < 5:
                duplicates.append((id1, id2, content[:30], diff_seconds))
    
    return duplicates

def display_duplicates(duplicates):
    """Display the found duplicates"""
    if not duplicates:
        print("No duplicates found!")
        return
    
    print(f"Found {len(duplicates)} sets of duplicate messages:")
    print("\nID1\tID2\tContent\tTime Diff (s)")
    print("-" * 60)
    
    for id1, id2, content, diff in duplicates:
        print(f"{id1}\t{id2}\t{content}...\t{diff:.2f}")

def delete_newer_duplicates(conn, duplicates, dry_run=True):
    """Delete the newer of each duplicate pair (typically the second insert)"""
    if dry_run:
        print("\nDRY RUN: No messages will be deleted.")
    
    cursor = conn.cursor()
    deleted_count = 0
    
    for id1, id2, _, _ in duplicates:
        # We'll delete the message with the higher ID (newer one)
        delete_id = id2
        
        if dry_run:
            print(f"Would delete message ID: {delete_id}")
        else:
            cursor.execute("DELETE FROM messages WHERE id = ?", (delete_id,))
            deleted_count += 1
    
    if not dry_run:
        conn.commit()
        print(f"\nDeleted {deleted_count} duplicate messages.")

def main():
    parser = argparse.ArgumentParser(description='Find and clean up duplicate messages in the database')
    parser.add_argument('--db', default='assistant.db', help='Path to the database file (default: assistant.db)')
    parser.add_argument('--delete', action='store_true', help='Delete the newer duplicates (default: dry run)')
    
    args = parser.parse_args()
    
    conn = connect_to_db(args.db)
    duplicates = find_duplicate_messages(conn)
    display_duplicates(duplicates)
    
    if duplicates:
        delete_newer_duplicates(conn, duplicates, dry_run=not args.delete)
    
    conn.close()

if __name__ == "__main__":
    main() 