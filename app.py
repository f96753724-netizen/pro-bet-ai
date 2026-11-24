
import os
from datetime import date
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

API_URL = "https://sportapi.ai/api"


def sportapi_get(endpoint):
    api_key = os.getenv("SPORTAPI_KEY")

    if not api_key:
        return {"error": "SPORTAPI_KEY pa konfigire"}, 500

    try:
        response = requests.get(
            f"{API_URL}{endpoint}",
            headers={"X-Api-Key": api_key},
            timeout=20
        )

        if response.status_code != 200:
            return {
                "error": "SportAPI pa reponn nòmalman",
                "status_code": response.status_code
            }, response.status_code

        return response.json(), 200

    except requests.RequestException:
        return {"error": "Pwoblèm koneksyon ak SportAPI"}, 502


@app.route("/")
def home():
    return jsonify({
        "bot": "PRO BET AI",
        "status": "Online",
        "message": "Bot la pare!"
    })


@app.route("/health")
def health():
    return jsonify({"status": "OK"})


@app.route("/football")
def football():
    match_date = request.args.get("date", date.today().isoformat())

    data, status = sportapi_get(
        f"/fixtures/date/{match_date}"
    )
    return jsonify(data), status


@app.route("/basketball")
def basketball():
    match_date = request.args.get("date", date.today().isoformat())

    data, status = sportapi_get(
        f"/basketball/games/date/{match_date}"
    )
    return jsonify(data), status
@app.route("/stats/<int:fixture_id>")
def match_stats(fixture_id):
    data, status = sportapi_get(
        f"/fixtures/{fixture_id}/stats"
    )
    return jsonify(data), status

@app.route("/analyze/<int:fixture_id>")
def analyze(fixture_id):
    data, status = sportapi_get(
        f"/fixtures/{fixture_id}/stats"
    )

    if status != 200:
        return jsonify(data), status

    if not data.get("available") or not data.get("data"):
        return jsonify({
            "message": "Estatistik match sa a poko disponib"
        }), 404

    home = data["data"]["home"]
    away = data["data"]["away"]

    return jsonify({
        "bot": "PRO BET AI",
        "fixture_id": fixture_id,
        "analysis": {
            "home_shots": home.get("shots"),
            "away_shots": away.get("shots"),
            "home_shots_on_target": home.get("shots_on_target"),
            "away_shots_on_target": away.get("shots_on_target"),
            "home_fouls": home.get("fouls"),
            "away_fouls": away.get("fouls"),
            "home_yellow_cards": home.get("yellow_cards"),
            "away_yellow_cards": away.get("yellow_cards"),
            "team_with_more_shots": (
                "home" if home.get("shots", 0) > away.get("shots", 0)
                else "away" if away.get("shots", 0) > home.get("shots", 0)
                else "equal"
            )
        }
    })
    
@app.route("/team-last5/<int:team_id>")
def team_last5(team_id):
    data, status = sportapi_get(f"/teams/{team_id}")

    if status != 200:
        return jsonify(data), status

    matches = data.get("matches", [])

    played = [
        match for match in matches
        if match.get("status") in ["FT", "AET", "PENS"]
    ]

    played.sort(
        key=lambda match: match.get("date", ""),
        reverse=True
    )

    return jsonify({
        "bot": "PRO BET AI",
        "team_id": team_id,
        "last_5_matches": played[:5]
    })
    
