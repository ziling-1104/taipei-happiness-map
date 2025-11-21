from typing import List
import pandas as pd

# 定義每種心情關注的資料類別（依圖示說明的優先順序）
MOOD_TO_CATEGORY = {
    "療癒放鬆": ["air", "parks"],          # 專注呼吸與綠意
    "城市漫步": ["noise", "parks"],        # 著重安靜街區與步行友善
    "活力充電": ["sports", "parks"],       # 以運動設施為主，輔以綠地
    "文化探索": ["art_events", "parks"],   # 藝文活動優先，公園次之
}


def filter_by_mood(df: pd.DataFrame, mood: str) -> pd.DataFrame:
    """
    根據心情保留需要的資料類別，使左右欄位同步。
    若該心情無符合資料，回傳原始 df，避免畫面空白。
    """
    categories: List[str] = MOOD_TO_CATEGORY.get(mood, [])
    if not categories:
        return df
    filtered = df[df["category"].isin(categories)]
    return filtered if not filtered.empty else df

