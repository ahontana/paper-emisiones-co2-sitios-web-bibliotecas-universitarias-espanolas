# ¿Cuántas emisiones de CO₂ generan los sitios web de las bibliotecas universitarias españolas?

Scripts de extracción y análisis del artículo:

> Álvaro Hontanar y Sánchez-Núñez. ¿Cuántas emisiones de CO₂ generan los sitios web de las bibliotecas universitarias españolas? La huella de carbono digital, nuevo reto para la biblioteca verde. 

El estudio estima las emisiones de CO₂ por visita de la página principal de cada biblioteca mediante el Sustainable Web Design Model (SWDM v4), a través de Website Carbon™ Calculator v4, proyecta sus emisiones anuales a partir del tráfico web registrado en 2024 y analiza su relación con variables institucionales (titularidad, plantilla, comunidad de usuarios y gasto) y técnicas (rendimiento y peso de la página).

## Contenido del repositorio

```
├── extraccion/
│   └── 01_extraccion_[...]          # Obtención de los datos de emisiones, rendimiento y peso
├── analisis/
│   └── 02_analisis_estadistico.R    # Análisis estadístico y generación de las figuras
└── README.md
```

## Datos

Los datos no se incluyen en este repositorio. Están disponibles en:

> https://doi.org/10.21950/3KVEEX 

Para ejecutar el análisis, descargue el archivo `` y colóquelo en la carpeta `analisis/`, junto al script.

## Requisitos

- R (versión 4.5.2)
- RStudio (opcional, versión v. 2026.01.0+392)
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

## Guía de reproducibilidad

1. Coloque el dataset en la carpeta `analisis/`.
2. Establezca `analisis/` como directorio de trabajo. En RStudio: *Session > Set Working Directory > To Source File Location*.
3. Ejecute el script completo `02_analisis_estadistico.R`.

El script sigue el orden de la sección de Resultados del artículo:

| Sección del script                                   | Resultados del artículo                | Figuras generadas                               |
|------------------------------------------------------|----------------------------------------|-------------------------------------------------|
| 3.1. Distribución de las emisiones de CO₂ por visita | Estadísticos descriptivos y atípicos   | `figura1.jpg`, `figura2.jpg`                    |
| 3.2. Impacto agregado de las emisiones               | Emisiones totales y clasificación      | `figura3.jpg`                                   |
| 3.3. Factores organizativos                          | Titularidad y Tabla I (correlaciones)  | `figura4.jpg`, `figura_coste_especializado.jpg` |
| 3.4. Factores técnicos                               | Rendimiento, peso y tipo de energía    | `figura5.jpg`, `figura6.jpg`                    |

Los estadísticos se muestran en la consola de R y las figuras se guardan en el directorio de trabajo, en formato JPG a 300 ppp.

### Variable derivada

El script calcula las emisiones totales estimadas de cada sitio web a partir de los datos originales:

```
Emisiones totales (kg) = Emisiones de CO₂ por visita (g) × Visitas al sitio web / 1000
```

## Cita

Si utiliza estos scripts, cite el artículo original:

> [Referencia completa del artículo]

## Licencia

[Licencia elegida, p. ej., MIT para el código]
