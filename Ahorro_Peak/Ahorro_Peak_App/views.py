from django.shortcuts import render, redirect, get_object_or_404 #get_object_or_404: obtiene objeto o lanza error 404
from django.contrib.auth.decorators import login_required #asegura que solo los que iniciaron sesion accedan
from django.contrib import messages #muestra mensajes flash ej: "guardado correctamente"
from django.utils import timezone #permite trabajar con la fecha y hora
from .models import Usuario, Ingreso, Gastos, MetaAhorro, Notificacion, Reporte #importa todo lo de los modelos
from .forms import ReporteFrom, UsuarioForm, IngresoForm, GastosForm
from datetime import timedelta #ayuda a calcular fechas futuras y dias restantes
from django.db.models import Sum
from django.contrib.auth.hashers import check_password
import json

def registro(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario registrado correctamente. Ya puedes iniciar sesion.")
            return redirect('registro')
    else:
        form = UsuarioForm()
    return render(request, 'registro_login.html', {'form': form})

def login_usuario(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = Usuario.objects.get(email=email)
            if check_password(password, user.password):
                request.session['usuario_id'] = user.id  #guardamos el id del usuario en sesión
                return redirect('home')
            else:
                messages.error(request, "Contraseña incorrecta")
        except Usuario.DoesNotExist:
            messages.error(request, "Usuario no existe")
    form = UsuarioForm()
    return render(request, 'registro_login.html', {'form': form})

def logout_usuario(request):
    request.session.flush()
    return redirect('registro')

#VISTA PRINCIPAL

def home(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('registro')
    
    usuario = Usuario.objects.get(id=usuario_id)

    if request.method == 'POST':
        # Guardar Ingreso
        if 'tipo_ingreso' in request.POST:
            ingreso_form = IngresoForm(request.POST)
            gasto_form = GastosForm()
            if ingreso_form.is_valid():
                ingreso = ingreso_form.save(commit=False)
                ingreso.usuario = usuario
                ingreso.save()
                messages.success(request, 'Ingreso registrado')
                return redirect('home')

        # Guardar Gasto
        elif 'tipo_gasto' in request.POST:
            gasto_form = GastosForm(request.POST)
            ingreso_form = IngresoForm()
            if gasto_form.is_valid():
                gasto = gasto_form.save(commit=False)
                gasto.usuario = usuario
                gasto.save()
                messages.success(request, 'Gasto registrado')
                return redirect('home')

    else:
        ingreso_form = IngresoForm()
        gasto_form = GastosForm()

    # Resumen
    gastos = Gastos.objects.filter(usuario=usuario).order_by('-fecha_gasto')
    ingresos = Ingreso.objects.filter(usuario=usuario)
    total_ingresos = sum(i.monto for i in ingresos)
    total_gastos = sum(g.monto for g in gastos)
    saldo_disponible = total_ingresos - total_gastos

    #graficos
    resumen = Gastos.objects.filter(usuario=usuario).values('tipo_gasto').annotate(total=Sum('monto'))
    labels = [r['tipo_gasto'] for r in resumen]
    data = [r['total'] for r in resumen]

    # Convertir a JSON para usar en JS
    labels_json = json.dumps(labels)
    data_json = json.dumps(data)

    resumen = Gastos.objects.filter(usuario=usuario).values('tipo_gasto').annotate(total=Sum('monto'))
    labels = [r['tipo_gasto'] for r in resumen]
    data = [r['total'] for r in resumen]

    return render(request, 'home.html', {
        'saldo_disponible': saldo_disponible,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'gastos': gastos,
        'ingresos' : ingresos,
        'labels': labels_json,
        'data': data_json,
        'ingreso_form': ingreso_form,
        'gasto_form': gasto_form,
        'usuario' : usuario,
    })


# #VISTA PRINCIPAL
# def home(request):
#     usuario_id = request.session.get('usuario_id')
#     if not usuario_id:
#         return redirect('registro')  # Redirige al login/registro si no hay sesión

#     # Obtenemos el usuario real
#     usuario = Usuario.objects.get(id=usuario_id)

#     # Gastos e ingresos del usuario
#     gastos = Gastos.objects.filter(usuario=usuario).order_by('-fecha_gasto')
#     ingresos = Ingreso.objects.filter(usuario=usuario)

#     # Cálculo de totales
#     total_ingresos = sum(i.monto for i in ingresos)
#     total_gastos = sum(g.monto for g in gastos)
#     saldo_disponible = total_ingresos - total_gastos

#     # Resumen para la gráfica
#     resumen = (
#         Gastos.objects.filter(usuario=usuario)
#         .values('tipo_gasto')
#         .annotate(total=Sum('monto'))
#     )
#     labels = [r['tipo_gasto'] for r in resumen]
#     data = [r['total'] for r in resumen]

#     return render(request, 'home.html', {
#         'saldo_disponible': saldo_disponible,
#         'total_ingresos': total_ingresos,
#         'total_gastos': total_gastos,
#         'gastos': gastos,
#         'labels': labels,
#         'data': data
#     })


#VISTA DEL USUARIO
@login_required
def perfil_usuario(request): #muestra al usuario logueado
    usuario = request.user.usuario
    return render(request, 'usuarios/perfil.html', {'usuario' : usuario})

#VISTAS DE INGRESO
@login_required
def listar_ingresos(request): #muestra los ingresos del usuario
    ingresos = Ingreso.objects.filter(usuario = request.user.usuario).order_by('-fecha_ingreso')
    return render(request, 'listar.html', {'ingresos' : ingresos})

#VISTAS DE GASTOS
@login_required
def listar_gastos(request): #muestra los gastos del usuario
    gastos = Gastos.objects.filter(usuario=request.user.usuario).order_by('-fecha_gasto')
    resumen = ( #agrupa los gastos y los suma
        Gastos.objects.filter(usuario = request.user.usuario)
        .values('tipo_gasto')
        .annotate(total=Sum('monto'))
    )
    labels = [r['tipo_gasto'] for r in resumen]
    data = [r['total'] for r in resumen]
    context = {
        'gastos' : gastos,
        'labels' : labels,
        'data' : data,
    }
    return render(request, 'listar_gasto.html', context)

#VISTAS DE METASAHORRO
@login_required
def listar_metas(request): # lista las metas que el usuario ingreso
    metas = MetaAhorro.objects.filter(usuaio = request.user.usuario)
    return render(request, 'listar.html', {'metas' : metas})

@login_required
def crear_meta(request): #crea una nueva meta de ahorro
    if request.methof == 'POST':
        nombre_meta = request.POST.get('nombre_meta')
        monto_objetivo = request.POST.get('monto_objetivo')
        fecha_limite = request.POST.get('fecha_limite')
        progreso_actual = request.POST.get('progreso_actual', 0)

        meta = MetaAhorro(
            usuario = request.user.usuario,
            nombre_meta = nombre_meta,
            monto_objetivo = monto_objetivo,
            fecha_limite = fecha_limite,
            progreso_actual = progreso_actual
        )
        meta.save()
        messages.success(request, "Meta de ahorro creada.")
        return redirect('listar_metas')
    return render(request, 'crear.html')

#VISTAS DE NOTIFICACIONES
@login_required
def mostrar_notificaciones(request): #muestra las notificaciones activas en formato POP-UP
    notificaciones =Notificacion.objects.filter(usuario = request.user.usuario, estado = 'activa')
    return render(request, 'notificaciones.html', {'notificaciones', notificaciones})

@login_required
def generar_reporte(request): #genera el reporte mensual con los ingresos, gastos y ahorros
    reporte = None
    if request.method == 'POST':
        form = ReporteFrom(request.POST)

        if form.is_valid():
            mes = form.cleaned_data['mes']
            anio = form.cleaned_data['anio']
            usuario = request.user.usuario

            ingresos = Ingreso.objects.filter(usuario=usuario, fecha_ingreso__year=anio, fecha_ingreso__month=mes)
            gastos = Gastos.objects.filter(usuario=usuario, fecha_gasto__year=anio, fecha_gasto__month=mes)
            metas = MetaAhorro.objects.filter(usuario=usuario)

            total_ingresos = sum(i.monto for i in ingresos)
            total_gastos = sum(g.monto for g in gastos)
            total_ahorro = sum(m.progreso_acual for m in metas)

            reporte, creado = Reporte.objects.update_or_create(
                usuario = usuario,
                mes = mes,
                anio = anio,
                defaults={
                    'total_ingresos' : total_ingresos,
                    'total_gastos' : total_gastos,
                    'total_ahorro' : total_ahorro,
                }
            )
    else:
        form = ReporteFrom()
    
    return render(request, 'reoirte.html', {'form' : form, 'reporte' : reporte})