@app.route("/team-average/<int:team_id>")
def team_average(team_id):
    data, status = sportapi_get(f"/teams/{team_id}")

    if status != 200:
        return jsonify(data), status

    matches = data.get("matches", [])

    played = [
        m for m in matches
        if m.get("status") in ["FT", "AET", "PENS"]
    ]

    played.sort(
        key=lambda m: m.get("date", ""),
        reverse=True
    )

    last5 = played[:5]

    fields = [
        "shots",
        "shots_on_target",
        "fouls",
        "yellow_cards"
    ]

    totals = {field: 0 for field in fields}
    count = 0

    for match in last5:
        fixture_id = match.get("id")

        stats, stat_status = sportapi_get(
            f"/fixtures/{fixture_id}/stats"
        )

        if stat_status != 200:
            continue

        if not stats.get("available") or not stats.get("data"):
            continue

        if match.get("home_id") == team_id:
            team_stats = stats["data"].get("home", {})
        else:
            team_stats = stats["data"].get("away", {})

        if not team_stats:
            continue

        for field in fields:
            totals[field] += team_stats.get(field) or 0

        count += 1

    averages = {
        field: round(value / count, 2) if count else None
        for field, value in totals.items()
    }

    return jsonify({
        "bot": "PRO BET AI",
        "team_id": team_id,
        "matches_found": len(last5),
        "matches_with_stats": count,
        "averages": averages
    })
    
@app.route("/compare/<int:home_id>/<int:away_id>")
def compare_teams(home_id, away_id):

    def get_team_analysis(team_id):
        data, status = sportapi_get(f"/teams/{team_id}")

        if status != 200:
            return None

        matches = data.get("matches", [])

        played = [
            m for m in matches
            if m.get("status") in ["FT", "AET", "PENS"]
        ]

        played.sort(
            key=lambda m: m.get("date", ""),
            reverse=True
        )

        last5 = played[:5]

        fields = [
            "shots",
            "shots_on_target",
            "fouls",
            "yellow_cards"
        ]

        totals = {field: 0 for field in fields}
        count = 0
        form = []

        for match in last5:
            is_home = match.get("home_id") == team_id

            goals_for = (
                match.get("home_score") if is_home
                else match.get("away_score")
            )

            goals_against = (
                match.get("away_score") if is_home
                else match.get("home_score")
            )

            if goals_for is not None and goals_against is not None:
                form.append(
                    "W" if goals_for > goals_against
                    else "D" if goals_for == goals_against
                    else "L"
                )

            stats, stat_status = sportapi_get(
                f"/fixtures/{match.get('id')}/stats"
            )

            if stat_status != 200:
                continue

            if not stats.get("available") or not stats.get("data"):
                continue

            side = "home" if is_home else "away"
            team_stats = stats["data"].get(side, {})

            if not team_stats:
                continue

            for field in fields:
                value = team_stats.get(field)

                if value is not None:
                    totals[field] += value

            count += 1

        averages = {
            field: round(value / count, 2) if count else None
            for field, value in totals.items()
        }

        return {
            "team_id": team_id,
            "matches_found": len(last5),
            "matches_with_stats": count,
            "form": form,
            "averages": averages
        }

    home = get_team_analysis(home_id)
    away = get_team_analysis(away_id)

    if home is None or away is None:
        return jsonify({
            "error": "Nou pa kapab jwenn done youn nan ekip yo"
        }), 502

    return jsonify({
        "bot": "PRO BET AI",
        "comparison": {
            "home": home,
            "away": away
        }
    })
       
@app.route("/predict/<int:home_id>/<int:away_id>")
def predict_match(home_id, away_id):

    result = compare_teams(home_id, away_id)

    if isinstance(result, tuple):
        return result

    comparison = result.get_json()["comparison"]

    home = comparison["home"]["averages"]
    away = comparison["away"]["averages"]

    metrics = [
        "shots",
        "shots_on_target",
        "fouls",
        "yellow_cards"
    ]

    predictions = {}

    for metric in metrics:
        h = home.get(metric)
        a = away.get(metric)

        if h is None or a is None:
            predictions[metric] = {
                "status": "Done ki manke"
            }
            continue

        difference = abs(h - a)
        base = max(h, a, 1)

        gap = (difference / base) * 100

        if gap < 8:
            confidence = "Ba"
        elif gap < 18:
            confidence = "Mwayen"
        else:
            confidence = "Wo"

        if h > a:
            advantage = "home"
        elif a > h:
            advantage = "away"
        else:
            advantage = "equal"

        predictions[metric] = {
            "home_average": h,
            "away_average": a,
            "advantage": advantage,
            "historical_gap_percent": round(gap, 1),
            "confidence_level": confidence
        }

    return jsonify({
        "bot": "PRO BET AI",
        "type": "Historical statistical estimate",
        "home_team_id": home_id,
        "away_team_id": away_id,
        "predictions": predictions,
        "warning": "Se estimasyon ki baze sou 5 dènye match yo, se pa garanti."
    })
    
