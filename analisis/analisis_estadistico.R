library(readxl)
library(dplyr)
library(ggplot2)
library(scales)
library(patchwork)

#CARGA DEL DATASET
df <- read.csv2("emisiones-co2-sitios-web-bibliotecas-universitarias-espanolas.csv",
                fileEncoding = "latin1", check.names = FALSE)

#CREAR COLUMNA CON LAS EMISIONES TOTALES ESTIMADAS DE CADA SITIO WEB (kg)
df$`Emisiones totales kg` <- df$`Emisiones de CO2` * df$`Visitas al sitio web de la biblioteca` / 1000

########################################################
# 3.1. DISTRIBUCIÓN DE LAS EMISIONES DE CO2 POR VISITA #
########################################################

#ESTADÍSTICOS DESCRIPTIVOS DE LA VARIABLE EMISIONES DE CO2
summary(df$`Emisiones de CO2`)
sd(df$`Emisiones de CO2`)
IQR(df$`Emisiones de CO2`)
nrow(df)
mean(df$`Emisiones de CO2` < 1) * 100

outliers <- boxplot.stats(df$`Emisiones de CO2`)$out
df[df$`Emisiones de CO2` %in% outliers, c("Biblioteca universitaria", "Emisiones de CO2")]

#FIGURA 1 - BOXPLOT EMISIONES DE CO2 POR VISITA
figura1_boxplot_emisiones <- ggplot(df, aes(x = "", y = `Emisiones de CO2`)) +

  geom_boxplot(
    fill = "#001489",
    color = "#001489",
    alpha = 0.7,
    width = 0.3,
    outlier.color = "#001489"
  ) +

  geom_hline(
    aes(yintercept = 0.359, linetype = "Mediana global (0,359 g)"),
    color = "red",
    linewidth = 1
  ) +

  stat_summary(
    fun = mean,
    geom = "point",
    shape = 4,
    size = 4,
    stroke = 1.5,
    color = "#001489"
  ) +

  coord_flip() +

  scale_y_continuous(
    breaks = seq(0, 4, by = 0.5),
    labels = number_format(accuracy = 0.1, decimal.mark = ",")
  ) +

  scale_linetype_manual(
    name = "",
    values = c("Mediana global (0,359 g)" = "dashed")
  ) +

  labs(
    title = "Distribución de las emisiones de CO₂ por visita",
    x = "Bibliotecas",
    y = "Emisiones de CO₂ (g por visita)"
  ) +

  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(face = "bold"),
    axis.title = element_text(face = "bold"),
    legend.position = "bottom"
  )

figura1_boxplot_emisiones
ggsave("figura1.jpg", plot = figura1_boxplot_emisiones, width = 8, height = 5, dpi = 300)


#FIGURA 2 - BARRAS CALIFICACIÓN DE SOSTENIBILIDAD
calificacion <- df %>%
  mutate(`Calificación de sostenibilidad` = factor(
    `Calificación de sostenibilidad`,
    levels = c("A+", "A", "B", "C", "D", "E", "F")
  )) %>%
  count(`Calificación de sostenibilidad`, .drop = FALSE) %>%   
  mutate(porcentaje = n / sum(n))

figura2_barras_calificacion <- ggplot(calificacion, aes(x = `Calificación de sostenibilidad`, y = porcentaje)) +

  geom_col(
    fill = "#001489",
    alpha = 0.9,
    width = 0.7
  ) +

  geom_text(
    aes(label = percent(porcentaje, accuracy = 0.1, decimal.mark = ",")),
    vjust = -0.4,
    size = 4
  ) +

  scale_y_continuous(
    labels = percent_format(decimal.mark = ","),
    expand = expansion(mult = c(0, 0.1))
  ) +

  labs(
    title = "Distribución de la calificación de sostenibilidad",
    x = "Calificación de sostenibilidad",
    y = "Páginas analizadas (%)"
  ) +

  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(face = "bold", hjust = 0),
    axis.title = element_text(face = "bold"),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank()
  )

figura2_barras_calificacion
ggsave("figura2.jpg", plot = figura2_barras_calificacion, width = 8, height = 5, dpi = 300)


##########################################
# 3.2. IMPACTO AGREGADO DE LAS EMISIONES #
##########################################

#EMISIONES TOTALES DE TODAS LAS BIBLIOTECAS
total_emisiones_rebiun <- sum(df$`Emisiones totales kg`)
total_emisiones_rebiun

#FIGURA 3 - BARRAS TOP 10 BIBLIOTECAS CON MÁS EMISIONES DE CO2 AGREGADAS
df$posicion_visitas <- rank(-df$`Visitas al sitio web de la biblioteca`)
df$posicion_emisiones_totales <- rank(-df$`Emisiones totales kg`)
df_ordenado <- df[order(-df$`Emisiones totales kg`), ]
top10_total <- head(df_ordenado, 10)
top10_total <- top10_total[, c("Biblioteca universitaria", "Visitas al sitio web de la biblioteca", "Emisiones de CO2",
                               "Emisiones totales kg", "posicion_visitas", "posicion_emisiones_totales")]

