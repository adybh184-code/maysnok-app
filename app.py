from flask import Flask, jsonify, request, send_from_directory
import os

app = Flask(__name__, static_folder="static", static_url_path="/static")

CATEGORIES = [
    {"id": "electric", "name": "كهربائي", "icon": "⚡"},
    {"id": "plumber", "name": "سباك", "icon": "🔧"},
    {"id": "building", "name": "بناء وترميم", "icon": "🧱"},
    {"id": "glass", "name": "ألمنيوم وزجاج", "icon": "🪟"},
    {"id": "repairs", "name": "إصلاحات المنازل والمكاتب", "icon": "🏠"},
    {"id": "moving", "name": "نقل الأثاث والبضائع", "icon": "🚚"},
    {"id": "it", "name": "الإعلاميات والكمبيوتر", "icon": "💻"},
    {"id": "painting", "name": "صباغ", "icon": "🎨"},
    {"id": "catering", "name": "تموين المناسبات", "icon": "🍽️"},
    {"id": "cleaning", "name": "تنظيف المنازل والمكاتب", "icon": "🧹"},
    {"id": "mechanic", "name": "ميكانيك وإصلاح السيارات", "icon": "🚗"},
    {"id": "carpenter", "name": "نجارة", "icon": "🪚"},
    {"id": "welding", "name": "حدادة ولحام", "icon": "🔩"},
]

ARTISANS = [
    {"name": "محمد", "job": "كهربائي", "city": "كلميم", "rating": 4.9, "phone": "0600000001", "available": True},
    {"name": "سعيد", "job": "سباك", "city": "كلميم", "rating": 4.8, "phone": "0600000002", "available": True},
    {"name": "يونس", "job": "صباغ", "city": "تزنيت", "rating": 4.7, "phone": "0600000003", "available": False},
    {"name": "رشيد", "job": "ميكانيك وإصلاح السيارات", "city": "تزنيت", "rating": 4.9, "phone": "0600000004", "available": True},
]

@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")

@app.get("/api/categories")
def categories():
    return jsonify(CATEGORIES)

@app.get("/api/artisans")
def artisans():
    city = (request.args.get("city") or "").strip()
    job = (request.args.get("job") or "").strip()
    result = ARTISANS
    if city:
        result = [a for a in result if city in a["city"]]
    if job:
        result = [a for a in result if job in a["job"]]
    return jsonify(result)

@app.post("/api/ai-match")
def ai_match():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    city = (data.get("city") or "").strip()

    keyword_map = {
        "ضو": "كهربائي", "كهرب": "كهربائي", "فيشة": "كهربائي",
        "ماء": "سباك", "حنفية": "سباك", "تسرب": "سباك",
        "صباغ": "صباغ", "دهان": "صباغ",
        "سيارة": "ميكانيك وإصلاح السيارات", "موتور": "ميكانيك وإصلاح السيارات",
        "كمبيوتر": "الإعلاميات والكمبيوتر", "حاسوب": "الإعلاميات والكمبيوتر",
        "نقل": "نقل الأثاث والبضائع", "اثاث": "نقل الأثاث والبضائع",
        "زجاج": "ألمنيوم وزجاج", "المنيوم": "ألمنيوم وزجاج",
        "تنظيف": "تنظيف المنازل والمكاتب",
        "نجار": "نجارة", "خشب": "نجارة",
    }

    job = ""
    for key, value in keyword_map.items():
        if key in text:
            job = value
            break

    matches = ARTISANS
    if city:
        matches = [a for a in matches if city in a["city"]]
    if job:
        matches = [a for a in matches if job in a["job"]]

    return jsonify({
        "detected_job": job or "خدمة عامة",
        "matches": matches[:3],
        "message": "تم اقتراح أقرب المهنيين حسب وصفك."
    })

@app.get("/health")
def health():
    return jsonify({"status": "ok"})
@app.get("/")
def  homepage ():
    return send_from_directory(".", "index.html")
if __name__ == "__main__":
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
