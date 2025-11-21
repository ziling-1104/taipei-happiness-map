/* ============================================================
   工具：計算兩點距離（公里）
============================================================ */
function calcDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // 地球半徑（公里）
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a =
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1*Math.PI/180) * Math.cos(lat2*Math.PI/180) *
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c; // KM
}

// 全局變數，用於儲存用戶的地理位置
let userGeolocation = {
    lat: null,
    lon: null
};

/* ============================================================
   切換心情（改為 AJAX 動態更新頁面）
============================================================ */
function switchMood(mood) {
    // 更新 URL，但不重新載入頁面，以便歷史記錄和分享
    const url = new URL(window.location.href);
    url.searchParams.set('mood', mood);
    if (userGeolocation.lat && userGeolocation.lon) {
        url.searchParams.set('lat', userGeolocation.lat);
        url.searchParams.set('lon', userGeolocation.lon);
    }
    window.history.pushState({ path: url.href }, '', url.href);

    fetch(`/api/mood/${mood}?lat=${userGeolocation.lat || ''}&lon=${userGeolocation.lon || ''}`)
        .then(response => response.json())
        .then(data => {
            if (data.recommendations) {
                renderRecommendationList(data.recommendations); // 更新右側列表
                updateMapMarkers(data.recommendations); // 更新地圖標記
            }
        })
        .catch(error => console.error('Error fetching mood recommendations:', error));
}

/* ============================================================
   顯示用戶當前位置
============================================================ */
function showUserLocation() {
    const locationDiv = document.getElementById("user-location");
    if (!locationDiv) return;

    const urlParams = new URLSearchParams(window.location.search);
    const latFromUrl = parseFloat(urlParams.get('lat'));
    const lonFromUrl = parseFloat(urlParams.get('lon'));

    const currentMood = urlParams.get('mood') || '療癒放鬆';

    const processLocation = (lat, lon) => {
        userGeolocation.lat = lat;
        userGeolocation.lon = lon;
        // 獲取位置後，調用 switchMood 來載入推薦並更新地圖/列表
        switchMood(currentMood); 
    };

    if (!isNaN(latFromUrl) && !isNaN(lonFromUrl)) {
        processLocation(latFromUrl, lonFromUrl);
    } else {
    navigator.geolocation.getCurrentPosition(pos => {
            processLocation(pos.coords.latitude, pos.coords.longitude);
    }, () => {
        locationDiv.innerHTML = "無法獲取您的位置。";
            // 即使無法獲取位置，也嘗試載入推薦（不帶位置參數）
            switchMood(currentMood);
    });
    }
}

// 在頁面載入時呼叫以顯示位置並初始化地圖
window.addEventListener("load", () => {
    showUserLocation();
});

/* ============================================================
   更新地圖標記 (新功能)
============================================================ */
let currentMap; // 用於儲存目前的 Folium 地圖實例

// 由於 Folium 是在 Python 後端生成 HTML，我們需要一種方式來重新初始化地圖或更新標記
// 最簡單的方法是替換整個地圖 iframe/div 的內容，但這會導致閃爍
// 更好的方法是直接操作 Folium map 對象，但這需要 Folium 提供 JS API
// 鑑於目前 Folium 在前端主要是靜態 HTML，我們暫時通過重新載入地圖區域來模擬更新。
// 這不是最優解，但比重新載入整個頁面要好。
// 未來可以考慮使用 Leaflet.js 或 Google Maps API 直接在前端操作地圖，以達到更流暢的體驗。
function updateMapMarkers(recs = []) {
    // 重新請求整個地圖區域的 HTML，並告訴後端要顯示哪些景點
    const urlParams = new URLSearchParams(window.location.search);
    const currentMood = urlParams.get('mood') || '療癒放鬆';
    const latParam = userGeolocation.lat ? `&lat=${userGeolocation.lat}` : '';
    const lonParam = userGeolocation.lon ? `&lon=${userGeolocation.lon}` : '';
    const namesParam = recs.length
        ? `&names=${encodeURIComponent(JSON.stringify(recs.map(r => r.name)))}`
        : '';

    fetch(`/?mood=${currentMood}${latParam}${lonParam}&map_only=true${namesParam}`)
        .then(response => response.text())
        .then(mapHtml => {
            const mapContainer = document.getElementById('map-area');
            if (mapContainer) {
                // 簡單粗暴地替換地圖內容。這會導致閃爍，但避免了整頁重載。
                mapContainer.innerHTML = mapHtml;
            }
        })
        .catch(error => console.error('Error updating map markers:', error));
}

