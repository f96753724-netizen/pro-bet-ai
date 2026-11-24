
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
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
