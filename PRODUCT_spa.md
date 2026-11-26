<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# GitHub Actions Monitor: qué es

[English](PRODUCT.md) · **Español** · [Français](PRODUCT_fra.md) · [Italiano](PRODUCT_ita.md) · [Deutsch](PRODUCT_deu.md) · [简体中文](PRODUCT_zho.md) · [日本語](PRODUCT_jpn.md) · [Português](PRODUCT_por.md)

## Propósito

Decir a una persona o a un equipo pequeño, en su propio equipo, si la CI de todos sus repositorios está de verdad en verde, qué ha fallado y por qué, sin abrir cada repositorio.

## Para quién es

- Dueños de muchos repositorios (desde unos pocos hasta varios cientos).
- Equipos pequeños que comparten una pantalla o un panel de pared.
- Herramientas de IA que trabajan en esos repositorios y necesitan leer el estado antes de subir cambios.

## Qué es y qué no es

Es un programa local que lee GitHub con tu propio token o GitHub App. No es un servicio alojado, no es un sistema de CI y no sustituye a GitHub: observa, y las pocas acciones que escriben están apagadas hasta que las enciendas.

## Reglas duraderas

- No hace falta ningún paquete: el núcleo es la biblioteca estándar de Python.
- Nada sale de tu equipo salvo que un ajuste visible lo diga; no hay telemetría.
- Lo que no se ha comprobado nunca se muestra en verde.
- Todo lo que escribe en GitHub o en el sistema está apagado por defecto y pregunta antes de actuar.
- Cada texto de la interfaz y de la ayuda existe en ocho idiomas.
- GPL-3.0-or-later.
