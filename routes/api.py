# routes/api.py
# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, request # import request
from services.opendata import load_all_opendata_spots # 引入新的載入函數
from utils.happiness import compute_happiness, haversine_distance # 引入 haversine_distance
from utils.mood_filter import filter_by_mood
import pandas as pd
import json
from datetime import datetime
import os
# import numpy as np # Removed as haversine_distance is moved

# 輔助函數：計算兩點距離 (Haversine 公式，回傳公里) - 已移動到 utils/happiness.py
# def haversine_distance(lat1, lon1, lat2, lon2):
#     R = 6371  # 地球半徑 (公里)
#     lat1_rad = np.radians(lat1)
#     lat2_rad = np.radians(lat2)
#     lon1_rad = np.radians(lon1)
#     lon2_rad = np.radians(lon2)

#     dlon = lon2_rad - lon1_rad
#     dlat = lat2_rad - lat1_rad

#     a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
#     c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
#     return R * c

# Define the task
HAPPINESS_BELL_TASK_ID = "happiness_bell_task_1"
HAPPINESS_BELL_TASK_NAME = "幸福響鈴：探索三個不同地點"
REQUIRED_UNIQUE_CHECKINS = 3

# Define Achievements
ACH_ART_EXPLORER_ID = "ach_art_explorer"
ACH_ART_EXPLORER_NAME = "藝文探索者"
REQUIRED_ART_CHECKINS = 3

# Define "Park Wanderer" Achievement
ACH_PARK_WANDERER_ID = "ach_park_wanderer"
ACH_PARK_WANDERER_NAME = "公園漫步者"
REQUIRED_PARK_CHECKINS = 5

# Define "Sports Enthusiast" Achievement
ACH_SPORTS_ENTHUSIAST_ID = "ach_sports_enthusiast"
ACH_SPORTS_ENTHUSIAST_NAME = "運動健將"
REQUIRED_SPORTS_CHECKINS = 3

# Define "Fresh Air Seeker" Achievement
ACH_FRESH_AIR_SEEKER_ID = "ach_fresh_air_seeker"
ACH_FRESH_AIR_SEEKER_NAME = "清新空氣偵測員"
REQUIRED_FRESH_AIR_CHECKINS = 2
FRESH_AIR_PM25_THRESHOLD = 20

# Define "Quiet Guardian" Achievement
ACH_QUIET_GUARDIAN_ID = "ach_quiet_guardian"
ACH_QUIET_GUARDIAN_NAME = "寧靜守護者"
REQUIRED_QUIET_CHECKINS = 2
QUIET_NOISE_THRESHOLD = 60 # Assuming noise values are lower for quieter places

# Define "YouBike Master" Achievement
ACH_BIKE_MASTER_ID = "ach_bike_master"
ACH_BIKE_MASTER_NAME = "YouBike 大師"
REQUIRED_BIKE_CHECKINS = 3 # 需要打卡 3 個不同的 YouBike 站點

api_bp = Blueprint("api", __name__)

MASTER = load_all_opendata_spots() # 使用新的載入函數

def get_recommendations(mood, user_lat=None, user_lon=None):
    df = compute_happiness(MASTER, mood, user_lat=user_lat, user_lon=user_lon)
    df = filter_by_mood(df, mood)
    df = df.sort_values("happiness", ascending=False).head(10)

    rec = []
    for _, r in df.iterrows():
        item = {
            "name": r["name"],
            "category": r["category"],
            "happiness": r["happiness"],
            "lat": r["lat"],
            "lon": r["lon"],
            "base": r["base"],
            "weight": r["weight"],
            "value_norm": r["value_norm"],
            "value": r["value"],
            "happiness_color": r["happiness_color"]
        }
        if 'dist_score' in r:
            item['dist_score'] = r['dist_score']
        rec.append(item)
    return rec

