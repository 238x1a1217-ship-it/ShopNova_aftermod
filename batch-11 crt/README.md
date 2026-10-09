# Good Goods — Django Online Shop

A small server-rendered online shop built with Django templates, CSS, and plain JavaScript. Products are managed in Django Admin; anonymous visitors can browse and keep a session cart, while authenticated users can place cash-on-delivery demo orders and review their order history.

## Requirements

- Python 3.12 or newer
- pip

## Run locally

From the project root, create and activate a virtual environment, install dependencies, migrate the database, and start Django:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`. The admin is available at `/admin/`. Add categories and products there; uploaded product images are stored under `media/products/` and served during development.

## Database configuration

SQLite is the default for local development. To use MySQL, install a compatible MySQL Python driver (for example, `python -m pip install mysqlclient`) and set these environment variables before starting Django:

```text
DB_ENGINE=mysql
DB_NAME=online_shop
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

Use `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, and a comma-separated `DJANGO_ALLOWED_HOSTS` for a deployment. Do not use the development secret key in production. Configure a production web server/object storage for static and media files before deployment.

## Features

- Product catalog, category filters, name search, and price sorting
- Optional product images with a clean no-image placeholder
- Anonymous and authenticated session cart with stock-aware quantity controls
- Registration, login, logout, and login-protected checkout
- Account profile page and user-scoped order history
- Transactional checkout with server-calculated totals, product price snapshots, and stock reduction
- User-scoped order history, order details, and order-success pages
- Django Admin management for categories, products, orders, and order items
- Responsive templates with custom CSS and plain JavaScript

## ShopNova Admin dashboard

The default Django Admin at `/admin/` opens on the ShopNova store overview, with live product, category, order, revenue, and low-stock metrics. It retains Django Admin's normal model-management pages and adds a branded sidebar, recent orders, and stock alerts. Products, categories, orders, customers, and inventory are managed through the existing Admin changelists; product stock and order status can be updated there. Dashboard sections and links respect the signed-in staff user's model permissions. Revenue excludes cancelled orders, and products with five or fewer units are flagged as low stock.

For compatibility, the separate `/gcommerce/` staff dashboard remains available with its searchable, paginated management pages and inventory controls.

## Tests

```powershell
python manage.py test shop
```
