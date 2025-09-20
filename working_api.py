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
    query = f"""
    WITH last_games AS (
        SELECT 
            pgs.{stat_type} as stat_value,
            g.game_date,
            g.week,
            g.season,
            ROW_NUMBER() OVER (ORDER BY g.game_date DESC) as rn
        FROM players p
        JOIN player_game_stats pgs ON p.player_id = pgs.player_id
        JOIN games g ON pgs.game_id = g.game_id
        WHERE p.player_id = ? AND pgs.{stat_type} IS NOT NULL AND g.season IN (2024, 2025)
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
        "games": games
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
    
    query = f"""
    WITH player_analysis AS (
        SELECT 
            p.player_id,
            p.full_name,
            p.position,
            t.abbr as team,
            COUNT(*) as games_analyzed,
            SUM(CASE WHEN pgs.{stat_type} >= ? THEN 1 ELSE 0 END) as hits,
            ROUND(100.0 * SUM(CASE WHEN pgs.{stat_type} >= ? THEN 1 ELSE 0 END) / COUNT(*), 2) as hit_rate,
            ROUND(AVG(pgs.{stat_type}), 1) as avg_value
        FROM players p
        JOIN player_game_stats pgs ON p.player_id = pgs.player_id
        JOIN games g ON pgs.game_id = g.game_id
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE pgs.{stat_type} IS NOT NULL 
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
            ('rushing_yards', [5.5, 10.5, 15.5, 20.5])
        ],
        'RB': [
            ('rushing_yards', [40.5, 50.5, 60.5, 75.5, 90.5, 100.5]), 
            ('receiving_yards', [10.5, 20.5, 30.5, 40.5, 50.5]),
            ('receptions', [1.5, 2.5, 3.5, 4.5, 5.5])
        ],
        'TE': [
            ('receiving_yards', [25.5, 35.5, 45.5, 55.5, 65.5]), 
            ('receptions', [2.5, 3.5, 4.5, 5.5, 6.5])
        ]
    }
    
    all_picks = []
    
    for position, stats_list in position_stats.items():
        for stat_type, line_values in stats_list:
            for line_value in line_values:
                cursor.execute(f"""
                    SELECT 
                        p.player_id,
                        p.full_name,
                        p.position,
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
                    GROUP BY p.player_id, p.full_name, p.position, t.abbr
                    HAVING COUNT(*) >= ? AND 
                           ROUND(100.0 * SUM(CASE WHEN pgs.{stat_type} >= ? THEN 1 ELSE 0 END) / COUNT(*), 2) >= ? AND
                           ROUND(100.0 * SUM(CASE WHEN pgs.{stat_type} >= ? THEN 1 ELSE 0 END) / COUNT(*), 2) <= ? AND
                           ? >= (AVG(pgs.{stat_type}) * 0.75) AND ? <= (AVG(pgs.{stat_type}) * 1.25)
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
    </head>
    <body class="bg-gray-100 min-h-screen">
        <div class="container mx-auto px-4 py-8">
            <div class="text-center mb-12">
                <h1 class="text-5xl font-bold text-gray-800 mb-4">🏈 Page Picks</h1>
                <h2 class="text-2xl text-gray-600 mb-2">NFL Analytics & Betting Insights</h2>
                <p class="text-gray-500 max-w-2xl mx-auto">Real-time player statistics, hit rate analysis, and data-driven betting recommendations based on actual NFL performance data.</p>
            </div>
            
            <div class="bg-white rounded-lg shadow-lg p-8 mb-8">
                <h2 class="text-2xl font-semibold mb-4">Live Player Analysis</h2>
                <div class="max-w-2xl mx-auto">
                    <div>
                        <h3 class="text-lg font-semibold mb-4">Custom Analysis</h3>
                        <div class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium mb-2">Search Player</label>
                                <input type="text" id="playerSearch" placeholder="Type player name..." 
                                       class="w-full p-2 border rounded" onkeyup="searchPlayers()">
                                <div id="playerResults" class="mt-2 max-h-40 overflow-y-auto border rounded bg-white hidden">
                                    <!-- Search results will appear here -->
                                </div>
                                <input type="hidden" id="selectedPlayerId" value="">
                                <div id="selectedPlayer" class="mt-2 p-2 bg-blue-50 rounded hidden">
                                    <span class="font-medium">Selected: </span>
                                    <span id="selectedPlayerName"></span>
                                </div>
                            </div>
                            <select id="statSelect" class="w-full p-2 border rounded">
                                <option value="receiving_yards">Receiving Yards</option>
                                <option value="passing_yards">Passing Yards</option>
                                <option value="rushing_yards">Rushing Yards</option>
                                <option value="receptions">Receptions</option>
                            </select>
                            <input type="number" id="lineValue" placeholder="Line Value" 
                                   class="w-full p-2 border rounded" value="100">
                            <button onclick="runCustomAnalysis()" 
                                    class="w-full bg-indigo-500 text-white py-2 px-4 rounded hover:bg-indigo-600">
                                Analyze
                            </button>
                        </div>
                    </div>
                </div>
                
                <div id="results" class="mt-8">
                    <p class="text-gray-500">Select a player above to see their analysis...</p>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow-lg p-8 mb-8">
                <h2 class="text-2xl font-semibold mb-4">🎯 Our Picks - Realistic Betting Lines</h2>
                <p class="text-gray-600 mb-6">Sportsbook lines within 25% of player averages with 70-90% hit rates</p>
                
                <div class="flex gap-4 mb-6">
                    <button onclick="loadBestPicks(70, 90, 5)" 
                            class="bg-green-500 text-white py-2 px-4 rounded hover:bg-green-600">
                        All Picks (70-90%)
                    </button>
                    <button onclick="loadBestPicks(75, 85, 5)" 
                            class="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600">
                        Solid Picks (75-85%)
                    </button>
                    <button onclick="loadBestPicks(85, 95, 10)" 
                            class="bg-purple-500 text-white py-2 px-4 rounded hover:bg-purple-600">
                        Elite Picks (85-95%)
                    </button>
                </div>
                
                <div id="picksResults" class="space-y-4">
                    <p class="text-gray-500">Click a button above to load our best picks...</p>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow-lg p-8">
                <h2 class="text-2xl font-semibold mb-4">📊 Position Analysis</h2>
                <p class="text-gray-600 mb-6">Analyze players by position to find the best betting opportunities</p>
                
                <div class="flex gap-4 mb-6">
                    <button onclick="loadPositionAnalysis('QB')" 
                            class="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600">
                        Quarterbacks
                    </button>
                    <button onclick="loadPositionAnalysis('WR')" 
                            class="bg-green-500 text-white py-2 px-4 rounded hover:bg-green-600">
                        Wide Receivers
                    </button>
                    <button onclick="loadPositionAnalysis('RB')" 
                            class="bg-orange-500 text-white py-2 px-4 rounded hover:bg-orange-600">
                        Running Backs
                    </button>
                    <button onclick="loadPositionAnalysis('TE')" 
                            class="bg-purple-500 text-white py-2 px-4 rounded hover:bg-purple-600">
                        Tight Ends
                    </button>
                </div>
                
                <div id="positionResults" class="space-y-4">
                    <p class="text-gray-500">Click a position above to see the best players...</p>
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
                resultsDiv.innerHTML = '<div class="p-2 text-gray-500">Searching...</div>';
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
                            resultsDiv.innerHTML = '<div class="p-2 text-gray-500">No players found. Try a different name.</div>';
                        } else {
                            resultsDiv.innerHTML = data.players.map(player => 
                                `<div class="p-2 hover:bg-blue-50 cursor-pointer border-b transition-colors" onclick="selectPlayer('${player.player_id}', '${player.player_name} (${player.position}) - ${player.team}')">
                                    <div class="font-medium">${player.player_name}</div>
                                    <div class="text-sm text-gray-600">${player.position} - ${player.team}</div>
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
                
                resultsDiv.innerHTML = `
                    <div class="bg-gray-50 rounded-lg p-6">
                        <h4 class="text-xl font-semibold mb-4">${data.player_name} - ${data.stat_type.replace('_', ' ').toUpperCase()}</h4>
                        
                        <div class="grid md:grid-cols-2 gap-6">
                            <div>
                                <h5 class="font-semibold mb-2">Analysis Results</h5>
                                <div class="space-y-2">
                                    <p><strong>Line Value:</strong> ${data.line_value}+</p>
                                    <p><strong>Games Analyzed:</strong> ${data.games_analyzed}</p>
                                    <p><strong>Hits:</strong> ${data.hits}</p>
                                    <p><strong>Hit Rate:</strong> <span class="${hitRateColor} font-bold">${data.hit_rate}%</span></p>
                                    <p><strong>Average:</strong> ${data.average_value}</p>
                                </div>
                            </div>
                            
                            <div>
                                <h5 class="font-semibold mb-2">Last ${data.games_analyzed} Games Analyzed</h5>
                                <div class="max-h-80 overflow-y-auto space-y-1">
                                    ${data.games.map(game => `
                                        <div class="flex justify-between items-center text-sm p-2 bg-white rounded border-l-4 ${game.hit ? 'border-green-400' : 'border-red-400'}">
                                            <div class="flex flex-col">
                                                <span class="font-medium">${game.season} Week ${game.week}</span>
                                                <span class="text-xs text-gray-500">${game.game_date}</span>
                                            </div>
                                            <div class="text-right">
                                                <span class="font-bold ${game.hit ? 'text-green-600' : 'text-red-600'}">
                                                    ${game.stat_value} ${game.hit ? '✓' : '✗'}
                                                </span>
                                                <div class="text-xs text-gray-500">Game #${game.game_number}</div>
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
                resultsDiv.innerHTML = '<div class="text-center py-4"><div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div><p class="mt-2 text-gray-500">Loading best picks...</p></div>';
                
                try {
                    const response = await fetch(`/api/picks/best?min_hit_rate=${minHitRate}&max_hit_rate=${maxHitRate}&min_games=${minGames}&limit=100`);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    if (data.picks.length === 0) {
                        resultsDiv.innerHTML = `
                            <div class="text-center py-8">
                                <p class="text-gray-500 text-lg">No picks found with ${minHitRate}-${maxHitRate}% hit rate</p>
                                <p class="text-gray-400 text-sm">Try adjusting the hit rate range or minimum games requirement</p>
                            </div>
                        `;
                    } else {
                        resultsDiv.innerHTML = `
                            <div class="mb-4">
                                <h4 class="text-lg font-semibold text-gray-800">Found ${data.count} picks with ${minHitRate}-${maxHitRate}% hit rate</h4>
                                <p class="text-sm text-gray-600">Minimum ${minGames} games required</p>
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
                                                <p class="text-gray-600">${pick.position} - ${pick.team}</p>
                                            </div>
                                            <div class="text-right">
                                                <div class="text-2xl font-bold ${hitRateColor}">${pick.hit_rate}%</div>
                                                <div class="text-sm text-gray-500">Hit Rate</div>
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
                                        <div class="mt-2 text-sm text-gray-500">
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
                resultsDiv.innerHTML = '<div class="text-center py-4"><div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div><p class="mt-2 text-gray-500">Loading position analysis...</p></div>';
                
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
                                <p class="text-gray-500 text-lg">No ${position} players found</p>
                                <p class="text-gray-400 text-sm">Try a different position or adjust the criteria</p>
                            </div>
                        `;
                    } else {
                        // Sort by hit rate and get top results
                        allResults.sort((a, b) => b.hit_rate - a.hit_rate);
                        const topResults = allResults.slice(0, 15);
                        
                        resultsDiv.innerHTML = `
                            <div class="mb-4">
                                <h4 class="text-lg font-semibold text-gray-800">Top ${position} Players - All Stats</h4>
                                <p class="text-sm text-gray-600">${allResults.length} total opportunities analyzed</p>
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
                                                <p class="text-gray-600">${player.team}</p>
                                            </div>
                                            <div class="text-right">
                                                <div class="text-2xl font-bold ${hitRateColor}">${player.hit_rate}%</div>
                                                <div class="text-sm text-gray-500">Hit Rate</div>
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
