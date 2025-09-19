from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models import Player, PlayerStats, StatType
from services.analytics_service import AnalyticsService
from services.nfl_data_service import NFLDataService, MockNFLDataService
import os

router = APIRouter()

# Use mock service if no API key is configured
nfl_service = MockNFLDataService() if not os.getenv("NFL_API_KEY") else NFLDataService()

@router.get("/")
async def get_players(
    team: Optional[str] = Query(None, description="Filter by team (e.g., DAL, BUF)"),
    position: Optional[str] = Query(None, description="Filter by position (e.g., QB, WR, RB)"),
    db: Session = Depends(get_db)
):
    """Get all players with optional filtering"""
    query = db.query(Player)
    
    if team:
        query = query.filter(Player.team == team.upper())
    if position:
        query = query.filter(Player.position == position.upper())
    
    players = query.all()
    return {"players": players, "count": len(players)}

@router.get("/{player_id}")
async def get_player(player_id: int, db: Session = Depends(get_db)):
    """Get a specific player by ID"""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player

@router.get("/{player_id}/stats")
async def get_player_stats(
    player_id: int,
    season: Optional[int] = Query(None, description="Filter by season"),
    week: Optional[int] = Query(None, description="Filter by week"),
    db: Session = Depends(get_db)
):
    """Get player statistics"""
    query = db.query(PlayerStats).filter(PlayerStats.player_id == player_id)
    
    if season:
        # Join with Game to filter by season
        query = query.join(Game).filter(Game.season == season)
    if week:
        query = query.join(Game).filter(Game.week == week)
    
    stats = query.all()
    return {"player_id": player_id, "stats": stats, "count": len(stats)}

@router.get("/{player_id}/line-analysis")
async def get_player_line_analysis(
    player_id: int,
    stat_type: str = Query(..., description="Stat type (e.g., receiving_yards, passing_yards)"),
    line_value: float = Query(..., description="Line value to analyze"),
    games_back: int = Query(20, description="Number of recent games to analyze"),
    db: Session = Depends(get_db)
):
    """Analyze how often a player hits a specific line"""
    try:
        stat_enum = StatType(stat_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stat type: {stat_type}")
    
    analytics = AnalyticsService(db)
    analysis = analytics.get_player_line_analysis(player_id, stat_enum, line_value, games_back)
    
    return analysis

@router.get("/{player_id}/multiple-lines")
async def get_multiple_line_analysis(
    player_id: int,
    stat_type: str = Query(..., description="Stat type"),
    line_values: str = Query(..., description="Comma-separated line values (e.g., 50,75,100)"),
    games_back: int = Query(20, description="Number of recent games to analyze"),
    db: Session = Depends(get_db)
):
    """Analyze multiple line values for the same player/stat"""
    try:
        stat_enum = StatType(stat_type)
        line_values_list = [float(x.strip()) for x in line_values.split(",")]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {e}")
    
    analytics = AnalyticsService(db)
    analysis = analytics.get_multiple_line_analysis(player_id, stat_enum, line_values_list, games_back)
    
    return analysis

@router.post("/sync")
async def sync_players(db: Session = Depends(get_db)):
    """Sync players from NFL API to database"""
    try:
        # Get players from NFL API
        players_data = await nfl_service.get_players()
        
        synced_count = 0
        for player_data in players_data:
            # Check if player already exists
            existing_player = db.query(Player).filter(Player.nfl_id == player_data["id"]).first()
            
            if not existing_player:
                # Create new player
                new_player = Player(
                    nfl_id=player_data["id"],
                    name=player_data["name"],
                    position=player_data["position"],
                    team=player_data["team"],
                    jersey_number=player_data.get("jersey_number"),
                    height=player_data.get("height"),
                    weight=player_data.get("weight"),
                    age=player_data.get("age"),
                    college=player_data.get("college"),
                    years_pro=player_data.get("years_pro")
                )
                db.add(new_player)
                synced_count += 1
        
        db.commit()
        return {"message": f"Synced {synced_count} new players", "total_players": len(players_data)}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error syncing players: {str(e)}")

# Import Game here to avoid circular imports
from models import Game


