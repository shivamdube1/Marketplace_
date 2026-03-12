# 🛏️ Dube DreamWeave — Premium Bedding E-Commerce

> **Where Comfort Meets Dreams**

---

## ⚡ Quick Start (Windows)

### Option A — Automatic (recommended)
Double-click `setup_windows.bat` — it creates the venv, installs everything, then run `run_windows.bat`.

### Option B — Manual

```cmd
REM 1. Create virtual environment
python -m venv venv

REM 2. Activate it
venv\Scripts\activate

REM 3. Upgrade pip (important on Python 3.13)
python -m pip install --upgrade pip

REM 4. Install packages
pip install -r requirements.txt

REM 5. Seed the database (creates sample products + admin account)
python seed.py

REM 6. Run the app
python app.py
```

Then open **http://localhost:5000** in your browser.

---

## 🔑 Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@dubedreamweave.com` | `Admin@1234` |
| Customer | `jane@example.com` | `Password@1` |

---

## 📋 Requirements

- **Python 3.10, 3.11, 3.12, or 3.13** (all supported)
- Windows 10/11
- Internet connection (for Google Fonts + Font Awesome CDN)

---

## 📁 Project Structure

```
dreamweave/
├── app.py                  # Application factory
├── config.py               # Configuration (dev/prod/test)
├── extensions.py           # Flask extensions
├── seed.py                 # Database seeder
├── requirements.txt        # Python dependencies
├── setup_windows.bat       # Windows auto-installer
├── run_windows.bat         # Windows runner
│
├── models/                 # SQLAlchemy models
│   ├── user.py
│   ├── product.py
│   ├── category.py
│   ├── order.py
│   └── cart.py
│
├── routes/                 # Flask blueprints
│   ├── main.py             # Homepage, About, Contact, Search
│   ├── auth.py             # Login, Register, Logout
│   ├── shop.py             # Shop listing + product detail
│   ├── cart.py             # Cart management
│   ├── checkout.py         # Checkout + order confirmation
│   └── admin.py            # Admin dashboard
│
├── forms/                  # WTForms
│   ├── auth_forms.py
│   ├── checkout_forms.py
│   ├── contact_forms.py
│   └── admin_forms.py
│
├── static/
│   ├── css/main.css        # Full luxury styling
│   ├── js/main.js          # Interactivity
│   └── images/
│       ├── hero-bg.jpg
│       ├── about-hero.jpg
│       ├── placeholder.jpg
│       ├── products/       # 11 product images
│       └── categories/     # 5 category images
│
└── templates/
    ├── base.html
    ├── index.html
    ├── shop.html
    ├── product_detail.html
    ├── cart.html
    ├── checkout.html
    ├── order_confirmation.html
    ├── about.html
    ├── contact.html
    ├── search.html
    ├── auth/
    │   ├── login.html
    │   └── register.html
    └── admin/
        ├── dashboard.html
        ├── products.html
        ├── add_product.html
        ├── edit_product.html
        └── orders.html
```

---

## 🛒 Key URLs

| URL | Page |
|-----|------|
| `/` | Homepage |
| `/shop` | Shop with filters |
| `/shop/product/<slug>` | Product detail |
| `/cart` | Shopping cart |
| `/checkout` | Checkout |
| `/auth/login` | Sign in |
| `/auth/register` | Register |
| `/admin` | Admin dashboard |
| `/admin/products` | Manage products |
| `/admin/orders` | Manage orders |

---

## 🔧 Troubleshooting

**"ModuleNotFoundError: No module named 'flask_sqlalchemy'"**
```cmd
venv\Scripts\activate
pip install -r requirements.txt
```

**"Pillow build error" on Python 3.13**
```cmd
python -m pip install --upgrade pip
pip install Pillow==11.1.0
```

**Port already in use**
```cmd
REM Change port in app.py last line:
app.run(debug=True, port=5001)
```

**Database reset**
```cmd
del dreamweave_dev.db
python seed.py
```

---

## 🔄 Production Upgrade

Switch to PostgreSQL by setting in `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/dreamweave
```

Run with Gunicorn (Linux/Mac):
```bash
pip install gunicorn
gunicorn "app:create_app('production')" -w 4 -b 0.0.0.0:8000
```

---

*Dube DreamWeave — Where Comfort Meets Dreams* 🛏️
