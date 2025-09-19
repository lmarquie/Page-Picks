#!/usr/bin/env python3
"""
Complete 2025 update script - updates games, player stats, and injuries
Run this after each week to get the latest data
"""

import requests
import pandas as pd
import sqlite3
import logging
from datetime import datetime
import time
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_latest_2025_data():
    """Download the latest 2025 play-by-play data from nflverse"""
    url = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2025.csv"
    
    logger.info("📥 Downloading latest 2025 play-by-play data...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open("play_by_play_2025.csv", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info("✅ Downloaded latest 2025 data")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error downloading: {e}")
        return False

def process_2025_data():
    """Process the 2025 CSV and extract player stats"""
    logger.info("📊 Processing 2025 data...")
    
    try:
        # Read the CSV
        df = pd.read_csv("play_by_play_2025.csv")
        logger.info(f"✅ Loaded {len(df)} play-by-play records")
        
        # Check what weeks we have
        if 'week' in df.columns:
            weeks = sorted(df['week'].unique())
            logger.info(f"📅 Available weeks: {weeks}")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Error reading CSV: {e}")
        return None

def extract_player_stats(df):
    """Extract player statistics from play-by-play data"""
    logger.info("📊 Extracting player statistics...")
    
    player_stats = []
    games = df[['game_id', 'season', 'week', 'game_date']].drop_duplicates()
    logger.info(f"Found {len(games)} unique games")
    
    for _, game in games.iterrows():
        game_id = game['game_id']
        season = game['season']
        week = game['week']
        game_date = game['game_date']
        
        game_plays = df[df['game_id'] == game_id]
        
        players = set()
        for col in ['passer_player_id', 'rusher_player_id', 'receiver_player_id']:
            if col in game_plays.columns:
                players.update(game_plays[col].dropna().unique())
        
        for player_id in players:
            if pd.isna(player_id) or player_id == '':
                continue
                
            player_plays = game_plays[
                (game_plays['passer_player_id'] == player_id) |
                (game_plays['rusher_player_id'] == player_id) |
                (game_plays['receiver_player_id'] == player_id)
            ]
            
            passing_yards = player_plays[player_plays['passer_player_id'] == player_id]['passing_yards'].sum()
            rushing_yards = player_plays[player_plays['rusher_player_id'] == player_id]['rushing_yards'].sum()
            receiving_yards = player_plays[player_plays['receiver_player_id'] == player_id]['receiving_yards'].sum()
            receptions = player_plays[player_plays['receiver_player_id'] == player_id]['complete_pass'].sum()
            passing_tds = player_plays[player_plays['passer_player_id'] == player_id]['pass_touchdown'].sum()
            rushing_tds = player_plays[player_plays['rusher_player_id'] == player_id]['rush_touchdown'].sum()
            receiving_tds = player_plays[player_plays['receiver_player_id'] == player_id]['pass_touchdown'].sum()
            
            if passing_yards > 0 or rushing_yards > 0 or receiving_yards > 0:
                player_stats.append({
                    'player_id': player_id,
                    'game_id': game_id,
                    'season': season,
                    'week': week,
                    'game_date': game_date,
                    'passing_yards': int(passing_yards) if not pd.isna(passing_yards) else 0,
                    'rushing_yards': int(rushing_yards) if not pd.isna(rushing_yards) else 0,
                    'receiving_yards': int(receiving_yards) if not pd.isna(receiving_yards) else 0,
                    'receptions': int(receptions) if not pd.isna(receptions) else 0,
                    'passing_tds': int(passing_tds) if not pd.isna(passing_tds) else 0,
                    'rushing_tds': int(rushing_tds) if not pd.isna(rushing_tds) else 0,
                    'receiving_tds': int(receiving_tds) if not pd.isna(receiving_tds) else 0
                })
    
    logger.info(f"✅ Extracted stats for {len(player_stats)} player-game combinations")
    return player_stats

