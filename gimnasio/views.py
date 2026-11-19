from django.shortcuts import render
from .models import Cliente
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from .models import Cliente, Membresia, RegistroAcceso
from django.db.models import Sum
from decimal import Decimal
from .models import Pago
from decimal import Decimal
from datetime import timedelta
from django.db.models import Q,Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import render, redirect
from dateutil.relativedelta import relativedelta
from .models import Cliente, Membresia, Pago, RegistroAcceso
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import OuterRef, Subquery, DateField

from .models import Pago, Venta, CorteCaja
from .models import (
    Cliente,
    Membresia,
    Pago,
    RegistroAcceso,
    Producto,
    Venta,
    DetalleVenta,
)

def home(request):
    return render(request, "gimnasio/home.html")


def escanear_qr(request):
    return render(request, "gimnasio/escanear_qr.html")


def validar_qr(request, codigo_qr):
    cliente = get_object_or_404(Cliente, codigo_qr=codigo_qr)

    ahora = timezone.now()
    limite_repeticion = ahora - timedelta(seconds=30)

    acceso_reciente = (
        RegistroAcceso.objects.filter(
            cliente=cliente, fecha_hora__gte=limite_repeticion
        )
        .order_by("-fecha_hora")
        .first()
    )

    if acceso_reciente:
        return JsonResponse(
            {
                "status": "duplicado",
                "permitido": acceso_reciente.acceso_permitido,
                "cliente": cliente.nombre,
                "motivo": "Este QR ya fue escaneado recientemente.",
            }
        )

    membresia_actual = (
        Membresia.objects.filter(
            cliente=cliente, activa=True, fecha_fin__gte=timezone.localdate()
        )
        .order_by("-fecha_fin")
        .first()
    )

    if cliente.activo and membresia_actual:
        acceso = RegistroAcceso.objects.create(
            cliente=cliente, acceso_permitido=True, motivo="Acceso permitido"
        )

        return JsonResponse(
            {
                "status": "ok",
                "permitido": True,
                "cliente": cliente.nombre,
                "motivo": acceso.motivo,
            }
        )

    acceso = RegistroAcceso.objects.create(
        cliente=cliente, acceso_permitido=False, motivo="Membresía vencida"
    )

    return JsonResponse(
        {
            "status": "denegado",
            "permitido": False,
            "cliente": cliente.nombre,
            "motivo": acceso.motivo,
        }
    )


def detalle_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    hoy = timezone.now().date()

    # Calcular meses desde registro
    fecha_registro = cliente.fecha_registro.date()
    meses_registrado = (hoy.year - fecha_registro.year) * 12 + (
        hoy.month - fecha_registro.month
    )

    # Membresía más reciente
    membresia_actual = (
        Membresia.objects.filter(cliente=cliente).order_by("-fecha_fin").first()
    )

    # Último pago
    ultimo_pago = Pago.objects.filter(cliente=cliente).order_by("-fecha_pago").first()

    # Total pagado
    total_pagado = (
        Pago.objects.filter(cliente=cliente).aggregate(total=Sum("monto"))["total"] or 0
    )

    # Últimos accesos
    ultimos_accesos = RegistroAcceso.objects.filter(cliente=cliente).order_by(
        "-fecha_hora"
    )[:10]

    # Estado de membresía
    if (
        membresia_actual
        and membresia_actual.activa
        and membresia_actual.fecha_fin >= hoy
    ):
        estado_membresia = "ACTIVA"
        estado_color = "success"
    elif membresia_actual:
        estado_membresia = "VENCIDA"
        estado_color = "danger"
    else:
        estado_membresia = "SIN MEMBRESÍA"
        estado_color = "warning"

    context = {
        "cliente": cliente,
        "membresia_actual": membresia_actual,
        "ultimo_pago": ultimo_pago,
        "total_pagado": total_pagado,
        "ultimos_accesos": ultimos_accesos,
        "meses_registrado": meses_registrado,
        "estado_membresia": estado_membresia,
        "estado_color": estado_color,
    }

    return render(request, "gimnasio/detalle_cliente.html", context)


