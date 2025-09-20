#!/usr/bin/env python3
"""
Working NFL Analytics API
This is a production-ready API that works with the SQLite database
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import sqlite3
import json
from datetime import datetime

app = FastAPI(
    title="Page Picks NFL Analytics",
    description="Real NFL player statistics and betting line analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
def get_db_connection():
    return sqlite3.connect('nfl_analytics.db')

# Pydantic models
class PlayerAnalysis(BaseModel):
    player_name: str
    stat_type: str
    line_value: float
    games_analyzed: int
    hits: int
    hit_rate: float
    average_value: float

class PlayerStats(BaseModel):
    player_id: int
    player_name: str
    position: str
    team: str
    stat_value: float
    game_date: str
    week: int

# API Endpoints
@app.get("/", response_class=HTMLResponse)

async def root():
    """Redirect to demo page"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Page Picks - NFL Analytics</title>
        <script>
            // Redirect to demo page
            window.location.href = '/demo';
        </script>
    </head>
    <body>
        <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
            <h1>🏈 Page Picks NFL Analytics</h1>
            <p>Redirecting to demo page...</p>
            <p><a href="/demo">Click here if you're not redirected automatically</a></p>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        player_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "players": player_count
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/api/players")
async def get_players(
    team: Optional[str] = Query(None, description="Filter by team (e.g., DAL, BUF)"),
    position: Optional[str] = Query(None, description="Filter by position (e.g., QB, WR, RB)"),
    limit: int = Query(50, description="Maximum number of players to return")
):
    """Get all players with optional filtering"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT p.player_id, p.full_name, p.position, t.abbr as team, 
           p.jersey_number, p.height, p.weight, p.age, p.college, p.years_pro
    FROM players p
    LEFT JOIN teams t ON p.team_id = t.team_id
    WHERE 1=1
    """
    params = []
    
    if team:
        query += " AND t.abbr = ?"
        params.append(team.upper())
    
    if position:
        query += " AND p.position = ?"
        params.append(position.upper())
    
    query += " ORDER BY p.full_name LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    players = []
    for row in results:
        players.append({
            "player_id": row[0],
            "full_name": row[1],
            "position": row[2],
            "team": row[3],
            "jersey_number": row[4],
            "height": row[5],
            "weight": row[6],
            "age": row[7],
            "college": row[8],
            "years_pro": row[9]
        })
    
    conn.close()
    return {"players": players, "count": len(players)}

@app.get("/api/players/search")
async def search_players(
    query: str = Query("", description="Search term for player name"),
    position: str = Query("", description="Filter by position"),
    limit: int = Query(20, description="Maximum number of results")
):
    """Search for players by name"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build search query
    search_conditions = []
    params = []
    
    if query:
        search_conditions.append("p.full_name LIKE ?")
        params.append(f"%{query}%")
    
    if position:
        search_conditions.append("p.position = ?")
        params.append(position.upper())
    
    where_clause = "WHERE " + " AND ".join(search_conditions) if search_conditions else ""
    params.append(limit)
    
    sql_query = f"""
    SELECT p.player_id, p.full_name, p.position, t.abbr as team
    FROM players p
    LEFT JOIN teams t ON p.team_id = t.team_id
    {where_clause}
    ORDER BY p.full_name
    LIMIT ?
    """
    
    cursor.execute(sql_query, params)
    results = cursor.fetchall()
    
    players = []
    for row in results:
        players.append({
            "player_id": row[0],
            "player_name": row[1],
            "position": row[2],
            "team": row[3] or "Unknown"
        })
    
    conn.close()
    
    return {
        "query": query,
        "position": position,
        "players": players,
        "count": len(players)
    }

@app.get("/api/players/{player_id}")
async def get_player(player_id: str):
    """Get a specific player by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT p.player_id, p.full_name, p.position, t.abbr as team
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE p.player_id = ?
    """, (player_id,))
    
    result = cursor.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Player not found")
    
    conn.close()
    
    return {
        "player_id": result[0],
        "full_name": result[1],
        "position": result[2],
        "team": result[3] or "Unknown"
    }

def get_stat_column(stat_type):
    """Get the appropriate SQL column expression for a stat type"""
    if stat_type == 'total_yards':
        return "COALESCE(pgs.receiving_yards, 0) + COALESCE(pgs.rushing_yards, 0)"
    else:
        return f"pgs.{stat_type}"

def get_stat_condition(stat_type):
    """Get the appropriate WHERE condition for a stat type"""
    if stat_type == 'total_yards':
        return "(pgs.receiving_yards IS NOT NULL OR pgs.rushing_yards IS NOT NULL)"
    else:
        return f"pgs.{stat_type} IS NOT NULL"

@app.get("/api/players/{player_id}/analysis")
async def get_player_analysis(
    player_id: str,
    stat_type: str = Query("receiving_yards", description="Stat type to analyze"),
    line_value: float = Query(100.0, description="Line value to analyze"),
    games_back: int = Query(20, description="Number of recent games to analyze")
):
    """Analyze how often a player hits a specific line"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get player info
    cursor.execute("SELECT full_name FROM players WHERE player_id = ?", (player_id,))
    player_result = cursor.fetchone()
    if not player_result:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player_name = player_result[0]
    
    # Get last N games with the specified stat - ONLY REAL 2024 DATA
    stat_column = get_stat_column(stat_type)
    stat_condition = get_stat_condition(stat_type)
    
    query = f"""
    WITH last_games AS (
        SELECT 
            {stat_column} as stat_value,
            g.game_date,
            g.week,
            g.season,
            ROW_NUMBER() OVER (ORDER BY g.game_date DESC) as rn
        FROM players p
        JOIN player_game_stats pgs ON p.player_id = pgs.player_id
        JOIN games g ON pgs.game_id = g.game_id
        WHERE p.player_id = ? AND {stat_condition} AND g.season IN (2024, 2025)
    )
    SELECT 
        stat_value,
        game_date,
        week,
        season,
        rn,
        CASE WHEN stat_value >= ? THEN 1 ELSE 0 END as hit
    FROM last_games
    WHERE rn <= ?
    ORDER BY rn
    """
    
    cursor.execute(query, (player_id, line_value, games_back))
    results = cursor.fetchall()
    
    if not results:
        raise HTTPException(status_code=404, detail="No stats found for this player/stat combination")
    
    # Calculate analysis
    games_analyzed = len(results)
    hits = sum(row[5] for row in results)  # Updated to use the correct column index
    hit_rate = (hits / games_analyzed) * 100 if games_analyzed > 0 else 0
    average_value = sum(row[0] for row in results) / games_analyzed if games_analyzed > 0 else 0
    
    # Calculate 2025 season specific hit rate
    games_2025 = [row for row in results if row[3] == 2025]  # Filter for 2025 season
    games_2025_count = len(games_2025)
    hits_2025 = sum(row[5] for row in games_2025)
    hit_rate_2025 = (hits_2025 / games_2025_count) * 100 if games_2025_count > 0 else 0
    average_value_2025 = sum(row[0] for row in games_2025) / games_2025_count if games_2025_count > 0 else 0
    
    # Format game details
    games = []
    for row in results:
        games.append({
            "week": row[2],
            "season": row[3],
            "game_date": row[1],
            "stat_value": row[0],
            "hit": bool(row[5]),
            "game_number": row[4]  # This shows which game in the sequence (1-20)
        })
    
    conn.close()
    
    return {
        "player_id": player_id,
        "player_name": player_name,
        "stat_type": stat_type,
        "line_value": line_value,
        "games_analyzed": games_analyzed,
        "hits": hits,
        "hit_rate": round(hit_rate, 2),
        "average_value": round(average_value, 2),
        "games": games,
        "season_2025": {
            "games_analyzed": games_2025_count,
            "hits": hits_2025,
            "hit_rate": round(hit_rate_2025, 2),
            "average_value": round(average_value_2025, 2)
        }
    }

