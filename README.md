# Limburg.net Waste Collection for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Displays waste collection **calendar**, weights, and account data from [Limburg.net](https://limburg.net) / Mijn limburg.net as sensors (and a calendar entity) in Home Assistant.

Account sensors (v0.2.1+) use the correct `/afvalbelasting/...` and `/saldo/...` API paths from limnet.js. Calendar support (v0.3.0+) uses the public Limburg.net afvalkalender API (no JWT).

## Sensors

### Collection calendar (v0.3.0+)

Configured during setup (or later via **Configure** / options) with gemeente → straat → huisnummer.

| Sensor | Description |
|--------|-------------|
| `sensor.limburg_net_volgende_ophaling` | Next pickup date (any fraction); attrs: `fractie`, `upcoming`, `next_by_fractie` |
| `sensor.limburg_net_volgende_huisvuil` | Next residual waste (huisvuil) date |
| `sensor.limburg_net_volgende_keukenafval` | Next kitchen waste date |
| `sensor.limburg_net_volgende_tuinafval` | Next garden waste date |
| `sensor.limburg_net_volgende_pmd` | Next PMD date |
| `sensor.limburg_net_volgende_papier` | Next paper & cardboard date |
| `sensor.limburg_net_volgende_textiel` | Next textile date |

Per-fraction sensors use `device_class: date`. Attributes include `datum`, `fractie`, `upcoming` (list). Fractions present depend on your municipality calendar.

### Calendar entity

| Entity | Description |
|--------|-------------|
| `calendar.limburg_net_ophalingen_…` | Upcoming house-to-house collections as calendar events |

### House-to-house collections (account / weights)

| Sensor | Description |
|--------|-------------|
| `sensor.limburg_net_restfractie_huisvuil` | Weight of last residual waste collection (kg) |
| `sensor.limburg_net_gft_groente_fruit_tuin` | Weight of last GFT collection (kg) |

Attributes per weight sensor: `datum`, `datum_iso`, `betaald_bedrag`, `prijs_per_kg`, `fractie`, `kosten_dit_jaar`, `recente_ledigingen` (max 12).

### Yearly costs (house-to-house)

| Sensor | Description |
|--------|-------------|
| `sensor.limburg_net_kosten_jaar_restfractie_huisvuil` | Residual waste cost this calendar year (EUR) |
| `sensor.limburg_net_kosten_jaar_gft_groente_fruit_tuin` | GFT cost this calendar year (EUR) |
| `sensor.limburg_net_kosten_jaar_totaal` | Combined house-to-house cost this year (EUR) |

### Billing / afvalbelasting / rekenstaat

| Sensor | Description |
|--------|-------------|
| `sensor.limburg_net_openstaand_bedrag` | Outstanding amount (EUR); attrs include recent movements/timeline |
| `sensor.limburg_net_huidig_saldo` | Current account balance (EUR) |
| `sensor.limburg_net_saldo_directe_inning` | Direct debit balance (EUR) |
| `sensor.limburg_net_aanslagbiljetten` | Count of aanslagbiljetten; attrs: betaald/onvolledig/overgedragen, recente, payment_reference |
| `sensor.limburg_net_kohier_huidig_jaar` | Kohier article amount(s) for current year (EUR) |

### Recycling park

Quota sensors (one per fraction, remaining quota) plus:

| Sensor | Description |
|--------|-------------|
| `sensor.limburg_net_parkbezoek_laatste_gewicht` | Last park visit weight (kg); attrs: recente_bezoeken |
| `sensor.limburg_net_parkbezoek_kosten_jaar` | Park visit costs this calendar year (EUR) |

### Slimmesorteerpunten

| Sensor | Description |
|--------|-------------|
| `sensor.limburg_net_slimmesorteerpunten_saldo` | Points balance; attrs: historiek, acties (may be empty) |

### Ophaling overzicht

| Sensor | Description |
|--------|-------------|
| `sensor.limburg_net_ophaling_overzicht` | Count of overview items; attrs: items |

Entity IDs may vary slightly depending on Home Assistant slugification of the Dutch names.

## Installation via HACS

1. Go to **HACS → Integrations** in Home Assistant
2. Click the **three dots** in the top right → **Custom repositories**
3. Add: `https://github.com/janmeermans/limburgnet-ha`
4. Category: **Integration**
5. Click **Add**
6. Search for **Limburg.net** and install
7. Restart Home Assistant
8. Go to **Settings → Devices & Services → Add Integration**
9. Search for **Limburg.net** and follow the wizard (login → gemeente → straat → huisnummer)

## Manual installation

1. Download this repository as a ZIP
2. Extract and copy the `custom_components/limburgnet` folder to `/config/custom_components/limburgnet`
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration → Limburg.net**

## Configuration

| Field | Required | Description |
|-------|----------|-------------|
| Email address | ✅ | Your limburg.net email address |
| Password | ✅ | Your limburg.net password |
| Gemeente | ✅ (calendar) | Municipality search (stored: `nis_code`, display name) |
| Straat | ✅ (calendar) | Street search (stored: `straat_nummer`, display name) |
| Huisnummer | ✅ (calendar) | House number |
| Toevoeging | ❌ | Optional house number suffix |

Existing installations can add or change the calendar address via **Settings → Devices & Services → Limburg.net → Configure**.

<img width="352" height="668" alt="image" src="https://github.com/user-attachments/assets/e3e6c16f-8259-4091-aabb-c36c6af1d983" />

## Issues?

Please open an [issue on GitHub](https://github.com/janmeermans/limburgnet-ha/issues).

## License

MIT License — free to use and modify.