@app.route("/h2h/<int:home_id>/<int:away_id>")
def head_to_head(home_id, away_id):

    data, status = sportapi_get(
        f"/fixtures/h2h/{home_id}/{away_id}"
    )

    if status != 200:
        return jsonify(data), status

    return jsonify({
        "bot": "PRO BET AI",
        "home_team_id": home_id,
        "away_team_id": away_id,
        "head_to_head": data
    })
    
@app.route("/full-analysis/<int:home_id>/<int:away_id>")
def full_analysis(home_id, away_id):

    # Analiz estatistik ekip yo
    prediction_response = predict_match(home_id, away_id)

    if isinstance(prediction_response, tuple):
        return prediction_response

    prediction = prediction_response.get_json()

    # Analiz rankont dirèk yo
    h2h_data, h2h_status = sportapi_get(
        f"/fixtures/h2h/{home_id}/{away_id}"
    )

    if h2h_status != 200:
        return jsonify(h2h_data), h2h_status

    matches = h2h_data.get("data", [])

    wins_home = 0
    wins_away = 0
    draws = 0
    goals_home = 0
    goals_away = 0

    for match in matches:
        home_is_home = match.get("home_id") == home_id

        home_goals = (
            match.get("home_score") if home_is_home
            else match.get("away_score")
        )

        away_goals = (
            match.get("away_score") if home_is_home
            else match.get("home_score")
        )

        if home_goals is None or away_goals is None:
            continue

        goals_home += home_goals
        goals_away += away_goals

        if home_goals > away_goals:
            wins_home += 1
        elif away_goals > home_goals:
            wins_away += 1
        else:
            draws += 1

    return jsonify({
        "bot": "PRO BET AI",
        "home_team_id": home_id,
        "away_team_id": away_id,
        "statistical_prediction": prediction.get("predictions"),
        "head_to_head": {
            "matches_found": len(matches),
            "home_wins": wins_home,
            "away_wins": wins_away,
            "draws": draws,
            "home_goals": goals_home,
            "away_goals": goals_away
        },
        "warning": "Analiz sa a baze sou done istorik; li pa garanti rezilta paryaj."
    })
    
