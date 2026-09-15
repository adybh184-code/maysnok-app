from flask import Flask, jsonify, request, send_from_directory, session, redirect
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.environ.get("SECRET_KEY")


# =========================
# DATABASE
# =========================
def get_db():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL غير موجود")

    return psycopg2.connect(database_url)


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            role VARCHAR(20) NOT NULL,
            full_name VARCHAR(150) NOT NULL,
            phone VARCHAR(30) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            job VARCHAR(100),
            city VARCHAR(100),
            areas TEXT,
            photo_url TEXT,
            available BOOLEAN DEFAULT TRUE,
            verified BOOLEAN DEFAULT FALSE,
            active BOOLEAN DEFAULT TRUE,
            rating NUMERIC(3,2) DEFAULT 0,
            rating_count INTEGER DEFAULT 0,
            subscription_status VARCHAR(30) DEFAULT 'trial',
            trial_ends_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '30 days',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS service_requests (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            professional_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            description TEXT,
            photo_url TEXT,
            voice_url TEXT,
            status VARCHAR(30) DEFAULT 'pending',
            quoted_price NUMERIC(10,2),
            customer_lat DOUBLE PRECISION,
            customer_lng DOUBLE PRECISION,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            professional_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            stars INTEGER CHECK (stars >= 1 AND stars <= 5),
            comment TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


try:
    init_db()
    print("Database ready")
except Exception as e:
    print("Database error:", e)
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
   return send_from_directory(".", "index.html") 

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
def homepage():
    return send_from_directory(".", "index.html")

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            username == os.environ.get("ADMIN_USER")
            and password == os.environ.get("ADMIN_PASSWORD")
        ):
            session["admin_logged_in"] = True
            return redirect("/admin")

        error = "اسم المستخدم أو كلمة السر غير صحيحة"

    html = """
    <!doctype html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>دخول الإدارة - Maysnok</title>
        <style>
            body {
                font-family: Arial;
                background: #f3f6fb;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }
            .box {
                background: white;
                width: 340px;
                padding: 30px;
                border-radius: 18px;
                box-shadow: 0 8px 30px rgba(0,0,0,.12);
            }
            h2 {
                text-align: center;
                color: #1264d8;
            }
            input {
                width: 100%;
                padding: 13px;
                margin: 8px 0;
                box-sizing: border-box;
                border: 1px solid #ddd;
                border-radius: 10px;
            }
            button {
                width: 100%;
                padding: 13px;
                background: #1264d8;
                color: white;
                border: 0;
                border-radius: 10px;
                font-size: 16px;
                cursor: pointer;
            }
            .error {
                color: red;
                text-align: center;
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>Maysnok</h2>
            <p style="text-align:center;">دخول لوحة الإدارة</p>

            <div class="error">__ERROR__</div>

            <form method="POST">
                <input name="username" placeholder="اسم المستخدم" required>
                <input name="password" type="password" placeholder="كلمة السر" required>
                <button type="submit">دخول</button>
            </form>
        </div>
    </body>
    </html>
    """

    return html.replace("__ERROR__", error)


@app.get("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    return send_from_directory(".", "admin.html")


@app.get("/admin-logout")
def admin_logout():
    session.clear()
    return redirect("/admin-login")                                                                                                                                            
@app.post("/api/register")
def register_user():
    data = request.get_json(silent=True) or {}

    role = data.get("role", "").strip()
    full_name = data.get("full_name", "").strip()
    phone = data.get("phone", "").strip()
    password = data.get("password", "")
    job = data.get("job", "").strip()
    city = data.get("city", "").strip()

    if role not in ["professional", "customer"]:
        return jsonify({
            "ok": False,
            "message": "نوع الحساب غير صحيح"
        }), 400

    if not full_name or not phone or not password:
        return jsonify({
            "ok": False,
            "message": "عمر جميع المعلومات"
        }), 400

    if role == "professional" and (not job or not city):
        return jsonify({
            "ok": False,
            "message": "اختر المهنة والمدينة"
        }), 400

    password_hash = generate_password_hash(password)

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            INSERT INTO users
            (role, full_name, phone, password_hash, job, city)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, role, full_name, phone, job, city
        """, (
            role,
            full_name,
            phone,
            password_hash,
            job or None,
            city or None
        ))

        user = cur.fetchone()
        conn.commit()

        return jsonify({
            "ok": True,
            "message": "تم إنشاء الحساب بنجاح",
            "user": user
        })

    except psycopg2.Error as e:
        conn.rollback()

        if e.pgcode == "23505":
            return jsonify({
                "ok": False,
                "message": "رقم الهاتف مسجل من قبل"
            }), 409

        return jsonify({
            "ok": False,
            "message": "وقع خطأ أثناء إنشاء الحساب"
        }), 500

    finally:
        cur.close()
        conn.close()
@app.get("/api/admin/users")
def admin_users():
    if not session.get("admin_logged_in"):
        return jsonify({
            "ok": False,
            "message": "غير مسموح"
        }), 401

    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            id,
            role,
            full_name,
            phone,
            job,
            city,
            active,
            verified,
            subscription_status
        FROM users
        ORDER BY id DESC
    """)

    users = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify(users) 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
