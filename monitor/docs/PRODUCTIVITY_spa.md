<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PRODUCTIVITY.md) | **🇪🇸 Español** | [🇫🇷 Français](PRODUCTIVITY_fra.md) | [🇮🇹 Italiano](PRODUCTIVITY_ita.md) | [🇩🇪 Deutsch](PRODUCTIVITY_deu.md) | [🇨🇳 简体中文](PRODUCTIVITY_zho.md) | [🇯🇵 日本語](PRODUCTIVITY_jpn.md) | [🇵🇹 Português](PRODUCTIVITY_por.md)

# Qué ahorra el monitor: una estimación y cómo medirlo

Esta guía explica las cifras del README. Son una estimación hecha con un modelo sencillo, no una medición tomada en tus repositorios. Mide las tuyas antes de fiarte de ellas.

## Las cifras

- Cerca del 85-95 % del tiempo que se dedica a vigilar el CI y a clasificar los fallos.
- Cerca del 15-25 % de la productividad global de un equipo, como consecuencia de la primera cifra.

## Cómo se construye la estimación

Tiempo ahorrado en una semana = la suma, sobre las tareas, de (veces por semana x minutos cada vez sin el monitor) x el ahorro de esa tarea. Las tareas son vigilar cada flujo de trabajo, decidir qué está de verdad en rojo, encontrar la causa de una ejecución fallida y enterarse a tiempo de un fallo. La estimación supone que:

1. Hay muchos repositorios con varios flujos de trabajo cada uno, así que mirarlos a mano obliga a abrir muchas páginas una y otra vez.
2. Sin el monitor, alguien revisa a mano las pestañas Actions y lee cada registro fallido para encontrar la causa. Con él, la página y las alertas ya dicen qué flujo está en rojo y por qué.
3. Hay fallos cada semana. Un equipo sin fallos no tiene nada que clasificar.
4. El ahorro cubre solo la vigilancia y la clasificación. Arreglar un fallo cuesta lo mismo con o sin el monitor y no se cuenta.

Las dos cifras solo concuerdan si vigilar y clasificar ocupan entre el 16 y el 29 % del tiempo de trabajo del equipo (0,15 / 0,95 a 0,25 / 0,85). Si en tu equipo ocupan menos, la ganancia global es menor.

## Cuándo ahorra menos

- Pocos repositorios o un solo flujo de trabajo: hay poco que vigilar.
- Hoy nadie vigila el CI a mano, o ya tienes alertas que nombran la causa.
- Las alertas no se leen. Leerlas también lleva tiempo, y el ahorro desaparece si se ignoran o se silencian sin motivo.

## Cómo medirlo en tu propio uso

1. Antes: durante una semana normal, anota cada vez que miras el CI a mano (minutos) y cada ejecución fallida que clasificas (minutos hasta saber la causa).
2. Después: repite las mismas notas durante una semana con el monitor abierto. La puntuación (tiempo de recuperación) y el libro de fallos (tendencia a 24 horas y 7 días) muestran si los fallos se cierran antes.
3. Para cada grupo, el ahorro es 1 - después / antes. Compáralo con el 85-95 %.
4. Para la ganancia global, divide las horas ahorradas entre el total de horas trabajadas esa semana. Compárala con el 15-25 %.

### Ejemplo con números inventados

Alguien dedica 20 minutos al día a mirar las pestañas Actions (100 minutos en una semana de cinco días) y clasifica 4 ejecuciones fallidas a la semana a 30 minutos cada una (120 minutos): 220 minutos en total. Con un ahorro del 85-95 %, quedan libres entre 187 y 209 minutos. Estos números son inventados para mostrar el cálculo; usa los tuyos.
