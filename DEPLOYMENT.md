# Django Backend Deployment Guide

## Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Database
python manage.py migrate
python manage.py createsuperuser

# Run server
python manage.py runserver
```

## Production Deployment

### Railway Deployment
1. Create `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python manage.py migrate && gunicorn ecommerce.wsgi",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

2. Add `Procfile`:
```
web: gunicorn ecommerce.wsgi --log-file -
release: python manage.py migrate
```

3. Environment Variables:
```
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=postgresql://...
ALLOWED_HOSTS=.railway.app
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

### Heroku Deployment
```bash
heroku create your-app-name
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

## API Endpoints

### Authentication
- POST `/api/users/register/` - Register new user
- POST `/api/users/login/` - Login (get JWT token)
- GET `/api/users/profile/` - Get user profile
- POST `/api/users/token/refresh/` - Refresh JWT token

### Products
- GET `/api/products/` - List all products
- GET `/api/products/{slug}/` - Get product details
- POST `/api/products/` - Create product (admin only)
- PUT `/api/products/{slug}/` - Update product (admin only)
- DELETE `/api/products/{slug}/` - Delete product (admin only)

### Categories
- GET `/api/products/categories/` - List categories
- POST `/api/products/categories/` - Create category (admin only)

### Orders
- GET `/api/orders/` - List orders (user's own or all for admin)
- POST `/api/orders/` - Create order
- GET `/api/orders/{id}/` - Get order details
- POST `/api/orders/{id}/update_status/` - Update order status (admin only)

### Documentation
- GET `/api/docs/` - Swagger API documentation

## Database Models

### Product
- name, slug, description
- price, discount_price
- category (FK)
- image, stock
- is_active, featured

### Category
- name, slug, description

### Order
- user (FK), order_number
- total_amount, status
- shipping_address, phone, email

### OrderItem
- order (FK), product (FK)
- quantity, price

## Admin Access
Visit `/admin/` to access Django admin panel
Create superuser: `python manage.py createsuperuser`