@app.get("/api/analytics/trending")
async def get_trending_players(
    stat_type: str = Query("receiving_yards", description="Stat type to analyze"),
    line_value: float = Query(100.0, description="Line value to analyze"),
    min_games: int = Query(10, description="Minimum games required"),
    limit: int = Query(20, description="Number of players to return")
):
    """Get trending players with highest hit rates"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    stat_column = get_stat_column(stat_type)
    stat_condition = get_stat_condition(stat_type)
    
    query = f"""
    WITH player_analysis AS (
        SELECT 
            p.player_id,
            p.full_name,
            p.position,
            t.abbr as team,
            COUNT(*) as games_analyzed,
            SUM(CASE WHEN {stat_column} >= ? THEN 1 ELSE 0 END) as hits,
            ROUND(100.0 * SUM(CASE WHEN {stat_column} >= ? THEN 1 ELSE 0 END) / COUNT(*), 2) as hit_rate,
            ROUND(AVG({stat_column}), 1) as avg_value
        FROM players p
        JOIN player_game_stats pgs ON p.player_id = pgs.player_id
        JOIN games g ON pgs.game_id = g.game_id
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE {stat_condition} 
          AND g.season IN (2024, 2025)
          AND p.player_id NOT IN (
              SELECT player_id FROM team_changes WHERE player_id IS NOT NULL
              UNION
              SELECT player_id FROM injured_players WHERE player_id IS NOT NULL
              UNION
              SELECT player_id FROM excluded_players WHERE active = 1 AND player_id IS NOT NULL
          )
        GROUP BY p.player_id, p.full_name, p.position, t.abbr
        HAVING COUNT(*) >= ?
    )
    SELECT 
        player_id, full_name, position, team, games_analyzed, hits, hit_rate, avg_value
    FROM player_analysis
    ORDER BY hit_rate DESC, games_analyzed DESC
    LIMIT ?
    """
    
    cursor.execute(query, (line_value, line_value, min_games, limit))
    results = cursor.fetchall()
    
    trending = []
    for row in results:
        trending.append({
            "player_id": row[0],
            "player_name": row[1],
            "position": row[2],
            "team": row[3],
            "games_analyzed": row[4],
            "hits": row[5],
            "hit_rate": row[6],
            "average_value": row[7]
        })
    
    conn.close()
    
    return {
        "stat_type": stat_type,
        "line_value": line_value,
        "trending_players": trending,
        "count": len(trending)
    }

@app.get("/api/analytics/position/{position}")
async def get_position_analysis(
    position: str,
    stat_type: str = Query("receiving_yards", description="Stat type to analyze"),
    line_value: float = Query(100.0, description="Line value to analyze"),
    min_games: int = Query(10, description="Minimum games required")
):
    """Analyze how often players at a position hit a specific line"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = f"""
    WITH position_analysis AS (
        SELECT 
            p.player_id,
            p.full_name,
            t.abbr as team,
            COUNT(*) as games_analyzed,
            SUM(CASE WHEN pgs.{stat_type} >= ? THEN 1 ELSE 0 END) as hits,
            ROUND(100.0 * SUM(CASE WHEN pgs.{stat_type} >= ? THEN 1 ELSE 0 END) / COUNT(*), 2) as hit_rate,
            ROUND(AVG(pgs.{stat_type}), 1) as avg_value
        FROM players p
        JOIN player_game_stats pgs ON p.player_id = pgs.player_id
        JOIN games g ON pgs.game_id = g.game_id
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE p.position = ? 
          AND pgs.{stat_type} IS NOT NULL 
          AND g.season IN (2024, 2025)
          AND p.player_id NOT IN (
              SELECT player_id FROM team_changes WHERE player_id IS NOT NULL
              UNION
              SELECT player_id FROM injured_players WHERE player_id IS NOT NULL
              UNION
              SELECT player_id FROM excluded_players WHERE active = 1 AND player_id IS NOT NULL
          )
        GROUP BY p.player_id, p.full_name, t.abbr
        HAVING COUNT(*) >= ?
    )
    SELECT 
        player_id, full_name, team, games_analyzed, hits, hit_rate, avg_value
    FROM position_analysis
    ORDER BY hit_rate DESC, games_analyzed DESC
    """
    
    cursor.execute(query, (line_value, line_value, position.upper(), min_games))
    results = cursor.fetchall()
    
    players = []
    for row in results:
        players.append({
            "player_id": row[0],
            "player_name": row[1],
            "team": row[2],
            "games_analyzed": row[3],
            "hits": row[4],
            "hit_rate": row[5],
            "average_value": row[6]
        })
    
    conn.close()
    
    return {
        "position": position,
        "stat_type": stat_type,
        "line_value": line_value,
        "total_players": len(players),
        "players": players
    }

@app.get("/api/picks/best")
async def get_best_picks(
    min_hit_rate: float = Query(70.0, description="Minimum hit rate percentage"),
    max_hit_rate: float = Query(90.0, description="Maximum hit rate percentage"),
    min_games: int = Query(5, description="Minimum games required"),
    limit: int = Query(100, description="Maximum number of picks to return")
):
    """Get all betting lines with realistic hit rates (70-90%) - EXCLUDING team changes and injured players"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Define position-appropriate stat types with realistic betting lines
    # Only using stats that exist in the database
    position_stats = {
        'QB': [
            ('passing_yards', [200.5, 225.5, 250.5, 275.5, 300.5]), 
            ('rushing_yards', [15.5, 20.5, 25.5, 30.5, 35.5])
        ],
        'WR': [
            ('receiving_yards', [40.5, 50.5, 60.5, 75.5, 90.5, 100.5]), 
            ('receptions', [2.5, 3.5, 4.5, 5.5, 6.5, 7.5]),
            ('rushing_yards', [5.5, 10.5, 15.5, 20.5]),
            ('total_yards', [45.5, 60.5, 75.5, 90.5, 105.5, 120.5])
        ],
        'RB': [
            ('rushing_yards', [40.5, 50.5, 60.5, 75.5, 90.5, 100.5]), 
            ('receiving_yards', [10.5, 20.5, 30.5, 40.5, 50.5]),
            ('receptions', [1.5, 2.5, 3.5, 4.5, 5.5]),
            ('total_yards', [50.5, 70.5, 90.5, 110.5, 130.5, 150.5])
        ],
        'TE': [
            ('receiving_yards', [25.5, 35.5, 45.5, 55.5, 65.5]), 
            ('receptions', [2.5, 3.5, 4.5, 5.5, 6.5]),
            ('total_yards', [25.5, 35.5, 45.5, 55.5, 65.5])
        ]
    }
    
    all_picks = []
    
    for position, stats_list in position_stats.items():
        for stat_type, line_values in stats_list:
            stat_column = get_stat_column(stat_type)
            stat_condition = get_stat_condition(stat_type)
            
            for line_value in line_values:
                cursor.execute(f"""
                    SELECT 
                        p.player_id,
                        p.full_name,
                        p.position,
                        t.abbr as team,
                        COUNT(*) as games_analyzed,
                        SUM(CASE WHEN {stat_column} >= ? THEN 1 ELSE 0 END) as hits,
                        ROUND(100.0 * SUM(CASE WHEN {stat_column} >= ? THEN 1 ELSE 0 END) / COUNT(*), 2) as hit_rate,
                        ROUND(AVG({stat_column}), 1) as avg_value
                    FROM players p
                    JOIN player_game_stats pgs ON p.player_id = pgs.player_id
                    JOIN games g ON pgs.game_id = g.game_id
                    LEFT JOIN teams t ON p.team_id = t.team_id
                    WHERE p.position = ? 
                      AND {stat_condition} 
                      AND g.season IN (2024, 2025)
                      AND p.player_id NOT IN (
                          SELECT player_id FROM team_changes WHERE player_id IS NOT NULL
                          UNION
                          SELECT player_id FROM injured_players WHERE player_id IS NOT NULL
                          UNION
                          SELECT player_id FROM excluded_players WHERE active = 1 AND player_id IS NOT NULL
                      )
                    GROUP BY p.player_id, p.full_name, p.position, t.abbr
                    HAVING COUNT(*) >= ? AND 
                           ROUND(100.0 * SUM(CASE WHEN {stat_column} >= ? THEN 1 ELSE 0 END) / COUNT(*), 2) >= ? AND
                           ROUND(100.0 * SUM(CASE WHEN {stat_column} >= ? THEN 1 ELSE 0 END) / COUNT(*), 2) <= ? AND
                           ? >= (AVG({stat_column}) * 0.75) AND ? <= (AVG({stat_column}) * 1.25)
                    ORDER BY hit_rate DESC, games_analyzed DESC
                """, (line_value, line_value, position, min_games, line_value, min_hit_rate, line_value, max_hit_rate, line_value, line_value))
                
                results = cursor.fetchall()
                
                for row in results:
                    all_picks.append({
                        "player_id": row[0],
                        "player_name": row[1],
                        "position": row[2],
                        "team": row[3] or "Unknown",
                        "stat_type": stat_type,
                        "line_value": line_value,
                        "games_analyzed": row[4],
                        "hits": row[5],
                        "hit_rate": row[6],
                        "average_value": row[7]
                    })
    
    # Sort all picks by hit rate
    all_picks.sort(key=lambda x: x['hit_rate'], reverse=True)
    
    conn.close()
    
    return {
        "min_hit_rate": min_hit_rate,
        "max_hit_rate": max_hit_rate,
        "min_games": min_games,
        "picks": all_picks[:limit],
        "count": len(all_picks[:limit]),
        "exclusions_applied": "Team changes, injuries, and other exclusions filtered out"
    }

