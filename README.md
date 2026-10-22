# Guane Hand Tracker

Prueba de concepto local para detectar una mano y reconocer un gesto de pinza
entre el pulgar y el indice. Esta primera etapa no envia video ni datos por red:
sirve para validar la camara, MediaPipe, la latencia y la retroalimentacion.

## Inicio rapido (Windows)

Python 3.12 debe estar instalado. Desde PowerShell, en la raiz del proyecto:

```powershell
.\scripts\setup.ps1
.\scripts\run_sensor.ps1
```

En el primer arranque se descarga el modelo oficial `hand_landmarker.task`
(aproximadamente 8 MB). Windows puede solicitar permiso para usar la camara.

## Controles

- `Q` o `Esc`: salir.
- `C`: repetir la estabilizacion inicial.
- `M`: activar o desactivar el efecto espejo.

Si la camara predeterminada no es la correcta:

```powershell
.\scripts\run_sensor.ps1 -Camera 1
```

Pruebe `0`, `1` o `2`. Para reducir el procesamiento puede indicarse otra
resolucion:

```powershell
.\scripts\run_sensor.ps1 -Width 640 -Height 480
```

## Que se muestra

- Los 21 puntos de la mano y sus conexiones.
- Una linea entre pulgar e indice.
- Estado `ESTABILIZANDO`, `MANO ABIERTA` o `PINZA DETECTADA`.
- Intensidad continua de la pinza, lateralidad estimada y FPS.

La pinza se calcula como la distancia entre las puntas del pulgar y el indice,
normalizada por el tamano de la palma. Esto hace que el resultado sea menos
sensible a la distancia entre la mano y la camara.

En esta primera prueba la distancia es bidimensional. Por eso debe usarse la
mano aproximadamente de frente: dos dedos alineados en la imagen, pero separados
en profundidad, pueden parecer una pinza. La profundidad relativa se evaluara en
una iteracion posterior.

## Estructura

```text
sensor/
  app.py                 captura, MediaPipe e interfaz OpenCV
  pinch.py               calculos independientes del detector
scripts/
  setup.ps1              crea .venv e instala dependencias
  run_sensor.ps1         inicia la prueba
tests/
  test_pinch.py          pruebas del calculo de pinza
```

## Privacidad

Todo el procesamiento de esta etapa ocurre localmente. No se graban imagenes ni
se transmite el video.
