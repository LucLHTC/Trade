# 🎯 START HERE - Ultra Simple Setup

## ⚡ HAD JE PROBLEMEN MET ANDERE SCRIPTS?

**Gebruik dit!** → `START_HERE.bat`

Dit is de **meest simpele versie** zonder fancy functies die errors kunnen veroorzaken.

---

## 🚀 Hoe Te Gebruiken

### Stap 1: Zorg dat Docker Desktop draait
- Start Docker Desktop vanuit Start menu
- Wacht tot whale icoontje rechtsonder steady is (niet meer animeren)

### Stap 2: Dubbelklik START_HERE.bat
- Gewoon dubbelklikken!
- **API key is al ingevuld** (1BYPHFL2ENMBITNZ)

### Stap 3: Volg De Stappen
Het script vraagt je:

**1. "Did you restart Docker Desktop? (Y/N)"**
- Type **Y** en druk Enter
- Dit zorgt voor de beste resultaten

### Stap 4: Wacht ~30 Minuten
Het script toont duidelijk wat het doet:
```
[*] = Bezig...
[OK] = Gelukt!
[WARN] = Waarschuwing (meestal niet erg)
[ERROR] = Fout (moet gefixt worden)
```

### Stap 5: Dashboard Opent Automatisch
Als alles klaar is:
- Browser opent naar http://localhost:8501
- Je ziet het trading dashboard! 🎉

---

## 📋 Wat Het Script Doet

| Stap | Actie | Tijd | Wat Je Ziet |
|------|-------|------|-------------|
| 0 | Detecteert OneDrive locatie | ~5 sec | `[!]` of `[OK]` |
| 1 | Checkt of Docker draait | ~5 sec | `[OK]` 3x |
| 2 | Cleaned Docker cache | ~1 min | `[*] Cleaning...` |
| 3 | Maakt .env configuratie | ~1 sec | `[OK]` |
| 4 | Maakt folders | ~1 sec | `[OK]` |
| 5 | Bouwt Docker containers | ~10 min | `[*] Building...` |
| 6 | Wacht op services | ~1 min | `[OK]` 2x |
| 7 | Verzamelt data | ~5 min | `[1/4]` |
| 7 | Genereert features | ~2 min | `[2/4]` |
| 7 | Maakt labels | ~1 min | `[3/4]` |
| 7 | Traint model | ~10 min | `[4/4]` |
| 8 | Opent browser | ~1 sec | Dashboard! |

**Totaal: ~30 minuten**

---

## ✅ Verschil Met Andere Scripts

| Script | Complexiteit | Kans op Errors | Aanbevolen Voor |
|--------|--------------|----------------|-----------------|
| `START_HERE.bat` ⭐ | Heel simpel | Laag | **Iedereen!** |
| `SETUP_FIX.bat` | Medium | Medium | Had problemen |
| `START_SYSTEM.bat` | Medium | Medium | Eerste poging |
| `setup-simple.ps1` | Simpel | Laag | PowerShell users |
| `setup-fixed.ps1` | Complex | Hoog | Experts |

**Conclusie: Gebruik START_HERE.bat!** ⭐

---

## 🐛 Troubleshooting

### "Docker is not running"
**Oplossing:**
1. Kijk rechtsonder in taskbalk
2. Zie je geen whale icoontje? → Start Docker Desktop
3. Wacht 2 minuten
4. Run START_HERE.bat opnieuw

---

### "Failed to start containers"
**Oplossing:**

**Check disk space:**
```powershell
Get-PSDrive C
```
Je hebt minimaal 10GB vrij nodig.

**Verhoog Docker memory:**
1. Docker Desktop → Settings → Resources
2. Memory → Verhoog naar 6GB
3. Apply & Restart
4. Wacht 2 minuten
5. Run START_HERE.bat opnieuw

---

### "Data collection had issues"
**Mogelijke oorzaken:**
- API rate limit (gratis tier: 25 calls/dag)
- Internet verbinding
- Alpha Vantage servers