@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    """Interactive demo page"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Page Picks - NFL Analytics Demo</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * { font-family: 'Inter', sans-serif; }
            .gradient-bg { 
                background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
            }
            .card-hover { 
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                backdrop-filter: blur(20px);
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            .card-hover:hover { 
                transform: translateY(-12px) scale(1.02);
                box-shadow: 0 25px 50px -12px rgba(234, 88, 12, 0.3);
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            .glass-effect {
                background: rgba(255, 255, 255, 0.15);
                backdrop-filter: blur(25px);
                border: 1px solid rgba(255, 255, 255, 0.25);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            .floating {
                animation: floating 3s ease-in-out infinite;
            }
            @keyframes floating {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-10px); }
            }
            .btn-modern {
                background: linear-gradient(135deg, rgba(234, 88, 12, 0.8) 0%, rgba(249, 115, 22, 0.8) 100%);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.3);
                transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
                box-shadow: 0 8px 32px rgba(234, 88, 12, 0.2);
            }
            .btn-modern:hover {
                transform: translateY(-3px) scale(1.05);
                box-shadow: 0 15px 35px rgba(234, 88, 12, 0.4);
                background: linear-gradient(135deg, rgba(234, 88, 12, 0.9) 0%, rgba(249, 115, 22, 0.9) 100%);
                border: 1px solid rgba(255, 255, 255, 0.4);
            }
            .btn-modern::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
                transition: left 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .btn-modern:hover::before {
                left: 100%;
            }
            .stat-card {
                background: linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 100%);
                backdrop-filter: blur(25px);
                border: 1px solid rgba(255,255,255,0.25);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            .liquid-glass {
                background: linear-gradient(135deg, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0.15) 100%);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255,255,255,0.3);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                position: relative;
                overflow: hidden;
            }
            .liquid-glass::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
            }
            .liquid-glass::after {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                animation: shimmer 3s infinite;
            }
            @keyframes shimmer {
                0% { left: -100%; }
                100% { left: 100%; }
            }
        </style>
    </head>
    <body class="bg-gradient-to-br from-orange-900 via-amber-900 to-yellow-900 min-h-screen">
        <!-- Liquid Glass Background -->
        <div class="fixed inset-0 overflow-hidden pointer-events-none">
            <div class="absolute -top-40 -right-40 w-96 h-96 bg-orange-500 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse"></div>
            <div class="absolute -bottom-40 -left-40 w-96 h-96 bg-amber-500 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse" style="animation-delay: 2s;"></div>
            <div class="absolute top-40 left-40 w-96 h-96 bg-yellow-500 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse" style="animation-delay: 4s;"></div>
            <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-orange-400 rounded-full mix-blend-multiply filter blur-2xl opacity-20 animate-pulse" style="animation-delay: 1s;"></div>
        </div>
        
        <div class="gradient-bg text-white py-20 relative">
            <div class="container mx-auto px-6 text-center relative z-10">
                <div class="floating mb-8">
                    <h1 class="text-7xl font-black mb-6 tracking-tight">
                        <span class="text-white drop-shadow-2xl">🏈</span>
                        <span class="text-white drop-shadow-2xl">Page Picks</span>
                    </h1>
                </div>
                <h2 class="text-3xl font-semibold text-white mb-4 tracking-wide">NFL Analytics & Betting Insights</h2>
                <p class="text-xl text-white max-w-3xl mx-auto leading-relaxed mb-8">
                    Real-time player statistics, hit rate analysis, and data-driven betting recommendations 
                    based on actual NFL performance data.
                </p>
                <div class="flex justify-center space-x-4 text-sm text-white">
                    <span class="px-6 py-3 liquid-glass rounded-full backdrop-blur-sm border border-white border-opacity-30">Real Data</span>
                    <span class="px-6 py-3 liquid-glass rounded-full backdrop-blur-sm border border-white border-opacity-30">Live Updates</span>
                    <span class="px-6 py-3 liquid-glass rounded-full backdrop-blur-sm border border-white border-opacity-30">AI-Powered</span>
                </div>
            </div>
        </div>
        
        <div class="container mx-auto px-4 py-12 relative z-10">
            
            <div class="liquid-glass card-hover rounded-2xl p-8 mb-8">
                <div class="flex items-center mb-6">
                    <div class="w-12 h-12 bg-gradient-to-r from-orange-500 to-amber-600 rounded-xl flex items-center justify-center mr-4 liquid-glass">
                        <span class="text-2xl">🔍</span>
                    </div>
                    <div>
                        <h2 class="text-3xl font-bold text-white">Live Player Analysis</h2>
                        <p class="text-white">Deep dive into individual player performance</p>
                    </div>
                </div>
                <div class="max-w-2xl mx-auto">
                    <div class="space-y-6">
                        <div>
                            <label class="block text-sm font-semibold text-white mb-3">Search Player</label>
                            <input type="text" id="playerSearch" placeholder="Type player name..." 
                                   class="w-full p-4 liquid-glass rounded-xl focus:ring-2 focus:ring-orange-300 transition-all duration-300 text-white placeholder-gray-300" onkeyup="searchPlayers()">
                            <div id="playerResults" class="mt-3 max-h-40 overflow-y-auto liquid-glass rounded-xl hidden shadow-lg">
                                <!-- Search results will appear here -->
                            </div>
                            <input type="hidden" id="selectedPlayerId" value="">
                            <div id="selectedPlayer" class="mt-3 p-4 liquid-glass rounded-xl border border-orange-300 border-opacity-30 hidden">
                                <span class="font-semibold text-orange-200">Selected: </span>
                                <span id="selectedPlayerName" class="text-orange-100"></span>
                            </div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-semibold text-white mb-3">Stat Type</label>
                                <select id="statSelect" class="w-full p-4 liquid-glass rounded-xl focus:ring-2 focus:ring-orange-300 transition-all duration-300 text-white">
                                    <option value="receiving_yards" class="bg-gray-800">Receiving Yards</option>
                                    <option value="passing_yards" class="bg-gray-800">Passing Yards</option>
                                    <option value="rushing_yards" class="bg-gray-800">Rushing Yards</option>
                                    <option value="receptions" class="bg-gray-800">Receptions</option>
                                    <option value="total_yards" class="bg-gray-800">Total Scrimmage Yards (Rush + Rec)</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm font-semibold text-white mb-3">Line Value</label>
                                <input type="number" id="lineValue" placeholder="100" 
                                       class="w-full p-4 liquid-glass rounded-xl focus:ring-2 focus:ring-orange-300 transition-all duration-300 text-white placeholder-gray-300" value="100">
                            </div>
                        </div>
                        <button onclick="runCustomAnalysis()" 
                                class="w-full btn-modern text-white py-4 px-6 rounded-xl font-semibold text-lg relative">
                            <span class="relative z-10">🚀 Analyze Player</span>
                        </button>
                    </div>
                </div>
                
                <div id="results" class="mt-8">
                    <div class="text-center py-12">
                        <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <span class="text-2xl">⚡</span>
                        </div>
                        <p class="text-white text-lg">Select a player above to see their analysis...</p>
                    </div>
                </div>
            </div>
            
            <div class="liquid-glass card-hover rounded-2xl p-8 mb-8">
                <div class="flex items-center mb-6">
                    <div class="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-600 rounded-xl flex items-center justify-center mr-4 liquid-glass">
                        <span class="text-2xl">🎯</span>
                    </div>
                    <div>
                        <h2 class="text-3xl font-bold text-white">Our Picks - Realistic Betting Lines</h2>
                        <p class="text-white">Sportsbook lines within 25% of player averages with 70-90% hit rates</p>
                    </div>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <button onclick="loadBestPicks(70, 90, 5)" 
                            class="group liquid-glass text-white py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg border border-orange-300 border-opacity-30">
                        <div class="flex items-center justify-center">
                            <span class="mr-2">📊</span>
                            <div class="text-left">
                                <div class="font-bold">All Picks</div>
                                <div class="text-sm opacity-90">70-90% Hit Rate</div>
                            </div>
                        </div>
                    </button>
                    <button onclick="loadBestPicks(75, 85, 5)" 
                            class="group liquid-glass text-white py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg border border-amber-300 border-opacity-30">
                        <div class="flex items-center justify-center">
                            <span class="mr-2">💎</span>
                            <div class="text-left">
                                <div class="font-bold">Solid Picks</div>
                                <div class="text-sm opacity-90">75-85% Hit Rate</div>
                            </div>
                        </div>
                    </button>
                    <button onclick="loadBestPicks(85, 95, 10)" 
                            class="group liquid-glass text-white py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg border border-yellow-300 border-opacity-30">
                        <div class="flex items-center justify-center">
                            <span class="mr-2">👑</span>
                            <div class="text-left">
                                <div class="font-bold">Elite Picks</div>
                                <div class="text-sm opacity-90">85-95% Hit Rate</div>
                            </div>
                        </div>
                    </button>
                </div>
                
                <div id="picksResults" class="space-y-4">
                    <div class="text-center py-12">
                        <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <span class="text-2xl">🎲</span>
                        </div>
                        <p class="text-white text-lg">Click a button above to load our best picks...</p>
                    </div>
                </div>
            </div>
            
            <div class="liquid-glass card-hover rounded-2xl p-8">
                <div class="flex items-center mb-6">
                    <div class="w-12 h-12 bg-gradient-to-r from-amber-500 to-yellow-600 rounded-xl flex items-center justify-center mr-4 liquid-glass">
                        <span class="text-2xl">📊</span>
                    </div>
                    <div>
                        <h2 class="text-3xl font-bold text-white">Position Analysis</h2>
                        <p class="text-white">Analyze players by position to find the best betting opportunities</p>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    <button onclick="loadPositionAnalysis('QB')" 
                            class="group liquid-glass text-white py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg border border-orange-300 border-opacity-30">
                        <div class="flex flex-col items-center">
                            <span class="text-2xl mb-2">🏈</span>
                            <div class="font-bold">Quarterbacks</div>
                            <div class="text-sm opacity-90">QB</div>
                        </div>
                    </button>
                    <button onclick="loadPositionAnalysis('WR')" 
                            class="group liquid-glass text-white py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg border border-amber-300 border-opacity-30">
                        <div class="flex flex-col items-center">
                            <span class="text-2xl mb-2">🏃</span>
                            <div class="font-bold">Wide Receivers</div>
                            <div class="text-sm opacity-90">WR</div>
                        </div>
                    </button>
                    <button onclick="loadPositionAnalysis('RB')" 
                            class="group liquid-glass text-white py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg border border-yellow-300 border-opacity-30">
                        <div class="flex flex-col items-center">
                            <span class="text-2xl mb-2">💪</span>
                            <div class="font-bold">Running Backs</div>
                            <div class="text-sm opacity-90">RB</div>
                        </div>
                    </button>
                    <button onclick="loadPositionAnalysis('TE')" 
                            class="group liquid-glass text-white py-4 px-6 rounded-xl font-semibold text-lg transition-all duration-300 hover:scale-105 hover:shadow-lg border border-orange-400 border-opacity-30">
                        <div class="flex flex-col items-center">
                            <span class="text-2xl mb-2">🎯</span>
                            <div class="font-bold">Tight Ends</div>
                            <div class="text-sm opacity-90">TE</div>
                        </div>
                    </button>
                </div>
                
                <div id="positionResults" class="space-y-4">
                    <div class="text-center py-12">
                        <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                            <span class="text-2xl">⚡</span>
                        </div>
                        <p class="text-white text-lg">Click a position above to see the best players...</p>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            async function analyzePlayer(playerId, statType, lineValue) {
                try {
                    const response = await fetch(`/api/players/${playerId}/analysis?stat_type=${statType}&line_value=${lineValue}`);
                    const data = await response.json();
                    displayResults(data);
                } catch (error) {
                    document.getElementById('results').innerHTML = `<p class="text-red-500">Error: ${error.message}</p>`;
                }
            }
            
            let searchTimeout;
            
            async function searchPlayers() {
                const query = document.getElementById('playerSearch').value.trim();
                const resultsDiv = document.getElementById('playerResults');
                
                // Clear previous timeout
                clearTimeout(searchTimeout);
                
                if (query.length < 2) {
                    resultsDiv.classList.add('hidden');
                    return;
                }
                
                // Show loading state
                resultsDiv.innerHTML = '<div class="p-2 text-white">Searching...</div>';
                resultsDiv.classList.remove('hidden');
                
                // Debounce the search
                searchTimeout = setTimeout(async () => {
                    try {
                        const response = await fetch(`/api/players/search?query=${encodeURIComponent(query)}&limit=15`);
                        
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        
                        const data = await response.json();
                        
                        if (data.players.length === 0) {
                            resultsDiv.innerHTML = '<div class="p-2 text-white">No players found. Try a different name.</div>';
                        } else {
                            resultsDiv.innerHTML = data.players.map(player => 
                                `<div class="p-2 hover:bg-blue-50 cursor-pointer border-b transition-colors" onclick="selectPlayer('${player.player_id}', '${player.player_name} (${player.position}) - ${player.team}')">
                                    <div class="font-medium">${player.player_name}</div>
                                    <div class="text-sm text-white">${player.position} - ${player.team}</div>
                                </div>`
                            ).join('');
                        }
                        resultsDiv.classList.remove('hidden');
                    } catch (error) {
                        console.error('Search error:', error);
                        resultsDiv.innerHTML = '<div class="p-2 text-red-500">Error searching players. Please try again.</div>';
                    }
                }, 300); // 300ms delay
            }
            
            function selectPlayer(playerId, playerName) {
                document.getElementById('selectedPlayerId').value = playerId;
                document.getElementById('selectedPlayerName').textContent = playerName;
                document.getElementById('selectedPlayer').classList.remove('hidden');
                document.getElementById('playerResults').classList.add('hidden');
                document.getElementById('playerSearch').value = '';
            }
            
            async function runCustomAnalysis() {
                const playerId = document.getElementById('selectedPlayerId').value;
                const statType = document.getElementById('statSelect').value;
                const lineValue = document.getElementById('lineValue').value;
                
                if (!playerId) {
                    alert('Please search and select a player');
                    return;
                }
                
                if (!lineValue) {
                    alert('Please enter a line value');
                    return;
                }
                
                await analyzePlayer(playerId, statType, parseFloat(lineValue));
            }
            
            function displayResults(data) {
                const resultsDiv = document.getElementById('results');
                
                const hitRateColor = data.hit_rate >= 60 ? 'text-green-600' : 
                                   data.hit_rate >= 40 ? 'text-yellow-600' : 'text-red-600';
                
                const hitRate2025Color = data.season_2025.hit_rate >= 60 ? 'text-green-400' : 
                                        data.season_2025.hit_rate >= 40 ? 'text-yellow-400' : 'text-red-400';
                
                resultsDiv.innerHTML = `
                    <div class="liquid-glass rounded-2xl p-8 border border-orange-300 border-opacity-30">
                        <h4 class="text-2xl font-bold text-white mb-6">${data.player_name} - ${data.stat_type.replace('_', ' ').toUpperCase()}</h4>
                        
                        <div class="grid md:grid-cols-3 gap-6">
                            <div class="liquid-glass rounded-xl p-6 border border-orange-200 border-opacity-20">
                                <h5 class="font-bold text-white mb-4 text-lg">Overall Analysis</h5>
                                <div class="space-y-3">
                                    <p class="text-gray-200"><strong>Line Value:</strong> ${data.line_value}+</p>
                                    <p class="text-gray-200"><strong>Games Analyzed:</strong> ${data.games_analyzed}</p>
                                    <p class="text-gray-200"><strong>Hits:</strong> ${data.hits}</p>
                                    <p class="text-gray-200"><strong>Hit Rate:</strong> <span class="${hitRateColor} font-bold text-lg">${data.hit_rate}%</span></p>
                                    <p class="text-gray-200"><strong>Average:</strong> ${data.average_value}</p>
                                </div>
                            </div>
                            
                            <div class="liquid-glass rounded-xl p-6 border border-orange-200 border-opacity-20">
                                <h5 class="font-bold text-white mb-4 text-lg">2025 Season</h5>
                                <div class="space-y-3">
                                    <p class="text-gray-200"><strong>Games:</strong> ${data.season_2025.games_analyzed}</p>
                                    <p class="text-gray-200"><strong>Hits:</strong> ${data.season_2025.hits}</p>
                                    <p class="text-gray-200"><strong>Hit Rate:</strong> <span class="${hitRate2025Color} font-bold text-lg">${data.season_2025.hit_rate}%</span></p>
                                    <p class="text-gray-200"><strong>Average:</strong> ${data.season_2025.average_value}</p>
                                </div>
                            </div>
                            
                            <div class="liquid-glass rounded-xl p-6 border border-orange-200 border-opacity-20 md:col-span-3">
                                <h5 class="font-bold text-white mb-4 text-lg">Last ${data.games_analyzed} Games Analyzed</h5>
                                <div class="max-h-80 overflow-y-auto space-y-2">
                                    ${data.games.map(game => `
                                        <div class="flex justify-between items-center text-sm p-3 liquid-glass rounded-lg border ${game.hit ? 'border-green-400 border-opacity-30' : 'border-red-400 border-opacity-30'}">
                                            <div class="flex flex-col">
                                                <span class="font-semibold text-white">${game.season} Week ${game.week}</span>
                                                <span class="text-xs text-gray-300">${game.game_date}</span>
                                            </div>
                                            <div class="text-right">
                                                <span class="font-bold text-lg ${game.hit ? 'text-green-400' : 'text-red-400'}">
                                                    ${game.stat_value} ${game.hit ? '✓' : '✗'}
                                                </span>
                                                <div class="text-xs text-gray-300">Game #${game.game_number}</div>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                                <div class="mt-2 text-xs text-gray-500 text-center">
                                    Showing all ${data.games_analyzed} games used in analysis
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            async function loadBestPicks(minHitRate, maxHitRate, minGames) {
                const resultsDiv = document.getElementById('picksResults');
                
                // Show loading state
                resultsDiv.innerHTML = '<div class="text-center py-4"><div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div><p class="mt-2 text-white">Loading best picks...</p></div>';
                
                try {
                    const response = await fetch(`/api/picks/best?min_hit_rate=${minHitRate}&max_hit_rate=${maxHitRate}&min_games=${minGames}&limit=100`);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.picks.length === 0) {
                        resultsDiv.innerHTML = `
                            <div class="text-center py-8">
                                <p class="text-white text-lg">No picks found with ${minHitRate}-${maxHitRate}% hit rate</p>
                                <p class="text-white text-sm">Try adjusting the hit rate range or minimum games requirement</p>
                            </div>
                        `;
                    } else {
                        resultsDiv.innerHTML = `
                            <div class="mb-4">
                                <h4 class="text-lg font-semibold text-white">Found ${data.count} picks with ${minHitRate}-${maxHitRate}% hit rate</h4>
                                <p class="text-sm text-white">Minimum ${minGames} games required</p>
                            </div>
                            <div class="grid gap-4">
                                ${data.picks.map(pick => {
                                    const hitRateColor = pick.hit_rate >= 90 ? 'text-green-600' : 
                                                       pick.hit_rate >= 85 ? 'text-blue-600' : 
                                                       pick.hit_rate >= 75 ? 'text-orange-600' : 'text-gray-600';
                                    
                                    return `
                                    <div class="border rounded-lg p-4 hover:shadow-md transition-shadow">
                                        <div class="flex justify-between items-start mb-2">
                                            <div>
                                                <h5 class="font-semibold text-lg">${pick.player_name}</h5>
                                                <p class="text-white">${pick.position} - ${pick.team}</p>
                                            </div>
                                            <div class="text-right">
                                                <div class="text-2xl font-bold ${hitRateColor}">${pick.hit_rate}%</div>
                                                <div class="text-sm text-white">Hit Rate</div>
                                            </div>
                                        </div>
                                        <div class="grid grid-cols-2 gap-4 text-sm">
                                            <div>
                                                <span class="font-medium">Stat:</span> ${pick.stat_type.replace('_', ' ').toUpperCase()}
                                            </div>
                                            <div>
                                                <span class="font-medium">Line:</span> Over ${pick.line_value}
                                            </div>
                                            <div>
                                                <span class="font-medium">Games:</span> ${pick.games_analyzed}
                                            </div>
                                            <div>
                                                <span class="font-medium">Hits:</span> ${pick.hits}/${pick.games_analyzed}
                                            </div>
                                        </div>
                                        <div class="mt-2 text-sm text-white">
                                            Average: ${pick.average_value} ${pick.stat_type.replace('_', ' ')}
                                        </div>
                                    </div>`;
                                }).join('')}
                            </div>
                        `;
                    }
                } catch (error) {
                    console.error('Error loading picks:', error);
                    resultsDiv.innerHTML = '<div class="text-center py-4 text-red-500">Error loading picks. Please try again.</div>';
                }
            }
            
            async function loadPositionAnalysis(position) {
                const resultsDiv = document.getElementById('positionResults');
                
                // Show loading state
                resultsDiv.innerHTML = '<div class="text-center py-4"><div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div><p class="mt-2 text-white">Loading position analysis...</p></div>';
                
                // Define position-appropriate stats (only using stats that exist in database)
                const positionStats = {
                    'QB': [
                        { stat: 'passing_yards', name: 'Passing Yards', lines: [200.5, 225.5, 250.5, 275.5, 300.5] },
                        { stat: 'rushing_yards', name: 'Rushing Yards', lines: [15.5, 20.5, 25.5, 30.5, 35.5] }
                    ],
                    'WR': [
                        { stat: 'receiving_yards', name: 'Receiving Yards', lines: [40.5, 50.5, 60.5, 75.5, 90.5, 100.5] },
                        { stat: 'receptions', name: 'Receptions', lines: [2.5, 3.5, 4.5, 5.5, 6.5, 7.5] },
                        { stat: 'rushing_yards', name: 'Rushing Yards', lines: [5.5, 10.5, 15.5, 20.5] }
                    ],
                    'RB': [
                        { stat: 'rushing_yards', name: 'Rushing Yards', lines: [40.5, 50.5, 60.5, 75.5, 90.5, 100.5] },
                        { stat: 'receiving_yards', name: 'Receiving Yards', lines: [10.5, 20.5, 30.5, 40.5, 50.5] },
                        { stat: 'receptions', name: 'Receptions', lines: [1.5, 2.5, 3.5, 4.5, 5.5] }
                    ],
                    'TE': [
                        { stat: 'receiving_yards', name: 'Receiving Yards', lines: [25.5, 35.5, 45.5, 55.5, 65.5] },
                        { stat: 'receptions', name: 'Receptions', lines: [2.5, 3.5, 4.5, 5.5, 6.5] }
                    ]
                };
                
                const stats = positionStats[position] || [];
                let allResults = [];
                
                try {
                    // Load data for each stat type
                    for (const statInfo of stats) {
                        for (const lineValue of statInfo.lines) {
                            const response = await fetch(`/api/analytics/position/${position}?stat_type=${statInfo.stat}&line_value=${lineValue}&min_games=5`);
                            
                            if (response.ok) {
                                const data = await response.json();
                                
                                // Add stat info to each player result
                                data.players.forEach(player => {
                                    allResults.push({
                                        ...player,
                                        stat_type: statInfo.stat,
                                        stat_name: statInfo.name,
                                        line_value: lineValue
                                    });
                                });
                            }
                        }
                    }
                    
                    if (allResults.length === 0) {
                        resultsDiv.innerHTML = `
                            <div class="text-center py-8">
                                <p class="text-white text-lg">No ${position} players found</p>
                                <p class="text-white text-sm">Try a different position or adjust the criteria</p>
                            </div>
                        `;
                    } else {
                        // Sort by hit rate and get top results
                        allResults.sort((a, b) => b.hit_rate - a.hit_rate);
                        const topResults = allResults.slice(0, 15);
                        
                        resultsDiv.innerHTML = `
                            <div class="mb-4">
                                <h4 class="text-lg font-semibold text-white">Top ${position} Players - All Stats</h4>
                                <p class="text-sm text-white">${allResults.length} total opportunities analyzed</p>
                            </div>
                            <div class="grid gap-4">
                                ${topResults.map(player => {
                                    const hitRateColor = player.hit_rate >= 90 ? 'text-green-600' : 
                                                       player.hit_rate >= 85 ? 'text-blue-600' : 
                                                       player.hit_rate >= 75 ? 'text-orange-600' : 'text-gray-600';
                                    
                                    return `
                                    <div class="border rounded-lg p-4 hover:shadow-md transition-shadow">
                                        <div class="flex justify-between items-start mb-2">
                                            <div>
                                                <h5 class="font-semibold text-lg">${player.player_name}</h5>
                                                <p class="text-white">${player.team}</p>
                                            </div>
                                            <div class="text-right">
                                                <div class="text-2xl font-bold ${hitRateColor}">${player.hit_rate}%</div>
                                                <div class="text-sm text-white">Hit Rate</div>
                                            </div>
                                        </div>
                                        <div class="grid grid-cols-2 gap-4 text-sm">
                                            <div>
                                                <span class="font-medium">Stat:</span> ${player.stat_name}
                                            </div>
                                            <div>
                                                <span class="font-medium">Line:</span> Over ${player.line_value}
                                            </div>
                                            <div>
                                                <span class="font-medium">Games:</span> ${player.games_analyzed}
                                            </div>
                                            <div>
                                                <span class="font-medium">Hits:</span> ${player.hits}/${player.games_analyzed}
                                            </div>
                                            <div>
                                                <span class="font-medium">Average:</span> ${player.average_value}
                                            </div>
                                            <div>
                                                <span class="font-medium">Value:</span> ${player.average_value >= player.line_value ? 'Good' : 'Under'}
                                            </div>
                                        </div>
                                    </div>`;
                                }).join('')}
                            </div>
                        `;
                    }
                } catch (error) {
                    console.error('Error loading position analysis:', error);
                    resultsDiv.innerHTML = '<div class="text-center py-4 text-red-500">Error loading position analysis. Please try again.</div>';
                }
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable (for production) or default to 8000
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(app, host="0.0.0.0", port=port)
