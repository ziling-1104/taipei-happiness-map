# app.py
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify
from services.opendata import load_all_opendata_spots
from utils.happiness import compute_happiness
from utils.mood_filter import filter_by_mood
from routes.api import api_bp
import folium # 引入 folium
import pandas as pd
import json

app = Flask(__name__)

print("🚀 啟動 Flask：正在載入資料中…")
MASTER_DF = load_all_opendata_spots()
print(f"✅ 載入完成，共 {len(MASTER_DF)} 筆資料\n")

@app.route("/")
def index():
    mood = request.args.get("mood", "療癒放鬆")
    user_lat = request.args.get("lat", type=float)
    user_lon = request.args.get("lon", type=float)
    map_only = request.args.get("map_only", "false").lower() == "true"
    requested_names_raw = request.args.get("names")
    requested_names = []
    if requested_names_raw:
        try:
            requested_names = json.loads(requested_names_raw)
        except json.JSONDecodeError:
            requested_names = []

    df = compute_happiness(MASTER_DF, mood, user_lat=user_lat, user_lon=user_lon)
    df = filter_by_mood(df, mood)

    if requested_names:
        df = df[df["name"].isin(requested_names)]
        if not df.empty:
            df["name"] = pd.Categorical(df["name"], categories=requested_names, ordered=True)
            df = df.sort_values("name")
    else:
        df = df.sort_values("happiness", ascending=False).head(10)

    # 創建 Folium 地圖
    # 預設地圖中心點，可以根據實際數據調整
    if not df.empty:
        map_center = [df["lat"].mean(), df["lon"].mean()]
    else:
        map_center = [25.0330, 121.5654] # 台北市中心預設經緯度

    m = folium.Map(location=map_center, zoom_start=13)

    # 在地圖上添加標記
    for _, row in df.iterrows():
        popup_html = f"""
            <b>{row['name']}</b><br>
            幸福感: {row['happiness']}<br>
            類別: {row['category']}<br>
            OpenData 原始值: {row['value']}<br>
            OpenData 正規化值: {row['value_norm']:.2f}<br>
            心情權重: {row['weight']:.1f}<br>
            中位數基準: {row['base']:.1f}<br>
        """
        if 'dist_score' in row and row['dist_score'] > 0:
            popup_html += f"距離分: {row['dist_score']:.1f}<br>"

        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=row["happiness_color"])
        ).add_to(m)

    # 將 Folium 地圖轉換為 HTML 字符串
    map_html = m._repr_html_()

    if map_only:
        return map_html

    return render_template(
        "index.html",
        mood=mood,
        recommendations=df.to_dict(orient="records"),
        map_html=map_html  # 將地圖 HTML 傳遞給模板
    )

@app.route("/survey")
def survey():
    return render_template("survey.html")

@app.route("/result", methods=["POST"])
def result():
    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers", [])
    if len(answers) < 4:
        return jsonify({"error": "問卷資料不足"}), 400

    experience_pref = answers[0]
    noise_pref = answers[1]
    activity_level = answers[2]
    stress_level = answers[3]

    score = {
        "療癒放鬆": 0,
        "城市漫步": 0,
        "活力充電": 0,
        "文化探索": 0,
    }

    # 依照第一題直接給主要權重
    primary_weights = {
        "療癒放鬆": "療癒放鬆",
        "城市漫步": "城市漫步",
        "活力充電": "活力充電",
        "文化探索": "文化探索",
        "獨自沉澱": "城市漫步",  # 偏好安靜、沉澱 → 靜態路線
    }
    mapped_primary = primary_weights.get(experience_pref)
    if mapped_primary:
        score[mapped_primary] += 50

    # 噪音偏好
    if noise_pref == "quiet_pref_quiet":
        score["療癒放鬆"] += 20
        score["城市漫步"] += 20
    else:
        score["活力充電"] += 15
        score["文化探索"] += 10

    # 活動強度
    if activity_level == "activity_static":
        score["療癒放鬆"] += 15
        score["城市漫步"] += 15
        score["文化探索"] += 10
    else:
        score["活力充電"] += 30

    # 壓力程度
    if stress_level == "stress_high":
        score["療癒放鬆"] += 25
    elif stress_level == "stress_medium":
        score["療癒放鬆"] += 10
        score["城市漫步"] += 10
    else:
        score["活力充電"] += 15
        score["文化探索"] += 10

    mood = max(score, key=score.get)
    return jsonify({"mood": mood})

app.register_blueprint(api_bp, url_prefix="/api")

if __name__ == "__main__":
    print("🌈 Flask 啟動：http://127.0.0.1:5051")
    app.run(debug=False, port=5051)
