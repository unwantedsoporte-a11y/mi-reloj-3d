# FlipGames — CEX vs Vinted/Wallapop

App web local que busca juegos de Nintendo Switch, 3DS y DS en Vinted y
Wallapop, compara su precio con lo que **CEX paga en efectivo**, y te
muestra las compras más rentables. Cuando compras uno, lo marcas como
"Comprado" y la app va sumando tu beneficio real y dibujando la gráfica
de beneficio acumulado.

## ⚠️ Importante antes de usarla

- Usa los endpoints JSON internos que usan las propias webs de CEX,
  Vinted y Wallapop para su buscador. **No son APIs públicas oficiales**:
  pueden cambiar de un día para otro y dejar de funcionar. Si eso pasa,
  revisa `app/services/cex.py`, `app/services/vinted.py` y
  `app/services/wallapop.py` — están escritos para fallar de forma
  controlada (si una web cambia, esa fuente simplemente no devuelve
  resultados, no rompe la app) y con comentarios de dónde tocar.
- Usa la app con cabeza: no la dejes escaneando en bucle todo el día.
  Por defecto pausa un poco entre peticiones (`REQUEST_DELAY` en
  `app/config.py`) y limita cuántos juegos/anuncios mira por escaneo.
- Los precios "en EUR" de Vinted/Wallapop se filtran automáticamente
  cuando la API indica la moneda. Si un anuncio no la indica, aparece
  marcado como "¿EUR?" y tienes un botón para copiar un mensaje y
  preguntarle al vendedor, o descartarlo.
- El beneficio estimado es orientativo (precio del anuncio vs precio en
  efectivo de CEX). No incluye gastos de envío ni comisiones.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate    # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar

```bash
python run.py
```

Abre http://127.0.0.1:5000 en el navegador.

## Cómo se usa

1. Pulsa **"Buscar oportunidades reales"** para lanzar un escaneo (tarda
   un rato: recorre Switch/3DS/DS, consulta CEX y luego Vinted/Wallapop
   por cada juego). También puedes pulsar **"Cargar datos de ejemplo"**
   para ver la interfaz funcionando con datos ficticios sin tocar la red.
2. En la tabla verás, por cada anuncio rentable: plataforma, si es *con
   carátula* / *sin carátula* / *sin confirmar* (detectado por palabras
   clave del título del anuncio), precio del anuncio, si está confirmado
   en EUR, ubicación del vendedor, precio en efectivo de CEX, beneficio
   estimado y margen.
3. Filtra por condición (con/sin carátula) con los radios de arriba.
4. Si un anuncio no confirma la moneda, pulsa **"Preguntar/Comprobar"**:
   copia un mensaje al portapapeles, abre el anuncio en una pestaña
   nueva, y cuando el vendedor te conteste marcas si era EUR o no.
5. Cuando compres un juego, pulsa **"Comprado"** e indica el precio real
   pagado. La app calcula el beneficio real (precio CEX − precio pagado)
   y lo suma al histórico.
6. En **Historial & Beneficio** ves todas tus compras y la gráfica de
   beneficio acumulado en el tiempo.

## Configuración

Todo ajustable en `app/config.py` (o por variables de entorno):
plataformas a buscar, nº de juegos por plataforma, nº de anuncios por
juego, beneficio mínimo para considerar un "deal", ubicación usada para
Wallapop, y pausa entre peticiones.

## Estructura

```
app/
  app.py              -> rutas Flask
  db.py               -> SQLite (tabla `deals`, que también sirve de historial de compras)
  config.py
  services/
    cex.py            -> precio en efectivo de CEX
    vinted.py         -> búsqueda de anuncios en Vinted
    wallapop.py       -> búsqueda de anuncios en Wallapop
    matcher.py        -> clasifica con/sin carátula y calcula beneficio
    scanner.py        -> orquesta el escaneo completo
    demo.py           -> datos de ejemplo para probar sin red
  templates/, static/ -> panel web (tabla + gráfica con Chart.js)
run.py
```
