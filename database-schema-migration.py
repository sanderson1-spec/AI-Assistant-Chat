import sqlite3
import os
import sys

# Path to your database file
DB_PATH = "data/assistant.db"

def backup_database(db_path):
    """Create a backup of the database file"""
    if os.path.exists(db_path):
        backup_path = db_path + ".backup"
        print(f"Creating backup at: {backup_path}")
        
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        
        print("Backup created successfully")
        return True
    else:
        print(f"Database file not found at: {db_path}")
        return False

def migrate_database(db_path):
    """Migrate the database to the new schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get current schema
        cursor.execute("PRAGMA table_info(messages)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"Current message table columns: {column_names}")
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Add new columns if they don't exist
        new_columns = [
            ("parent_id", "INTEGER"), 
            ("is_edited", "INTEGER DEFAULT 0"),
            ("version", "INTEGER DEFAULT 1"),
            ("is_active_version", "INTEGER DEFAULT 1")
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in column_names:
                print(f"Adding column: {col_name}")
                cursor.execute(f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}")
        
        # Commit the transaction
        cursor.execute("COMMIT")
        print("Migration completed successfully")
        return True
        
    except Exception as e:
        # Rollback in case of error
        cursor.execute("ROLLBACK")
        print(f"Error during migration: {e}")
        return False
    finally:
        conn.close()

def main():
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        print(f"Database file does not exist at: {DB_PATH}")
        print("No migration needed - the updated schema will be created when the app runs.")
        return
    
    # Backup the database
    if backup_database(DB_PATH):
        # Migrate the database
        if migrate_database(DB_PATH):
            print("Database ready to use with new features!")
        else:
            print("Migration failed. Please restore from backup.")
    else:
        print("Could not create backup. Migration aborted.")

if __name__ == "__main__":
    main()