def registrar_pago_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    hoy = timezone.now().date()

    membresia_actual = (
        Membresia.objects.filter(cliente=cliente, activa=True)
        .order_by("-fecha_fin")
        .first()
    )

    if request.method == "POST":
        tipo = request.POST.get("tipo_membresia") or request.POST.get("tipo")
        cantidad_periodos = request.POST.get("cantidad_periodos", "1")
        monto = request.POST.get("monto")
        metodo_pago = request.POST.get("metodo_pago")
        notas = request.POST.get("notas", "").strip()

        if not tipo or not cantidad_periodos or not monto or not metodo_pago:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect("registrar_pago_cliente", cliente_id=cliente.id)

        tipos_validos = [opcion[0] for opcion in Membresia.TIPOS]
        metodos_validos = [opcion[0] for opcion in Pago.METODOS_PAGO]

        if tipo not in tipos_validos:
            messages.error(request, "El tipo de membresía no es válido.")
            return redirect("registrar_pago_cliente", cliente_id=cliente.id)

        if metodo_pago not in metodos_validos:
            messages.error(request, "El método de pago no es válido.")
            return redirect("registrar_pago_cliente", cliente_id=cliente.id)

        try:
            cantidad_periodos = int(cantidad_periodos)

            if cantidad_periodos < 1:
                messages.error(request, "La cantidad a pagar debe ser mínimo 1.")
                return redirect("registrar_pago_cliente", cliente_id=cliente.id)

        except:
            messages.error(request, "La cantidad a pagar no es válida.")
            return redirect("registrar_pago_cliente", cliente_id=cliente.id)

        try:
            monto = Decimal(monto)

            if monto <= 0:
                messages.error(request, "El monto debe ser mayor a 0.")
                return redirect("registrar_pago_cliente", cliente_id=cliente.id)

        except:
            messages.error(request, "El monto no es válido.")
            return redirect("registrar_pago_cliente", cliente_id=cliente.id)

        pago = Pago.objects.create(
            cliente=cliente,
            tipo_membresia=tipo,
            cantidad_periodos=cantidad_periodos,
            monto=monto,
            metodo_pago=metodo_pago,
            notas=notas,
        )

        membresia = pago.membresia

        if membresia:
            messages.success(
                request,
                f"Pago registrado correctamente. Membresía {membresia.get_tipo_display()} x{cantidad_periodos} "
                f"vigente del {membresia.fecha_inicio.strftime('%d/%m/%Y')} "
                f"al {membresia.fecha_fin.strftime('%d/%m/%Y')}.",
            )
        else:
            messages.success(request, "Pago registrado correctamente.")

        return redirect("detalle_cliente", cliente_id=cliente.id)

    context = {
        "cliente": cliente,
        "hoy": hoy,
        "membresia_actual": membresia_actual,
        "tipos_membresia": Membresia.TIPOS,
        "metodos_pago": Pago.METODOS_PAGO,
    }

    return render(request, "gimnasio/registrar_pago.html", context)


def credencial_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    hoy = timezone.now().date()

    membresia_actual = (
        Membresia.objects.filter(cliente=cliente).order_by("-fecha_fin").first()
    )

    if (
        membresia_actual
        and membresia_actual.activa
        and membresia_actual.fecha_fin >= hoy
    ):
        estado_membresia = "ACTIVA"
        estado_color = "success"
        fecha_vencimiento = membresia_actual.fecha_fin
    elif membresia_actual:
        estado_membresia = "VENCIDA"
        estado_color = "danger"
        fecha_vencimiento = membresia_actual.fecha_fin
    else:
        estado_membresia = "SIN MEMBRESÍA"
        estado_color = "warning"
        fecha_vencimiento = None

    context = {
        "cliente": cliente,
        "estado_membresia": estado_membresia,
        "estado_color": estado_color,
        "fecha_vencimiento": fecha_vencimiento,
    }

    return render(request, "gimnasio/credencial_cliente.html", context)


def lista_clientes(request):
    query = request.GET.get("q", "").strip()
    hoy = timezone.now().date()

    clientes = Cliente.objects.all().order_by("-fecha_registro")

    if query:
        clientes = clientes.filter(
            Q(nombre__icontains=query)
            | Q(telefono__icontains=query)
            | Q(email__icontains=query)
        )

    clientes_data = []

    for cliente in clientes:
        membresia_actual = (
            Membresia.objects.filter(cliente=cliente).order_by("-fecha_fin").first()
        )

        if (
            membresia_actual
            and membresia_actual.activa
            and membresia_actual.fecha_fin >= hoy
        ):
            estado = "ACTIVA"
            estado_color = "success"
            vencimiento = membresia_actual.fecha_fin
        elif membresia_actual:
            estado = "VENCIDA"
            estado_color = "danger"
            vencimiento = membresia_actual.fecha_fin
        else:
            estado = "SIN MEMBRESÍA"
            estado_color = "warning"
            vencimiento = None

        clientes_data.append(
            {
                "cliente": cliente,
                "estado": estado,
                "estado_color": estado_color,
                "vencimiento": vencimiento,
            }
        )

    context = {
        "clientes_data": clientes_data,
        "query": query,
        "total_clientes": clientes.count(),
    }

    return render(request, "gimnasio/lista_clientes.html", context)


