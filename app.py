from flask import Flask, jsonify, request, send_from_directory, session, redirect
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# MAYSNOK
# =========================================================

app = Flask(__name__, static_folder="static", static_url_path="/static")

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "maysnok-secret-key"
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise Exception("DATABASE_URL غير موجود")

    return psycopg2.connect(database_url)


# =========================================================
# CREATE TABLES
# =========================================================

def init_db():

    conn = get_db()
    cur = conn.cursor()

    try:

        # ---------------- USERS ----------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,

                role VARCHAR(30) NOT NULL,

                full_name VARCHAR(150) NOT NULL,

                phone VARCHAR(30) UNIQUE NOT NULL,

                password_hash TEXT NOT NULL,

                job VARCHAR(150),

                city VARCHAR(100),

                areas TEXT,

                photo_url TEXT,

                available BOOLEAN DEFAULT TRUE,

                verified BOOLEAN DEFAULT FALSE,

                active BOOLEAN DEFAULT TRUE,

                rating NUMERIC(3,2) DEFAULT 0,

                rating_count INTEGER DEFAULT 0,

                subscription_status VARCHAR(30)
                    DEFAULT 'trial',

                trial_ends_at TIMESTAMPTZ,

                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)


        # ---------------- SERVICE REQUESTS ----------------

        cur.execute("""
            CREATE TABLE IF NOT EXISTS service_requests (
                id SERIAL PRIMARY KEY,

                customer_id INTEGER
                    REFERENCES users(id)
                    ON DELETE SET NULL,

                professional_id INTEGER
                    REFERENCES users(id)
                    ON DELETE SET NULL,

                description TEXT,

                photo_url TEXT,

                voice_url TEXT,

                status VARCHAR(30)
                    DEFAULT 'pending',

                quoted_price NUMERIC(10,2),

                customer_lat DOUBLE PRECISION,

                customer_lng DOUBLE PRECISION,

                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return send_from_directory(".", "index.html")


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "app": "Maysnok"
    })


# =========================================================
# REGISTER
# =========================================================

@app.post("/api/register")
def register():

    data = request.get_json(silent=True) or {}

    role = str(
        data.get("role", "customer")
    ).strip().lower()

    full_name = str(
        data.get("full_name", "")
    ).strip()

    phone = str(
        data.get("phone", "")
    ).strip()

    password = str(
        data.get("password", "")
    )

    job = str(
        data.get("job", "")
    ).strip() or None

    city = str(
        data.get("city", "")
    ).strip() or None


    # ---------------- VALIDATION ----------------

    if role not in ["customer", "professional"]:

        return jsonify({
            "ok": False,
            "error": "نوع الحساب غير صحيح"
        }), 400


    if not full_name:

        return jsonify({
            "ok": False,
            "error": "أدخل الاسم الكامل"
        }), 400


    if not phone:

        return jsonify({
            "ok": False,
            "error": "أدخل رقم الهاتف"
        }), 400


    if len(password) < 4:

        return jsonify({
            "ok": False,
            "error": "كلمة المرور يجب أن تحتوي على 4 أحرف على الأقل"
        }), 400


    if role == "professional":

        if not job:

            return jsonify({
                "ok": False,
                "error": "اختر المهنة"
            }), 400

        if not city:

            return jsonify({
                "ok": False,
                "error": "اختر المدينة"
            }), 400


    password_hash = generate_password_hash(password)


    conn = get_db()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )

    try:

        # هل الهاتف موجود؟

        cur.execute("""
            SELECT id
            FROM users
            WHERE phone = %s
            LIMIT 1
        """, (phone,))

        existing = cur.fetchone()

        if existing:

            return jsonify({
                "ok": False,
                "error": "رقم الهاتف مسجل من قبل"
            }), 409


        # إنشاء الحساب

        cur.execute("""
            INSERT INTO users
            (
                role,
                full_name,
                phone,
                password_hash,
                job,
                city
            )
            VALUES
            (%s, %s, %s, %s, %s, %s)

            RETURNING
                id,
                role,
                full_name,
                phone,
                job,
                city
        """, (
            role,
            full_name,
            phone,
            password_hash,
            job,
            city
        ))


        user = cur.fetchone()

        conn.commit()


        return jsonify({
            "ok": True,
            "message": "تم إنشاء الحساب بنجاح",
            "user": user
        }), 201


    except Exception as e:

        conn.rollback()

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


    finally:

        cur.close()
        conn.close()


# =========================================================
# LOGIN
# =========================================================

@app.post("/api/login")
def login():

    data = request.get_json(silent=True) or {}

    phone = str(
        data.get("phone", "")
    ).strip()

    password = str(
        data.get("password", "")
    )


    if not phone or not password:

        return jsonify({
            "ok": False,
            "error": "أدخل رقم الهاتف وكلمة المرور"
        }), 400


    conn = get_db()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )


    try:

        cur.execute("""
            SELECT
                id,
                role,
                full_name,
                phone,
                password_hash,
                job,
                city,
                active,
                verified
            FROM users
            WHERE phone = %s
            LIMIT 1
        """, (phone,))


        user = cur.fetchone()


        if not user:

            return jsonify({
                "ok": False,
                "error": "رقم الهاتف غير مسجل"
            }), 401


        if not check_password_hash(
            user["password_hash"],
            password
        ):

            return jsonify({
                "ok": False,
                "error": "كلمة المرور غير صحيحة"
            }), 401


        if not user["active"]:

            return jsonify({
                "ok": False,
                "error": "الحساب موقوف"
            }), 403


        # ---------------- SESSION ----------------

        session["user_id"] = user["id"]
        session["role"] = user["role"]


        return jsonify({

            "ok": True,

            "id": user["id"],

            "role": user["role"],

            "full_name": user["full_name"],

            "phone": user["phone"],

            "job": user["job"],

            "city": user["city"]

        })


    finally:

        cur.close()
        conn.close()


# =========================================================
# LOGOUT
# =========================================================

@app.post("/api/logout")
def logout():

    session.clear()

    return jsonify({
        "ok": True,
        "message": "تم تسجيل الخروج"
    })


# =========================================================
# CURRENT USER
# =========================================================

@app.get("/api/me")
def current_user():

    user_id = session.get("user_id")

    if not user_id:

        return jsonify({
            "ok": False,
            "logged_in": False
        }), 401


    conn = get_db()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )


    try:

        cur.execute("""
            SELECT
                id,
                role,
                full_name,
                phone,
                job,
                city,
                areas,
                photo_url,
                available,
                verified,
                active,
                rating,
                rating_count,
                subscription_status
            FROM users
            WHERE id = %s
            LIMIT 1
        """, (user_id,))


        user = cur.fetchone()


        if not user:

            session.clear()

            return jsonify({
                "ok": False,
                "logged_in": False
            }), 401


        return jsonify({
            "ok": True,
            "logged_in": True,
            "user": user
        })


    finally:

        cur.close()
        conn.close()


# =========================================================
# PROFESSIONALS
# =========================================================

@app.get("/api/professionals")
def professionals():

    job = request.args.get(
        "job",
        ""
    ).strip()

    city = request.args.get(
        "city",
        ""
    ).strip()


    conn = get_db()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )


    try:

        query = """
            SELECT
                id,
                full_name,
                phone,
                job,
                city,
                areas,
                photo_url,
                available,
                verified,
                rating,
                rating_count
            FROM users
            WHERE role = 'professional'
              AND active = TRUE
        """

        params = []


        if job:

            query += """
                AND LOWER(job)
                LIKE LOWER(%s)
            """

            params.append(
                "%" + job + "%"
            )


        if city:

            query += """
                AND LOWER(city)
                LIKE LOWER(%s)
            """

            params.append(
                "%" + city + "%"
            )


        query += """
            ORDER BY
                verified DESC,
                available DESC,
                rating DESC,
                created_at DESC
            LIMIT 100
        """


        cur.execute(
            query,
            tuple(params)
        )


        rows = cur.fetchall()


        return jsonify({
            "ok": True,
            "professionals": rows
        })


    finally:

        cur.close()
        conn.close()


# =========================================================
# CREATE SERVICE REQUEST
# =========================================================

@app.post("/api/requests")
def create_service_request():

    user_id = session.get("user_id")

    role = session.get("role")


    if not user_id:

        return jsonify({
            "ok": False,
            "error": "يجب تسجيل الدخول أولاً"
        }), 401


    if role != "customer":

        return jsonify({
            "ok": False,
            "error": "طلب الخدمة مخصص للزبون"
        }), 403


    data = request.get_json(silent=True) or {}


    professional_id = data.get(
        "professional_id"
    )

    description = str(
        data.get("description", "")
    ).strip()

    photo_url = data.get(
        "photo_url"
    )

    voice_url = data.get(
        "voice_url"
    )

    customer_lat = data.get(
        "customer_lat"
    )

    customer_lng = data.get(
        "customer_lng"
    )


    if not professional_id:

        return jsonify({
            "ok": False,
            "error": "اختر المهني"
        }), 400


    conn = get_db()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )


    try:

        # التأكد من أن المهني موجود

        cur.execute("""
            SELECT
                id,
                full_name
            FROM users
            WHERE id = %s
              AND role = 'professional'
              AND active = TRUE
            LIMIT 1
        """, (professional_id,))


        professional = cur.fetchone()


        if not professional:

            return jsonify({
                "ok": False,
                "error": "المهني غير موجود"
            }), 404


        cur.execute("""
            INSERT INTO service_requests
            (
                customer_id,
                professional_id,
                description,
                photo_url,
                voice_url,
                customer_lat,
                customer_lng
            )

            VALUES
            (%s, %s, %s, %s, %s, %s, %s)

            RETURNING
                id,
                status,
                created_at
        """, (

            user_id,

            professional_id,

            description,

            photo_url,

            voice_url,

            customer_lat,

            customer_lng

        ))


        service_request = cur.fetchone()

        conn.commit()


        return jsonify({

            "ok": True,

            "message":
                "تم إرسال الطلب إلى المهني بنجاح",

            "request":
                service_request

        }), 201


    except Exception as e:

        conn.rollback()

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


    finally:

        cur.close()
        conn.close()


# =========================================================
# PROFESSIONAL REQUESTS
# =========================================================

@app.get("/api/requests")
def professional_requests():

    user_id = session.get("user_id")

    role = session.get("role")


    if not user_id:

        return jsonify({
            "ok": False,
            "error": "يجب تسجيل الدخول"
        }), 401


    if role != "professional":

        return jsonify({
            "ok": False,
            "error": "هذه الصفحة خاصة بالمهني"
        }), 403


    conn = get_db()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )


    try:

        cur.execute("""
            SELECT
                r.id,
                r.description,
                r.photo_url,
                r.voice_url,
                r.status,
                r.quoted_price,
                r.customer_lat,
                r.customer_lng,
                r.created_at,

                u.full_name AS customer_name,

                u.phone AS customer_phone

            FROM service_requests r

            LEFT JOIN users u
                ON u.id = r.customer_id

            WHERE r.professional_id = %s

            ORDER BY r.created_at DESC
        """, (user_id,))


        rows = cur.fetchall()


        return jsonify({
            "ok": True,
            "requests": rows
        })


    finally:

        cur.close()
        conn.close()


# =========================================================
# CUSTOMER REQUESTS
# =========================================================

@app.get("/api/my-requests")
def customer_requests():

    user_id = session.get("user_id")

    role = session.get("role")


    if not user_id:

        return jsonify({
            "ok": False,
            "error": "يجب تسجيل الدخول"
        }), 401


    if role != "customer":

        return jsonify({
            "ok": False,
            "error": "هذه الصفحة خاصة بالزبون"
        }), 403


    conn = get_db()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )


    try:

        cur.execute("""
            SELECT
                r.id,
                r.description,
                r.status,
                r.quoted_price,
                r.created_at,

                u.full_name
                    AS professional_name,

                u.phone
                    AS professional_phone,

                u.job
                    AS professional_job

            FROM service_requests r

            LEFT JOIN users u
                ON u.id = r.professional_id

            WHERE r.customer_id = %s

            ORDER BY r.created_at DESC
        """, (user_id,))


        rows = cur.fetchall()


        return jsonify({
            "ok": True,
            "requests": rows
        })


    finally:

        cur.close()
        conn.close()


# =========================================================
# PROFESSIONAL PAGE
# =========================================================

@app.get("/professional")
def professional_page():

    if (
        not session.get("user_id")
        or session.get("role")
        != "professional"
    ):

        return redirect("/")


    if os.path.exists(
        "professional.html"
    ):

        return send_from_directory(
            ".",
            "professional.html"
        )


    return redirect("/")


# =========================================================
# ADMIN
# =========================================================

@app.get("/admin")
def admin_page():

    if os.path.exists("admin.html"):

        return send_from_directory(
            ".",
            "admin.html"
        )

    return jsonify({
        "ok": False,
        "error": "admin.html غير موجود"
    }), 404


# =========================================================
# ADMIN USERS
# =========================================================

@app.get("/api/admin/users")
def admin_users():

    conn = get_db()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )


    try:

        cur.execute("""
            SELECT
                id,
                role,
                full_name,
                phone,
                job,
                city,
                available,
                verified,
                active,
                rating,
                rating_count,
                subscription_status,
                created_at

            FROM users

            ORDER BY created_at DESC
        """)


        users = cur.fetchall()


        return jsonify({
            "ok": True,
            "users": users
        })


    finally:

        cur.close()
        conn.close()


# =========================================================
# ADMIN REQUESTS
# =========================================================

@app.get("/api/admin/requests")
def admin_requests():

    conn = get_db()

    cur = conn.cursor(
        cursor_factory=RealDictCursor
    )


    try:

        cur.execute("""
            SELECT
                r.id,

                r.description,

                r.status,

                r.quoted_price,

                r.created_at,

                c.full_name
                    AS customer_name,

                p.full_name
                    AS professional_name,

                p.job
                    AS professional_job

            FROM service_requests r

            LEFT JOIN users c
                ON c.id = r.customer_id

            LEFT JOIN users p
                ON p.id = r.professional_id

            ORDER BY r.created_at DESC
        """)


        rows = cur.fetchall()


        return jsonify({
            "ok": True,
            "requests": rows
        })


    finally:

        cur.close()
        conn.close()


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({
        "ok": False,
        "error": "الصفحة غير موجودة"
    }), 404


@app.errorhandler(500)
def internal_error(error):

    return jsonify({
        "ok": False,
        "error": "وقع خطأ في الخادم"
    }), 500


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    try:

        init_db()

        print(
            "Maysnok database ready"
        )

    except Exception as e:

        print(
            "Database error:",
            e
        )


    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(
        host="0.0.0.0",
        port=port
    )
        
