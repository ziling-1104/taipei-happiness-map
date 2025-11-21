# services/opendata.py
# -*- coding: utf-8 -*-
import json
import pandas as pd
import os
import requests
import io # 引入 io 模組
import numpy as np # 引入 numpy 模組

# 臺北市立美術館的固定經緯度
TAIPEI_FINE_ARTS_MUSEUM_LAT = 25.0747
TAIPEI_FINE_ARTS_MUSEUM_LON = 121.5209

# OpenData API 連結
OPENDATA_APIS = {
    "art_events": "https://data.taipei/api/frontstage/tpeod/dataset/resource.download?rid=1700a7e6-3d27-47f9-89d9-1811c9f7489c", # 更改回 CSV 連結
    "noise": "https://data.taipei/api/v1/dataset/ac5e1557-5590-4bec-8709-e5f0f8d4bd1e?scope=resourceAquire",
    "sports": "https://data.taipei/api/v1/dataset/112521a2-7ee3-4c15-8495-9ddb3278ce75?scope=resourceAquire",
    "air": "https://data.taipei/api/v1/dataset/2382aab0-6814-46bd-99e5-56a65eecace5?scope=resourceAquire",
    "parks": "https://parks.gov.taipei/parks/api/", # 新增公園 API
    "youbike": "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json", # 新增 YouBike API
}

