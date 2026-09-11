# Maysnok App

نسخة أولية جاهزة للنشر على Railway.

## التشغيل محلياً
```bash
pip install -r requirements.txt
python app.py
```

## Railway
Railway سيستعمل Procfile تلقائياً:
`web: gunicorn app:app`