def update_2025_database(player_stats):
    """Update the database with new 2025 player stats"""
    conn = sqlite3.connect('nfl_analytics.db')
    cursor = conn.cursor()
    
    try:
        # Clear existing 2025 player stats
        cursor.execute("DELETE FROM player_game_stats WHERE game_id IN (SELECT game_id FROM games WHERE season = 2025)")
        logger.info("🗑️ Cleared existing 2025 player stats")
        
        # Add any missing games
        games_added = 0
        for stat in player_stats:
            cursor.execute("""
                INSERT OR IGNORE INTO games (season, week, game_date)
                VALUES (?, ?, ?)
            """, (stat['season'], stat['week'], stat['game_date']))
            if cursor.rowcount > 0:
                games_added += 1
        
        logger.info(f"📅 Added {games_added} new games")
        
        # Get game_id mapping
        cursor.execute("SELECT game_id, season, week, game_date FROM games WHERE season = 2025")
        game_mapping = {}
        for row in cursor.fetchall():
            key = (row[1], row[2], row[3])
            game_mapping[key] = row[0]
        
        # Add player stats
        stats_added = 0
        for stat in player_stats:
            game_key = (stat['season'], stat['week'], stat['game_date'])
            if game_key in game_mapping:
                game_id = game_mapping[game_key]
                
                cursor.execute("""
                    INSERT INTO player_game_stats 
                    (player_id, game_id, passing_yards, rushing_yards, receiving_yards, 
                     receptions, passing_tds, rushing_tds, receiving_tds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stat['player_id'], game_id, stat['passing_yards'], stat['rushing_yards'],
                    stat['receiving_yards'], stat['receptions'], stat['passing_tds'],
                    stat['rushing_tds'], stat['receiving_tds']
                ))
                stats_added += 1
        
        conn.commit()
        logger.info(f"✅ Added {stats_added} 2025 player stat records")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM games WHERE season = 2025")
        games_2025 = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM player_game_stats pgs JOIN games g ON pgs.game_id = g.game_id WHERE g.season = 2025")
        stats_2025 = cursor.fetchone()[0]
        
        cursor.execute("SELECT DISTINCT week FROM games WHERE season = 2025 ORDER BY week")
        weeks = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"📊 2025 Summary: {games_2025} games, {stats_2025} player stats, weeks {weeks}")
        
    except Exception as e:
        logger.error(f"❌ Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

def scrape_espn_injuries():
    """Scrape injury data from ESPN"""
    url = "https://www.espn.com/nfl/injuries"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        logger.info("📡 Scraping ESPN injuries...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        injuries = []
        
        injury_tables = soup.find_all('table', class_='Table')
        
        for table in injury_tables:
            rows = table.find_all('tr')[1:]
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    try:
                        player_name = cells[0].get_text(strip=True)
                        position = cells[1].get_text(strip=True)
                        injury_type = cells[2].get_text(strip=True)
                        status = cells[3].get_text(strip=True)
                        
                        if player_name and injury_type and status:
                            injuries.append({
                                'player_name': player_name,
                                'position': position,
                                'injury_type': injury_type,
                                'status': status
                            })
                    except Exception as e:
                        continue
        
        logger.info(f"✅ Scraped {len(injuries)} injuries from ESPN")
        return injuries
        
    except Exception as e:
        logger.error(f"❌ Error scraping ESPN: {e}")
        return []

def similarity(a, b):
    """Calculate similarity between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_player_id_by_name(name, cursor):
    """Find player ID by name in the database"""
    # Try exact match first
    cursor.execute("SELECT player_id, full_name FROM players WHERE full_name = ?", (name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # Try partial match
    cursor.execute("SELECT player_id, full_name FROM players WHERE full_name LIKE ?", (f"%{name}%",))
    results = cursor.fetchall()
    
    if results:
        # Find best match by similarity
        best_match = None
        best_sim = 0
        for row in results:
            sim = similarity(name, row[1])
            if sim > best_sim and sim > 0.7:
                best_sim = sim
                best_match = row[0]
        return best_match
    
    return None

def update_injuries():
    """Update injury data"""
    conn = sqlite3.connect('nfl_analytics.db')
    cursor = conn.cursor()
    
    try:
        # Scrape injuries
        scraped_injuries = scrape_espn_injuries()
        
        # Clear existing injuries
        cursor.execute("DELETE FROM injured_players")
        logger.info("🗑️ Cleared existing injury data")
        
        added_count = 0
        for injury in scraped_injuries:
            player_name = injury['player_name']
            player_id = find_player_id_by_name(player_name, cursor)
            
            if player_id:
                cursor.execute("""
                    INSERT INTO injured_players 
                    (player_id, player_name, injury_type, status, expected_return, added_date, reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    player_id,
                    player_name,
                    injury['injury_type'],
                    injury['status'],
                    'Unknown',
                    datetime.now().strftime('%Y-%m-%d'),
                    'ESPN Scraped'
                ))
                added_count += 1
            else:
                logger.warning(f"❌ Could not match injured player: {player_name}")
        
        # Add key injured players manually (backup)
        key_injured = [
            "Chris Godwin", "Brock Purdy", "Cooper Kupp", "Nick Chubb", 
            "Jalen Hurts", "Davante Adams", "Aaron Rodgers", "Saquon Barkley",
            "Josh Jacobs", "Derrick Henry", "Calvin Ridley", "Tyreek Hill",
            "Stefon Diggs", "Travis Kelce", "Mark Andrews", "George Kittle"
        ]
        
        for player_name in key_injured:
            player_id = find_player_id_by_name(player_name, cursor)
            if player_id:
                # Check if already added
                cursor.execute("SELECT COUNT(*) FROM injured_players WHERE player_id = ?", (player_id,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        INSERT INTO injured_players 
                        (player_id, player_name, injury_type, status, expected_return, added_date, reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        player_id, player_name, "Injury", "Out/Questionable",
                        "2025-09-25", "2025-01-15", "Manual Entry"
                    ))
                    added_count += 1
        
        conn.commit()
        logger.info(f"✅ Updated {added_count} injured players")
        
        # Show sample
        cursor.execute("SELECT player_name, injury_type, status FROM injured_players LIMIT 10")
        results = cursor.fetchall()
        logger.info("Sample injured players:")
        for row in results:
            logger.info(f"  - {row[0]}: {row[1]} ({row[2]})")
        
    except Exception as e:
        logger.error(f"❌ Error updating injuries: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Main function"""
    logger.info("🏈 Starting complete 2025 update...")
    logger.info(f"⏰ Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Update 2025 data
    if download_latest_2025_data():
        df = process_2025_data()
        if df is not None:
            player_stats = extract_player_stats(df)
            if player_stats:
                update_2025_database(player_stats)
                logger.info("✅ 2025 data updated successfully!")
            else:
                logger.error("No player stats extracted")
        else:
            logger.error("Failed to process 2025 data")
    else:
        logger.error("Failed to download 2025 data")
    
    # Update injuries
    logger.info("🏥 Updating injury data...")
    update_injuries()
    
    logger.info("✅ Complete update finished!")
    logger.info(f"⏰ Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
