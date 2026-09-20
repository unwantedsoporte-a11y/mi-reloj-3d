# FlipGames — CEX vs Vinted/Wallapop

App web local para juegos de Nintendo Switch, 3DS y DS: busca automáticamente
en CEX, Vinted y Wallapop (con un navegador automatizado, para saltarse sus
bloqueos anti-bots), compara precios, calcula el beneficio, detecta
packs/lotes rentables, y te deja marcar compras reales con gráfica de
beneficio acumulado. También puedes añadir juegos a mano en "Mis juegos" si
quieres forzar un precio de CEX concreto o CEX no lo encuentra solo.

## ⚠️ Importante antes de usarla

- **CEX, Vinted y Wallapop bloquean las peticiones directas a su API**
  (403/404) si no vienen de un navegador real. Por eso la app usa
  [Playwright](https://playwright.dev) para abrir sus páginas de búsqueda
  en un navegador automatizado de verdad y capturar ahí la respuesta —
  tiene más posibilidades de colar que pedir la API a pelo, pero **sigue
  sin haber garantía**: estas protecciones a veces también detectan
  navegadores automatizados. Si deja de funcionar, revisa
  `app/services/browser.py`, `cex.py`, `vinted.py` y `wallapop.py` — están
  escritos para fallar de forma controlada (si una fuente falla, esa
  fuente simplemente no devuelve resultados, no rompe la app).
- Por eso mismo, los escaneos son más **lentos** que una petición HTTP
  normal (cada búsqueda abre una página real y espera a que cargue).
- Si CEX no encuentra un juego, o quieres forzar un precio concreto,
  añádelo a mano en **"Mis juegos"** — se combina automáticamente con lo
  que encuentre CEX solo.
- Los precios "en EUR" de Vinted/Wallapop se filtran automáticamente
  cuando la API indica la moneda. Si un anuncio no la indica, aparece
  marcado como "¿EUR?" y tienes un botón para copiar un mensaje y
  preguntarle al vendedor, o descartarlo.
- Los packs/lotes se detectan buscando palabras como "lote"/"pack" y
  comprobando si el texto del anuncio menciona varios juegos de los que
  ya conoces. Es un matching por texto, best-effort: **revisa siempre el
  anuncio real** antes de comprar un lote.
- El beneficio estimado es orientativo (precio del anuncio vs precio en
  efectivo de CEX). No incluye gastos de envío ni comisiones.
- Usa la app con cabeza: no la dejes escaneando en bucle todo el día.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate    # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

El último paso descarga el navegador que usa la app (chromium, unos
300 MB) — **solo hace falta hacerlo una vez**.

## Ejecutar

```bash
python run.py
```

Abre http://127.0.0.1:5000 en el navegador.

## Cómo se usa

1. (Opcional) Ve a **"Mis juegos (CEX)"** y añade a mano juegos concretos
   con su precio "pagamos en efectivo" si quieres forzar un precio o CEX
   no los encuentra solo. Puedes pegar varios de golpe con el formato
   `Título, Plataforma, Precio`.
2. Ve a **"Oportunidades"** y pulsa **"Buscar oportunidades reales"**:
   busca juegos en CEX automáticamente, los combina con los que hayas
   guardado a mano, y para cada uno busca en Vinted y Wallapop el más
   barato (y también packs/lotes). Tarda un rato porque abre páginas
   reales una a una. También puedes pulsar **"Cargar datos de ejemplo"**
   para ver la interfaz funcionando con datos ficticios sin tocar la red.
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

Todo ajustable en `app/config.py` (o por variables de entorno):
plataformas a buscar, nº de juegos por plataforma, nº de anuncios por
juego, beneficio mínimo para considerar un "deal", términos de búsqueda
de packs, ubicación usada para Wallapop, y tiempo máximo de espera por
página.

## Estructura

```
app/
  app.py              -> rutas Flask
  db.py               -> SQLite (tablas `deals` y `games`)
  config.py
  services/
    browser.py        -> navegador automatizado (Playwright) compartido por los 3 clientes
    cex.py             -> precio en efectivo de CEX
    vinted.py          -> búsqueda de anuncios en Vinted
    wallapop.py        -> búsqueda de anuncios en Wallapop
    matcher.py         -> clasifica con/sin carátula, detecta packs y calcula beneficio
    scanner.py         -> orquesta el escaneo (CEX auto + Mis juegos -> Vinted/Wallapop)
    demo.py            -> datos de ejemplo para probar sin red
  templates/, static/ -> panel web (Oportunidades, Mis juegos, Historial + gráfica Chart.js)
run.py
```
