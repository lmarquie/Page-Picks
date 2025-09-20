import sqlite3

# Connect to database
conn = sqlite3.connect('nfl_analytics.db')
cursor = conn.cursor()

# Get table info
cursor.execute("PRAGMA table_info(player_game_stats)")
columns = cursor.fetchall()

print("Player Game Stats columns:")
for col in columns:
    print(f"  {col[1]} - {col[2]}")

print("\nSample data:")
cursor.execute("SELECT * FROM player_game_stats LIMIT 1")
sample = cursor.fetchone()
if sample:
    print(f"Sample row: {sample}")
else:
    print("No data found")

conn.close()
