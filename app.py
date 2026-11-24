
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
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
    
