# ⚡ Quick Start - One-Click Setup

Dit document legt uit hoe je het trading systeem met **één druk op de knop** kunt opstarten.

## 🎯 Voor Windows Gebruikers (Makkelijkste Methode)

### Methode 1: Dubbel-klik de batch file ✨ **(AANBEVOLEN)**

1. **Zorg dat Docker Desktop draait** (whale icoontje in je systeem tray)

2. **Dubbelklik op** `START_SYSTEM.bat`

3. **Voer je API key in** wanneer gevraagd:
   - Gratis API key ophalen: https://www.alphavantage.co/support/#api-key
   - Plak de key en druk op Enter

4. **Wacht ~30 minuten** (eerste keer)
   - Het systeem download Docker images
   - Verzamelt 90 dagen aan data
   - Traint het ML model
   - Opent automatisch de UI in je browser

5. **Klaar!** 🎉
   - Dashboard: http://localhost:8501

---

### Methode 2: PowerShell Script

Als je meer controle wilt:

1. **Open PowerShell** in de project folder
   - Rechtermuisknop in File Explorer → "Open in Terminal"

2. **Run het setup script:**
   ```powershell
   .\setup.ps1
   ```

3. **Of met opties:**
   ```powershell
   # Quick mode (30 dagen data, ~15 minuten)
   .\setup.ps1 -Quick

   # API key meegeven
   .\setup.ps1 -ApiKey "ABC123XYZ456"

   # Alleen containers starten (zonder training)
   .\setup.ps1 -SkipTraining

   # Custom aantal dagen
   .\setup.ps1 -DataDays 60
   ```

---

### Methode 3: Python Script (Cross-platform)

Voor Windows, Mac, of Linux:

1. **Zorg dat Python 3.8+ is geïnstalleerd**

2. **Run:**
   ```bash
   python setup.py
   ```

3. **Of met opties:**
   ```bash
   # Quick mode
   python setup.py --quick

   # API key meegeven
   python setup.py --api-key "ABC123XYZ456"

   # Alleen containers starten
   python setup.py --skip-training

   # Custom aantal dagen
   python setup.py --data-days 60
   ```

---

## ⏱️ Hoe Lang Duurt Het?

### Eerste Keer (Volledige Setup)
| Stap | Tijd |
|------|------|
| Docker images downloaden | 3-5 min |
| Containers bouwen | 2-3 min |
| Data verzamelen (90 dagen) | 5-7 min |
| Features genereren | 2-3 min |
| Labels maken | 1 min |
| Model trainen | 10-15 min |
| **Totaal** | **~25-35 min** |

### Quick Mode (30 dagen data)
| Stap | Tijd |
|------|------|
| Setup + Data + Training | **~15-20 min** |

### Tweede Keer (Herstart)
| Stap | Tijd |
|------|------|
| Containers starten | **~30 seconden** |

---

## 🔧 Vereisten

Voordat je start, zorg dat je hebt:

### ✅ Docker Desktop
- Download: https://www.docker.com/products/docker-desktop/
- **Moet draaien** voordat je het script start
- Check: Whale icoontje in systeem tray (rechtsonder)

### ✅ Alpha Vantage API Key (Gratis)
- Ophalen: https://www.alphavantage.co/support/#api-key
- Vul je email in en krijg direct je key
- Gratis tier: 25 calls/dag (voldoende voor dit systeem)

### ✅ Minimaal 4GB RAM beschikbaar
- Check in Docker Desktop: Settings → Resources → Memory

### ✅ ~2GB vrije schijfruimte
- Voor Docker images, data, en models

---

## 📊 Wat Gebeurt Er Tijdens Setup?

Het script doet automatisch:

1. ✅ **Checkt of Docker draait**
2. ✅ **Vraagt je API key** (éénmalig)
3. ✅ **Maakt `.env` configuratie bestand**
4. ✅ **Maakt data/models/logs folders**
5. ✅ **Start 4 Docker containers:**
   - PostgreSQL database
   - FastAPI backend
   - Streamlit dashboard
   - Scheduler service
6. ✅ **Verzamelt EUR/USD data** (laatste 90 dagen)
7. ✅ **Genereert 150+ technische indicatoren**
8. ✅ **Maakt trading labels**
9. ✅ **Traint ensemble model** (XGBoost, LightGBM, RandomForest)
10. ✅ **Opent dashboard** in je browser

**Je hoeft niets te doen behalve wachten!** ☕

---

## 🌐 Na Setup - Toegang Tot Het Systeem

Als de setup compleet is, heb je toegang tot:

### 📈 Dashboard (Streamlit UI)
```
http://localhost:8501
```
- **Overview**: Systeemstatus, recente trades, equity curve
- **Trading**: Open posities, trade geschiedenis
- **Performance**: Win rate, drawdown, P&L charts
- **Model**: Predictions, SHAP features
- **System**: Controls, health checks