@app.route("/goals-analysis/<int:home_id>/<int:away_id>")
def goals_analysis(home_id, away_id):

    def get_goal_stats(team_id):
        data, status = sportapi_get(f"/teams/{team_id}")

        if status != 200:
            return None

        matches = data.get("matches", [])

        played = [
            m for m in matches
            if m.get("status") in ["FT", "AET", "PENS"]
            and m.get("home_score") is not None
            and m.get("away_score") is not None
        ]

        played.sort(
            key=lambda m: m.get("date", ""),
            reverse=True
        )

        last5 = played[:5]

        total_scored = 0
        total_conceded = 0
        over15 = 0
        over25 = 0
        over35 = 0
        btts = 0
        count = 0

        for match in last5:
            is_home = match.get("home_id") == team_id

            scored = (
                match.get("home_score") if is_home
                else match.get("away_score")
            )

            conceded = (
                match.get("away_score") if is_home
                else match.get("home_score")
            )

            total = scored + conceded

            total_scored += scored
            total_conceded += conceded

            if total >= 2:
                over15 += 1
            if total >= 3:
                over25 += 1
            if total >= 4:
                over35 += 1
            if scored > 0 and conceded > 0:
                btts += 1

            count += 1

        return {
            "team_id": team_id,
            "matches_analyzed": count,
            "average_scored": round(total_scored / count, 2) if count else None,
            "average_conceded": round(total_conceded / count, 2) if count else None,
            "over_1_5": over15,
            "over_2_5": over25,
            "over_3_5": over35,
            "btts": btts
        }

    home = get_goal_stats(home_id)
    away = get_goal_stats(away_id)

    if home is None or away is None:
        return jsonify({
            "error": "Nou pa kapab jwenn done ekip yo"
        }), 502

    h2h_data, status = sportapi_get(
        f"/fixtures/h2h/{home_id}/{away_id}"
    )

    if status != 200:
        return jsonify(h2h_data), status

    h2h_matches = h2h_data.get("data", [])

    h2h_stats = {
        "matches_analyzed": 0,
        "over_1_5": 0,
        "over_2_5": 0,
        "over_3_5": 0,
        "btts": 0
    }

    for match in h2h_matches:
        hs = match.get("home_score")
        aws = match.get("away_score")

        if hs is None or aws is None:
            continue

        total = hs + aws

        h2h_stats["matches_analyzed"] += 1

        if total >= 2:
            h2h_stats["over_1_5"] += 1
        if total >= 3:
            h2h_stats["over_2_5"] += 1
        if total >= 4:
            h2h_stats["over_3_5"] += 1
        if hs > 0 and aws > 0:
            h2h_stats["btts"] += 1

    return jsonify({
        "bot": "PRO BET AI",
        "home_team": home,
        "away_team": away,
        "head_to_head_goals": h2h_stats,
        "warning": "Se frekans istorik, se pa garanti rezilta pwochen match."
    })
    
@app.route("/final-analysis/<int:home_id>/<int:away_id>")
def final_analysis(home_id, away_id):

    client = app.test_client()

    goals_response = client.get(
        f"/goals-analysis/{home_id}/{away_id}"
    )

    stats_response = client.get(
        f"/predict/{home_id}/{away_id}"
    )

    if goals_response.status_code != 200:
        return jsonify({
            "error": "Erè nan analiz gòl"
        }), 502

    if stats_response.status_code != 200:
        return jsonify({
            "error": "Erè nan analiz estatistik"
        }), 502

    goals = goals_response.get_json()
    stats = stats_response.get_json()

    home = goals["home_team"]
    away = goals["away_team"]
    h2h = goals["head_to_head_goals"]

    picks = []

    def add_pick(name, count, total, source):
        if total > 0:
            picks.append({
                "market": name,
                "historical_hits": count,
                "matches": total,
                "frequency_percent": round(
                    count / total * 100, 1
                ),
                "source": source
            })

    add_pick(
        "Over 1.5",
        home["over_1_5"] + away["over_1_5"],
        home["matches_analyzed"] + away["matches_analyzed"],
        "Last 5 matches per team"
    )

    add_pick(
        "Over 2.5",
        home["over_2_5"] + away["over_2_5"],
        home["matches_analyzed"] + away["matches_analyzed"],
        "Last 5 matches per team"
    )

    add_pick(
        "Over 3.5",
        home["over_3_5"] + away["over_3_5"],
        home["matches_analyzed"] + away["matches_analyzed"],
        "Last 5 matches per team"
    )

    add_pick(
        "BTTS",
        home["btts"] + away["btts"],
        home["matches_analyzed"] + away["matches_analyzed"],
        "Last 5 matches per team"
    )

    add_pick(
        "H2H Over 2.5",
        h2h["over_2_5"],
        h2h["matches_analyzed"],
        "Head to head"
    )

    add_pick(
        "H2H BTTS",
        h2h["btts"],
        h2h["matches_analyzed"],
        "Head to head"
    )

    picks.sort(
        key=lambda item: item["frequency_percent"],
        reverse=True
    )

    return jsonify({
        "bot": "PRO BET AI",
        "home_team_id": home_id,
        "away_team_id": away_id,
        "goals_analysis": goals,
        "statistical_analysis": stats.get(
            "predictions", {}
        ),
        "ranked_picks": picks,
        "warning": (
            "Klasman sa a baze sou frekans istorik, "
            "li pa garanti yon paryaj ap genyen."
        )
    })
    
