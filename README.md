# Gym Control

Sistema para gimnasios hecho con Django: socios con credencial QR, membresías por día, semana, quincena, mes, trimestre o año, control de acceso al escanear el QR, punto de venta de productos, corte de caja y alertas de vencimiento.

```powershell
python -m venv venv
venv\Scripts\activate
pip install django pillow qrcode python-dateutil
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
