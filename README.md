# Taipei Vibe Finder — 台北市幸福鈴🔔 
### 「數據驅動的城市療癒，為你的心情找到最佳出口。」

## 🌟 專案簡介 (Introduction)
為了協助使用者們紓解在城市中累積的生活壓力，我們開發出可以依據使用者心情，<br>
並從臺北市資料大平臺中擷取資料並生成互動地圖，<br>
透過數據科學，為市民客製化推薦「最適合散心、運動、放鬆」的地點。

## 🖥️ 工具概述
這是一個可直接執行的 Python 專案（Flask + Folium + Pandas + Requests）。

主要使用之程式語言：Python
* 所有功能皆基於 Python 的第三方套件進行開發

🟡 後端：flask<br>
🟡 資料分析與處理套件：pandas, numpy<br>
🟡 交互式地圖套件：folium

## 🧭 使用指南
這是任何程式碼專案的關鍵，應提供清晰的步驟讓評審或任何人能成功運行。

環境要求： (例如：Node.js vX.X, Python vX.X)

Clone 專案：

```bash
git clone https://github.com/ziling-1104/taipei-happiness-map.git
cd taipei-happiness-map
後端設定： (包括設定 .env 檔中的 API Keys 和資料庫連線)
```

```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate  # Windows PowerShell

pip install -r requirements.txt

python app.py
```
