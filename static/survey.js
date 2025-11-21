// survey.js

function submitSurvey() {

    const experience_pref = document.getElementById("q1").value; // 第一題：希望獲得什麼體驗
    const noise_pref = document.querySelector("input[name='q2']:checked").value; // 第二題：環境聲音偏好
    const activity_intensity = document.querySelector("input[name='q3']:checked").value; // 第三題：活動強度
    const stress_level = document.getElementById("q4").value; // 新增的第四題：壓力程度

    const answers = [experience_pref, noise_pref, activity_intensity, stress_level];

    fetch("/result", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ answers })
    })
    .then(r => r.json())
    .then(data => {

        const mood = data.mood;
        const mood_map = {
            "療癒放鬆": "🌿 療癒放鬆",
            "城市漫步": "🚶‍♀️ 城市漫步",
            "活力充電": "⚡ 活力充電",
            "文化探索": "🎨 文化探索",
        };

        document.getElementById("mood-text").innerText =
            "你的今日心情是：" + (mood_map[mood] || mood);

        const modal = document.getElementById("mood-modal");
        modal.style.display = "flex";

        // 1.5 秒後跳首頁
        setTimeout(() => {
            window.location.href = "/?mood=" + mood; // 使用新的 mood 標籤
        }, 1500);
    })
    .catch(err => {
        alert("送出失敗，請再試一次！");
        console.error(err);
    });
}