/* ============================================================
   右側卡片
============================================================ */
function renderRecommendationList(recs) {
    const box = document.getElementById("rec-list");
    box.innerHTML = "";

    recs.forEach((r, idx) => {
        let checkinButtonHtml = '';
        let distanceText = ''; // 新增距離文字變數
        if (userGeolocation.lat && userGeolocation.lon) {
            const dist = calcDistance(userGeolocation.lat, userGeolocation.lon, r.lat, r.lon) * 1000; // 公尺
            const isNear = dist <= 100; // 100 公尺內可打卡
            const btnClass = isNear ? 'btn-checkin-enabled' : 'btn-checkin-disabled';
            const isDisabled = isNear ? '' : 'disabled';
            
            // 無論是否在範圍內，都顯示距離
            distanceText = ` (${Math.round(dist)} 公尺)`; 

            const btnText = `打卡${distanceText}`;
            
            let titleText = '';
            if (!userGeolocation.lat || !userGeolocation.lon) {
                titleText = '請先開啟位置服務，才能打卡喔！';
            } else if (!isNear) {
                titleText = `距離目標 ${Math.round(dist)} 公尺，太遠了，請靠近一點才能打卡！`;
            } else {
                titleText = '點擊打卡！';
            }

            checkinButtonHtml = `<button class="${btnClass}" ${isDisabled} title="${titleText}" onclick="completeTask('${r.name}', ${r.lat}, ${r.lon}, ${userGeolocation.lat}, ${userGeolocation.lon})">${btnText}</button>`;
        } else {
            checkinButtonHtml = '<button class="btn-checkin-disabled" disabled title="請先開啟位置服務，才能打卡喔！">打卡</button>';
        }

        box.innerHTML += `
            <div class="card">
                <div class="card-title" onclick="navigateToSpot(${r.lat}, ${r.lon})">${r.name}</div> <!-- 新增 onclick 事件 -->
                <div class="card-cat">分類：${r.category}</div>

                <div class="happiness" style="color:${r.happiness_color}">
                    幸福指數：${r.happiness}
                </div>

                <div class="show-detail" onclick="toggleDetail('${idx}')">
                    ➜ 查看公式
                </div>
                ${checkinButtonHtml}

                <div id="detail-${idx}" class="detail-box">
                    base：${r.base}<br>
                    weight：${r.weight}<br>
                    value_norm：${r.value_norm}<br>
                    距離分：${r.dist_score}<br>
                    原始 value：${r.value}<br>
                </div>
            </div>
        `;
    });
}

function toggleDetail(id) {
    const box = document.getElementById("detail-" + id);
    if (!box) return;
    box.style.display = box.style.display === "none" ? "block" : "none";
}

/* ============================================================
   導航到景點
============================================================ */
function navigateToSpot(lat, lon) {
    window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`, '_blank');
}

/* ============================================================
   打卡（加入距離判定）
============================================================ */
function completeTask(name, lat, lon, userLat, userLon) {
    // 距離驗證已在後端處理，這裡只需要發送請求
        fetch("/api/complete", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                name: name,
            lat: userLat, // 傳遞用戶實際位置
            lon: userLon, // 傳遞用戶實際位置
                target_lat: lat,
                target_lon: lon
            })
        })
        .then(r => r.json())
        .then(data => {
            alert(data.message);
        // 不論是否成功打卡，都重新載入頁面以更新任務列表和成就
                window.location.reload();
        })
        .catch(() => alert("打卡失敗！"));
}