def lista_pagos(request):
    query = request.GET.get("q", "").strip()

    pagos = Pago.objects.select_related("cliente", "membresia").order_by("-fecha_pago")

    if query:
        pagos = pagos.filter(
            Q(cliente__nombre__icontains=query)
            | Q(cliente__email__icontains=query)
            | Q(cliente__telefono__icontains=query)
            | Q(metodo_pago__icontains=query)
            | Q(tipo_membresia__icontains=query)
            | Q(notas__icontains=query)
            | Q(membresia__tipo__icontains=query)
        )

    total_recaudado = pagos.aggregate(total=Sum("monto"))["total"] or 0

    context = {
        "pagos": pagos,
        "query": query,
        "total_pagos": pagos.count(),
        "total_recaudado": total_recaudado,
    }

    return render(request, "gimnasio/lista_pagos.html", context)


def lista_accesos(request):
    query = request.GET.get("q", "").strip()

    accesos = RegistroAcceso.objects.select_related("cliente").order_by("-fecha_hora")

    if query:
        accesos = accesos.filter(
            Q(cliente__nombre__icontains=query)
            | Q(cliente__telefono__icontains=query)
            | Q(cliente__email__icontains=query)
            | Q(motivo__icontains=query)
        )

    total_accesos = accesos.count()
    accesos_permitidos = accesos.filter(acceso_permitido=True).count()
    accesos_denegados = accesos.filter(acceso_permitido=False).count()

    context = {
        "accesos": accesos,
        "query": query,
        "total_accesos": total_accesos,
        "accesos_permitidos": accesos_permitidos,
        "accesos_denegados": accesos_denegados,
    }

    return render(request, "gimnasio/lista_accesos.html", context)


def busqueda_global(request):
    query = request.GET.get("q", "").strip()

    clientes = []
    pagos = []
    accesos = []
    membresias = []

    if query:
        clientes = Cliente.objects.filter(
            Q(nombre__icontains=query)
            | Q(telefono__icontains=query)
            | Q(email__icontains=query)
        ).order_by("-fecha_registro")[:10]

        pagos = (
            Pago.objects.select_related("cliente", "membresia")
            .filter(
                Q(cliente__nombre__icontains=query)
                | Q(cliente__email__icontains=query)
                | Q(cliente__telefono__icontains=query)
                | Q(metodo_pago__icontains=query)
                | Q(monto__icontains=query)
            )
            .order_by("-fecha_pago")[:10]
        )

        accesos = (
            RegistroAcceso.objects.select_related("cliente")
            .filter(
                Q(cliente__nombre__icontains=query)
                | Q(cliente__email__icontains=query)
                | Q(cliente__telefono__icontains=query)
                | Q(motivo__icontains=query)
            )
            .order_by("-fecha_hora")[:10]
        )

        membresias = (
            Membresia.objects.select_related("cliente")
            .filter(
                Q(cliente__nombre__icontains=query)
                | Q(cliente__email__icontains=query)
                | Q(cliente__telefono__icontains=query)
                | Q(tipo__icontains=query)
            )
            .order_by("-fecha_fin")[:10]
        )

    context = {
        "query": query,
        "clientes": clientes,
        "pagos": pagos,
        "accesos": accesos,
        "membresias": membresias,
    }

    return render(request, "gimnasio/busqueda_global.html", context)


def sugerencias_busqueda(request):
    query = request.GET.get("q", "").strip()

    resultados = []

    if len(query) < 2:
        return JsonResponse({"resultados": []})

    # =========================
    # CLIENTES
    # =========================
    clientes = Cliente.objects.filter(
        Q(nombre__icontains=query)
        | Q(email__icontains=query)
        | Q(telefono__icontains=query)
    ).order_by("nombre")[:5]

    for cliente in clientes:
        resultados.append(
            {
                "tipo": "Cliente",
                "titulo": cliente.nombre,
                "subtitulo": cliente.email or cliente.telefono or "Cliente registrado",
                "url": f"/cliente/{cliente.id}/",
            }
        )

    # =========================
    # PAGOS
    # =========================
    pagos = (
        Pago.objects.select_related("cliente", "membresia")
        .filter(
            Q(cliente__nombre__icontains=query)
            | Q(cliente__email__icontains=query)
            | Q(cliente__telefono__icontains=query)
            | Q(metodo_pago__icontains=query)
            | Q(tipo_membresia__icontains=query)
            | Q(notas__icontains=query)
        )
        .order_by("-fecha_pago")[:5]
    )

    for pago in pagos:
        resultados.append(
            {
                "tipo": "Pago",
                "titulo": f"Pago de {pago.cliente.nombre}",
                "subtitulo": f"${pago.monto} - {pago.get_metodo_pago_display()} - {pago.fecha_pago.strftime('%d/%m/%Y')}",
                "url": f"/cliente/{pago.cliente.id}/",
            }
        )

    # =========================
    # PRODUCTOS
    # =========================
    productos = Producto.objects.filter(
        Q(nombre__icontains=query) | Q(codigo_barras__icontains=query)
    ).order_by("nombre")[:5]

    for producto in productos:
        resultados.append(
            {
                "tipo": "Producto",
                "titulo": producto.nombre,
                "subtitulo": f"Código: {producto.codigo_barras} | Stock: {producto.stock}",
                "url": "/productos/",
            }
        )

    return JsonResponse({"resultados": resultados[:10]})


