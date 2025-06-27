#!/usr/bin/env python3
"""
Database migration script to add reactflow_data column to existing processes
Run this once after updating the Process model
"""

import sqlite3
import sys
import os

# Add the backend directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def migrate_database():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'knowledge_transfer.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(processes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'reactflow_data' in columns:
            print("Column 'reactflow_data' already exists in processes table")
        else:
            # Add the new column
            cursor.execute("ALTER TABLE processes ADD COLUMN reactflow_data TEXT")
            print("Successfully added 'reactflow_data' column to processes table")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    print("Running database migration...")
    success = migrate_database()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1) 