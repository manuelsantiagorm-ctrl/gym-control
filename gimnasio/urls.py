from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("escanear-qr/", views.escanear_qr, name="escanear_qr"),
    path("validar-qr/<uuid:codigo_qr>/", views.validar_qr, name="validar_qr"),
    path("cliente/<int:cliente_id>/", views.detalle_cliente, name="detalle_cliente"),
    path(
        "cliente/<int:cliente_id>/editar/", views.editar_cliente, name="editar_cliente"
    ),
    path(
        "cliente/<int:cliente_id>/registrar-pago/",
        views.registrar_pago_cliente,
        name="registrar_pago_cliente",
    ),
    path(
        "cliente/<int:cliente_id>/credencial/",
        views.credencial_cliente,
        name="credencial_cliente",
    ),
    path("clientes/", views.lista_clientes, name="lista_clientes"),
    path("clientes/nuevo/", views.crear_cliente, name="crear_cliente"),
    path("pagos/", views.lista_pagos, name="lista_pagos"),
    path("accesos/", views.lista_accesos, name="lista_accesos"),
    path("buscar/", views.busqueda_global, name="busqueda_global"),
    path(
        "buscar/sugerencias/", views.sugerencias_busqueda, name="sugerencias_busqueda"
    ),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("productos/", views.lista_productos, name="lista_productos"),
    path("productos/nuevo/", views.crear_producto, name="crear_producto"),
    path(
        "productos/<int:producto_id>/editar/",
        views.editar_producto,
        name="editar_producto",
    ),
    path("pos/", views.punto_venta, name="punto_venta"),
    path("pos/agregar/", views.pos_agregar_producto, name="pos_agregar_producto"),
    path(
        "pos/eliminar/<int:producto_id>/",
        views.pos_eliminar_producto,
        name="pos_eliminar_producto",
    ),
    path("pos/limpiar/", views.pos_limpiar, name="pos_limpiar"),
    path("pos/registrar/", views.pos_registrar_venta, name="pos_registrar_venta"),
    path("ventas/", views.lista_ventas, name="lista_ventas"),
    path("corte-caja/", views.corte_caja, name="corte_caja"),
    path(
        "corte-caja/<int:corte_id>/",
        views.detalle_corte_caja,
        name="detalle_corte_caja",
    ),
    path("alertas-membresias/", views.alertas_membresias, name="alertas_membresias"),
    path(
        "cliente/<int:cliente_id>/desactivar/",
        views.desactivar_cliente,
        name="desactivar_cliente",
    ),
    path(
        "productos/<int:producto_id>/desactivar/",
        views.desactivar_producto,
        name="desactivar_producto",
    ),
]
