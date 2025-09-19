from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models import Player, StatType
from services.analytics_service import AnalyticsService

router = APIRouter()

@router.get("/position/{position}")
async def get_position_analysis(
    position: str,
    stat_type: str = Query(..., description="Stat type (e.g., receiving_yards)"),
    line_value: float = Query(..., description="Line value to analyze"),
    games_back: int = Query(20, description="Number of recent games to analyze"),
    db: Session = Depends(get_db)
):
    """Analyze how often players at a position hit a specific line"""
    try:
        stat_enum = StatType(stat_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stat type: {stat_type}")
    
    analytics = AnalyticsService(db)
    analysis = analytics.get_position_analysis(position.upper(), stat_enum, line_value, games_back)
    
    return analysis

@router.get("/team/{team}")
async def get_team_analysis(
    team: str,
    stat_type: str = Query(..., description="Stat type"),
    line_value: float = Query(..., description="Line value to analyze"),
    games_back: int = Query(20, description="Number of recent games to analyze"),
    db: Session = Depends(get_db)
):
    """Analyze how often players from a team hit a specific line"""
    try:
        stat_enum = StatType(stat_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stat type: {stat_type}")
    
    analytics = AnalyticsService(db)
    analysis = analytics.get_team_analysis(team.upper(), stat_enum, line_value, games_back)
    
    return analysis

@router.get("/trending")
async def get_trending_players(
    stat_type: str = Query(..., description="Stat type"),
    line_value: float = Query(..., description="Line value to analyze"),
    min_games: int = Query(10, description="Minimum games required"),
    games_back: int = Query(20, description="Number of recent games to analyze"),
    limit: int = Query(20, description="Number of players to return"),
    db: Session = Depends(get_db)
):
    """Get trending players with highest hit rates for a specific line"""
    try:
        stat_enum = StatType(stat_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stat type: {stat_type}")
    
    # Get all players
    players = db.query(Player).all()
    
    analytics = AnalyticsService(db)
    trending_players = []
    
    for player in players:
        analysis = analytics.get_player_line_analysis(player.id, stat_enum, line_value, games_back)
        
        if analysis["games_analyzed"] >= min_games:
            trending_players.append({
                "player_id": player.id,
                "player_name": player.name,
                "position": player.position.value,
                "team": player.team,
                "hit_rate": analysis["hit_rate"],
                "games_analyzed": analysis["games_analyzed"],
                "average_value": analysis["average_value"]
            })
    
    # Sort by hit rate and limit results
    trending_players.sort(key=lambda x: x["hit_rate"], reverse=True)
    trending_players = trending_players[:limit]
    
    return {
        "stat_type": stat_type,
        "line_value": line_value,
        "trending_players": trending_players,
        "count": len(trending_players)
    }

@router.get("/comparison")
async def compare_players(
    player_ids: str = Query(..., description="Comma-separated player IDs"),
    stat_type: str = Query(..., description="Stat type"),
    line_value: float = Query(..., description="Line value to analyze"),
    games_back: int = Query(20, description="Number of recent games to analyze"),
    db: Session = Depends(get_db)
):
    """Compare multiple players' performance against the same line"""
    try:
        stat_enum = StatType(stat_type)
        player_id_list = [int(x.strip()) for x in player_ids.split(",")]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {e}")
    
    analytics = AnalyticsService(db)
    comparisons = []
    
    for player_id in player_id_list:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            continue
            
        analysis = analytics.get_player_line_analysis(player_id, stat_enum, line_value, games_back)
        comparisons.append({
            "player_id": player_id,
            "player_name": player.name,
            "position": player.position.value,
            "team": player.team,
            "hit_rate": analysis["hit_rate"],
            "games_analyzed": analysis["games_analyzed"],
            "average_value": analysis["average_value"],
            "total_hits": analysis["total_hits"]
        })
    
    # Sort by hit rate
    comparisons.sort(key=lambda x: x["hit_rate"], reverse=True)
    
    return {
        "stat_type": stat_type,
        "line_value": line_value,
        "comparisons": comparisons,
        "count": len(comparisons)
    }


