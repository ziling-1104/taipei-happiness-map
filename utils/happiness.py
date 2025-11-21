# utils/happiness.py
import pandas as pd
import numpy as np
from math import exp

# 輔助函數：計算兩點距離 (Haversine 公式，回傳公里)
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # 地球半徑 (公里)
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# -----------------------------------------------------
# 心情權重表（你原本的 + food 增加）
# -----------------------------------------------------
MOOD_WEIGHTS = {
    "療癒放鬆": { # 之前是 relax
        "parks": 1.8, "air": 1.6, "sports": 0.7, "art_events": 0.9, "noise": 1.0, "youbike": 0.5,
    },
    "城市漫步": { # 之前是 quiet (包含 art_events)
        "parks": 1.5, "air": 1.0, "sports": 0.5, "art_events": 1.2, "noise": 1.8, "youbike": 1.2,
    },
    "活力充電": { # 之前是 active
        "parks": 1.0, "air": 0.7, "sports": 2.0, "art_events": 1.0, "noise": 0.5, "youbike": 1.8,
    },
    "文化探索": { # 之前是 art
        "parks": 0.8, "air": 0.6, "sports": 0.8, "art_events": 2.5, "noise": 0.6, "youbike": 0.7,
    }
}

# 新增基礎類別貢獻度 (Base Category Contribution)
# 依圖示規範重新定義權重：空氣與綠地 25%，噪音 20%，
# 藝文與運動各 15%。其餘資料集目前不計入幸福指數。
BASE_CATEGORY_CONTRIBUTION = {
    "air": 0.25,
    "parks": 0.25,
    "noise": 0.20,
    "art_events": 0.15,
    "sports": 0.15,
    # 其餘類別未在圖示中出現，給 0 以避免影響分數
    "youbike": 0.0,
}

# -----------------------------------------------------
# 幸福顏色（主卡顯示用）
# -----------------------------------------------------
def happiness_color(v):
    if v >= 80:
        return "#8BC34A"     # 淺綠色
    elif v >= 50:
        return "#FFCA28"     # 柔和的橘黃色
    else:
        return "#EF5350"     # 較柔和的紅色


# -----------------------------------------------------
# 主幸福公式（新版）
# -----------------------------------------------------
def compute_happiness(df, mood, user_lat=None, user_lon=None, survey_mood=None):
    df = df.copy()

    # 如果 DataFrame 是空的，直接返回一個空的 DataFrame
    if df.empty:
        return pd.DataFrame(
            columns=["name", "category", "lat", "lon", "value", "value_norm", "weight", "base", "main_score", "main_norm", "distance", "dist_score", "happiness", "happiness_color"]
        )

    df["base"] = 0.0
    df["value_norm"] = 0.0
    df["weight"] = 1.0
    df["dist_score"] = 0.0    # 距離分
    df["happiness"] = 0.0

    # 如果有問卷結果，調整心情權重
    current_mood_weights = MOOD_WEIGHTS.get(mood, {}).copy()
    survey_weight_influence = 0.8 # 問卷結果的影響程度，提高到 0.8

    if survey_mood and survey_mood in MOOD_WEIGHTS:
        for category, survey_cat_weight in MOOD_WEIGHTS[survey_mood].items():
            # 將原始 mood 權重和 survey_mood 權重進行加權平均
            original_mood_weight = MOOD_WEIGHTS.get(mood, {}).get(category, 1.0)
            current_mood_weights[category] = (
                original_mood_weight * (1 - survey_weight_influence) +
                survey_cat_weight * survey_weight_influence
            )

    # -----------------------------------------------------
    # 1) 依 category 各自做 Min-Max
    # -----------------------------------------------------
    # 使用 groupby().transform() 優化，避免迴圈和多次篩選
    df['vmin'] = df.groupby('category')['value'].transform('min')
    df['vmax'] = df.groupby('category')['value'].transform('max')
    
    # 處理 vmax == vmin 的情況
    # 先計算正常情況下的 value_norm
    normal_values = (df['value'] - df['vmin']) / (df['vmax'] - df['vmin'])
    
    # 對於 vmax == vmin 的情況，設置為 1.0 (或 0.5) 並添加隨機擾動
    df['value_norm'] = np.where(
        df['vmax'] == df['vmin'],
        1.0,
        normal_values
    )
    
    # 設置 base 為 category 的 value 中位數
    df['base'] = df.groupby('category')['value'].transform('median')

    # 移除臨時欄位
    df = df.drop(columns=['vmin', 'vmax'])

    # -----------------------------------------------------
    # 2) 心情權重
    # -----------------------------------------------------
    df["weight"] = df["category"].map(current_mood_weights).fillna(1.0)

    # -----------------------------------------------------
    # 3) 幸福主分（不含距離）
    #    score = value_norm * (base_contribution * mood_adjustment) * base
    # -----------------------------------------------------
    # 獲取基礎貢獻度
    df["base_contribution"] = df["category"].map(BASE_CATEGORY_CONTRIBUTION).fillna(0)
    # 獲取心情調整因子 (現在使用已考慮 survey_mood 的 df["weight"])
    df["mood_adjustment"] = df["weight"]

    df["main_score"] = df["value_norm"] * \
                       (df["base_contribution"] * df["mood_adjustment"])

    # -----------------------------------------------------
    # 4) 幸福主分 Normalize → 0～100 區間
    # -----------------------------------------------------
    min_s = df["main_score"].min()
    max_s = df["main_score"].max()

    if max_s == min_s:
        df["main_norm"] = 50 # 如果所有分數都一樣，給予 50 分 (平均值)
    else:
        # 直接正規化到 0-100 區間
        df["main_norm"] = 100 * ((df["main_score"] - min_s) / (max_s - min_s))

    # -----------------------------------------------------
    # 5) 最終幸福 = 主分 (不再包含距離分)，並確保每個景點分數唯一
    # -----------------------------------------------------
    # 先以主分排名，確保排序穩定，再轉換為 100,99,98…
    ranks = df["main_score"].rank(method="first", ascending=False)
    df["happiness"] = (101 - ranks).astype(int)

    # 顏色
    df["happiness_color"] = df["happiness"].apply(happiness_color)

    # 最終輸出
    return df
