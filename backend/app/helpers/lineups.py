from __future__ import annotations

"""Helpers for the lineup summary API."""
from app.dbmodels.models import Player, Possession, Team
import json
from pathlib import Path
from typing import Any
from itertools import combinations

SAMPLE_SUMMARY_DATA_PATH = Path(__file__).resolve().parent / 'sample_summary_data' / 'sample_summary_data.json'
LineupRecord = dict[str, Any]


def _normalize_lineup_size(lineup_size: Any) -> int:
    try:
        normalized_lineup_size = int(lineup_size)
    except (TypeError, ValueError):
        return 5

    return max(1, min(5, normalized_lineup_size))


def _load_sample_lineups() -> list[LineupRecord]:
    with open(SAMPLE_SUMMARY_DATA_PATH) as sample_summary_data_file:
        return json.load(sample_summary_data_file)


def _truncate_sample_lineup(lineup: LineupRecord, lineup_size: int) -> LineupRecord:
    truncated_lineup = dict(lineup)
    truncated_lineup['player_ids'] = lineup['player_ids'][:lineup_size]
    truncated_lineup['players'] = lineup['players'][:lineup_size]
    return truncated_lineup


def _get_sample_lineups(lineup_size: int = 5) -> list[LineupRecord]:
    normalized_lineup_size = _normalize_lineup_size(lineup_size)
    return [
        _truncate_sample_lineup(lineup, normalized_lineup_size)
        for lineup in _load_sample_lineups()
    ]

STAT_FIELDS = [
    "points",
    "shot_attempts",
    "fg2_made",
    "fg2_attempted",
    "fg3_made",
    "fg3_attempted",
    "fg_made",
    "fg_attempted",
    "ft_made",
    "ft_attempted",
    "rebounds_offense",
    "rebounds_defense",
    "rebound_opportunities",
    "assists",
    "steals",
    "turnovers",
    "blocks",
    "offensive_fouls",
    "defensive_fouls",
    "shooting_fouls",
    "shot_attempt_points",
    "ft_potential_points",
    "transition_take_fouls",
]

def _empty_lineup_stats() -> dict[str, int]:
    return {field: 0 for field in STAT_FIELDS}

def _add_possession_stats(stats: dict[str, int], possession: Possession) -> None:
    for field in STAT_FIELDS:
        stats[field] += getattr(possession, field)

def _flatten_lineup_stats(
    lineup: LineupRecord,
) -> LineupRecord:
    flattened_lineup = dict(lineup)

    offensive_stats = flattened_lineup.pop("offensive_stats")
    defensive_stats = flattened_lineup.pop("defensive_stats")

    for field, value in offensive_stats.items():
        flattened_lineup[f"offensive_{field}"] = value

    for field, value in defensive_stats.items():
        flattened_lineup[f"defensive_{field}"] = value

    return flattened_lineup

def _calculate_lineup_metrics(lineup: LineupRecord) -> LineupRecord:
    lineup["total_possessions"] = (
        lineup["offensive_possessions"] + lineup["defensive_possessions"]
    )

    lineup["offensive_fg_pct"] = (
        lineup["offensive_fg_made"] / lineup["offensive_fg_attempted"]
        if lineup["offensive_fg_attempted"] > 0
        else 0
    )

    lineup["offensive_fg2_pct"] = (
        lineup["offensive_fg2_made"] / lineup["offensive_fg2_attempted"]
        if lineup["offensive_fg2_attempted"] > 0
        else 0
    )

    lineup["offensive_fg3_pct"] = (
        lineup["offensive_fg3_made"] / lineup["offensive_fg3_attempted"]
        if lineup["offensive_fg3_attempted"] > 0
        else 0
    )

    lineup["defensive_fg_pct"] = (
        lineup["defensive_fg_made"] / lineup["defensive_fg_attempted"]
        if lineup["defensive_fg_attempted"] > 0
        else 0
    )

    lineup["defensive_fg2_pct"] = (
        lineup["defensive_fg2_made"] / lineup["defensive_fg2_attempted"]
        if lineup["defensive_fg2_attempted"] > 0
        else 0
    )

    lineup["defensive_fg3_pct"] = (
        lineup["defensive_fg3_made"] / lineup["defensive_fg3_attempted"]
        if lineup["defensive_fg3_attempted"] > 0
        else 0
    )

    lineup["offensive_rating"] = (
        lineup["offensive_points"] / lineup["offensive_possessions"] * 100
        if lineup["offensive_possessions"] > 0
        else 0
    )

    lineup["defensive_rating"] = (
        lineup["defensive_points"] / lineup["defensive_possessions"] * 100
        if lineup["defensive_possessions"] > 0
        else 0
    )

    lineup["net_rating"] = (
        lineup["offensive_rating"] - lineup["defensive_rating"]
    )

    lineup["net_points"] = (
        lineup["offensive_points"] - lineup["defensive_points"]
    )

    lineup["defensive_rebound_rate"] = (
        lineup["defensive_rebounds_defense"]
        / lineup["defensive_rebound_opportunities"]
        if lineup["defensive_rebound_opportunities"] > 0
        else 0
    )

    return lineup