barras_top10 <- top10_total %>%
  mutate(`Biblioteca universitaria` = factor(
    `Biblioteca universitaria`,
    levels = rev(`Biblioteca universitaria`)
  ))

figura3_barras_top10_bibliotecas_mas_emisiones <- ggplot(barras_top10, aes(x = `Biblioteca universitaria`, y = `Emisiones totales kg`)) +

  geom_col(
    fill = "#001489",
    width = 0.7
  ) +

  coord_flip() +

  scale_y_continuous(
    labels = number_format(accuracy = 1, big.mark = ".", decimal.mark = ",")
  ) +

  labs(
    title = "Top 10 bibliotecas universitarias por emisiones totales de CO₂",
    x = "Bibliotecas",
    y = "Emisiones totales de CO₂ (kg)"
  ) +

  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(face = "bold", hjust = 0),
    plot.title.position = "plot",
    axis.title = element_text(face = "bold"),
    axis.text.y = element_text(size = 10),
    panel.grid.major.y = element_blank()
  )

figura3_barras_top10_bibliotecas_mas_emisiones
ggsave("figura3.jpg", plot = figura3_barras_top10_bibliotecas_mas_emisiones, width = 8, height = 5, dpi = 300)

#PESO DEL TOP 10 AGREGADAS SOBRE EL TOTAL
suma_top10 <- sum(top10_total$`Emisiones totales kg`)
suma_top10 / total_emisiones_rebiun * 100

#TOP 10 DE EMISIONES AGREGADAS QUE ESTÁN EN TOP 10 VISITAS
sum(top10_total$posicion_visitas <= 10)

#LAS QUE NO ESTÁN EN TOP 10 VISITAS, PERO SI EN TOP 10 EMISIONES AGREGADAS (Navarra, Alcalá y Extremadura)
top10_total[top10_total$posicion_visitas > 10, ]

###############################
# 3.3. FACTORES ORGANIZATIVOS #
###############################

#ESTADÍSTICOS DESCRIPTIVOS DE LA VARIABLE EMISIONES DE CO2 POR TITULARIDAD
df_publicas <- df %>% filter(Titularidad == "Pública")
df_privadas <- df %>% filter(Titularidad == "Privada")

nrow(df_publicas)
summary(df_publicas$`Emisiones de CO2`)
sd(df_publicas$`Emisiones de CO2`)
IQR(df_publicas$`Emisiones de CO2`)

nrow(df_privadas)
summary(df_privadas$`Emisiones de CO2`)
sd(df_privadas$`Emisiones de CO2`)
IQR(df_privadas$`Emisiones de CO2`)

#(porcentaje de cada grupo que supera la mediana global)
mean(df_publicas$`Emisiones de CO2` > 0.359) * 100
mean(df_privadas$`Emisiones de CO2` > 0.359) * 100

#FIGURA 4 - BOXPLOT DE EMISIONES DE CO2 POR VISITA POR TITULARIDAD
figura4_boxplot_titularidad <- ggplot(df, aes(x = Titularidad, y = `Emisiones de CO2`)) +

  geom_boxplot(
    fill = "#001489",
    color = "#001489",
    alpha = 0.7,
    width = 0.35,
    outlier.color = "#001489"
  ) +

  geom_hline(
    aes(yintercept = 0.359, linetype = "Mediana global (0,359 g)"),
    color = "red",
    linewidth = 1
  ) +

  stat_summary(
    fun = mean,
    geom = "point",
    shape = 4,
    size = 4,
    stroke = 1.5,
    color = "#001489"
  ) +

  coord_flip() +

  scale_y_continuous(
    breaks = seq(0, 4, by = 0.5),
    labels = number_format(accuracy = 0.1, decimal.mark = ",")
  ) +

  scale_linetype_manual(
    name = "",
    values = c("Mediana global (0,359 g)" = "dashed")
  ) +

  labs(
    title = "Distribución de las emisiones de CO₂ por titularidad",
    x = "Titularidad",
    y = "Emisiones de CO₂ (g por visita)"
  ) +

  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(face = "bold"),
    axis.title = element_text(face = "bold"),
    legend.position = "bottom"
  )

figura4_boxplot_titularidad
ggsave("figura4.jpg", plot = figura4_boxplot_titularidad, width = 8, height = 5, dpi = 300)

#TABLA I - CORRELACIÓN ENTRE LAS EMISIONES DE CO2 POR VISITA Y LAS VARIABLES ORGANIZATIVAS
variables_institucionales <- c(
  #personal de biblioteca
  "Personal bibliotecario",
  "Personal auxiliar de biblioteca",
  "Estudiantado trabajando con beca",
  "Personal administrativo",
  "Personal especializado",
  "Plantilla total de la biblioteca",
  #comunidad de usuarios
  "Número de docentes",
  "Personal empleado investigador",
  "Personal técnico de gestión y administración",
  "Número de estudiantes",
  "Total de usuarios potenciales",
  #recursos económicos
  "Coste total del personal especializado",
  "Coste total del personal",
  "Gasto en información electrónica",
  "Gasto en recursos de información"
)