**Oplossing:**
Als model training OK is, dan heb je genoeg data. Anders:
```powershell
# Ga naar C:\Trading (als script je daar naartoe verplaatst heeft)
cd C:\Trading

# Of blijf waar je bent

# Run data collection handmatig
docker compose exec api python -c "from src.data_collection.forex import ForexCollector; c = ForexCollector(); c.fetch_and_store('EURUSD', days=90)"
```

---

### "Model training had issues"
**Check of je genoeg data hebt:**
```powershell
docker compose exec api python -c "from src.features.manager import FeatureManager; m = FeatureManager(); features = m.load_features('EURUSD'); print(f'Rows: {len(features)}')"
```

Je hebt minimaal ~1000 rijen nodig voor training.

---

### Script Loopt Vast
**Oplossing:**
1. Druk **Ctrl + C** om te stoppen
2. Run dit:
   ```powershell
   docker compose down
   ```
3. Sluit Docker Desktop volledig
4. Start Docker Desktop opnieuw
5. Wacht 2 minuten
6. Run START_HERE.bat opnieuw

---

## 📍 Waar Draait Alles?

Na setup draait het systeem vanuit:
- Als je in OneDrive was: `C:\Trading\`
- Anders: Je originele folder

**Check met:**
```powershell
docker compose ps
```

Je moet 4 containers zien:
- trading_db (database)
- trading_api (backend)
- trading_ui (dashboard)
- trading_scheduler (automatisering)

---

## 🔄 Systeem Herstarten (Latere Keren)

**Je hoeft START_HERE.bat niet opnieuw te runnen!**

Gewoon:
```powershell
docker compose up -d
```

Dit start alles in **~30 seconden** (geen data/training meer nodig).

---

## 🛑 Systeem Stoppen

**Makkelijkste:**
Dubbelklik `STOP_SYSTEM.bat`

**Of:**
```powershell
docker compose down
```

Je data blijft veilig!

---

## 💡 Handige Commands

```powershell
# Check status
docker compose ps

# Bekijk logs (live)
docker compose logs -f

# Alleen API logs
docker compose logs -f api

# Stop alles
docker compose down

# Start zonder rebuild
docker compose up -d

# Complete cleanup (VERWIJDERT DATA!)
docker compose down -v
```

---

## 🎉 Success!

Als je dit ziet:
```
[OK] Model trained!

========================================================================
                    SETUP COMPLETE!
========================================================================

Dashboard:  http://localhost:8501
```

**Dan werkt alles!** 🎉

Je browser opent automatisch naar het dashboard.

---

## 📊 Dashboard Tabs

Na setup heb je toegang tot:

1. **📊 Overview**
   - Systeem health
   - Recent trades
   - Equity curve

2. **💰 Trading**
   - Open positions
   - Trade history
   - P&L breakdown

3. **📈 Performance**
   - Win rate
   - Drawdown chart
   - Performance metrics

4. **🤖 Model**
   - Predictions
   - SHAP features
   - Model stats

5. **⚙️ System**
   - Controls
   - Scheduler status
   - Configuration

---

## 🔒 Security

Je API key (1BYPHFL2ENMBITNZ) is:
- ✅ Gratis Alpha Vantage tier
- ✅ Beperkt tot 25 calls/dag
- ✅ Geen financieel risico
- ✅ Kan altijd nieuwe maken op alphavantage.co

Dit script wordt **niet** gecommit naar GitHub (staat in .gitignore).

---

## 📞 Nog Problemen?

Als START_HERE.bat ook niet werkt:

**Check dit:**
1. Docker Desktop versie → Update naar latest
2. Windows versie → Minimaal Windows 10
3. PowerShell versie → Run `$PSVersionTable`
4. Disk space → Minimaal 10GB vrij
5. RAM → Docker heeft minimaal 4GB nodig

**Manual fallback:**
```powershell
# Stop alles
docker compose down

# Clean Docker
docker system prune -a -f --volumes

# Maak .env
Copy-Item .env.example .env
notepad .env  # Voeg API key 1BYPHFL2ENMBITNZ toe

# Start containers
docker compose up -d

# Wacht 2 minuten, dan:
# Open http://localhost:8501
```

---

**Veel success! 🚀**

Dit script is gemaakt om **gegarandeerd** te werken, zonder fancy features die errors kunnen geven.
