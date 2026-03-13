"""
One-time migration: adds delivered_at column to orders table.
Run once: python migrate_db.py
"""
import sqlite3, os, sys

# Find the database file
DB_PATHS = [
    os.path.join(os.path.dirname(__file__), 'instance', 'marketplace.db'),
    os.path.join(os.path.dirname(__file__), 'marketplace.db'),
]

db_path = None
for p in DB_PATHS:
    if os.path.exists(p):
        db_path = p
        break

if not db_path:
    print("❌  Database not found. Tried:")
    for p in DB_PATHS:
        print(f"     {p}")
    sys.exit(1)

print(f"📂  Found database: {db_path}")

conn = sqlite3.connect(db_path)
cur  = conn.cursor()

# Check existing columns
cur.execute("PRAGMA table_info(orders)")
cols = [row[1] for row in cur.fetchall()]
print(f"   Existing columns: {cols}")

added = []

if 'delivered_at' not in cols:
    cur.execute("ALTER TABLE orders ADD COLUMN delivered_at DATETIME")
    added.append('delivered_at')
    print("   ✓ Added delivered_at")
else:
    print("   — delivered_at already exists, skipping")

conn.commit()
conn.close()

if added:
    print(f"\n✅  Migration complete. Added: {added}")
else:
    print("\n✅  Database already up to date. Nothing changed.")