def crear_cliente(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        email = request.POST.get("email", "").strip()
        activo = request.POST.get("activo") == "on"

        if not nombre or not email:
            messages.error(request, "El nombre y el correo son obligatorios.")
            return redirect("crear_cliente")

        try:
            cliente = Cliente.objects.create(
                nombre=nombre, telefono=telefono, email=email, activo=activo
            )

            messages.success(request, "Cliente creado correctamente.")
            return redirect("detalle_cliente", cliente_id=cliente.id)

        except IntegrityError:
            messages.error(request, "Ya existe un cliente registrado con ese correo.")
            return redirect("crear_cliente")

    return render(request, "gimnasio/crear_cliente.html")


def dashboard(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    proximos_7_dias = hoy + timedelta(days=7)

    total_clientes = Cliente.objects.count()

    clientes_activos = Cliente.objects.filter(activo=True).count()

    membresias_activas = Membresia.objects.filter(
        activa=True, fecha_fin__gte=hoy
    ).count()

    clientes_con_membresia_activa = (
        Membresia.objects.filter(activa=True, fecha_fin__gte=hoy)
        .values("cliente")
        .distinct()
        .count()
    )

    clientes_vencidos_o_sin_membresia = total_clientes - clientes_con_membresia_activa

    ingresos_mes = (
        Pago.objects.filter(
            fecha_pago__date__gte=inicio_mes, fecha_pago__date__lte=hoy
        ).aggregate(total=Sum("monto"))["total"]
        or 0
    )

    pagos_hoy = (
        Pago.objects.filter(fecha_pago__date=hoy).aggregate(total=Sum("monto"))["total"]
        or 0
    )

    accesos_hoy = RegistroAcceso.objects.filter(fecha_hora__date=hoy).count()

    accesos_permitidos_hoy = RegistroAcceso.objects.filter(
        fecha_hora__date=hoy, acceso_permitido=True
    ).count()

    accesos_denegados_hoy = RegistroAcceso.objects.filter(
        fecha_hora__date=hoy, acceso_permitido=False
    ).count()

    pagos_recientes = Pago.objects.select_related("cliente", "membresia").order_by(
        "-fecha_pago"
    )[:5]

    accesos_recientes = RegistroAcceso.objects.select_related("cliente").order_by(
        "-fecha_hora"
    )[:6]

    membresias_por_vencer = (
        Membresia.objects.select_related("cliente")
        .filter(activa=True, fecha_fin__gte=hoy, fecha_fin__lte=proximos_7_dias)
        .order_by("fecha_fin")[:6]
    )

    membresias_vencidas = (
        Membresia.objects.select_related("cliente")
        .filter(activa=True, fecha_fin__lt=hoy)
        .order_by("fecha_fin")[:6]
    )

    context = {
        "hoy": hoy,
        "total_clientes": total_clientes,
        "clientes_activos": clientes_activos,
        "membresias_activas": membresias_activas,
        "clientes_vencidos_o_sin_membresia": clientes_vencidos_o_sin_membresia,
        "ingresos_mes": ingresos_mes,
        "pagos_hoy": pagos_hoy,
        "accesos_hoy": accesos_hoy,
        "accesos_permitidos_hoy": accesos_permitidos_hoy,
        "accesos_denegados_hoy": accesos_denegados_hoy,
        "pagos_recientes": pagos_recientes,
        "accesos_recientes": accesos_recientes,
        "membresias_por_vencer": membresias_por_vencer,
        "membresias_vencidas": membresias_vencidas,
    }

    return render(request, "gimnasio/dashboard.html", context)


# =========================
# PRODUCTOS
# =========================
def lista_productos(request):
    query = request.GET.get("q", "").strip()

    productos = Producto.objects.all().order_by("categoria", "nombre")

    if query:
        productos = productos.filter(
            Q(nombre__icontains=query) | Q(codigo_barras__icontains=query)
        )

    categorias = [
        {
            "key": "agua",
            "nombre": "Agua embotellada",
            "descripcion": "Botellas de agua natural para venta rápida.",
            "productos": productos.filter(categoria="agua"),
        },
        {
            "key": "energizante",
            "nombre": "Bebidas energizantes",
            "descripcion": "Bebidas para energía antes o después del entrenamiento.",
            "productos": productos.filter(categoria="energizante"),
        },
        {
            "key": "proteina",
            "nombre": "Proteínas",
            "descripcion": "Proteínas en polvo, bebidas proteicas y suplementos similares.",
            "productos": productos.filter(categoria="proteina"),
        },
        {
            "key": "snack",
            "nombre": "Snacks saludables",
            "descripcion": "Barras, galletas, botanas fitness o alimentos rápidos.",
            "productos": productos.filter(categoria="snack"),
        },
        {
            "key": "suplemento",
            "nombre": "Suplementos",
            "descripcion": "Creatina, pre-entreno, aminoácidos y otros suplementos.",
            "productos": productos.filter(categoria="suplemento"),
        },
        {
            "key": "accesorio",
            "nombre": "Accesorios",
            "descripcion": "Guantes, straps, vendas, toallas y accesorios de entrenamiento.",
            "productos": productos.filter(categoria="accesorio"),
        },
        {
            "key": "ropa",
            "nombre": "Ropa deportiva",
            "descripcion": "Playeras, shorts, sudaderas y ropa del gimnasio.",
            "productos": productos.filter(categoria="ropa"),
        },
        {
            "key": "otro",
            "nombre": "Otros productos",
            "descripcion": "Productos que no pertenecen a otra categoría.",
            "productos": productos.filter(categoria="otro"),
        },
    ]

    context = {
        "categorias": categorias,
        "query": query,
    }

    return render(request, "gimnasio/lista_productos.html", context)


def crear_producto(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        codigo_barras = request.POST.get("codigo_barras", "").strip()
        precio_venta = request.POST.get("precio_venta", "").strip()
        costo = request.POST.get("costo", "0").strip()
        stock = request.POST.get("stock", "0").strip()
        activo = request.POST.get("activo") == "on"
        imagen = request.FILES.get("imagen")

        if not nombre or not codigo_barras or not precio_venta:
            messages.error(request, "Nombre, código de barras y precio son obligatorios.")
            return redirect("crear_producto")

        if Producto.objects.filter(codigo_barras=codigo_barras).exists():
            messages.error(request, "Ya existe un producto con ese código de barras.")
            return redirect("crear_producto")

        Producto.objects.create(
            nombre=nombre,
            codigo_barras=codigo_barras,
            precio_venta=Decimal(precio_venta),
            costo=Decimal(costo or 0),
            stock=int(stock or 0),
            activo=activo,
            imagen=imagen
        )

        messages.success(request, "Producto creado correctamente.")
        return redirect("lista_productos")

    return render(request, "gimnasio/crear_producto.html")


# =========================
# PUNTO DE VENTA
# =========================

def obtener_carrito(request):
    return request.session.get("carrito_pos", {})


def guardar_carrito(request, carrito):
    request.session["carrito_pos"] = carrito
    request.session.modified = True


def punto_venta(request):
    carrito = obtener_carrito(request)

    items = []
    total = Decimal("0.00")

    for producto_id, cantidad in carrito.items():
        producto = Producto.objects.filter(id=producto_id, activo=True).first()

        if producto:
            cantidad = int(cantidad)
            subtotal = producto.precio_venta * cantidad
            total += subtotal

            items.append({
                "producto": producto,
                "cantidad": cantidad,
                "subtotal": subtotal,
            })

    productos = Producto.objects.filter(activo=True).order_by("nombre")[:20]

    context = {
        "items": items,
        "total": total,
        "productos": productos,
    }

    return render(request, "gimnasio/punto_venta.html", context)


def pos_agregar_producto(request):
    if request.method == "POST":
        codigo = request.POST.get("codigo_barras", "").strip()

        if not codigo:
            messages.error(request, "Escanea o escribe un código de barras.")
            return redirect("punto_venta")

        producto = Producto.objects.filter(
            codigo_barras=codigo,
            activo=True
        ).first()

        if not producto:
            messages.error(request, "Producto no encontrado.")
            return redirect("punto_venta")

        if producto.stock <= 0:
            messages.error(request, "Producto sin stock disponible.")
            return redirect("punto_venta")

        carrito = obtener_carrito(request)
        producto_id = str(producto.id)

        cantidad_actual = int(carrito.get(producto_id, 0))

        if cantidad_actual + 1 > producto.stock:
            messages.error(request, "No hay suficiente stock disponible.")
            return redirect("punto_venta")

        carrito[producto_id] = cantidad_actual + 1
        guardar_carrito(request, carrito)

        messages.success(request, f"{producto.nombre} agregado al carrito.")
        return redirect("punto_venta")

    return redirect("punto_venta")


def pos_eliminar_producto(request, producto_id):
    carrito = obtener_carrito(request)
    producto_id = str(producto_id)

    if producto_id in carrito:
        del carrito[producto_id]
        guardar_carrito(request, carrito)

    return redirect("punto_venta")


def pos_limpiar(request):
    request.session["carrito_pos"] = {}
    request.session.modified = True
    messages.success(request, "Carrito limpiado.")
    return redirect("punto_venta")


def pos_registrar_venta(request):
    if request.method == "POST":
        carrito = obtener_carrito(request)
        metodo_pago = request.POST.get("metodo_pago", "efectivo")
        notas = request.POST.get("notas", "").strip()

        if not carrito:
            messages.error(request, "El carrito está vacío.")
            return redirect("punto_venta")

        with transaction.atomic():
            total = Decimal("0.00")
            productos_venta = []

            for producto_id, cantidad in carrito.items():
                producto = Producto.objects.select_for_update().get(id=producto_id)
                cantidad = int(cantidad)

                if cantidad > producto.stock:
                    messages.error(
                        request,
                        f"No hay suficiente stock de {producto.nombre}."
                    )
                    return redirect("punto_venta")

                subtotal = producto.precio_venta * cantidad
                total += subtotal

                productos_venta.append({
                    "producto": producto,
                    "cantidad": cantidad,
                    "precio_unitario": producto.precio_venta,
                    "subtotal": subtotal,
                })

            venta = Venta.objects.create(
                metodo_pago=metodo_pago,
                total=total,
                notas=notas
            )

            for item in productos_venta:
                producto = item["producto"]

                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=item["cantidad"],
                    precio_unitario=item["precio_unitario"],
                    subtotal=item["subtotal"],
                )

                producto.stock -= item["cantidad"]
                producto.save()

            request.session["carrito_pos"] = {}
            request.session.modified = True

        messages.success(request, f"Venta #{venta.id} registrada correctamente.")
        return redirect("lista_ventas")

    return redirect("punto_venta")


def lista_ventas(request):
    ventas = Venta.objects.prefetch_related("detalles").order_by("-fecha")

    total_ventas = ventas.aggregate(
        total=Sum("total")
    )["total"] or 0

    context = {
        "ventas": ventas,
        "total_ventas": total_ventas,
    }

    return render(request, "gimnasio/lista_ventas.html", context)


@login_required
def corte_caja(request):
    hoy = timezone.localdate()

    fecha_seleccionada = request.GET.get("fecha")

    if fecha_seleccionada:
        try:
            fecha_corte = timezone.datetime.strptime(
                fecha_seleccionada, "%Y-%m-%d"
            ).date()
        except:
            fecha_corte = hoy
    else:
        fecha_corte = hoy

    pagos = Pago.objects.filter(fecha_pago__date=fecha_corte).select_related(
        "cliente", "membresia"
    )

    ventas = Venta.objects.filter(fecha__date=fecha_corte).select_related(
        "cliente", "usuario"
    )

    total_pagos_membresias = pagos.aggregate(total=Sum("monto"))["total"] or Decimal(
        "0.00"
    )

    total_ventas_productos = ventas.aggregate(total=Sum("total"))["total"] or Decimal(
        "0.00"
    )

    total_general = total_pagos_membresias + total_ventas_productos

    total_efectivo_pagos = pagos.filter(metodo_pago="efectivo").aggregate(
        total=Sum("monto")
    )["total"] or Decimal("0.00")

    total_tarjeta_pagos = pagos.filter(metodo_pago="tarjeta").aggregate(
        total=Sum("monto")
    )["total"] or Decimal("0.00")

    total_transferencia_pagos = pagos.filter(metodo_pago="transferencia").aggregate(
        total=Sum("monto")
    )["total"] or Decimal("0.00")

    total_mixto_pagos = pagos.filter(metodo_pago="mixto").aggregate(total=Sum("monto"))[
        "total"
    ] or Decimal("0.00")

    total_efectivo_ventas = ventas.filter(metodo_pago="efectivo").aggregate(
        total=Sum("total")
    )["total"] or Decimal("0.00")

    total_tarjeta_ventas = ventas.filter(metodo_pago="tarjeta").aggregate(
        total=Sum("total")
    )["total"] or Decimal("0.00")

    total_transferencia_ventas = ventas.filter(metodo_pago="transferencia").aggregate(
        total=Sum("total")
    )["total"] or Decimal("0.00")

    total_mixto_ventas = ventas.filter(metodo_pago="mixto").aggregate(
        total=Sum("total")
    )["total"] or Decimal("0.00")

    total_efectivo = total_efectivo_pagos + total_efectivo_ventas
    total_tarjeta = total_tarjeta_pagos + total_tarjeta_ventas
    total_transferencia = total_transferencia_pagos + total_transferencia_ventas
    total_mixto = total_mixto_pagos + total_mixto_ventas

    if request.method == "POST":
        observaciones = request.POST.get("observaciones", "").strip()

        corte = CorteCaja.objects.create(
            fecha=fecha_corte,
            usuario=request.user if request.user.is_authenticated else None,
            total_pagos_membresias=total_pagos_membresias,
            total_ventas_productos=total_ventas_productos,
            total_efectivo=total_efectivo,
            total_tarjeta=total_tarjeta,
            total_transferencia=total_transferencia,
            total_mixto=total_mixto,
            total_general=total_general,
            cantidad_pagos=pagos.count(),
            cantidad_ventas=ventas.count(),
            observaciones=observaciones,
        )

        messages.success(
            request,
            f"Corte de caja guardado correctamente. Total: ${corte.total_general}",
        )

        return redirect("corte_caja")

    ultimos_cortes = CorteCaja.objects.select_related("usuario").order_by(
        "-fecha_creacion"
    )[:10]

    context = {
        "fecha_corte": fecha_corte,
        "fecha_seleccionada": fecha_corte.strftime("%Y-%m-%d"),
        "pagos": pagos,
        "ventas": ventas,
        "total_pagos_membresias": total_pagos_membresias,
        "total_ventas_productos": total_ventas_productos,
        "total_general": total_general,
        "total_efectivo": total_efectivo,
        "total_tarjeta": total_tarjeta,
        "total_transferencia": total_transferencia,
        "total_mixto": total_mixto,
        "total_efectivo_pagos": total_efectivo_pagos,
        "total_tarjeta_pagos": total_tarjeta_pagos,
        "total_transferencia_pagos": total_transferencia_pagos,
        "total_mixto_pagos": total_mixto_pagos,
        "total_efectivo_ventas": total_efectivo_ventas,
        "total_tarjeta_ventas": total_tarjeta_ventas,
        "total_transferencia_ventas": total_transferencia_ventas,
        "total_mixto_ventas": total_mixto_ventas,
        "cantidad_pagos": pagos.count(),
        "cantidad_ventas": ventas.count(),
        "ultimos_cortes": ultimos_cortes,
    }

    return render(request, "gimnasio/corte_caja.html", context)


@login_required
def detalle_corte_caja(request, corte_id):
    corte = get_object_or_404(CorteCaja, id=corte_id)

    pagos = (
        Pago.objects.filter(fecha_pago__date=corte.fecha)
        .select_related("cliente", "membresia")
        .order_by("-fecha_pago")
    )

    ventas = (
        Venta.objects.filter(fecha__date=corte.fecha)
        .select_related("cliente", "usuario")
        .order_by("-fecha")
    )

    context = {
        "corte": corte,
        "pagos": pagos,
        "ventas": ventas,
        "cantidad_pagos": pagos.count(),
        "cantidad_ventas": ventas.count(),
    }

    return render(request, "gimnasio/detalle_corte_caja.html", context)


@login_required
def alertas_membresias(request):
    hoy = timezone.localdate()
    limite_por_vencer = hoy + timedelta(days=3)

    # Última membresía de cada cliente
    ultima_membresia = Membresia.objects.filter(cliente=OuterRef("pk")).order_by(
        "-fecha_fin"
    )

    clientes = Cliente.objects.annotate(
        ultima_fecha_fin=Subquery(
            ultima_membresia.values("fecha_fin")[:1], output_field=DateField()
        )
    ).order_by("nombre")

    vencen_hoy = []
    por_vencer = []
    vencidos = []
    sin_membresia = []

    for cliente in clientes:
        membresia = cliente.membresias.order_by("-fecha_fin").first()

        if not membresia:
            cliente.alerta_membresia = None
            cliente.dias_restantes_alerta = None
            sin_membresia.append(cliente)
            continue

        cliente.alerta_membresia = membresia
        cliente.dias_restantes_alerta = (membresia.fecha_fin - hoy).days

        if membresia.fecha_fin == hoy:
            vencen_hoy.append(cliente)

        elif hoy < membresia.fecha_fin <= limite_por_vencer:
            por_vencer.append(cliente)

        elif membresia.fecha_fin < hoy:
            vencidos.append(cliente)

    context = {
        "hoy": hoy,
        "limite_por_vencer": limite_por_vencer,
        "vencen_hoy": vencen_hoy,
        "por_vencer": por_vencer,
        "vencidos": vencidos,
        "sin_membresia": sin_membresia,
        "total_vencen_hoy": len(vencen_hoy),
        "total_por_vencer": len(por_vencer),
        "total_vencidos": len(vencidos),
        "total_sin_membresia": len(sin_membresia),
    }

    return render(request, "gimnasio/alertas_membresias.html", context)


def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        email = request.POST.get("email", "").strip()
        activo = request.POST.get("activo") == "on"

        if not nombre:
            messages.error(request, "El nombre del cliente es obligatorio.")
            return redirect("editar_cliente", cliente_id=cliente.id)

        if not email:
            messages.error(request, "El correo del cliente es obligatorio.")
            return redirect("editar_cliente", cliente_id=cliente.id)

        email_existente = (
            Cliente.objects.filter(email=email).exclude(id=cliente.id).exists()
        )

        if email_existente:
            messages.error(request, "Ya existe otro cliente con ese correo.")
            return redirect("editar_cliente", cliente_id=cliente.id)

        cliente.nombre = nombre
        cliente.telefono = telefono
        cliente.email = email
        cliente.activo = activo
        cliente.save()

        messages.success(request, "Cliente actualizado correctamente.")
        return redirect("detalle_cliente", cliente_id=cliente.id)

    context = {
        "cliente": cliente,
    }

    return render(request, "gimnasio/editar_cliente.html", context)


def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        codigo_barras = request.POST.get("codigo_barras", "").strip()
        categoria = request.POST.get("categoria", Producto.CATEGORIA_OTRO)
        precio_venta = request.POST.get("precio_venta", "").strip()
        costo = request.POST.get("costo", "0").strip()
        stock = request.POST.get("stock", "0").strip()
        stock_minimo = request.POST.get("stock_minimo", "5").strip()
        activo = request.POST.get("activo") == "on"
        imagen = request.FILES.get("imagen")

        if not nombre:
            messages.error(request, "El nombre del producto es obligatorio.")
            return redirect("editar_producto", producto_id=producto.id)

        if not codigo_barras:
            messages.error(request, "El código de barras es obligatorio.")
            return redirect("editar_producto", producto_id=producto.id)

        codigo_existente = Producto.objects.filter(
            codigo_barras=codigo_barras
        ).exclude(
            id=producto.id
        ).exists()

        if codigo_existente:
            messages.error(request, "Ya existe otro producto con ese código de barras.")
            return redirect("editar_producto", producto_id=producto.id)

        try:
            precio_venta = Decimal(precio_venta)
            costo = Decimal(costo or 0)
            stock = int(stock or 0)
            stock_minimo = int(stock_minimo or 5)

            if precio_venta <= 0:
                messages.error(request, "El precio de venta debe ser mayor a 0.")
                return redirect("editar_producto", producto_id=producto.id)

            if costo < 0 or stock < 0 or stock_minimo < 0:
                messages.error(request, "Costo, stock y stock mínimo no pueden ser negativos.")
                return redirect("editar_producto", producto_id=producto.id)

        except:
            messages.error(request, "Verifica que precio, costo y stock sean valores válidos.")
            return redirect("editar_producto", producto_id=producto.id)

        producto.nombre = nombre
        producto.codigo_barras = codigo_barras
        producto.categoria = categoria
        producto.precio_venta = precio_venta
        producto.costo = costo
        producto.stock = stock
        producto.stock_minimo = stock_minimo
        producto.activo = activo

        if imagen:
            producto.imagen = imagen

        producto.save()

        messages.success(request, "Producto actualizado correctamente.")
        return redirect("lista_productos")

    context = {
        "producto": producto,
        "categorias": Producto.CATEGORIAS,
    }

    return render(request, "gimnasio/editar_producto.html", context)


def desactivar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    if request.method == "POST":
        cliente.activo = False
        cliente.save()

        messages.success(
            request, f"El cliente {cliente.nombre} fue desactivado correctamente."
        )

        return redirect("detalle_cliente", cliente_id=cliente.id)

    context = {
        "cliente": cliente,
    }

    return render(request, "gimnasio/desactivar_cliente.html", context)


def desactivar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        producto.activo = False
        producto.save()

        messages.success(
            request, f"El producto {producto.nombre} fue desactivado correctamente."
        )

        return redirect("lista_productos")

    context = {
        "producto": producto,
    }

    return render(request, "gimnasio/desactivar_producto.html", context)