def fetch_data_from_url(url, category, lat_col=None, lon_col=None, value_col=None, name_col=None, default_value=1.0):
    print(f"📡 正在從 {url} 獲取 {category} 資料...")
    try:
        response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status() # 檢查 HTTP 請求是否成功
        
        # 根據不同的 API 結構調整資料解析方式
        if category == "parks":
            data = response.json() # 公園 API 的頂層就是陣列
        elif category == "youbike": # YouBike API 的頂層也是陣列
            data = response.json()
        else:
            data = response.json()["result"]["results"]
        
        df = pd.DataFrame(data)

        if df.empty:
            print(f"[WARN] {category} 資料為空。")
            return pd.DataFrame()

        # 標準化欄位名稱
        df["category"] = category
        df["name"] = df[name_col] if name_col else "未命名地點"
        df["lat"] = pd.to_numeric(df[lat_col], errors='coerce') if lat_col else None
        df["lon"] = pd.to_numeric(df[lon_col], errors='coerce') if lon_col else None
        df["value"] = pd.to_numeric(df[value_col], errors='coerce') if value_col else default_value

        # 處理缺失的經緯度
        df.dropna(subset=["lat", "lon"], inplace=True)

        print(f"[OK] {category} 資料載入完成，共 {len(df)} 筆。")
        return df[["name", "category", "lat", "lon", "value"]]
    except requests.exceptions.RequestException as e:
        print(f"[ERR] 無法從 {url} 獲取 {category} 資料：{e}")
        return pd.DataFrame()
    except KeyError as e:
        print(f"[ERR] {category} 資料 JSON 結構錯誤：{e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"[ERR] 處理 {category} 資料時發生未知錯誤：{e}")
        return pd.DataFrame()

def fetch_art_events():
    url = OPENDATA_APIS["art_events"]
    print(f"📡 正在從 CSV 連結 {url} 獲取 art_events 資料...")
    try:
        response = requests.get(url, timeout=10, verify=False)
        response.raise_for_status()
        # 讀取 CSV 內容
        csv_content = io.StringIO(response.text)
        df = pd.read_csv(csv_content)

        if df.empty:
            print(f"[WARN] art_events 資料為空。")
            return pd.DataFrame()

        df["category"] = "art_events"
        df["name"] = df["title"]
        
        # 在美術館經緯度基礎上增加隨機偏移
        random_offset_lat = (np.random.rand(len(df)) - 0.5) * 0.01  # -0.005 到 +0.005 之間
        random_offset_lon = (np.random.rand(len(df)) - 0.5) * 0.01  # -0.005 到 +0.005 之間

        df["lat"] = TAIPEI_FINE_ARTS_MUSEUM_LAT + random_offset_lat
        df["lon"] = TAIPEI_FINE_ARTS_MUSEUM_LON + random_offset_lon
        df["value"] = 1.0 # 每個展覽都算一個點

        df.dropna(subset=["lat", "lon"], inplace=True)

        print(f"[OK] art_events 資料載入完成，共 {len(df)} 筆。")
        return df[["name", "category", "lat", "lon", "value"]]
    except requests.exceptions.RequestException as e:
        print(f"[ERR] 無法從 CSV 連結 {url} 獲取 art_events 資料：{e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"[ERR] 處理 art_events CSV 資料時發生未知錯誤：{e}")
        return pd.DataFrame()

def fetch_noise_monitoring():
    df = fetch_data_from_url(
        OPENDATA_APIS["noise"],
        "noise",
        name_col="測點名稱",
        lat_col="緯度",
        lon_col="經度",
        value_col=None, # 噪音監測點沒有直接的噪音數值，暫時給預設值
        default_value=50.0 # 假設一個中等噪音值
    )
    # 噪音數值應該是越低越好，所以這裡的 value 需要在 happiness.py 中反向處理
    return df

def fetch_sports_facilities():
    return fetch_data_from_url(
        OPENDATA_APIS["sports"],
        "sports",
        name_col="廠商名稱_市招",
        lat_col="緯度",
        lon_col="經度",
        value_col=None,
        default_value=1.0 # 每個場館都算一個點
    )

def fetch_air_quality():
    return fetch_data_from_url(
        OPENDATA_APIS["air"],
        "air",
        name_col="name", # 更正為 "name"
        lat_col="lat",
        lon_col="lon",
        value_col="value", # 更正為 "value"
        default_value=20.0
    )

def load_local_parks():
    # 從 OpenData API 獲取公園資料
    return fetch_data_from_url(
        OPENDATA_APIS["parks"],
        "parks",
        name_col="pm_name",
        lat_col="pm_Latitude",
        lon_col="pm_Longitude",
        value_col=None, # 公園沒有直接的數值，給預設值
        default_value=1.0
    )

def fetch_youbike_stations():
    # 從 OpenData API 獲取 YouBike 站點資料
    return fetch_data_from_url(
        OPENDATA_APIS["youbike"],
        "youbike",
        name_col="sna", # 站點名稱
        lat_col="latitude", # 緯度
        lon_col="longitude", # 經度
        value_col="available_rent_bikes", # 可租借車輛數作為數值
        default_value=0 # 預設為 0
    )

def load_all_opendata_spots():
    cache_file = os.path.join(os.path.dirname(__file__), "..", "cache", "spots_cache.json")
    
    # 嘗試從快取載入
    if os.path.exists(cache_file):
        try:
            print(f"💾 正在從快取檔案 {cache_file} 載入資料...")
            master_df = pd.read_json(cache_file)
            print(f"✅ 從快取載入完成，共 {len(master_df)} 筆資料。")
            return master_df
        except Exception as e:
            print(f"[ERR] 無法從快取載入資料：{e}，將嘗試重新獲取 OpenData。")

    dfs = []
    dfs.append(fetch_art_events())
    dfs.append(fetch_noise_monitoring())
    dfs.append(fetch_sports_facilities())
    dfs.append(fetch_air_quality())
    dfs.append(load_local_parks()) # 載入本地公園資料
    dfs.append(fetch_youbike_stations()) # 載入 YouBike 站點資料

    # 過濾掉空的 DataFrame
    dfs = [df for df in dfs if not df.empty]

    if not dfs:
        print("[ERR] 沒有任何 OpenData 資料成功載入！")
        return pd.DataFrame()

    master = pd.concat(dfs, ignore_index=True)
    print(f"✅ OpenData 資料載入完成，共 {len(master)} 筆。")

    # 將資料存入快取
    try:
        master.to_json(cache_file, orient="records", force_ascii=False, indent=2)
        print(f"💾 資料已成功存入快取檔案 {cache_file}。")
    except Exception as e:
        print(f"[ERR] 無法將資料存入快取：{e}")

    return master