def get_player_impact_stats() -> list[dict[str, Any]]:
    """Return on-court impact statistics for each player."""
    players = {
        str(player.id): player.name
        for player in Player.objects.all()
    }

    player_stats = {}

    for possession in Possession.objects.all():
        for player_id in possession.offensive_player_ids:
            player_id = str(player_id)

            stats = player_stats.setdefault(
                player_id,
                {
                    "offensive_points": 0,
                    "offensive_possessions": 0,
                    "defensive_points_allowed": 0,
                    "defensive_possessions": 0,
                },
            )

            stats["offensive_points"] += possession.points
            stats["offensive_possessions"] += 1

            for player_id in possession.defensive_player_ids:
                player_id = str(player_id)

                stats = player_stats.setdefault(
                    player_id,
                    {
                        "offensive_points": 0,
                        "offensive_possessions": 0,
                        "defensive_points_allowed": 0,
                        "defensive_possessions": 0,
                    },
                )

                stats["defensive_points_allowed"] += possession.points
                stats["defensive_possessions"] += 1

    results = []

    for player_id, stats in player_stats.items():
        offensive_rating = (
            stats["offensive_points"] / stats["offensive_possessions"] * 100
            if stats["offensive_possessions"] > 0
            else None
        )

        defensive_rating = (
            stats["defensive_points_allowed"]
            / stats["defensive_possessions"]
            * 100
            if stats["defensive_possessions"] > 0
            else None
        )

        net_rating = (
            offensive_rating - defensive_rating
            if offensive_rating is not None and defensive_rating is not None
            else None
        )

        results.append(
            {
                "player_id": player_id,
                "player_name": players.get(player_id, "Unknown Player"),
                "offensive_possessions": stats["offensive_possessions"],
                "defensive_possessions": stats["defensive_possessions"],
                "offensive_rating": offensive_rating,
                "defensive_rating": defensive_rating,
                "net_rating": net_rating,
            }
        )

    results = [
        player
        for player in results
        if (
            player["offensive_possessions"] >= 50
            and player["defensive_possessions"] >= 50
            and player["net_rating"] is not None
        )
    ]

    results.sort(
        key=lambda player: (
            player["net_rating"] is not None,
            player["net_rating"] if player["net_rating"] is not None else 0,
        ),
        reverse=True,
    )

    return results

def get_lineup_league_summary_stats(lineup_size: int = 5) -> list[LineupRecord]:
    """Return lineup summaries across the entire league."""
    lineup_size = _normalize_lineup_size(lineup_size)

    possessions = Possession.objects.all()

    players = {
        str(player.id): player.name
        for player in Player.objects.all()
    }

    lineups = {}

    for possession in possessions:
        offensive_players = [
            str(player_id) for player_id in possession.offensive_player_ids
        ]

        defensive_players = [
            str(player_id) for player_id in possession.defensive_player_ids
        ]

        offensive_lineups = combinations(offensive_players, lineup_size)
        defensive_lineups = combinations(defensive_players, lineup_size)

        for lineup_players in offensive_lineups:
            lineup_players = tuple(sorted(lineup_players))
            key = (str(possession.offensive_team_id), lineup_players)

            lineups.setdefault(
                key,
                {
                    "team_id": str(possession.offensive_team_id),
                    "player_ids": list(lineup_players),
                    "players": [
                        {
                            "player_id": player_id,
                            "name": players.get(player_id, "Unknown Player"),
                        }
                        for player_id in lineup_players
                    ],
                    "offensive_possessions": 0,
                    "defensive_possessions": 0,
                    "offensive_stats": _empty_lineup_stats(),
                    "defensive_stats": _empty_lineup_stats(),
                },
            )

            lineups[key]["offensive_possessions"] += 1
            _add_possession_stats(
                lineups[key]["offensive_stats"],
                possession,
            )

        for lineup_players in defensive_lineups:
            lineup_players = tuple(sorted(lineup_players))
            key = (str(possession.defensive_team_id), lineup_players)

            lineups.setdefault(
                key,
                {
                    "team_id": str(possession.defensive_team_id),
                    "player_ids": list(lineup_players),
                    "players": [
                        {
                            "player_id": player_id,
                            "name": players.get(player_id, "Unknown Player"),
                        }
                        for player_id in lineup_players
                    ],
                    "offensive_possessions": 0,
                    "defensive_possessions": 0,
                    "offensive_stats": _empty_lineup_stats(),
                    "defensive_stats": _empty_lineup_stats(),
                },
            )

            lineups[key]["defensive_possessions"] += 1
            _add_possession_stats(
                lineups[key]["defensive_stats"],
                possession,
            )

    return [
        _calculate_lineup_metrics(
            _flatten_lineup_stats(lineup)
        )
        for lineup in lineups.values()
    ]