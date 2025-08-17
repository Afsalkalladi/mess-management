# Mess Management System - Backend

Production-ready backend for hostel mess management with Telegram bot integration and QR-based access control.

## Features

- **Student Management**: Registration, approval workflow, QR code generation
- **Payment Processing**: Screenshot upload, admin verification, cycle management
- **Mess Operations**: Cut applications with 11 PM cutoff, closure management
- **QR Scanner**: Staff access via web scanner, real-time validation
- **Telegram Bot**: Complete user interface through Telegram
- **Audit Trail**: Google Sheets backup, comprehensive logging
- **Security**: HMAC-signed QR codes, token authentication, rate limiting

## Tech Stack

- **Framework**: Django 5.0 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis + Celery
- **Bot**: python-telegram-bot
- **Storage**: Cloudinary
- **Monitoring**: Sentry
- **Deployment**: Docker + Nginx

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Installation

1. **Clone repository**
```bash
git clone <repository-url>
cd mess-management
```

2. **Setup environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Initialize project**
```bash
make init
```

4. **Create admin user**
```bash
make createsuperuser
```

5. **Generate staff token**
```bash
make generate-token
```

## Configuration

### Environment Variables

Key variables in `.env`:

```bash
DJANGO_SECRET_KEY=<secure-random-key>
DATABASE_URL=postgresql://user:pass@localhost/db
TELEGRAM_BOT_TOKEN=<bot-token>
ADMIN_TG_IDS=123456789,987654321
CLOUDINARY_URL=cloudinary://...
GOOGLE_SHEETS_CREDENTIALS_JSON={...}
QR_SECRET=<secure-secret>
```

### Telegram Bot Setup

1. Create bot via [@BotFather](https://t.me/botfather)
2. Set webhook URL: `https://your-domain.com/api/v1/telegram/webhook/`
3. Configure commands:
   - `/start` - Main menu
   - `/register` - Student registration
   - `/payment` - Payment upload
   - `/messcut` - Apply mess cut
   - `/myqr` - View QR code
   - `/admin` - Admin panel

## API Documentation

### Authentication

**Staff Scanner**
```
Authorization: Bearer <staff-token>
```

**Admin Endpoints**
```
X-Admin-ID: <telegram-user-id>
```

### Core Endpoints

#### Student Registration
```http
POST /api/v1/students/register/
{
  "tg_user_id": 123456789,
  "name": "John Doe",
  "roll_no": "20CS001",
  "room_no": "A-101",
  "phone": "+919876543210"
}
```

#### QR Scan
```http
POST /api/v1/scanner/scan/
Authorization: Bearer <staff-token>
{
  "qr_data": "v|1|1|nonce|signature",
  "meal": "LUNCH",
  "device_info": "Scanner-1"
}
```

#### Payment Upload
```http
POST /api/v1/payments/upload/
{
  "student": 1,
  "cycle_start": "2025-01-01",
  "cycle_end": "2025-01-31",
  "amount": 3000,
  "screenshot_url": "https://..."
}
```

## Development

### Running Locally

```bash
# Start services
make up

# View logs
make logs

# Run migrations
make migrate

# Run tests
make test

# Format code
make format
```

### Project Structure

```
mess-management/
├── config/           # Django settings
├── core/            # Core utilities
├── mess/            # Main app
│   ├── models.py    # Database models
│   ├── serializers.py
│   ├── views.py     # API views
│   ├── tasks.py     # Celery tasks
│   └── telegram_bot.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── manage.py
```

## Testing

```bash
# Run all tests
make test

# With coverage
make coverage

# Linting
make lint
```

## Deployment

### Production Setup

1. **Configure environment**
```bash
cp .env.example .env.prod
# Set production values
```

2. **Deploy**
```bash
make deploy
```

3. **SSL/TLS Setup**
- Use Let's Encrypt for certificates
- Update nginx.conf with SSL configuration

### Monitoring

- **Logs**: `/app/logs/`
- **Metrics**: Sentry integration
- **Health Check**: `GET /health/`

## Security

- HMAC-signed QR codes with rotation
- Rate limiting on API endpoints
- Token-based staff authentication
- Admin actions audit trail
- Input validation and sanitization
- HTTPS enforcement in production

## Backup & Recovery

### Database Backup
```bash
make backup
```

### Google Sheets Sync
- Automatic backup of all critical data
- Dead Letter Queue for failed syncs
- Hourly retry mechanism

## Troubleshooting

### Common Issues

1. **Telegram webhook not working**
   - Verify webhook URL
   - Check secret token
   - Ensure HTTPS in production

2. **QR scan failing**
   - Verify QR_SECRET matches
   - Check student approval status
   - Validate payment cycle

3. **Celery tasks not running**
   - Check Redis connection
   - Verify worker is running
   - Check task queue routing

## Support

For issues or questions:
- Technical: Create GitHub issue
- Operations: Contact admin via Telegram

## License

Proprietary - All rights reserved