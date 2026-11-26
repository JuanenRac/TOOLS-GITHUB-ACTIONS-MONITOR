<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# GitHub Actions Monitor: che cos'è

[English](PRODUCT.md) · [Español](PRODUCT_spa.md) · [Français](PRODUCT_fra.md) · **Italiano** · [Deutsch](PRODUCT_deu.md) · [简体中文](PRODUCT_zho.md) · [日本語](PRODUCT_jpn.md) · [Português](PRODUCT_por.md)

## Scopo

Dire a una persona o a un piccolo gruppo, sul proprio computer, se la CI di tutti i repository è davvero verde, che cosa è fallito e perché, senza aprire ogni repository.

## Per chi è

- Chi ha molti repository (da pochi a diverse centinaia).
- Piccoli gruppi che condividono uno schermo o un pannello a parete.
- Strumenti di IA che lavorano su quei repository e devono leggere lo stato prima di fare push.

## Che cos'è e che cosa non è

È un programma locale che legge GitHub con il tuo token o la tua GitHub App. Non è un servizio ospitato, non è un sistema di CI e non sostituisce GitHub: osserva, e le poche azioni che scrivono restano spente finché non le attivi.

## Regole durature

- Non serve alcun pacchetto: il nucleo è la libreria standard di Python.
- Nulla lascia il computer se non lo dice un'impostazione visibile; non c'è telemetria.
- Ciò che non è stato controllato non appare mai verde.
- Tutto ciò che scrive su GitHub o sul sistema è spento per impostazione e chiede conferma.
- Ogni testo dell'interfaccia e della guida esiste in otto lingue.
- GPL-3.0-or-later.
