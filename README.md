# FlipGames — CEX vs Vinted/Wallapop

App web local para juegos de Nintendo Switch, 3DS y DS: tú metes el precio
que **CEX paga en efectivo** por cada juego (a mano, porque CEX bloquea las
búsquedas automáticas — ver más abajo), y la app busca sola en Vinted y
Wallapop el más barato, calcula el beneficio, detecta packs/lotes rentables,
y te deja marcar compras reales con gráfica de beneficio acumulado.

## ⚠️ Importante antes de usarla

- **CEX no se consulta automáticamente.** Su web bloquea (403 Forbidden)
  las peticiones que no vienen de un navegador real, así que en la pestaña
  **"Mis juegos"** añades tú el nombre, la plataforma y el precio "pagamos
  en efectivo" que veas en [es.webuy.com](https://es.webuy.com) — tarda
  segundos por juego. (El código que intentaba consultarlo solo sigue en
  `app/services/cex.py` / `run_scan_cex_auto`, por si en el futuro CEX
  deja de bloquear estas peticiones, pero ahora mismo no se usa.)
- Vinted y Wallapop sí se consultan automáticamente, con los endpoints
  JSON internos que usan sus propias webs (**no son APIs públicas
  oficiales**): pueden cambiar de un día para otro y dejar de funcionar.
  Si eso pasa, revisa `app/services/vinted.py` y `app/services/wallapop.py`
  — están escritos para fallar de forma controlada (si una web cambia, esa
  fuente simplemente no devuelve resultados, no rompe la app).
- Usa la app con cabeza: no la dejes escaneando en bucle todo el día. Por
  defecto pausa un poco entre peticiones (`REQUEST_DELAY` en
  `app/config.py`).
- Los precios "en EUR" de Vinted/Wallapop se filtran automáticamente
  cuando la API indica la moneda. Si un anuncio no la indica, aparece
  marcado como "¿EUR?" y tienes un botón para copiar un mensaje y
  preguntarle al vendedor, o descartarlo.
- Los packs/lotes se detectan buscando palabras como "lote"/"pack" y
  comprobando si el texto del anuncio menciona varios juegos de los que
  ya tienes guardados. Es un matching por texto, best-effort: **revisa
  siempre el anuncio real** antes de comprar un lote.
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

1. Ve a **"Mis juegos (CEX)"** y añade los juegos que te interesen: nombre,
   plataforma y precio "pagamos en efectivo" (búscalo en es.webuy.com).
2. Vuelve a **"Oportunidades"** y pulsa **"Buscar oportunidades reales"**:
   busca en Vinted y Wallapop cada juego guardado (y también packs/lotes),
   y calcula el beneficio frente al precio de CEX que metiste. También
   puedes pulsar **"Cargar datos de ejemplo"** para ver la interfaz
   funcionando con datos ficticios sin tocar la red ni necesitar juegos
   guardados.
3. En la tabla verás, por cada anuncio rentable: plataforma, si es *con
   carátula* / *sin carátula* / *sin confirmar* (detectado por palabras
   clave del título del anuncio), precio del anuncio, si está confirmado
   en EUR, ubicación del vendedor, precio en efectivo de CEX, beneficio
   estimado y margen. Los packs salen marcados con 📦 y con los juegos
   detectados dentro.
4. Filtra por condición (con/sin carátula) o solo packs con los radios de
   arriba.
5. Si un anuncio no confirma la moneda, pulsa **"Preguntar/Comprobar"**:
   copia un mensaje al portapapeles, abre el anuncio en una pestaña
   nueva, y cuando el vendedor te conteste marcas si era EUR o no.
6. Cuando compres un juego, pulsa **"Comprado"** e indica el precio real
   pagado. La app calcula el beneficio real (precio CEX − precio pagado)
   y lo suma al histórico.
7. En **Historial & Beneficio** ves todas tus compras y la gráfica de
   beneficio acumulado en el tiempo.

## Configuración

Todo ajustable en `app/config.py` (o por variables de entorno): nº de
anuncios por juego, beneficio mínimo para considerar un "deal", términos
de búsqueda de packs, ubicación usada para Wallapop, y pausa entre
peticiones.

## Estructura

```
app/
  app.py              -> rutas Flask
  db.py               -> SQLite (tablas `deals` y `games`)
  config.py
  services/
    cex.py            -> precio de CEX (NO SE USA ahora mismo, ver arriba)
    vinted.py         -> búsqueda de anuncios en Vinted
    wallapop.py       -> búsqueda de anuncios en Wallapop
    matcher.py        -> clasifica con/sin carátula, detecta packs y calcula beneficio
    scanner.py        -> orquesta el escaneo (juegos guardados -> Vinted/Wallapop)
    demo.py           -> datos de ejemplo para probar sin red
  templates/, static/ -> panel web (Oportunidades, Mis juegos, Historial + gráfica Chart.js)
run.py
```
