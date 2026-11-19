from django.contrib import admin
from django.utils.html import format_html
from .models import Cliente, Membresia, Pago, RegistroAcceso
from .models import Producto, Venta, DetalleVenta

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    exclude = ("qr_imagen", "codigo_qr")
    list_display = ("nombre", "telefono", "email", "activo", "ver_qr")

    readonly_fields = ("ver_qr",)

    def ver_qr(self, obj):
        if obj.qr_imagen:
            return format_html(
                '<img src="{}" width="100" height="100" />', obj.qr_imagen.url
            )
        return "No QR generado"

    ver_qr.short_description = "Código QR"


@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    pass


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    pass


@admin.register(RegistroAcceso)
class RegistroAccesoAdmin(admin.ModelAdmin):
    pass



@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo_barras",
        "precio_venta",
        "costo",
        "stock",
        "activo",
        "fecha_registro",
    )
    search_fields = (
        "nombre",
        "codigo_barras",
    )
    list_filter = (
        "activo",
        "fecha_registro",
    )


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = (
        "producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    can_delete = False


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "metodo_pago",
        "total",
        "fecha",
    )
    search_fields = (
        "cliente__nombre",
        "cliente__email",
        "detalles__producto__nombre",
        "detalles__producto__codigo_barras",
    )
    list_filter = (
        "metodo_pago",
        "fecha",
    )
    inlines = [DetalleVentaInline]


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = (
        "venta",
        "producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    search_fields = (
        "producto__nombre",
        "producto__codigo_barras",
    )