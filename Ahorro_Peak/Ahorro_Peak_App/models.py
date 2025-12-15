from django.db import models
from django.contrib.auth.hashers import make_password #para encriptar la contraseña
from django.utils import timezone #el usuario ingresa la fecha
from datetime import datetime

# Create your models here.

class Usuario(models.Model):
    TIPO_USUARIO = [
        ('independiente', 'Independiente'),
        ('mantenido', 'Mantenido'),
    ]
    nombre = models.CharField(max_length=20)  
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO, default='independiente')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)

    def save(self, *args, **kwargs): #funcion que encripa la contraseña
        if not self.pk or 'pbkdf2_' not in self.password: #compara si esta encripatada o no
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Ingreso(models.Model):
    TIPO_INGRESO = [
        ('sueldo', 'Sueldo'),
        ('bono', 'Bono'),
        ('regalo', 'Regalo'),
        ('personalizado', 'Personalizado'),
    ]
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='ingresos')
    tipo_ingreso = models.CharField(max_length=20, choices=TIPO_INGRESO, default='sueldo')
    descripcion = models.CharField(max_length=100, blank=True, null=True)
    monto = models.PositiveIntegerField() #almacena en numero entero positivo
    fecha_ingreso = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.usuario.nombre} - {self.tipo_ingreso} (${self.monto})"

class Gastos(models.Model):
    TIPO_GASTO = [
        ('luz', 'Luz'),
        ('agua', 'Agua'),
        ('gas', 'Gas'),
        ('mercaderia', 'Mercaderia'),
        ('internet', 'Internet'),
        ('entretenimiento', 'Entretenimiento'),
        ('personalizado', 'Personalizado'),
    ]
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="gastos")
    tipo_gasto = models.CharField(max_length=20, choices=TIPO_GASTO, default='personalizado')
    descripcion = models.CharField(max_length=100, blank=True, null=True)
    monto = models.PositiveIntegerField()
    fecha_gasto = models.DateTimeField(auto_now_add=True) #si el usuario no lo edita, se queda con la fecha actual

    def str(self):
        return f"{self.gasto} - (${self.monto})"
    def __str__(self):
        return f"{self.gasto} - (${self.monto})"

class MetaAhorro(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="metas")
    nombre_meta = models.CharField(max_length=100)
    monto_objetivo = models.PositiveIntegerField()
    fecha_limite = models.DateTimeField() #sin el "default=timezone.now" obliga al usuario a colocar el una fecha
    progreso_actual = models.PositiveIntegerField(default=0)

    def progreso_porcentaje(self): #calcula el progreso y lo muestra en %
        if self.monto_objetivo > 0:
            return round((self.progreso_actual / self.monto_objetivo) * 100)
        return 0
    
    def mostrar_progreso_actual(self): #las 2 funciones de progreso transforman los numeros enteros a precio chileno, ej: $120.000
        return f"${self.progreso_actual:,.0f}".replace(",",".") #reemplaza al coma por el punto
    def mostrar_progreso_objetivo(self):
        return f"${self.monto_objetivo:,.0f}".replace(",",".")

    def __str__(self):#devuelve el valor en % y le agrega el simbolo
        return f"{self.nombre_meta} - {self.mostrar_progreso_actual()} / {self.mostrar_progreso_objetivo()} ({self.progreso_porcentaje()}%)"

class Notificacion(models.Model):
    FRECUENCIA = [
        ('diaria', 'Diaria'),
        ('semanal', 'Semanal'),
        ('mensual', 'Mensual'),
        ('entrar', 'Cada vez que se ingrese a la pagina o inicie sesion')
    ]
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="notificaciones")
    frecuencia = models.CharField(max_length=20, choices=FRECUENCIA, default='entrar')
    contenido = models.TextField()
    estado = models.CharField(max_length=10, choices=[('activa', 'Activa'), ('inactiva', ('Inactiva'))], default='activa')

    def __str__(self):
        return f"Notificacion para {self.usuario.nombre} ({self.frecuencia}) - {self.estado}"
    
    def desactivar_notificacion(self):
        metas_vencidas = MetaAhorro.objects.filter(Usuario=self.usuario, fecha_limite__lt=timezone.now())
        if metas_vencidas.exists():
            self.estado = 'inactiva'
            self.save()

    def generar_notificaciones(self):
        metas = MetaAhorro.objects.filter(usuario=self.usuario)
        for meta in metas:
            dias_restantes = (meta.fecha_limite - timezone.now()).days
            if dias_restantes <= 3 and meta.progreso_actual < meta.monto_objetivo:
                contenido = f"Tu meta '{meta.nombre_meta}' termina en {dias_restantes} dias. ¡Ahorra mas para alcanzar tu objetivo!"
                Notificacion.objects.create(
                    usuario=self.usuario,
                    frecuencia='entrar',
                    contenido=contenido
                )

class Reporte(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='reportes')
    mes = models.PositiveSmallIntegerField() #1= enero 2 = febrero 12 = diciembre
    anio = models.PositiveSmallIntegerField(default=timezone.now().year)

    def total_ingresos(self):
        ingresos = Ingreso.objects.filter(
            usuario = self.usuario,
            fecha_ingreso__month = self.mes,
            fecha_ingreso__year = self.anio
        )
        return sum(i.monto for i in ingresos)
    
    def total_gastos(self):
        gastos = Gastos.objects.filter(
            usuario = self.usuario,
            fecha_gasto__month = self.mes,
            fecha_gasto__year = self.anio
        )
        return sum(g.monto for g in gastos)
    
    def total_ahorrado(self):
        return self.total_ingresos() - self.total_gastos()
    
    def __str__(self):
        mes = datetime(1900, self.mes, 1).strftime('%B').capitalize()
        return f"Reporte de {mes} {self.anio} - {self.usuario}"