# Correr parado en la raíz del repo (news tracker):
#   powershell -ExecutionPolicy Bypass -File check_agenda.ps1
# o simplemente pegar todo el contenido en la terminal.

Write-Host "=== Verificando archivos ===" -ForegroundColor Cyan

$archivos = @(
    "dashboard.html",
    "agenda_data.json",
    "agenda\agenda_scraper.py",
    "agenda\agenda_config.json",
    "agenda\agenda_schema.py",
    "agenda\agenda_ics.py",
    "agenda\add_manual_event.py",
    "agenda\manual_events.json",
    "agenda\scrapers\agenda_ons.py",
    "agenda\scrapers\agenda_parliament.py",
    "agenda\scrapers\agenda_lse_earnings.py",
    "agenda\scrapers\agenda_company_ir.py",
    "agenda\scrapers\agenda_brc.py",
    ".github\workflows\agenda_scraper.yml"
)

foreach ($f in $archivos) {
    if (Test-Path $f) {
        Write-Host "OK    $f" -ForegroundColor Green
    } else {
        Write-Host "FALTA $f" -ForegroundColor Red
    }
}

Write-Host "`n=== Verificando contenido clave (versiones correctas) ===" -ForegroundColor Cyan

$checks = @(
    @{file="agenda\agenda_config.json"; pattern='"business_and_trade": 365'; desc="committee_ids de Parlamento cargados"},
    @{file="agenda\agenda_config.json"; pattern='"output_file": "\.\./agenda_data\.json"'; desc="ruta de salida corregida"},
    @{file="agenda\agenda_scraper.py"; pattern='generate_ics'; desc="conectado a agenda_ics.py"},
    @{file="agenda\agenda_scraper.py"; pattern='encoding="utf-8"'; desc="fix de encoding aplicado"},
    @{file="agenda\scrapers\agenda_parliament.py"; pattern='startDate'; desc="usa el campo de fecha real"},
    @{file="agenda\scrapers\agenda_parliament.py"; pattern='\[debug\]'; desc="NO deberia tener prints de debug"; expectAbsent=$true},
    @{file="agenda\scrapers\agenda_lse_earnings.py"; pattern='Path\("\.\./dashboard_data\.json"\)'; desc="ruta de LSE corregida"},
    @{file="agenda\scrapers\agenda_brc.py"; pattern='needs_confirmation'; desc="version de fechas calculadas (no HTML scraping)"},
    @{file="dashboard.html"; pattern='gcalUrl'; desc="link de Google Calendar presente"},
    @{file="dashboard.html"; pattern='agenda-toolbar'; desc="tab Agenda integrado"}
)

foreach ($c in $checks) {
    if (-not (Test-Path $c.file)) {
        Write-Host "SKIP  $($c.desc) -- archivo no existe: $($c.file)" -ForegroundColor Yellow
        continue
    }
    $found = Select-String -Path $c.file -Pattern $c.pattern -Quiet
    $expectAbsent = $c.ContainsKey("expectAbsent") -and $c.expectAbsent
    if ($expectAbsent) {
        if (-not $found) { Write-Host "OK    $($c.desc)" -ForegroundColor Green }
        else { Write-Host "OJO   $($c.desc) -- todavia presente" -ForegroundColor Red }
    } else {
        if ($found) { Write-Host "OK    $($c.desc)" -ForegroundColor Green }
        else { Write-Host "FALTA $($c.desc)" -ForegroundColor Red }
    }
}

Write-Host "`n=== Listo. Si todo dice OK en verde, esta listo para git add / commit / push ===" -ForegroundColor Cyan
