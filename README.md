# ¿Cuántas emisiones de CO₂ generan los sitios web de las bibliotecas universitarias españolas?

Scripts de extracción y análisis del artículo:

> Álvaro Hontanar y Pablo Sánchez-Núñez. ¿Cuántas emisiones de CO₂ generan los sitios web de las bibliotecas universitarias españolas? La huella de carbono digital, nuevo reto para la biblioteca verde. 

El estudio estima las emisiones de CO₂ por visita de la página principal de cada biblioteca mediante el Sustainable Web Design Model (SWDM v4), a través de Website Carbon™ Calculator v4. Proyecta sus emisiones anuales a partir del tráfico web registrado en 2024 (según datos de REBIUN) y analiza su relación con variables institucionales (titularidad, plantilla, comunidad de usuarios y gasto) y técnicas (rendimiento y peso de la página).

## Contenido del repositorio

```
├── extraccion/
│   └── pagespeed_api.py
│   └── websitecarbon_scraper.py  # Obtención de los datos de emisiones, rendimiento y peso
├── analisis/
│   └── analisis_estadistico.R    # Análisis estadístico y generación de las figuras
└── README.md
```

## Guía de reproducibilidad

Las medidas estadísticas y las figuras obtenidas en este estudio son reproducibles. Ten en cuenta la siguiente información:

### Datos

Los utilizados en el estudio datos no se incluyen en este repositorio. Están disponibles en:

> https://doi.org/10.21950/3KVEEX 

### Código

El código utilizado para analizar los datos está disponible en este mismo repositorio, en la dirección: `analisis/analisis_estadistico.R`

#### Requisitos de software

- R (versión 4.5.2)
- RStudio (versión v. 2026.01.0+392)
- Paquetes de R:

| Paquete   | Versión   |
|-----------|-----------|
| readxl    | 1.4.5   |
| dplyr     | 1.1.4   |
| ggplot2   | 4.0.2   |
| scales    | 1.4.0   |
| patchwork | 1.3.2   |

Los paquetes pueden instalarse con:

```r
install.packages(c("readxl", "dplyr", "ggplot2", "scales", "patchwork"))
```

### Pasos para reproducir el estudio

1. Descargue los datos desde el siguiente DOI (https://doi.org/10.21950/3KVEEX) y coloquelos en el directorio de su preferencia, por ejemplo `analisis/`.
2. Descargue el archivo analisis_estadistico.R, ubicado en el directorio `analisis/analisis_estadistico.R` de este mismo repositorio y colóquelo en el mismo repositorio donde guardaste los datos.
3. Establezca en RStudio el repositorio donde guardó los archivos como directorio de trabajo. En RStudio: *Session > Set Working Directory > To Source File Location*.
4. Ejecute el script completo `analisis_estadistico.R`. Asegurese de que el nombre del archivo en el que estén los datos sea: `emisiones-co2-sitios-web-bibliotecas-universitarias-espanolas.csv`

El script sigue el orden de la sección de Resultados del artículo:

| Sección del script                                   | Resultados del artículo                | Figuras generadas                               |
|------------------------------------------------------|----------------------------------------|-------------------------------------------------|
| 3.1. Distribución de las emisiones de CO₂ por visita | Estadísticos descriptivos y atípicos   | `figura1.jpg`, `figura2.jpg`                    |
| 3.2. Impacto agregado de las emisiones               | Emisiones totales y clasificación      | `figura3.jpg`                                   |
| 3.3. Factores organizativos                          | Titularidad y Tabla I (correlaciones)  | `figura4.jpg` 
| 3.4. Factores técnicos                               | Rendimiento, peso y tipo de energía    | `figura5.jpg`, `figura6.jpg`                    |

Los estadísticos se muestran en la consola de R y las figuras se guardan en el directorio de trabajo, en formato JPG a 300 ppp.

## Cita

Si utiliza estos scripts, cite el artículo original:

> [PROXIMAMENTE]

## Licencia

[CC BY 4.0]([https://creativecommons.org](https://creativecommons.org/licenses/by/4.0/deed.en))
