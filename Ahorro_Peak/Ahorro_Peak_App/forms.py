from django import forms
from .models import Ingreso, Gastos, MetaAhorro, Notificacion, Usuario, Reporte
from django.utils import timezone

class UsuarioForm(forms.ModelForm):
    
    class Meta:
        model = Usuario
        fields = ['nombre','tipo_usuario','email','password']
        widgets = {
            'password' : forms.PasswordInput(),
        }


class IngresoForm(forms.ModelForm):
    class Meta:
        model = Ingreso
        fields = ['tipo_ingreso', 'descripcion', 'monto', 'fecha_ingreso']

#Lo que hace las funciones clean es obligar a agregar una descripcion si el usuario elijio 'PERSONALIAZDO' para identificar el pago o la compra.

    widgets = {
        'fecha_ingreso' : forms.DateTimeInput(attrs={
            'type' : 'datetime-local',
            'class' : 'form-control'
        }),
    }

    def clean_fecha_ingreso(self):
        fecha = self.cleaned_data.get('fecha_ingreso')
        return fecha or timezone.now()

class GastosForm(forms.ModelForm):
    class Meta:
        model = Gastos
        fields = ['tipo_gasto', 'descripcion', 'monto']
        widgets = {
            'fecha_gasto' : forms.DateTimeInput(attrs={
                'type' : 'datetime-local',
                'class' : 'form-control'
            }),
        }


    def clean_fecha_gasto(self):
        fecha = self.cleaned_data.get('fecha_gasto')
        return fecha or timezone.now()


class MetaAhorroForm(forms.ModelForm):
    class Meta:
        model = MetaAhorro
        fields = ['usuario', 'nombre_meta', 'monto_objetivo', 'fecha_limite', 'progreso_actual']
        widgets = {
            'fecha_limite' : forms.DateTimeInput(attrs={
                'type' : 'datetime-local',
                'class' : 'form-control'
            })
        }

    def clean_fecha_limite(self): #el usuario no podra poner fechas anteriores a la actual
        fecha = self.cleaned_data.get('fecha_limite')
        if fecha < timezone.now():
            raise forms.ValidationError("La fecha es invalida, ingrese una fecha futura.")
        return fecha

class ReporteFrom(forms.Form):
    MESES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'),
        (4, 'Abril'), (5, 'Mayo'), (6, 'Junio'),
        (7, 'Julio'), (8, 'Agosto'), (9, 'Septiembre'),
        (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
    ]
    
    mes = forms.ChoiceField(choices=MESES, label="Mes") #muesta la lista de los meses
    anio = forms.IntegerField( #permite ingresar el año validando que no sea mayor al actual
        label = "Año",
        min_value=2000,
        max_value=timezone.now().year,
        initial=timezone.now().year
    )