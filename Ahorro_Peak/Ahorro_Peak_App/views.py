from django.shortcuts import render, redirect, get_object_or_404 #get_object_or_404: obtiene objeto o lanza error 404
from django.contrib.auth.decorators import login_required #asegura que solo los que iniciaron sesion accedan
from django.contrib import messages #muestra mensajes flash ej: "guardado correctamente"
from django.utils import timezone #permite trabajar con la fecha y hora
from .models import Usuario, Ingreso, Gastos, MetaAhorro, Notificacion, Reporte #importa todo lo de los modelos
from .forms import ReporteFrom, UsuarioForm, IngresoForm, GastosForm, MetaAhorroForm
from datetime import timedelta #ayuda a calcular fechas futuras y dias restantes
from django.db.models import Sum
from django.contrib.auth.hashers import check_password
import json

def registro(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario registrado correctamente. Ya puedes iniciar sesión.")
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
                request.session['usuario_id'] = user.id
                request.session['acaba_de_entrar'] = True 
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

# --- VISTA PRINCIPAL ---
def home(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('registro')
    
    usuario = Usuario.objects.get(id=usuario_id)
    if request.session.get('acaba_de_entrar'):
        mis_metas = MetaAhorro.objects.filter(usuario=usuario)
        
        for meta in mis_metas:
            notif = Notificacion.objects.filter(
                usuario=usuario, 
                contenido__contains=meta.nombre_meta,
                frecuencia='entrar', 
                estado='activa'
            ).first()

            if notif:
                dias_restantes = (meta.fecha_limite.date() - timezone.now().date()).days
                falta_dinero = meta.monto_objetivo - meta.progreso_actual
                if falta_dinero < 0: falta_dinero = 0
                
                if meta.progreso_actual < meta.monto_objetivo:
                    mensaje_alerta = (
                        f"<strong>{meta.nombre_meta}</strong>: "
                        f"Te quedan <strong>{dias_restantes} días</strong>. "
                        f"Te faltan <strong>${falta_dinero:,.0f}</strong> "
                        f"({meta.progreso_porcentaje()}% completado)."
                    )
                    messages.info(request, mensaje_alerta)
        request.session['acaba_de_entrar'] = False

    # Inicializar formularios
    ingreso_form = IngresoForm()
    gasto_form = GastosForm()
    meta_form = MetaAhorroForm()

    if request.method == 'POST':
        if 'tipo_ingreso' in request.POST:
            ingreso_form = IngresoForm(request.POST)
            if ingreso_form.is_valid():
                ingreso = ingreso_form.save(commit=False)
                ingreso.usuario = usuario
                ingreso.save()
                messages.success(request, 'Ingreso registrado')
                return redirect('home')

        elif 'tipo_gasto' in request.POST:
            gasto_form = GastosForm(request.POST)
            if gasto_form.is_valid():
                gasto = gasto_form.save(commit=False)
                gasto.usuario = usuario
                gasto.save()
                messages.success(request, 'Gasto registrado')
                return redirect('home')
        
        elif 'nombre_meta' in request.POST:
            meta_form = MetaAhorroForm(request.POST)
            if meta_form.is_valid():
                meta = meta_form.save(commit=False)
                meta.usuario = usuario
                meta.save()
                
                frecuencia = meta_form.cleaned_data['frecuencia_notificacion']
                Notificacion.objects.create(
                    usuario=usuario,
                    frecuencia=frecuencia,
                    contenido=f"Recordatorio de meta: {meta.nombre_meta}",
                    estado='activa'
                )
                messages.success(request, 'Meta creada exitosamente')
                return redirect('home')
        
        elif 'abonar_meta' in request.POST:
            meta_id = request.POST.get('meta_id')
            try:
                monto_ahorro = int(request.POST.get('monto_ahorro'))
                meta = get_object_or_404(MetaAhorro, id=meta_id, usuario=usuario)
                
                ing_total = sum(i.monto for i in Ingreso.objects.filter(usuario=usuario))
                gas_total = sum(g.monto for g in Gastos.objects.filter(usuario=usuario))
                ahorro_total_actual = MetaAhorro.objects.filter(usuario=usuario).aggregate(Sum('progreso_actual'))['progreso_actual__sum'] or 0
                
                saldo_en_mano = ing_total - gas_total - ahorro_total_actual
                
                if monto_ahorro > 0 and monto_ahorro <= saldo_en_mano:
                    meta.progreso_actual += monto_ahorro
                    meta.save()
                    messages.success(request, f'¡Abonaste ${monto_ahorro} a tu meta "{meta.nombre_meta}"!')
                else:
                    messages.error(request, 'No tienes suficiente saldo disponible.')
            except ValueError:
                messages.error(request, 'Monto invalido.')
            return redirect('home')

        elif 'eliminar_meta' in request.POST:
            meta_id = request.POST.get('meta_id')
            meta = get_object_or_404(MetaAhorro, id=meta_id, usuario=usuario)
            meta.delete()
            Notificacion.objects.filter(usuario=usuario, contenido__contains=meta.nombre_meta).delete()
            messages.success(request, 'Meta eliminada correctamente.')
            return redirect('home')

    # --- CÁLCULOS (GET) ---
    gastos = Gastos.objects.filter(usuario=usuario).order_by('-fecha_gasto')
    ingresos = Ingreso.objects.filter(usuario=usuario)
    metas = MetaAhorro.objects.filter(usuario=usuario).order_by('fecha_limite')
    
    total_ingresos = sum(i.monto for i in ingresos)
    total_gastos = sum(g.monto for g in gastos)
    total_ahorrado = metas.aggregate(Sum('progreso_actual'))['progreso_actual__sum'] or 0
    saldo_disponible = (total_ingresos - total_gastos) - total_ahorrado

    resumen = Gastos.objects.filter(usuario=usuario).values('tipo_gasto').annotate(total=Sum('monto'))
    labels = [r['tipo_gasto'] for r in resumen]
    data = [r['total'] for r in resumen]
    labels_json = json.dumps(labels)
    data_json = json.dumps(data)

    return render(request, 'home.html', {
        'saldo_disponible': saldo_disponible,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'total_ahorrado': total_ahorrado,
        'gastos': gastos,
        'ingresos' : ingresos,
        'metas': metas,
        'labels': labels_json,
        'data': data_json,
        'ingreso_form': ingreso_form,
        'gasto_form': gasto_form,
        'meta_form': meta_form,
        'usuario' : usuario,
    })