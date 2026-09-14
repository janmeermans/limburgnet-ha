# Limburg.net Waste Collection for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Displays waste collection data from [Limburg.net](https://limburg.net) as sensors in Home Assistant. Supports both house-to-house collections and recycling park quota.

## Sensors

### House-to-house collections

| Sensor | Description |
|--------|-------------|
| `sensor.limburg_net_restfractie_huisvuil` | Weight of last residual waste collection (kg) |
| `sensor.limburg_net_gft_groente_fruit_tuin` | Weight of last GFT collection (kg) |

Attributes per weight sensor:
- `datum` — date and time of the last collection
- `datum_iso` — ISO timestamp of the last collection
- `betaald_bedrag` — amount paid for the last collection (euro)
- `prijs_per_kg` — price per kg
- `fractie` — fraction key (`restfractie` / `gft`)
- `kosten_dit_jaar` — sum of paid amounts for this fraction in the current calendar year (euro)
- `recente_ledigingen` — up to 12 most recent emptyings (`datum_iso`, `gewicht_kg`, `betaald_bedrag`)

### Yearly costs (house-to-house)

| Sensor | Description |
|--------|-------------|
| `sensor.limburg_net_kosten_jaar_restfractie_huisvuil` | Residual waste cost total this calendar year (EUR) |
| `sensor.limburg_net_kosten_jaar_gft_groente_fruit_tuin` | GFT cost total this calendar year (EUR) |
| `sensor.limburg_net_kosten_jaar_totaal` | Combined house-to-house cost total this calendar year (EUR) |

These monetary sensors use `device_class: monetary`, unit `EUR`, and `state_class: total`. Values are derived from the full ledigingen history returned by Limburg.net (not only the last emptying).

### Recycling park quota

One sensor per fraction, showing the **remaining quota**:

| Sensor (example) | Description |
|--------|-------------|
| `sensor.limburg_net_quota_tuinafval` | Remaining garden waste quota (kg) |
| `sensor.limburg_net_quota_zuiver_steenpuin` | Remaining clean rubble quota (kg) |
| `sensor.limburg_net_quota_asbest` | Remaining asbestos quota (kg) |

The number of quota sensors depends on your municipality's configuration.

Attributes per quota sensor:
- `totaal_quota` — total quota
- `gebruikt` — amount already used
- `eenheid` — unit (kg, pieces, ...)
- `tarief_bedrag` — price per unit above quota
- `quotum_nummer` — quota number

## Installation via HACS

1. Go to **HACS → Integrations** in Home Assistant
2. Click the **three dots** in the top right → **Custom repositories**
3. Add: `https://github.com/janmeermans/limburgnet-ha`
4. Category: **Integration**
5. Click **Add**
6. Search for **Limburg.net** and install
7. Restart Home Assistant
8. Go to **Settings → Devices & Services → Add Integration**
9. Search for **Limburg.net** and follow the wizard

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

<img width="352" height="668" alt="image" src="https://github.com/user-attachments/assets/e3e6c16f-8259-4091-aabb-c36c6af1d983" />



## Issues?

Please open an [issue on GitHub](https://github.com/janmeermans/limburgnet-ha/issues).

## License

MIT License — free to use and modify.
