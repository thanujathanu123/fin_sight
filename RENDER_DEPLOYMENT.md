# 🚀 FinSight Deployment Guide - Render

This guide provides step-by-step instructions to deploy the **FinSight** Django application to Render.

---

## 📋 Prerequisites

Before starting, you need:
1. **GitHub account** with your repository pushed
2. **Render account** (free at https://render.com)
3. **PostgreSQL database** (Render provides managed PostgreSQL)
4. **Redis** for Celery and Channels (optional but recommended)
5. Environment variables configured

---

## 🔧 Step 1: Prepare Your Project for Deployment

### 1.1 Update `requirements.txt`

Add these packages to your requirements.txt for production:
```
gunicorn>=21.0
psycopg2-binary>=2.9
python-decouple>=3.8
whitenoise>=6.5
daphne>=4.0
```

Your complete requirements.txt should have:
```
Django>=4.2
pandas>=2.0
reportlab>=4.0
scikit-learn>=1.2
joblib>=1.3
numpy>=1.24
celery>=5.3
openpyxl>=3.1
python-dateutil>=2.8
djangorestframework>=3.14
channels>=4.0
channels-redis>=4.1
gunicorn>=21.0
psycopg2-binary>=2.9
python-decouple>=3.8
whitenoise>=6.5
daphne>=4.0
```

### 1.2 Create `.env.example` (for reference)
```
# Database
DATABASE_URL=postgresql://user:password@hostname:5432/dbname

# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.render.com,www.yourdomain.com

# Redis (optional)
REDIS_URL=redis://username:password@hostname:port

# Static Files
STATIC_URL=/static/
STATIC_ROOT=/opt/render/project/static
MEDIA_ROOT=/opt/render/project/media
```

### 1.3 Update `finsight/settings.py`

Make these changes to your settings file:

```python
# At the top, add:
import os
from decouple import config

# DEBUG - Set to False for production
DEBUG = config('DEBUG', default=False, cast=bool)

# ALLOWED_HOSTS
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=lambda v: [s.strip() for s in v.split(',')])

# SECRET_KEY
SECRET_KEY = config('SECRET_KEY', default='your-secret-key')

# DATABASES - Use PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='finsight_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# STATIC FILES
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# MEDIA FILES
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CSRF & Security (Production)
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', 
    default='https://yourdomain.render.com', 
    cast=lambda v: [s.strip() for s in v.split(',')])

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
}

# CELERY Configuration
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# CHANNELS Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://localhost:6379/0')],
        },
    },
}

# Add WhiteNoise middleware (must be first after SecurityMiddleware)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this line
    # ... rest of middleware
]
```

### 1.4 Create `render.yaml` (Build Configuration)

Create this file in your project root:

```yaml
services:
  - type: web
    name: finsight-web
    env: python
    plan: free
    runtime: python-3.11
    buildCommand: |
      pip install -r requirements.txt
      python manage.py collectstatic --noinput
      python manage.py migrate
    startCommand: gunicorn finsight.wsgi:application --bind 0.0.0.0:$PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.7
      - key: DEBUG
        value: false
      - key: SECRET_KEY
        fromDatabase:
          name: finsight_db
          property: password

  - type: redis
    name: finsight-redis
    plan: free
    maxmemoryPolicy: allkeys-lru

  - type: worker
    name: finsight-celery
    env: python
    plan: free
    runtime: python-3.11
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A finsight worker -l info
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.7
      - fromService:
          name: finsight-redis
          property: connectionString
        key: REDIS_URL

databases:
  - name: finsight_db
    databaseName: finsight_db
    user: finsight_user
    plan: free
```

---

## 📤 Step 2: Push to GitHub

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

---

## 🌐 Step 3: Create Services on Render

### 3.1 Create PostgreSQL Database
1. Go to https://dashboard.render.com
2. Click **New +** → **PostgreSQL**
3. Set:
   - **Name**: `finsight-db`
   - **Database**: `finsight_db`
   - **User**: `finsight_user`
   - **Plan**: Free
4. Click **Create Database**
5. Copy the **Internal Database URL** (you'll need this)

### 3.2 Create Redis Instance (Optional but Recommended)
1. Click **New +** → **Redis**
2. Set:
   - **Name**: `finsight-redis`
   - **Plan**: Free
3. Click **Create Redis**
4. Copy the **Internal Redis URL**

### 3.3 Create Web Service
1. Click **New +** → **Web Service**
2. Connect your GitHub repository
3. Set:
   - **Name**: `finsight-web`
   - **Environment**: Python 3
   - **Build Command**: 
     ```
     pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
     ```
   - **Start Command**: 
     ```
     gunicorn finsight.wsgi:application --bind 0.0.0.0:$PORT
     ```
4. Set **Plan**: Free

### 3.4 Add Environment Variables to Web Service

In the **Environment** section, add:

```
DEBUG=false
SECRET_KEY=<generate-strong-key>
ALLOWED_HOSTS=<your-render-domain>.onrender.com
DATABASE_URL=<postgresql-connection-string-from-step-3.1>
REDIS_URL=<redis-connection-string-from-step-3.2>
CSRF_TRUSTED_ORIGINS=https://<your-render-domain>.onrender.com
```

**To generate a strong SECRET_KEY:**
```python
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

### 3.5 Deploy Web Service
1. Click **Deploy**
2. Wait for the build to complete (5-10 minutes)
3. Once successful, you'll get a URL like: `https://finsight-web-xxxxx.onrender.com`

### 3.6 Create Celery Worker (Optional)
1. Click **New +** → **Background Worker**
2. Set:
   - **Name**: `finsight-celery`
   - **Environment**: Python 3
   - **Build Command**: 
     ```
     pip install -r requirements.txt
     ```
   - **Start Command**: 
     ```
     celery -A finsight worker -l info
     ```
3. Add the same environment variables as Web Service
4. Click **Deploy**

---

## 🔑 Step 4: Configure Environment Variables

Update your Render environment variables with your actual database/redis URLs:

### For Web Service:
```
DATABASE_URL=postgresql://finsight_user:<password>@<host>:<port>/finsight_db
REDIS_URL=redis://<host>:<port>
STATIC_ROOT=/opt/render/project/static
MEDIA_ROOT=/opt/render/project/media
```

---

## ✅ Step 5: Verify Deployment

1. Visit your Render URL: `https://finsight-web-xxxxx.onrender.com`
2. Check logs in Render dashboard for errors
3. Test admin login at `/admin`
4. Test ledger upload functionality

---

## 🛠️ Common Issues & Fixes

### Issue: Static Files Not Loading
**Solution:**
```bash
python manage.py collectstatic --noinput
```
Add to build command in Render.

### Issue: Database Connection Error
**Solution:**
- Verify `DATABASE_URL` is correct in environment variables
- Run migrations: `python manage.py migrate`

### Issue: Celery Tasks Not Running
**Solution:**
- Ensure Redis URL is set correctly
- Check Celery worker logs in Render dashboard
- Verify Celery worker service is running

### Issue: Media Files Not Persisting
**Solution:**
- Free tier Render instances reset daily
- Use external storage (AWS S3, Cloudinary) for production
- Or upgrade to paid tier with persistent storage

---

## 📈 Performance Optimization

### For Production:
1. **Use PostgreSQL** (not SQLite)
2. **Enable Redis** for caching and Celery
3. **Upgrade to paid Render plan** for persistent storage
4. **Use CDN** for static files (Cloudflare)
5. **Configure logging** and monitoring

---

## 🔐 Security Checklist

- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Enable `SECURE_SSL_REDIRECT`
- [ ] Set `ALLOWED_HOSTS` correctly
- [ ] Use PostgreSQL (not SQLite)
- [ ] Enable CSRF protection
- [ ] Configure CORS if needed
- [ ] Regularly update dependencies

---

## 📞 Support & Troubleshooting

- **Render Docs**: https://render.com/docs
- **Django Docs**: https://docs.djangoproject.com
- **Render Support**: https://render.com/support

---

## ✨ Next Steps After Deployment

1. Create superuser for admin access:
   ```bash
   python manage.py createsuperuser
   ```
   (Run locally, then sync via migrations)

2. Configure custom domain (if you have one):
   - Go to Render dashboard → Web Service → Settings
   - Add custom domain

3. Set up automated backups for database

4. Monitor application logs regularly

---

**Happy Deploying! 🎉**