@app.route("/basketball-analyze/<int:game_id>")
def basketball_analyze(game_id):

    game, status = sportapi_get(
        f"/basketball/games/{game_id}"
    )

    if status != 200:
        return jsonify(game), status

    stats, stats_status = sportapi_get(
        f"/basketball/games/{game_id}/stats"
    )

    players, players_status = sportapi_get(
        f"/basketball/games/{game_id}/players"
    )

    if stats_status != 200:
        stats = {"available": False}

    if players_status != 200:
        players = {"available": False}

    game_data = game.get("data", game)
    stats_data = stats.get("data", {})
    players_data = players.get("data", {})

    home = game_data.get("home", {})
    away = game_data.get("away", {})

    home_stats = stats_data.get("home", {})
    away_stats = stats_data.get("away", {})

    def player_leaders(team_players):
        leaders = []

        for item in team_players:
            player = item.get("player", {})
            if item.get("dnp"):
                continue

            leaders.append({
                "name": player.get("name"),
                "points": item.get("pts"),
                "rebounds": item.get("reb"),
                "assists": item.get("ast"),
                "three_pointers": item.get("tpm"),
                "minutes": item.get("minutes")
            })

        return sorted(
            leaders,
            key=lambda x: x.get("points") or 0,
            reverse=True
        )[:5]

    return jsonify({
        "bot": "PRO BET AI",
        "sport": "Basketball",
        "game_id": game_id,
        "league": game_data.get("league"),
        "status": game_data.get("status"),
        "home": {
            "name": home.get("name"),
            "score": home.get("score"),
            "stats": home_stats,
            "top_players": player_leaders(
                players_data.get("home", [])
            )
        },
        "away": {
            "name": away.get("name"),
            "score": away.get("score"),
            "stats": away_stats,
            "top_players": player_leaders(
                players_data.get("away", [])
            )
        },
        "warning": "Analiz estatistik, pa garanti rezilta paryaj."
    })
    


    

    

    
    
@app.route("/basketball/debug-team/<int:team_id>")
def basketball_debug_team(team_id):
    result, status = sportapi_get(
        f"/basketball/teams/{team_id}/games?limit=10"
    )

    if status != 200:
        return jsonify(result), status

    games = result.get("data", [])

    return jsonify({
        "team_id": team_id,
        "count": len(games),
        "statuses": [
            game.get("status") for game in games
        ],
        "first_games": games[:3]
    })
    
