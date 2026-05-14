# Limburg.net Afvalophaling voor Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Toont het gewicht van je laatste huis-aan-huis afvalophaling (restfractie en GFT) van [Limburg.net](https://limburg.net) als sensoren in Home Assistant.

## Sensoren

Na installatie krijg je twee sensoren:

| Sensor | Beschrijving |
|--------|-------------|
| `sensor.limburg_net_restfractie_huisvuil` | Gewicht laatste restfractie ophaling (kg) |
| `sensor.limburg_net_gft_groente_fruit_tuin` | Gewicht laatste GFT ophaling (kg) |

Elke sensor heeft ook deze attributen:
- `datum` — datum en uur van de ophaling
- `betaald_bedrag` — kostprijs in euro
- `prijs_per_kg` — tarief per kg

## Installatie via HACS

1. Ga in Home Assistant naar **HACS → Integraties**
2. Klik rechtsboven op de **drie puntjes** → **Aangepaste repositories**
3. Voeg toe: `https://github.com/JOUW_GITHUB_NAAM/limburgnet-ha`
4. Categorie: **Integratie**
5. Klik **Toevoegen**
6. Zoek op **Limburg.net** en installeer
7. Herstart Home Assistant
8. Ga naar **Instellingen → Apparaten & Services → Integratie toevoegen**
9. Zoek op **Limburg.net** en volg de wizard

## Handmatige installatie

1. Download deze repository als ZIP
2. Pak uit en kopieer de map `custom_components/limburgnet` naar `/config/custom_components/limburgnet`
3. Herstart Home Assistant
4. Ga naar **Instellingen → Apparaten & Services → Integratie toevoegen → Limburg.net**

## Configuratie

| Veld | Verplicht | Beschrijving |
|------|-----------|-------------|
| E-mailadres | ✅ | Je e-mailadres voor limburg.net |
| Wachtwoord | ✅ | Je wachtwoord voor limburg.net |
| Locatie cookie | ❌ | Kopieer uit browser als login mislukt (zie hieronder) |

### Locatie cookie (optioneel)

Als de login niet werkt, heb je de `locatie` cookie nodig:

1. Open Chrome en ga naar [limburg.net](https://limburg.net)
2. Open DevTools (F12) → tabblad **Application**
3. Links: **Cookies** → `https://limburg.net`
4. Kopieer de waarde van de `locatie` cookie
5. Plak die in het **Locatie cookie** veld tijdens de setup

## Dashboard kaart

```yaml
type: entities
title: "♻️ Afvalophaling"
entities:
  - entity: sensor.limburg_net_restfractie_huisvuil
    name: Restfractie
  - entity: sensor.limburg_net_gft_groente_fruit_tuin
    name: GFT
```

## Problemen?

Open een [issue op GitHub](https://github.com/JOUW_GITHUB_NAAM/limburgnet-ha/issues).

## Licentie

MIT License — vrij te gebruiken en aan te passen.