@api_bp.route("/mood/<m>", methods=["GET"])
def mood_api(m):
    user_lat = request.args.get("lat", type=float)
    user_lon = request.args.get("lon", type=float)
    return jsonify({
        "mood": m,
        "recommendations": get_recommendations(m, user_lat, user_lon)
    })

@api_bp.route("/complete", methods=["POST"])
def complete():
    data = request.get_json()
    name = data.get("name")
    user_lat = data.get("lat")
    user_lon = data.get("lon")
    target_lat = data.get("target_lat")
    target_lon = data.get("target_lon")

    # 距離驗證（100 公尺內視為到達）
    distance = haversine_distance(user_lat, user_lon, target_lat, target_lon) * 1000 # 轉換為公尺
    if distance > 100:
        return jsonify({"message": f"❌ 你還距離目標 {round(distance)} 公尺，太遠啦！", "task_completed": False}), 400

    # 讀取用戶進度檔案
    progress_file = os.path.join(os.path.dirname(__file__), "..", "user_progress.json")
    user_progress = {"checkins": [], "unique_checkin_names": [], "completed_tasks": [], "achievements": [], "survey_mood": "療癒放鬆"} # Initialize with all possible fields
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                existing_progress = json.load(f)
                user_progress.update(existing_progress)  # Merge existing data
        except json.JSONDecodeError:
            print(f"[ERR] 無法解碼 {progress_file}，可能為空或格式錯誤。將使用預設空數據。")
            # 如果檔案有問題，確保 user_progress 仍為空物件，或預設值
            user_progress = {
                "checkins": [],
                "unique_checkin_names": [],
                "completed_tasks": [],
                "achievements": [],
                "survey_mood": "療癒放鬆",
            }

    # 檢查是否已經打卡過
    existing_checkins = user_progress.get("checkins", [])
    for checkin in existing_checkins:
        # 判斷標準：景點名稱、目標經緯度都相同
        if checkin["name"] == name and checkin["target_lat"] == target_lat and checkin["target_lon"] == target_lon:
            return jsonify({"message": f"你已經打卡過 {name} 了！", "task_completed": False}), 200

    # 添加新的打卡記錄
    new_checkin = {
        "name": name,
        "timestamp": datetime.now().isoformat(),
        "user_lat": user_lat,
        "user_lon": user_lon,
        "target_lat": target_lat,
        "target_lon": target_lon,
    }
    user_progress["checkins"].append(new_checkin)

    # Track unique check-in names
    if name not in user_progress["unique_checkin_names"]:
        user_progress["unique_checkin_names"].append(name)

    message = f"已成功打卡：{name}！"
    task_completed = False
    achievement_unlocked = False

    # Check for "Happiness Bell" task completion
    if HAPPINESS_BELL_TASK_ID not in [task["id"] for task in user_progress.get("completed_tasks", [])]:
        if len(user_progress["unique_checkin_names"]) >= REQUIRED_UNIQUE_CHECKINS:
            user_progress["completed_tasks"].append({
                "id": HAPPINESS_BELL_TASK_ID,
                "name": HAPPINESS_BELL_TASK_NAME,
                "timestamp": datetime.now().isoformat()
            })
            message += f" 恭喜您完成任務：{HAPPINESS_BELL_TASK_NAME}！"
            task_completed = True
    
    # Check for "Art Explorer" achievement
    # Achievements are also stored in completed_tasks, but we might want a separate "achievements" list in user_progress
    # For now, let's keep them in completed_tasks for simplicity, but consider separating later.
    if ACH_ART_EXPLORER_ID not in [ach["id"] for ach in user_progress.get("completed_tasks", [])]: 
        # Get the category of the current checked-in spot
        current_spot_category_df = MASTER[MASTER["name"] == name]["category"]
        if not current_spot_category_df.empty:
            current_spot_category = current_spot_category_df.iloc[0]

        if current_spot_category == "art_events":
            # Count unique art event check-ins
            unique_art_checkins = set([
                checkin["name"] for checkin in user_progress["checkins"]
                    if not MASTER[MASTER["name"] == checkin["name"]]["category"].empty and \
                       MASTER[MASTER["name"] == checkin["name"]]["category"].iloc[0] == "art_events"
            ])
            if len(unique_art_checkins) >= REQUIRED_ART_CHECKINS:
                user_progress["completed_tasks"].append({
                    "id": ACH_ART_EXPLORER_ID,
                    "name": ACH_ART_EXPLORER_NAME,
                    "description": "成功打卡 3 個不同的藝文景點",
                    "timestamp": datetime.now().isoformat()
                })
                message += f" 恭喜您解鎖成就：{ACH_ART_EXPLORER_NAME}！"
                achievement_unlocked = True
    
    # Check for "Park Wanderer" achievement
    if ACH_PARK_WANDERER_ID not in [ach["id"] for ach in user_progress.get("completed_tasks", [])]:
        current_spot_category_df = MASTER[MASTER["name"] == name]["category"]
        if not current_spot_category_df.empty:
            current_spot_category = current_spot_category_df.iloc[0]

        if current_spot_category == "parks":
            unique_park_checkins = set([
                checkin["name"] for checkin in user_progress["checkins"]
                    if not MASTER[MASTER["name"] == checkin["name"]]["category"].empty and \
                       MASTER[MASTER["name"] == checkin["name"]]["category"].iloc[0] == "parks"
            ])
            if len(unique_park_checkins) >= REQUIRED_PARK_CHECKINS:
                user_progress["completed_tasks"].append({
                    "id": ACH_PARK_WANDERER_ID,
                    "name": ACH_PARK_WANDERER_NAME,
                    "description": "成功打卡 5 個不同的公園",
                    "timestamp": datetime.now().isoformat()
                })
                message += f" 恭喜您解鎖成就：{ACH_PARK_WANDERER_NAME}！"
                achievement_unlocked = True

    # Check for "Sports Enthusiast" achievement
    if ACH_SPORTS_ENTHUSIAST_ID not in [ach["id"] for ach in user_progress.get("completed_tasks", [])]:
        current_spot_category_df = MASTER[MASTER["name"] == name]["category"]
        if not current_spot_category_df.empty:
            current_spot_category = current_spot_category_df.iloc[0]

        if current_spot_category == "sports":
            unique_sports_checkins = set([
                checkin["name"] for checkin in user_progress["checkins"]
                    if not MASTER[MASTER["name"] == checkin["name"]]["category"].empty and \
                       MASTER[MASTER["name"] == checkin["name"]]["category"].iloc[0] == "sports"
            ])
            if len(unique_sports_checkins) >= REQUIRED_SPORTS_CHECKINS:
                user_progress["completed_tasks"].append({
                    "id": ACH_SPORTS_ENTHUSIAST_ID,
                    "name": ACH_SPORTS_ENTHUSIAST_NAME,
                    "description": "成功打卡 3 個不同的運動設施",
                    "timestamp": datetime.now().isoformat()
                })
                message += f" 恭喜您解鎖成就：{ACH_SPORTS_ENTHUSIAST_NAME}！"
                achievement_unlocked = True

    # Check for "Fresh Air Seeker" achievement
    if ACH_FRESH_AIR_SEEKER_ID not in [ach["id"] for ach in user_progress.get("completed_tasks", [])]:
        current_spot = MASTER[MASTER["name"] == name]
        if not current_spot.empty and current_spot["category"].iloc[0] == "air":
            current_pm25 = current_spot["value"].iloc[0]
            if current_pm25 < FRESH_AIR_PM25_THRESHOLD:
                unique_fresh_air_checkins = set([
                    checkin["name"] for checkin in user_progress["checkins"]
                    if not MASTER[MASTER["name"] == checkin["name"]]["category"].empty and \
                       MASTER[MASTER["name"] == checkin["name"]]["category"].iloc[0] == "air" and
                       MASTER[MASTER["name"] == checkin["name"]]["value"].iloc[0] < FRESH_AIR_PM25_THRESHOLD
                ])
                if len(unique_fresh_air_checkins) >= REQUIRED_FRESH_AIR_CHECKINS:
                    user_progress["completed_tasks"].append({
                        "id": ACH_FRESH_AIR_SEEKER_ID,
                        "name": ACH_FRESH_AIR_SEEKER_NAME,
                        "description": f"成功打卡 {REQUIRED_FRESH_AIR_CHECKINS} 個 PM2.5 值低於 {FRESH_AIR_PM25_THRESHOLD} 的空氣監測站",
                        "timestamp": datetime.now().isoformat()
                    })
                    message += f" 恭喜您解鎖成就：{ACH_FRESH_AIR_SEEKER_NAME}！"
                    achievement_unlocked = True

    # Check for "Quiet Guardian" achievement
    if ACH_QUIET_GUARDIAN_ID not in [ach["id"] for ach in user_progress.get("completed_tasks", [])]:
        current_spot = MASTER[MASTER["name"] == name]
        if not current_spot.empty and current_spot["category"].iloc[0] == "noise":
            current_noise_value = current_spot["value"].iloc[0]
            if current_noise_value < QUIET_NOISE_THRESHOLD:
                unique_quiet_checkins = set([
                    checkin["name"] for checkin in user_progress["checkins"]
                    if not MASTER[MASTER["name"] == checkin["name"]]["category"].empty and \
                       MASTER[MASTER["name"] == checkin["name"]]["category"].iloc[0] == "noise" and
                       MASTER[MASTER["name"] == checkin["name"]]["value"].iloc[0] < QUIET_NOISE_THRESHOLD
                ])
                if len(unique_quiet_checkins) >= REQUIRED_QUIET_CHECKINS:
                    user_progress["completed_tasks"].append({
                        "id": ACH_QUIET_GUARDIAN_ID,
                        "name": ACH_QUIET_GUARDIAN_NAME,
                        "description": f"成功打卡 {REQUIRED_QUIET_CHECKINS} 個噪音值低於 {QUIET_NOISE_THRESHOLD} 的噪音監測點",
                        "timestamp": datetime.now().isoformat()
                    })
                    message += f" 恭喜您解鎖成就：{ACH_QUIET_GUARDIAN_NAME}！"
                    achievement_unlocked = True

    # Check for "YouBike Master" achievement
    if ACH_BIKE_MASTER_ID not in [ach["id"] for ach in user_progress.get("completed_tasks", [])]:
        current_spot_category_df = MASTER[MASTER["name"] == name]["category"]
        if not current_spot_category_df.empty:
            current_spot_category = current_spot_category_df.iloc[0]

            if current_spot_category == "youbike":
                unique_bike_checkins = set([
                    checkin["name"] for checkin in user_progress["checkins"]
                    if not MASTER[MASTER["name"] == checkin["name"]]["category"].empty and \
                       MASTER[MASTER["name"] == checkin["name"]]["category"].iloc[0] == "youbike"
                ])
                if len(unique_bike_checkins) >= REQUIRED_BIKE_CHECKINS:
                    user_progress["completed_tasks"].append({
                        "id": ACH_BIKE_MASTER_ID,
                        "name": ACH_BIKE_MASTER_NAME,
                        "description": f"成功打卡 {REQUIRED_BIKE_CHECKINS} 個不同的 YouBike 站點",
                        "timestamp": datetime.now().isoformat()
                    })
                    message += f" 恭喜您解鎖成就：{ACH_BIKE_MASTER_NAME}！"
                    achievement_unlocked = True

    # 儲存更新後的用戶進度檔案
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(user_progress, f, ensure_ascii=False, indent=2)

    return jsonify({"message": message, "task_completed": task_completed, "achievement_unlocked": achievement_unlocked})