@app.route("/basketball/team-last5/<int:team_id>")
def basketball_team_last5(team_id):
    result, status = sportapi_get(
        f"/basketball/teams/{team_id}"
    )

    if status != 200:
        return jsonify(result), status

    data = result.get("data", result)

    if "team" in data and isinstance(data["team"], dict):
        team = data["team"]
    else:
        team = data

    games = data.get("last_games", result.get("last_games", []))

    if not games:
        return jsonify({
            "bot": "PRO BET AI",
            "error": "Pa gen dènye match ekip sa a nan API a."
        }), 404

    finished = [
        g for g in games
        if g.get("status") in ["FT", "AOT"]
    ][:5]

    if not finished:
        return jsonify({
            "bot": "PRO BET AI",
            "error": "Pa gen ase match fini pou ekip sa a."
        }), 404

    history = []
    totals = {
        "points_for": 0,
        "points_against": 0,
        "rebounds": 0,
        "assists": 0,
        "three_pointers": 0
    }

    stats_count = 0

    for game in finished:
        home = game.get("home", {})
        away = game.get("away", {})

        is_home = home.get("id") == team_id

        my_team = home if is_home else away
        opponent = away if is_home else home

        scored = my_team.get("score")
        conceded = opponent.get("score")

        if scored is None or conceded is None:
            continue

        totals["points_for"] += scored
        totals["points_against"] += conceded

        stats_result, stats_status = sportapi_get(
            f"/basketball/games/{game.get('id')}/stats"
        )

        team_stats = {}

        if stats_status == 200:
            stats_data = stats_result.get("data", {})
            side = "home" if is_home else "away"
            team_stats = stats_data.get(side, {})

        history.append({
            "date": game.get("start"),
            "opponent": opponent.get("name"),
            "score": f"{scored}-{conceded}",
            "result": "W" if scored > conceded else "L",
            "rebounds": team_stats.get("reb"),
            "assists": team_stats.get("ast"),
            "three_pointers": team_stats.get("tpm")
        })

        if team_stats:
            totals["rebounds"] += team_stats.get("reb", 0)
            totals["assists"] += team_stats.get("ast", 0)
            totals["three_pointers"] += team_stats.get("tpm", 0)
            stats_count += 1

    count = len(history)

    if count == 0:
        return jsonify({
            "bot": "PRO BET AI",
            "error": "Nou pa jwenn rezilta match yo."
        }), 404

    averages = {
        "points_for": round(totals["points_for"] / count, 1),
        "points_against": round(totals["points_against"] / count, 1)
    }

    if stats_count:
        averages.update({
            "rebounds": round(totals["rebounds"] / stats_count, 1),
            "assists": round(totals["assists"] / stats_count, 1),
            "three_pointers": round(
                totals["three_pointers"] / stats_count, 1
            )
        })

    return jsonify({
        "bot": "PRO BET AI",
        "team": team.get("name", f"Team {team_id}"),
        "matches_found": count,
        "matches": history,
        "averages": averages
    })
    
@app.route("/basketball/compare/<int:home_id>/<int:away_id>")
def basketball_compare(home_id, away_id):

    def get_team_form(team_id):
        result, status = sportapi_get(
            f"/basketball/teams/{team_id}"
        )

        if status != 200:
            return None

        data = result.get("data", result)
        games = data.get("last_games", [])

        finished = [
            g for g in games
            if g.get("status") in ["FT", "AOT"]
        ][:5]

        points_for = []
        points_against = []
        wins = 0
        losses = 0

        for game in finished:
            home = game.get("home", {})
            away = game.get("away", {})

            if home.get("id") == team_id:
                my_team = home
                opponent = away
            elif away.get("id") == team_id:
                my_team = away
                opponent = home
            else:
                continue

            scored = my_team.get("score")
            conceded = opponent.get("score")

            if scored is None or conceded is None:
                continue

            points_for.append(scored)
            points_against.append(conceded)

            if scored > conceded:
                wins += 1
            else:
                losses += 1

        count = len(points_for)

        if count == 0:
            return None

        return {
            "matches": count,
            "wins": wins,
            "losses": losses,
            "average_points_for": round(sum(points_for) / count, 1),
            "average_points_against": round(
                sum(points_against) / count, 1
            )
        }

    home = get_team_form(home_id)
    away = get_team_form(away_id)

    if not home or not away:
        return jsonify({
            "bot": "PRO BET AI",
            "error": "Nou pa jwenn ase done pou konpare ekip yo."
        }), 404

    return jsonify({
        "bot": "PRO BET AI",
        "home_team": {
            "team_id": home_id,
            **home
        },
        "away_team": {
            "team_id": away_id,
            **away
        },
        "points_difference": round(
            home["average_points_for"] -
            away["average_points_for"], 1
        )
    })
    
