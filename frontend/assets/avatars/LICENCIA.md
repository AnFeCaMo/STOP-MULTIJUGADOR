# Avatares vectoriales y emociones

Los 20 retratos y sus 12 expresiones se generan como ilustraciones SVG vectoriales locales mediante `tools/generar_avatares_vectoriales.py`. Los recursos no dependen de imágenes remotas ni contienen recortes rasterizados; pueden escalarse a cualquier tamaño sin pixelarse y tienen fondo transparente fuera del personaje.

## Catálogo e integración

El catálogo se conserva en `frontend/avatar-catalog.js`. Se mantienen los IDs persistentes (`persona-01` a `persona-20`), los nombres, los alias heredados y las rutas para no afectar perfiles, partidas o reconexiones. Las emociones se sirven desde `frontend/assets/avatars/expresiones/<id>/`; el menú utiliza siempre el estado `normal`.

Para regenerar los recursos desde la raíz del proyecto:

```bash
python3 tools/generar_avatares_vectoriales.py
```

Los scripts antiguos `generar_avatares_desde_tabla.py` y `generar_variantes_avatares.py` se mantienen como puntos de entrada compatibles y también generan los SVG vectoriales nítidos.


## Fuente de referencia proporcionada

El proyecto incluye `tools/source-assets/Tabla de Emociones Dragon Ball.png`, una tabla proporcionada por el propietario, quien declaró que cuenta con permiso para su uso. Los avatares activos se regeneran ahora como SVG vectoriales locales para evitar ampliaciones pixeladas; la tabla se conserva como referencia visual de nombres, paletas y expresiones.

El propietario confirma que también cuenta con permiso para publicar y usar los personajes y retratos Dragon Ball incluidos en este proyecto. Esta nota registra esa confirmación; conserva junto con el proyecto la autorización escrita y sus condiciones de uso.
