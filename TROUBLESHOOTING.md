# Mess Management System - Troubleshooting Guide

## Issues Fixed ✅

### 1. Django Admin Error
**Problem**: `admin.E108` error in ScanEventAdmin
**Solution**: Fixed the field reference from `'staff_token'` to `'staff_token_id'` in `mess/admin.py`

### 2. Database Tables Creation
**Problem**: No tables were created in the database
**Solution**: 
- Created migrations with `python manage.py makemigrations`
- Applied migrations with `python manage.py migrate`
- All tables are now created successfully

## Current Issues & Solutions 🔧

### 1. Supabase Database Connection ❌

**Problem**: Cannot connect to Supabase database
```
django.db.utils.OperationalError: could not translate host name "db.wqcswbpvsotrvdnrxesm.supabase.co" to address: nodename nor servname provided, or not known
```

**Possible Causes**:
- Incorrect Supabase URL
- Network connectivity issues
- Supabase project deleted or suspended
- DNS resolution problems

**Solutions**:
1. **Verify Supabase URL**: 
   - Go to your Supabase dashboard
   - Check if the project still exists
   - Get the correct database URL from Settings > Database

2. **Test Connection**:
   ```bash
   # Test if hostname resolves
   ping db.wqcswbpvsotrvdnrxesm.supabase.co
   
   # Test database connection
   psql "postgresql://postgres:imvajLub60cpcU6d@db.wqcswbpvsotrvdnrxesm.supabase.co:5432/postgres"
   ```

3. **Update .env file** with correct URL:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_PROJECT.supabase.co:5432/postgres
   ```

### 2. Telegram Bot Not Responding ❌

**Problem**: Bot token is set to placeholder value
```env
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

**Solution**:
1. **Create/Get Bot Token**:
   - Message @BotFather on Telegram
   - Use `/newbot` command or `/token` for existing bot
   - Copy the token

2. **Update .env file**:
   ```env
   TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

3. **Configure Webhook**:
   ```env
   TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook/
   ```

4. **Set Admin IDs**:
   ```env
   ADMIN_TG_IDS=123456789,987654321
   ```

## Testing & Verification 🧪

### 1. Test Database Connection
```bash
# With SQLite (current setup)
python manage.py check
python manage.py migrate

# With Supabase (after fixing URL)
python manage.py check --database=default
```

### 2. Test Telegram Bot
```bash
# Run the setup script
python setup_telegram_bot.py

# Test bot manually
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

### 3. Test Django Server
```bash
python manage.py runserver 8000
# Visit http://localhost:8000/admin/
```

## Configuration Steps 📋

### 1. Fix Supabase Connection
1. Login to [Supabase Dashboard](https://supabase.com/dashboard)
2. Find your project or create a new one
3. Go to Settings > Database
4. Copy the connection string
5. Update `.env` file:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_PROJECT.supabase.co:5432/postgres
   ```

### 2. Configure Telegram Bot
1. Get bot token from @BotFather
2. Update `.env` file:
   ```env
   TELEGRAM_BOT_TOKEN=your_actual_bot_token
   TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook/
   ADMIN_TG_IDS=your_telegram_user_id
   ```

### 3. Deploy and Set Webhook
1. Deploy your application to a public URL
2. Set the webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://your-domain.com/telegram/webhook/"}'
   ```

## Quick Start (Local Testing) 🚀

1. **Use SQLite for local testing** (already configured):
   ```bash
   python manage.py runserver 8000
   ```

2. **Access admin panel**:
   - URL: http://localhost:8000/admin/
   - Username: admin
   - Password: admin

3. **Test API endpoints**:
   - Health check: http://localhost:8000/health/
   - API info: http://localhost:8000/api/

## Next Steps 📝

1. **Fix Supabase connection** for production database
2. **Configure Telegram bot** with real token
3. **Set up webhook** for bot to receive messages
4. **Configure other services** (Redis, Cloudinary, Google Sheets)
5. **Deploy to production** server

## Support 💬

If you need help with any of these steps, please provide:
1. Your Supabase project status
2. Whether you have a Telegram bot token
3. Your deployment environment (local/production)
4. Any specific error messages you're seeing
