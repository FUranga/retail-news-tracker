# Módulo 7 — Agenda

## Qué es esto

Scaffolding completo del módulo de Agenda para el retail-news-tracker:
calendario de eventos relevantes (estadísticas, informes, reuniones
públicas, earnings/AGM, eventos sectoriales) para UK retail, con vista de
2 semanas navegable, filtro "a cubrir", carga manual y research on-demand
vía Claude Code.

## Qué está listo para usar tal cual

- `agenda_schema.py` — schema de evento común.
- `agenda_scraper.py` — orquestador (corre las 5 fuentes, mergea con
  manuales, preserva `to_cover`/`research_summary` entre corridas).
- `manual_events.json` + `add_manual_event.py` — carga manual, andando.
- `dashboard/agenda.js` + `agenda_tab.html` — UI completa: 2 semanas con
  flechas, toggle Todos/A cubrir, cards con inscripción/agenda/materiales,
  botón de research.
- `docs/agenda-research-skill.md` — spec del comando `/agenda-research`
  para Claude Code.

## Qué hay que verificar/ajustar antes de correr en serio

1. **`agenda_ons.py`** — el más sólido de los 5, endpoints RSS/iCal
   confirmados en vivo. Debería funcionar con mínimos ajustes.
2. **`agenda_parliament.py`** — API real (`committees-api.parliament.uk`)
   confirmada, pero no pude verificar el shape exacto de la respuesta JSON
   ni los `committee_id` reales desde acá. Primer paso: correr
   `_resolve_committee_id()` suelto y ajustar nombres de campo según lo que
   devuelva.
3. **`agenda_lse_earnings.py`** — asume una estructura de `dashboard_data.json`
   razonable pero no confirmada; ajustar nombres de campo (`headline`,
   `body`, `company`) a como esté realmente en tu repo. Es el que más valor
   da con menos esfuerzo porque no pega a ninguna API nueva.
4. **`agenda_company_ir.py`** — el más ruidoso por diseño (Google News sin
   estructura de "evento"). Lo dejé marcando `needs_confirmation: true` en
   cada resultado — capaz conviene, al menos al principio, que este sea el
   candidato a NO automatizar del todo y quede como sugerencia para
   confirmar manual con un click, no como fuente que entra directo al
   calendario.
5. **`agenda_brc.py`** — selectores CSS son un placeholder razonable, no
   verificado contra el HTML real (el dominio no está en la whitelist de
   red desde acá). Correr una vez con un `print(resp.text[:5000])` y
   ajustar.

## Integración al repo existente

- Copiar `agenda_scraper.py`, `agenda_config.json`, `agenda_schema.py`,
  `manual_events.json`, `add_manual_event.py` y la carpeta `scrapers/` a la
  raíz del repo (o a un subdirectorio `agenda/`, ajustando los imports).
- Sumar un step de GitHub Actions similar a los otros módulos, corriendo
  `python agenda_scraper.py` 1 vez/día.
- Pegar `dashboard/agenda_tab.html` en el HTML del dashboard donde están los
  otros tabs, y cargar `dashboard/agenda.js` + `agenda_data.json` como
  `window.agendaData`.
- Agregar el comando `/agenda-research` a Claude Code siguiendo
  `docs/agenda-research-skill.md`.

## Próxima tanda de fuentes (no incluidas ahora)

Think tanks, sindicatos, ferias (MAPIC, NRF, Retail Week Live, World Retail
Congress — probablemente mejor como lista fija anual que como scraper),
organismos internacionales (OCDE, FMI).