### 🔌 API Documentation
```
http://localhost:8000/docs
```
- Interactieve API documentatie
- Test endpoints direct in browser

### 💚 Health Check
```
http://localhost:8000/health
```
- Systeemstatus (database, API, scheduler)

---

## 🛑 Systeem Stoppen

### Windows (Batch File)
Dubbelklik op `STOP_SYSTEM.bat` (als beschikbaar)

### PowerShell / Terminal
```powershell
docker compose down
```

**Data blijft bewaard!** Bij herstart pakt het systeem verder waar het gebleven was.

---

## 🔄 Systeem Herstarten (Volgende Keer)

### Optie 1: Batch File
Dubbelklik opnieuw op `START_SYSTEM.bat` - duurt nu **~30 seconden**

### Optie 2: Docker Compose
```powershell
docker compose up -d
```

Geen `--build` nodig, tenzij je code hebt aangepast.

---

## 🐛 Problemen Oplossen

### ❌ "Docker is not running"
**Oplossing:**
1. Start Docker Desktop vanuit Start menu
2. Wacht tot whale icoontje steady is (niet animeren)
3. Probeer opnieuw

### ❌ "Port already in use"
**Oplossing:**
```powershell
# Vind wat de poort gebruikt
netstat -ano | findstr :8501

# Kill het process (vervang PID met nummer van hierboven)
taskkill /PID <PID> /F
```

### ❌ "API rate limit exceeded"
**Oplossing:**
- Alpha Vantage gratis tier: 25 calls/dag
- Wacht 24 uur en probeer opnieuw
- Of gebruik `--data-days 30` voor minder data

### ❌ "Out of memory"
**Oplossing:**
1. Docker Desktop → Settings → Resources
2. Verhoog Memory naar minimaal 4GB
3. Click "Apply & Restart"

### ❌ Scripts werken niet (PowerShell Execution Policy)
**Oplossing:**
```powershell
# Sta scripts toe voor deze sessie
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Dan run script
.\setup.ps1
```

### ❌ Database connection failed
**Oplossing:**
```powershell
# Herstart database
docker compose restart db

# Wacht 10 seconden
Start-Sleep -Seconds 10

# Herstart API
docker compose restart api
```

---

## 💡 Tips & Tricks

### Tip 1: Quick Mode Voor Testen
Als je het systeem gewoon wilt uitproberen:
```powershell
.\setup.ps1 -Quick
```
Dit gebruikt 30 dagen data i.p.v. 90, duurt ~15 minuten.

### Tip 2: Logs Bekijken
```powershell
# Alle logs live bekijken
docker compose logs -f

# Alleen API logs
docker compose logs -f api

# Alleen laatste 50 regels
docker compose logs --tail=50
```

### Tip 3: Container Status Checken
```powershell
docker compose ps
```
Alle services moeten "Up" en "healthy" zijn.

### Tip 4: Database Query's Uitvoeren
```powershell
# Open database console
docker compose exec db psql -U trader -d trading

# Bekijk trades
SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10;

# Exit
\q
```

### Tip 5: Background Mode
Om het systeem op de achtergrond te draaien zonder terminal open te houden:
```powershell
docker compose up -d
```

### Tip 6: Force Rebuild
Als je code hebt aangepast:
```powershell
docker compose up --build -d
```

---

## 📚 Meer Informatie

- **Volledige documentatie**: `README.md`
- **Windows specifiek**: `WINDOWS_SETUP.md`
- **Technische details**: Zie `/src` folders voor code

---

## 🆘 Hulp Nodig?

### Checklist Voor Troubleshooting:
1. ✅ Is Docker Desktop geïnstalleerd en aan het draaien?
2. ✅ Heb je een geldige Alpha Vantage API key?
3. ✅ Heb je minimaal 4GB RAM beschikbaar?
4. ✅ Is Windows Firewall niet blocking Docker?
5. ✅ Heb je de laatste versie van Docker Desktop?

### Log Files Checken:
```powershell
# System logs
docker compose logs

# Errors only
docker compose logs | Select-String -Pattern "ERROR"

# Specific service
docker compose logs api
docker compose logs db
docker compose logs ui
docker compose logs scheduler
```

---

## ✨ Samenvatting

| **Actie** | **Commando** |
|-----------|--------------|
| **Start systeem** (eerste keer) | Dubbelklik `START_SYSTEM.bat` |
| **Start systeem** (herstart) | `docker compose up -d` |
| **Stop systeem** | `docker compose down` |
| **Bekijk logs** | `docker compose logs -f` |
| **Check status** | `docker compose ps` |
| **Open dashboard** | http://localhost:8501 |

---

**Veel success met je ML Trading System!** 🚀📈

Als het systeem draait, zie je live trades, performance metrics, en model predictions in het dashboard. De scheduler zal automatisch elk uur nieuwe data verzamelen en predictions maken.
