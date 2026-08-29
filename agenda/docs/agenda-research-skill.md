# Skill de Claude Code: `/agenda-research <event_id>`

Sigue el mismo patrón que `/draft`, `/recategorize`, `/feedback` que ya tenés.
Se agrega como comando de Claude Code en el repo (`.claude/commands/agenda-research.md`
o donde tengas configurados los otros).

## Qué hace

1. Busca el evento con ese `id` en `agenda_data.json` (o `manual_events.json`
   si es manual).
2. Junta contexto:
   - El propio `summary`/`detail_url` del evento.
   - Búsqueda web sobre el organizador, el tema y antecedentes (ediciones
     anteriores del mismo informe/reunión, si las hay).
   - Cruce con lo que ya tenés en el tracker: busca en `dashboard_data.json`,
     `gov_data.json`, `media_data.json`, `company_data.json` menciones
     recientes al mismo tema/empresa/organismo, para no arrancar de cero.
3. Redacta un resumen con esta estructura fija:
   - **De qué trata** (2-3 líneas)
   - **Por qué importa para retail UK ahora** (el ángulo, no solo el hecho)
   - **Actores para entrevistar / contactar** (nombres o roles concretos si
     se pueden inferir — vocero del organismo, retailer afectado, analista)
   - **Ángulos de historia posibles** (2-4 bullets, distintos entre sí — no
     variaciones del mismo ángulo)
   - **Background histórico** (qué pasó la vez anterior con este mismo tipo
     de evento/informe, si hay precedente)
4. Escribe el resultado en el campo `research_summary` del evento dentro de
   `agenda_data.json` (mismo archivo, edición in-place — no un archivo aparte,
   así el dashboard lo muestra directo al recargar).
5. Hace `git add agenda_data.json && git commit -m "research: <título corto>"`
   — sin push automático, igual que tus otros comandos, para que revises antes.

## Por qué in-place y no un archivo separado en `drafts/`

A diferencia de `/draft` (que genera una nota completa para publicar), esto es
research de apoyo que tiene que vivir pegado al evento en el calendario — el
valor está en verlo ahí cuando filtrás "a cubrir", no en tener otro archivo
para ir a buscar.

## Prompt base sugerido (ajustar tono/extensión con el tiempo, como hiciste con /draft y /feedback)

```
Sos un asistente de investigación para Francisco, periodista de datos en
Retail Week (retail UK). Te doy un evento de la agenda y necesito que armes
un brief corto para preparar la cobertura.

Evento: {title}
Fuente: {source} / Categoría: {category}
Fecha: {date} {time}
Resumen original: {summary}
Link: {detail_url}

Contexto adicional del tracker (últimas menciones relacionadas):
{contexto_cruzado}

Escribí en español rioplatense, formato markdown, con esta estructura exacta:
## De qué trata
## Por qué importa ahora
## Actores para entrevistar
## Ángulos de historia posibles
## Background histórico

Sé concreto y específico al sector retail UK. Si no hay suficiente
información para alguna sección, decilo en vez de inventar.
```
