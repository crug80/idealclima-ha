# Handoff & Stato Avanzamento — `idealclima-ha` (Custom Integration Home Assistant)

> Documento completo di contesto e memoria storica del progetto, da fornire all'agente AI nelle prossime sessioni di lavoro dentro il workspace `idealclima-ha`.

---

## 1. Panoramica e Obiettivo del Progetto

Realizzare l'integrazione Home Assistant **`idealclima`** per i ventilconvettori idronici **Ideal Clima** collegati via **Modbus TCP** o **Modbus RTU (RS-485)**:
- **Comfosplit IKARO HW**
- **Radiantore SKUDO DC Inverter** (con comando a bordo `TQCT02`)

L'integrazione segue le nuove linee guida ufficiali di Home Assistant per dispositivi Modbus ([Modbus internals](https://contributors.home-assistant.io/core/internals/modbus/)):
1. Libreria Python asincrona separata su PyPI (**`idealclima-modbus==0.2.1`**) basata su [`modbus-connection`](https://github.com/home-assistant-libs/modbus-connection).
2. Connessione Modbus gestita e condivisa da Home Assistant tramite `homeassistant.components.modbus.async_get_unit` (in `async_setup_entry`) e `async_get_temporary_unit` (nel `config_flow`).
3. Strategia di distribuzione: come raccomandato dalla documentazione ufficiale Home Assistant ([Does it belong in core?](https://contributors.home-assistant.io/core/integrations/create/#does-it-belong-in-core) e [Publish a custom integration](https://contributors.home-assistant.io/marketplace/guides/integrations/)), l'integrazione viene pubblicata inizialmente come **Custom Integration** nel repository **`https://github.com/crug80/idealclima-ha`** (per Marketplace / HACS e test su hardware reale), mantenendo però il codice al 100% conforme agli standard di qualità di `home-assistant/core` (Bronze/Platinum quality scale, strict typing, 100% test coverage).

---

## 2. Stato della Libreria PyPI (`idealclima-modbus==0.2.1`)

- **Repository GitHub**: `https://github.com/crug80/idealclima-modbus`
- **Versione pubblicata su PyPI**: **`0.2.1`** (dipendenza `modbus-connection>=4.12.7`)
- **Novità introdotte nella `0.2.1` durante questa sessione**:
  1. **`SkudoRunningMode(IntEnum)`** (`COOL = 0`, `HEAT = 1`) esposto su `SkudoReadings.running_mode` (input register **`46807`**).
     - Quando lo SKUDO è in modalità `AUTO` (`28302 = 0`), il registro `46807` indica quale regime (raffreddamento o riscaldamento) è attivo sulla macchina, permettendo all'entità `climate` di leggere/scrivere il setpoint automatico corrispondente (`28312` `target_temp_auto_cool` oppure `28313` `target_temp_auto_heat`).
     - Poiché `SkudoReadings` usa `max_gap = 1` sul range `46801–46810`, la lettura di `46807` avviene già nella singola richiesta Modbus `0x04` (saltando solo `46803`).
  2. **Ripristino simmetrico della velocità ventola su `IkaroHW.async_set_power`**:
     - Su IKARO HW lo spegnimento richiede di portare anche il registro ventola `28303` a `0` (`FanSpeed.OFF`).
     - `IkaroHW` memorizza automaticamente l'ultima velocità ventola attiva (`_last_fan_speed`, default `FanSpeed.AUTO = 6`) ogni volta che viene letta o impostata.
     - Quando si chiama `await ikaro.async_set_power(True, restore_fan=True)`, se la ventola era `OFF` (`0`) o `None`, la libreria ripristina automaticamente `_last_fan_speed` sul registro `28303`.

---

## 3. Lavoro Svolto in `home-assistant/core` e in `idealclima-ha`

Lo sviluppo e la validazione sono stati eseguiti inizialmente sul branch `idealclima` di `home-assistant/core` (commit `2f01cb014b4` e `f8b3bfd9699`) superando tutti i controlli `prek` (`ruff`, `mypy` con `.strict-typing`, `pylint-home-assistant`, `hassfest`, `codespell`, `prettier`), e poi esportati nella struttura standalone **`idealclima-ha`**.

### Struttura del repository `idealclima-ha`

```text
idealclima-ha/
├── .github/workflows/
│   └── validate.yaml                        # GitHub Action ufficiale home-assistant/actions/hassfest
├── custom_components/
│   └── idealclima/
│       ├── __init__.py                      # async_setup_entry (async_get_unit) e async_unload_entry
│       ├── binary_sensor.py                 # 5 binary sensor per SKUDO (valvola, stato, 3 allarmi)
│       ├── climate.py                       # Termostato principale per IKARO HW e SKUDO DC Inverter
│       ├── config_flow.py                   # Flusso UI TCP e Seriale RS-485 con blocco unit_id=15
│       ├── const.py                         # Costanti, IdealclimaModel, limiti unit_id 1..32 != 15
│       ├── coordinator.py                   # IdealclimaDataUpdateCoordinator (polling 15s)
│       ├── entity.py                        # Classe base IdealclimaEntity + _async_execute
│       ├── helpers.py                       # Factory create_modbus_params e create_device
│       ├── manifest.json                    # Manifest Custom Integration (version 0.1.0)
│       ├── number.py                        # 5 controlli numerici per SKUDO (timer, min/max temp, anti-spifferi)
│       ├── select.py                        # Selettore unità temperatura display per SKUDO (°C / °F)
│       ├── sensor.py                        # Temperatura ambiente (comune) + batteria, RPM, regime attivo (SKUDO)
│       ├── strings.json                     # Sorgente stringhe traduzioni
│       ├── switch.py                        # 9 interruttori per SKUDO (sleep + 8 parametri configurazione)
│       └── translations/
│           ├── en.json                      # Traduzione inglese compilata
│           └── it.json                      # Traduzione italiana completa
├── tests/
│   ├── __init__.py                          # Costanti mock e funzioni seed_ikaro / seed_skudo
│   ├── conftest.py                          # Fixture MockModbusConnection, mock_get_unit, init_integration
│   ├── test_binary_sensor.py                # Test binary_sensor (SKUDO e assenza su IKARO)
│   ├── test_climate.py                      # Test completi climate (IKARO e SKUDO, inclusi AUTO e fan restore)
│   ├── test_config_flow.py                  # Test config_flow (TCP, Seriale, indirizzo 15, errori, duplicati)
│   ├── test_init.py                         # Test setup, unload, parametri link e retry errori Modbus
│   ├── test_number.py                       # Test number (lettura, scrittura, errori, None)
│   ├── test_select.py                       # Test select (lettura, scrittura, errori, None)
│   ├── test_sensor.py                       # Test sensor (IKARO e SKUDO)
│   └── test_switch.py                       # Test switch (tutti i 9 switch SKUDO e errori scrittura)
├── HANDOFF.md                               # Questo documento
├── README.md                                # Documentazione utente e sviluppatore
├── hacs.json                                # Metadati HACS
└── pyproject.toml                           # Configurazione uv, pytest (100% coverage), ruff, mypy
```

---

## 4. Scelte Progettuali e Dettagli Tecnici Concordati

1. **Config Flow (`config_flow.py`)**:
   - Menu iniziale (`user`) con scelta tra **Modbus TCP (`tcp`)** e **Porta seriale (`serial`)**.
   - Scelta del modello tramite `SelectSelector` (`ikaro_hw` $\rightarrow$ *"Comfosplit IKARO HW"*, `skudo_dc_inverter` $\rightarrow$ *"Radiantore SKUDO DC Inverter"*).
   - Parametri TCP: `host`, `port` (default `502`), `unit_id` (`1..32`, default `1`).
   - Parametri Seriale: `device` (`SerialPortSelector`), `baudrate` (default `9600`, con `8N1` standard di `ModbusSerialParams`), `unit_id` (`1..32`, default `1`).
   - **Blocco indirizzo `15`**: l'indirizzo Modbus di fabbrica `15` consente solo il cambio indirizzo e non il normale funzionamento; se inserito, il form restituisce subito l'errore tradotto `factory_default_unit_id` sul campo `unit_id`.
   - **Anti-duplicati**: poiché i fancoil non hanno un registro col numero di serie hardware, si usa `self._async_abort_entries_match(...)` sulla combinazione `(type, host, port, unit_id)` per TCP o `(type, device, unit_id)` per Seriale.
   - **Sonda pre-configurazione (`_async_probe`)**: usa `async_get_temporary_unit`, chiama `await device.async_update()` e verifica anche `if not report.complete:` per intercettare errori su singoli blocchi di registri.
   - **Titolo ConfigEntry**: generato automaticamente come `"{Nome Modello} ({unit_id})"`, es. `"Radiantore SKUDO DC Inverter (21)"`.

2. **Coordinator (`coordinator.py`)**:
   - Un singolo `IdealclimaDataUpdateCoordinator` esegue `await self.device.async_update()` ogni **15 secondi** (`SCAN_INTERVAL = 15`), aggiornando sia `readings` (input registers `0x04`) sia `settings` (holding registers `0x03`), così Home Assistant rileva tempestivamente anche modifiche fatte dal pannello a bordo macchina o dal telecomando IR.
   - Dopo ogni comando di scrittura (`_async_execute` in `entity.py`), viene chiamato `await self.coordinator.async_refresh()` (non `async_request_refresh()`, per evitare il ritardo di 10s del debouncer in caso di comandi ravvicinati).

3. **Piattaforma `climate.py`**:
   - **Precisione e passo temperatura**: **`0.5 °C`** (`PRECISION_HALVES`), fedele alla specifica dei manuali Ideal Clima.
   - **Range temperatura (`min_temp` / `max_temp`)**:
     - Default da manuale: **`18.0 °C – 30.0 °C`**.
     - Su SKUDO vengono letti dinamicamente i registri `min_target_temp` (`28309`) e `max_target_temp` (`28308`), con fallback a `18.0` / `30.0 °C`.
   - **Modalità HVAC (`hvac_mode`)**:
     - Se `device.settings.power` (`28301`) è `False` $\rightarrow$ restituisce sempre `HVACMode.OFF` (ignorando `28302` che da spento può restituire `0`).
     - Se `power` è `True` $\rightarrow$ mappa `28302`:
       - IKARO: `COOL (1)`, `DRY (2)`, `FAN_ONLY (3)`, `HEAT (4)`, `OFF (0)`.
       - SKUDO: `AUTO (0)`, `COOL (1)`, `DRY (2)`, `FAN_ONLY (3)`, `HEAT (4)`.
     - Quando si imposta una modalità attiva da spento, invia sia `async_set_mode(...)` sia `async_set_power(True)`.
   - **Velocità ventola (`fan_mode`, registro `28303`)**:
     - Modalità selezionabili: `["super_silence", "low", "medium", "high", "auto"]` (`1, 2, 3, 4, 6`), con `"super_silence"` tradotto in `strings.json` / `en.json` / `it.json`.
     - Se il registro `28303` vale `0` (`FanSpeed.OFF`, es. a macchina spenta su IKARO), `fan_mode` restituisce `FAN_OFF` (`"off"`).
   - **Setpoint temperatura (`native_target_temperature` e `async_set_temperature`)**:
     - In `COOL` e `DRY` $\rightarrow$ legge/scrive `target_temp_cool` (`28310`).
     - In `HEAT` $\rightarrow$ legge/scrive `target_temp_heat` (`28311`).
     - In `AUTO` (solo SKUDO) $\rightarrow$ controlla `device.readings.running_mode` (`46807`):
       - se `SkudoRunningMode.HEAT (1)` $\rightarrow$ legge/scrive `target_temp_auto_heat` (`28313`);
       - se `SkudoRunningMode.COOL (0)` $\rightarrow$ legge/scrive `target_temp_auto_cool` (`28312`).
     - In `OFF` e `FAN_ONLY` $\rightarrow$ `native_target_temperature` restituisce `None`.

4. **Organizzazione delle altre entità nella scheda Dispositivo**:
   - **Controlli principali**: `climate`, `switch.sleep` (`28305`), `number.timer_off_hours` (`28306`), `number.timer_on_hours` (`28307`).
   - **Configurazione (`EntityCategory.CONFIG`)**: gli 8 switch di configurazione SKUDO (`key_lock`, `anti_draft_enabled`, `super_silence_enabled`, `valve_present`, `key_lock_enabled`, `remote_enabled_with_key_lock`, `password_enabled`, `fan_intermittent`), i 3 limiti numerici temperatura (`max_target_temp`, `min_target_temp`, `anti_draft_threshold`) e il selettore `temperature_unit` (`28319`).
   - **Sensori**: `ambient_temperature` (`46801`, comune a entrambi), più su SKUDO `coil_temperature` (`46802`), `fan_rpm` (`46804`), `running_mode` (`46807`) e il binary sensor `valve_command` (`46805`).
   - **Diagnostica (`EntityCategory.DIAGNOSTIC`)**: `power_state` (`46806`) e i 3 allarmi con `BinarySensorDeviceClass.PROBLEM` (`motor_alarm` `46808`, `ambient_sensor_alarm` `46809`, `coil_sensor_alarm` `46810`).

---

## 5. Risultati Test Attuali

Tutti i **76 test unitari** in `tests/` passano al **100.00% di coverage** (`443/443` istruzioni coperte su tutti i 12 moduli in `custom_components/idealclima/`).

---

## 6. Prossimi Passi Operativi (nella nuova sessione in `idealclima-ha`)

1. **Setup ambiente virtuale in WSL (`~/idealclima-ha`)**:
   ```bash
   uv venv --python 3.14
   uv pip install -e ../core -e ../core/packages/pytest-homeassistant
   uv pip install -r ../core/requirements_test.txt
   uv pip install idealclima-modbus==0.2.1 modbus-connection[tmodbus]==4.12.7 pymodbus==3.13.1 aiousbwatcher==1.1.2 aiohasupervisor==0.11.0 ruff==0.17.4
   ```
2. **Verifica comandi nel nuovo workspace**:
   ```bash
   uv run --no-sync pytest
   uv run --no-sync ruff check .
   uv run --no-sync mypy custom_components tests
   ```
3. **Inizializzazione repository Git e pubblicazione su GitHub (`crug80/idealclima-ha`)**:
   ```bash
   git init -b main
   git add .
   git commit -m "Initial release of Ideal Clima custom integration (0.1.0)"
   gh repo create crug80/idealclima-ha --public --source=. --remote=origin --push
   ```
4. **Test su Hardware Reale (IKARO HW e SKUDO DC Inverter)**:
   - Installare `custom_components/idealclima` sull'istanza Home Assistant collegata ai ventilconvettori reali (es. *"Skudo 1000 Soggiorno"*, `unit_id = 21`).
   - Verificare lettura registri, cambio modalità, velocità ventola, setpoint e parametri di configurazione.
   - Creare tag e release GitHub `0.1.0` per la distribuzione su Marketplace / HACS.