@app.route("/basketball/predict/<int:home_id>/<int:away_id>")
def basketball_predict(home_id, away_id):

    def get_average(team_id):
        result, status = sportapi_get(
            f"/basketball/teams/{team_id}"
        )

        if status != 200:
            return None

        data = result.get("data", result)
        games = data.get("last_games", [])

        finished = [
            g for g in games
            if g.get("status") in ["FT", "AOT"]
        ][:5]

        scored_list = []
        conceded_list = []

        for game in finished:
            home = game.get("home", {})
            away = game.get("away", {})

            if home.get("id") == team_id:
                mine, opponent = home, away
            elif away.get("id") == team_id:
                mine, opponent = away, home
            else:
                continue

            scored = mine.get("score")
            conceded = opponent.get("score")

            if scored is None or conceded is None:
                continue

            scored_list.append(scored)
            conceded_list.append(conceded)

        if not scored_list:
            return None

        return {
            "scored": sum(scored_list) / len(scored_list),
            "conceded": sum(conceded_list) / len(conceded_list),
            "matches": len(scored_list)
        }

    home = get_average(home_id)
    away = get_average(away_id)

    if not home or not away:
        return jsonify({
            "bot": "PRO BET AI",
            "error": "Done 5 dènye match yo pa disponib."
        }), 404

    home_prediction = round(
        (home["scored"] + away["conceded"]) / 2
    )

    away_prediction = round(
        (away["scored"] + home["conceded"]) / 2
    )

    difference = home_prediction - away_prediction

    if difference > 0:
        favorite = "Ekip lakay"
    elif difference < 0:
        favorite = "Ekip deyò"
    else:
        favorite = "Match egal"

    return jsonify({
        "bot": "PRO BET AI",
        "prediction": {
            "home_points": home_prediction,
            "away_points": away_prediction,
            "estimated_total_points": (
                home_prediction + away_prediction
            ),
            "favorite": favorite
        },
        "home_statistics": home,
        "away_statistics": away,
        "warning": "Estimasyon estatistik, se pa rezilta garanti."
    })
    
@app.route("/basketball/players/<int:game_id>")
def basketball_players(game_id):

    result, status = sportapi_get(
        f"/basketball/games/{game_id}/players"
    )

    if status != 200:
        return jsonify(result), status

    return jsonify({
        "bot": "PRO BET AI",
        "game_id": game_id,
        "player_statistics": result.get("data", result)
    })
    
@app.route("/basketball/top-players/<int:game_id>")
def basketball_top_players(game_id):

    result, status = sportapi_get(
        f"/basketball/games/{game_id}/players"
    )

    if status != 200:
        return jsonify(result), status

    data = result.get("data", result)

    players = []

    def extract_players(obj):
        if isinstance(obj, dict):
            if any(k in obj for k in ["points", "pts"]):
                players.append(obj)
            else:
                for value in obj.values():
                    extract_players(value)

        elif isinstance(obj, list):
            for item in obj:
                extract_players(item)

    extract_players(data)

    if not players:
        return jsonify({
            "bot": "PRO BET AI",
            "error": "Pa jwenn estatistik jwè yo."
        }), 404

    players.sort(
        key=lambda p: p.get("points", p.get("pts", 0)) or 0,
        reverse=True
    )

    top_players = []

    for player in players[:10]:
        top_players.append({
            "name": player.get("name", player.get("player_name")),
            "points": player.get("points", player.get("pts")),
            "rebounds": player.get("rebounds", player.get("reb")),
            "assists": player.get("assists", player.get("ast")),
            "three_pointers": player.get(
                "three_pointers", player.get("tpm")
            )
        })

    return jsonify({
        "bot": "PRO BET AI",
        "game_id": game_id,
        "top_10_players": top_players
    })
    
@app.route("/basketball/full-report/<int:game_id>")
def basketball_full_report(game_id):

    game, game_status = sportapi_get(
        f"/basketball/games/{game_id}"
    )

    if game_status != 200:
        return jsonify(game), game_status

    stats, stats_status = sportapi_get(
        f"/basketball/games/{game_id}/stats"
    )

    players, players_status = sportapi_get(
        f"/basketball/games/{game_id}/players"
    )

    return jsonify({
        "bot": "PRO BET AI",
        "game_id": game_id,
        "match": game.get("data", game),
        "team_statistics": (
            stats.get("data", stats)
            if stats_status == 200 else None
        ),
        "player_statistics": (
            players.get("data", players)
            if players_status == 200 else None
        ),
        "stats_available": stats_status == 200,
        "players_available": players_status == 200
    })
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
