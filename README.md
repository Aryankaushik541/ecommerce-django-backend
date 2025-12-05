# Ecommerce Django Backend

REST API backend for ecommerce platform with full admin access.

## Features
- Django REST Framework
- Product Management API
- User Authentication & Authorization
- Order Management
- Admin Dashboard API
- PostgreSQL Database Support

## Setup

```bash
# Clone repository
git clone https://github.com/Aryankaushik541/ecommerce-django-backend.git
cd ecommerce-django-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run server
python manage.py runserver
```

## API Endpoints
- `/api/products/` - Product CRUD
- `/api/orders/` - Order management
- `/api/users/` - User management
- `/api/admin/` - Admin operations
- `/api/auth/` - Authentication

## Environment Variables
Create `.env` file:
```
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost/dbname
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000
```
