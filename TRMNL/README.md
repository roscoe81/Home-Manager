# TRMNL "Northcliff Today" Display

This folder holds the render side of the [TRMNL](https://usetrmnl.com/) e-ink display that the
Home Manager drives. The **push** side lives in `Northcliff_Home_Manager_Gen.py` (the `TrmnlClass`),
which every ~15 minutes POSTs a `merge_variables` JSON object to the TRMNL custom-plugins API. This
markup is what turns that JSON into the 800x480 layout on the device.

## Files

| File | Purpose |
|------|---------|
| `bom_trmnl_template.html` | The plugin **Markup**. Paste its full contents into the Markup field of your TRMNL Private Plugin (Full layout). Special characters are written as HTML entities (`&deg;`, `&micro;`, `&mdash;`) so the file stays pure ASCII and can't be corrupted by an editor's encoding. |
| `bom_trmnl_preview.html` | A standalone browser mock-up with sample data. Open it in a browser at 100% zoom to iterate on the layout without pushing to TRMNL. Same markup as the template but with literal values instead of `{{ }}` placeholders. |

## How the data flows

```
BOM API + Enviro Monitors + Shelly + iCloud calendar
        |
        v
TrmnlClass._build_payload()  (Northcliff_Home_Manager_Gen.py)
        |  merge_variables JSON, POSTed to
        v
https://trmnl.com/api/custom_plugins/<plugin_uuid>
        |
        v
bom_trmnl_template.html  ->  rendered on the TRMNL device
```

## Field map - every `{{variable}}` and where TrmnlClass gets it

**Header / current conditions** (from the BOM `observations` and `forecasts/hourly` endpoints)

| Template variable | Source in TrmnlClass |
|---|---|
| `{{updated}}` | Local time the payload was built |
| `{{current_temp}}` | BOM observations `temp` |
| `{{description}}` | Forecast `icon_descriptor`, mapped to friendly text via `_describe()` |
| `{{feels_like}}` | BOM observations `temp_feels_like` |
| `{{wind}}` | BOM observations `wind.speed_kilometre` + `wind.direction` |
| `{{humidity}}` | BOM observations `humidity` |
| `{{rain_since_9am}}` | BOM observations `rain_since_9am` |

**Hourly rain forecast** (next 6 hours from `forecasts/hourly`, padded to 6)

| Template variable | Source |
|---|---|
| `{{h0_label}}` .. `{{h5_label}}` | Forecast hour label (from each entry's `time`) |
| `{{h0_temp}}` .. `{{h5_temp}}` | Forecast hour `temp` |
| `{{h0_chance}}` .. `{{h5_chance}}` | Forecast hour `rain.chance` (also drives the bar width) |
| `{{h0_amount}}` .. `{{h5_amount}}` | Forecast hour `rain.amount.min`-`max` in mm; shown only when not "0" |

**Today's events** (from the iCloud CalDAV calendar, first 5, padded to 5)

| Template variable | Source |
|---|---|
| `{{cal_0_time}}` .. `{{cal_4_time}}` | Event start time (or "All day") from `_get_calendar_events()` |
| `{{cal_0_title}}` .. `{{cal_4_title}}` | Event summary/title |

**Sensor panel** (from the Enviro Monitors, latest reading each)

| Template variable | Source (`enviro_monitor[...]` .latest) |
|---|---|
| `{{front_balcony_temp/humidity/dewpoint/barometer/pm25}}` | `Front Outdoor` monitor: Temp / Hum / Dew / Bar / P2.5 |
| `{{rear_balcony_temp/humidity/dewpoint/pm25}}` | `Outdoor` monitor: Temp / Hum / Dew / P2.5 |
| `{{rear_balcony_wind}}` | `_local_wind()` |
| `{{kitchen_temp/humidity/dewpoint/pm25}}` | `Indoor` monitor: Temp / Hum / Dew / P2.5 |

**Footer** (sun + electricity)

| Template variable | Source |
|---|---|
| `{{sunrise}}` / `{{sunset}}` | `_get_sun_times()` (astral, for the configured location) |
| `{{tariff_name}}` | `_get_tariff()` current period (Off Peak / Shoulder / Peak) |
| `{{tariff_rate}}` | Current tariff rate, formatted `c/kWh` |
| `{{electricity_kw}}` | Shelly total power / 1000 |
| `{{electricity_cost_ph}}` | `electricity_kw` x tariff rate, formatted `$/hr` |

## Pushed but not displayed

`TrmnlClass` also sends `station` (BOM station name), which this template does not currently show.
It's harmless spare data - TRMNL ignores any merge variable the markup doesn't reference. (The
`h*_amount` rain-in-mm fields used to be in this category until they were added to the forecast tiles.)

## Deploying a change

1. Edit `bom_trmnl_template.html`.
2. Copy its entire contents and paste into the plugin's Markup field on usetrmnl.com, then Save.
3. No change to the Pi is needed unless you introduce a **new** `{{variable}}` - in that case add the
   matching key to `TrmnlClass._build_payload()` so it gets pushed, or it will render blank.