#FUNCIÓN PARA EL CÁLCULO DE CORRELACIONES
calcular_correlaciones <- function(df, variable_objetivo, variables_explicativas) {

  vars <- df %>%
    select(all_of(c(variable_objetivo, variables_explicativas))) %>%
    mutate(across(everything(), as.numeric))

  correlaciones <- sapply(vars[-1], function(x) {
    cor(vars[[variable_objetivo]], x, use = "complete.obs")
  })

  p_values <- sapply(vars[-1], function(x) {
    cor.test(vars[[variable_objetivo]], x)$p.value
  })

  tabla <- data.frame(
    Variable = names(correlaciones),
    Correlacion = round(correlaciones, 3),
    p_value = round(p_values, 3),
    row.names = NULL
  )

  return(tabla)
}

tabla_cor_emisiones_visita <- calcular_correlaciones(
  df = df,
  variable_objetivo = "Emisiones de CO2",
  variables_explicativas = variables_institucionales
)

tabla_cor_emisiones_visita

#COSTE DEL PERSONAL ESPECIALIZADO - ¿DE DÓNDE SALE EL r = 0,691?
#BIBLIOTECAS SIN DATO O COSTE 0
sum(!is.na(df$`Coste total del personal especializado`))
sum(df$`Coste total del personal especializado` == 0, na.rm = TRUE)

#BIBLIOTECA CON MAYOR COSTE DE PERSONAL ESPECIALIZADO (LEÓN)
df %>%
  arrange(desc(`Coste total del personal especializado`)) %>%
  select(`Biblioteca universitaria`, `Coste total del personal especializado`, `Emisiones de CO2`) %>%
  head(5)

#PEARSON QUITANDO LEÓN
df_sin_leon <- df %>% filter(`Biblioteca universitaria` != "Universidad de León")
cor.test(df_sin_leon$`Coste total del personal especializado`, df_sin_leon$`Emisiones de CO2`, method = "pearson")

#SPEARMAN
cor.test(df$`Coste total del personal especializado`, df$`Emisiones de CO2`, method = "spearman", exact = FALSE)

##########################
# 3.4. FACTORES TÉCNICOS #
##########################

#CORRELACIÓN EMISIONES POR VISITA - RENDIMIENTO
cor.test(
  df$`Rendimiento en dispositivos móviles`,
  df$`Emisiones de CO2`,
  use = "complete.obs",
  method = "pearson"
)

cor.test(
  df$`Rendimiento en escritorio`,
  df$`Emisiones de CO2`,
  use = "complete.obs",
  method = "pearson"
)

#FIGURA 5 - SCATTER PLOT ENTRE RENDIMIENTO Y EMISIONES DE CO2 POR VISITA
g_movil <- ggplot(df, aes(x = `Rendimiento en dispositivos móviles`, y = `Emisiones de CO2`)) +
  geom_point(color = "#001489", size = 3, alpha = 0.7) +
  geom_smooth(method = "lm", se = FALSE, color = "red") +
  labs(
    x = "Rendimiento en dispositivos móviles",
    y = "Emisiones de CO₂ (g por visita)"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    axis.title = element_text(face = "bold")
  )

g_escritorio <- ggplot(df, aes(x = `Rendimiento en escritorio`, y = `Emisiones de CO2`)) +
  geom_point(color = "#001489", size = 3, alpha = 0.7) +
  geom_smooth(method = "lm", se = FALSE, color = "red") +
  labs(
    x = "Rendimiento en escritorio",
    y = "Emisiones de CO₂ (g por visita)"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    axis.title = element_text(face = "bold")
  )

figura5_rendimiento_emisiones <- g_movil + g_escritorio +
  plot_annotation(
    title = "Relación entre rendimiento web y emisiones de CO₂",
    theme = theme(
      plot.title = element_text(face = "bold", size = 16)
    )
  )

figura5_rendimiento_emisiones
ggsave("figura5.jpg", plot = figura5_rendimiento_emisiones, width = 8, height = 5, dpi = 300)

#CORRELACIÓN EMISIONES POR VISITA - PESO
cor.test(
  df$`Peso total de la página`,
  df$`Emisiones de CO2`,
  use = "complete.obs",
  method = "pearson"
)

#FIGURA 6 - SCATTER PLOT ENTRE PESO DE LA PÁGINA Y EMISIONES DE CO2 POR VISITA
figura6_peso_emisiones <- ggplot(df, aes(x = `Peso total de la página`, y = `Emisiones de CO2`)) +
  geom_point(color = "#001489", size = 3, alpha = 0.7) +
  geom_smooth(method = "lm", se = FALSE, color = "red") +

  labs(
    title = "Relación entre el peso total de la página y las\nemisiones de CO₂",
    x = "Peso total de la página (MB)",
    y = "Emisiones de CO₂ (g por visita)"
  ) +

  theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(face = "bold", hjust = 0),
    axis.title = element_text(face = "bold")
  )

figura6_peso_emisiones
ggsave("figura6.jpg", plot = figura6_peso_emisiones, width = 6, height = 6, dpi = 300)

#TIPO DE ENERGÍA UTILIZADA POR LOS HOSTINGS DE LOS SITIOS WEB
table(df$`Tipo de energía utilizada`)
