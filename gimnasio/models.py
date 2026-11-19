from django.db import models
from django.utils import timezone
from django.core.files import File
from django.conf import settings

import uuid
import qrcode
import calendar
from io import BytesIO
from datetime import timedelta

# =========================
# FUNCIONES AUXILIARES
# =========================


def sumar_meses(fecha, meses):
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return fecha.replace(year=anio, month=mes, day=dia)


# =========================
# CLIENTES
# =========================
class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(unique=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    codigo_qr = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    qr_imagen = models.ImageField(upload_to="qr_codes/", blank=True, null=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        if not self.qr_imagen:
            qr = qrcode.make(str(self.codigo_qr))
            buffer = BytesIO()
            qr.save(buffer, format="PNG")

            nombre_limpio = self.nombre.replace(" ", "_").lower()
            file_name = f"{nombre_limpio}_qr.png"

            self.qr_imagen.save(file_name, File(buffer), save=False)

        super().save(*args, **kwargs)

    def membresia_actual(self):
        hoy = timezone.now().date()

        return (
            self.membresias.filter(activa=True, fecha_fin__gte=hoy)
            .order_by("-fecha_fin")
            .first()
        )

    def tiene_membresia_activa(self):
        return self.membresia_actual() is not None and self.activo

    def __str__(self):
        return self.nombre


# =========================
# MEMBRESÍAS
# =========================
class Membresia(models.Model):
    TIPO_DIA = "dia"
    TIPO_SEMANAL = "semanal"
    TIPO_QUINCENAL = "quincenal"
    TIPO_MENSUAL = "mensual"
    TIPO_TRIMESTRAL = "trimestral"
    TIPO_ANUAL = "anual"

    TIPOS = [
        (TIPO_DIA, "Día"),
        (TIPO_SEMANAL, "Semanal"),
        (TIPO_QUINCENAL, "Quincenal"),
        (TIPO_MENSUAL, "Mensual"),
        (TIPO_TRIMESTRAL, "Trimestral"),
        (TIPO_ANUAL, "Anual"),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="membresias"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default=TIPO_MENSUAL
    )

    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    activa = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Membresía"
        verbose_name_plural = "Membresías"
        ordering = ["-fecha_fin"]

    def esta_vigente(self):
        hoy = timezone.now().date()
        return self.activa and self.fecha_fin >= hoy

    def dias_restantes(self):
        hoy = timezone.now().date()
        restantes = (self.fecha_fin - hoy).days
        return max(restantes, 0)

    @property
    def estado(self):
        hoy = timezone.now().date()

        if not self.activa:
            return "Inactiva"

        if self.fecha_fin < hoy:
            return "Vencida"

        if self.fecha_fin == hoy:
            return "Vence hoy"

        if self.dias_restantes() <= 3:
            return "Por vencer"

        return "Activa"

    @staticmethod
    def calcular_fecha_fin(fecha_inicio, tipo, cantidad=1):
        cantidad = int(cantidad or 1)

        if cantidad < 1:
            cantidad = 1

        if tipo == Membresia.TIPO_DIA:
            return fecha_inicio + timedelta(days=1 * cantidad)

        if tipo == Membresia.TIPO_SEMANAL:
            return fecha_inicio + timedelta(days=7 * cantidad)

        if tipo == Membresia.TIPO_QUINCENAL:
            return fecha_inicio + timedelta(days=15 * cantidad)

        if tipo == Membresia.TIPO_MENSUAL:
            return sumar_meses(fecha_inicio, 1 * cantidad)

        if tipo == Membresia.TIPO_TRIMESTRAL:
            return sumar_meses(fecha_inicio, 3 * cantidad)

        if tipo == Membresia.TIPO_ANUAL:
            return sumar_meses(fecha_inicio, 12 * cantidad)

        return sumar_meses(fecha_inicio, 1 * cantidad)

    @classmethod
    def renovar_cliente(cls, cliente, tipo, cantidad=1):
        hoy = timezone.now().date()

        cantidad = int(cantidad or 1)

        if cantidad < 1:
            cantidad = 1

        ultima_membresia = (
            cliente.membresias
            .order_by("-fecha_fin")
            .first()
        )

        if ultima_membresia and ultima_membresia.fecha_fin >= hoy:
            fecha_inicio = ultima_membresia.fecha_fin
        else:
            fecha_inicio = hoy

        fecha_fin = cls.calcular_fecha_fin(
            fecha_inicio=fecha_inicio,
            tipo=tipo,
            cantidad=cantidad
        )

        membresia = cls.objects.create(
            cliente=cliente,
            tipo=tipo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activa=True
        )

        return membresia

    def __str__(self):
        return f"{self.cliente.nombre} - {self.get_tipo_display()} - vence {self.fecha_fin}"

# =========================
# PAGOS
# =========================
class Pago(models.Model):
    METODO_EFECTIVO = "efectivo"
    METODO_TARJETA = "tarjeta"
    METODO_TRANSFERENCIA = "transferencia"
    METODO_MIXTO = "mixto"

    METODOS_PAGO = [
        (METODO_EFECTIVO, "Efectivo"),
        (METODO_TARJETA, "Tarjeta"),
        (METODO_TRANSFERENCIA, "Transferencia"),
        (METODO_MIXTO, "Mixto"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="pagos")

    membresia = models.ForeignKey(
        Membresia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos",
    )

    tipo_membresia = models.CharField(
        max_length=20, choices=Membresia.TIPOS, default=Membresia.TIPO_MENSUAL
    )

    # Cantidad de periodos pagados
    # Ejemplo:
    # tipo_membresia = mensual y cantidad_periodos = 3
    # Resultado: se agregan 3 meses
    cantidad_periodos = models.PositiveIntegerField(default=1)

    monto = models.DecimalField(max_digits=10, decimal_places=2)

    fecha_pago = models.DateTimeField(auto_now_add=True)

    metodo_pago = models.CharField(
        max_length=50, choices=METODOS_PAGO, default=METODO_EFECTIVO
    )

    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-fecha_pago"]

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None

        if es_nuevo and not self.membresia:
            self.membresia = Membresia.renovar_cliente(
                cliente=self.cliente,
                tipo=self.tipo_membresia,
                cantidad=self.cantidad_periodos,
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pago de {self.cliente.nombre} - ${self.monto}"


# =========================
# REGISTRO DE ACCESOS
# =========================


class RegistroAcceso(models.Model):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name="accesos"
    )

    fecha_hora = models.DateTimeField(auto_now_add=True)

    acceso_permitido = models.BooleanField(default=False)

    motivo = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Registro de acceso"
        verbose_name_plural = "Registros de acceso"
        ordering = ["-fecha_hora"]

    def __str__(self):
        estado = "Permitido" if self.acceso_permitido else "Denegado"
        return f"{self.cliente.nombre} - {estado}"


# =========================
# PRODUCTOS / INVENTARIO
# =========================


class Producto(models.Model):
    CATEGORIA_AGUA = "agua"
    CATEGORIA_ENERGIZANTE = "energizante"
    CATEGORIA_PROTEINA = "proteina"
    CATEGORIA_SNACK = "snack"
    CATEGORIA_SUPLEMENTO = "suplemento"
    CATEGORIA_ACCESORIO = "accesorio"
    CATEGORIA_ROPA = "ropa"
    CATEGORIA_OTRO = "otro"

    CATEGORIAS = [
        (CATEGORIA_AGUA, "Agua embotellada"),
        (CATEGORIA_ENERGIZANTE, "Bebidas energizantes"),
        (CATEGORIA_PROTEINA, "Proteínas"),
        (CATEGORIA_SNACK, "Snacks saludables"),
        (CATEGORIA_SUPLEMENTO, "Suplementos"),
        (CATEGORIA_ACCESORIO, "Accesorios"),
        (CATEGORIA_ROPA, "Ropa deportiva"),
        (CATEGORIA_OTRO, "Otros"),
    ]

    nombre = models.CharField(max_length=150)

    codigo_barras = models.CharField(max_length=100, unique=True)

    categoria = models.CharField(
        max_length=30, choices=CATEGORIAS, default=CATEGORIA_OTRO
    )

    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)

    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    stock = models.PositiveIntegerField(default=0)

    stock_minimo = models.PositiveIntegerField(default=5)

    activo = models.BooleanField(default=True)

    imagen = models.ImageField(upload_to="productos/", blank=True, null=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["categoria", "nombre"]

    def bajo_stock(self):
        return self.stock <= self.stock_minimo

    def sin_stock(self):
        return self.stock <= 0

    def __str__(self):
        return self.nombre


# =========================
# VENTAS / POS
# =========================


class Venta(models.Model):
    METODOS_PAGO = [
        ("efectivo", "Efectivo"),
        ("tarjeta", "Tarjeta"),
        ("transferencia", "Transferencia"),
        ("mixto", "Mixto"),
    ]

    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="ventas"
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    fecha = models.DateTimeField(auto_now_add=True)

    metodo_pago = models.CharField(
        max_length=30, choices=METODOS_PAGO, default="efectivo"
    )

    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    notas = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Venta #{self.id} - ${self.total}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")

    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="detalles_venta"
    )

    cantidad = models.PositiveIntegerField(default=1)

    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"


# =========================
# CORTE DE CAJA
# =========================


class CorteCaja(models.Model):
    fecha = models.DateField(default=timezone.now)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    total_pagos_membresias = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    total_ventas_productos = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    total_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_tarjeta = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_transferencia = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    total_mixto = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_general = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    cantidad_pagos = models.PositiveIntegerField(default=0)

    cantidad_ventas = models.PositiveIntegerField(default=0)

    observaciones = models.TextField(blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Corte de caja"
        verbose_name_plural = "Cortes de caja"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Corte {self.fecha} - ${self.total_general}"
    