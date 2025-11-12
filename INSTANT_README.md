# ⚡ INSTANT SETUP - ZERO VRAGEN!

## 🎯 Voor Jou Persoonlijk Gemaakt

Dit bestand (`INSTANT_SETUP.bat`) is **speciaal voor jou geconfigureerd** met:
- ✅ GitHub Repository: https://github.com/LucLHTC/Trade.git
- ✅ API Key: 1BYPHFL2ENMBITNZ (al ingevuld!)
- ✅ Alle settings: Vooraf geconfigureerd

**Je hoeft NIETS in te vullen - gewoon dubbelklikken en wachten!**

---

## 🚀 Hoe Te Gebruiken

### Stap 1: Zorg dat Docker Desktop draait
- Start Docker Desktop
- Wacht tot het whale icoontje rechtsonder steady is

### Stap 2: Dubbelklik INSTANT_SETUP.bat
- Dat is alles!
- **GEEN vragen** over API keys
- **GEEN configuratie** nodig
- Alles is al ingesteld!

### Stap 3: Wacht ~30 minuten
- Eerste keer duurt langer (Docker images downloaden)
- Je browser opent automatisch als het klaar is
- Dashboard: http://localhost:8501

---

## ⏱️ Wat Gebeurt Er?

Het script doet automatisch:

| Stap | Actie | Tijd |
|------|-------|------|
| 1 | OneDrive detectie & relocatie | ~30 sec |
| 2 | Docker cache cleaning | ~1 min |
| 3 | Configuratie aanmaken | ~5 sec |
| 4 | Docker containers bouwen | ~10 min |
| 5 | Data verzamelen (90 dagen EUR/USD) | ~5 min |
| 6 | Features genereren (150+ indicatoren) | ~2 min |
| 7 | Labels maken | ~1 min |
| 8 | Model trainen (XGBoost+LightGBM+RF) | ~10 min |
| 9 | Dashboard openen | ~1 sec |
| **Totaal** | | **~30 min** |

---

## 🔒 Security Note

**BELANGRIJK:** Dit bestand bevat je API key en moet **NIET** gedeeld worden!

- ✅ Het staat in `.gitignore` → wordt niet naar GitHub gepusht
- ✅ Je API key is gratis Alpha Vantage tier → geen groot risico
- ⚠️ Deel dit bestand nooit met anderen
- ⚠️ Als je de repository publiek maakt, check dat `INSTANT_SETUP.bat` niet mee gaat

---

## 📊 Na Setup

Als alles klaar is, heb je toegang tot:

### Dashboard (http://localhost:8501)
5 tabs met volledige functionaliteit:
- **📊 Overview**: Systeem status, equity curve, recente trades
- **💰 Trading**: Actieve posities, trade geschiedenis met filters
- **📈 Performance**: Win rate, drawdown, P&L distributie
- **🤖 Model**: Predictions, SHAP features, model metrics
- **⚙️ System**: Controls, health checks, scheduler status

### API Documentatie (http://localhost:8000/docs)
- Interactieve Swagger UI
- Test alle endpoints direct
- Zie request/response schemas

### Health Check (http://localhost:8000/health)
- Real-time systeem status
- Database connectie
- API beschikbaarheid
- Scheduler status

---

## 🛑 Systeem Stoppen

**Makkelijkste manier:**
Dubbelklik `STOP_SYSTEM.bat`

**Of via command line:**
```powershell
docker compose down
```

**Je data blijft veilig!** Bij herstart pakt het systeem verder waar het was.

---

## 🔄 Systeem Herstarten

**Tweede keer opstarten (zonder data setup):**
```powershell
docker compose up -d
```

Dit duurt **~30 seconden** i.p.v. 30 minuten!

**Of run INSTANT_SETUP.bat opnieuw:**
- Het detecteert bestaande data
- Slaat data verzameling over als niet nodig
- Start gewoon de containers

---

## 🐛 Problemen Oplossen

### "Docker is not running"
1. Start Docker Desktop
2. Wacht 2 minuten
3. Run INSTANT_SETUP.bat opnieuw

### "Port already in use"
Iets anders gebruikt poort 8501 of 8000:
```powershell
# Stop andere containers
docker compose down

# Of vind wat de poort gebruikt
netstat -ano | findstr :8501
```

### "API rate limit exceeded"
Alpha Vantage gratis tier: 25 calls/dag
- Wacht 24 uur
- Of pas de setup aan voor minder data

### "Build failed with I/O error"
1. Check disk space (minimaal 10GB)
2. Verhoog Docker memory naar 6GB
3. Restart Docker Desktop
4. Run opnieuw

### "Database not ready"
Gewoon even wachten (1-2 minuten extra):
```powershell
# Check status
docker compose ps

# Bekijk logs
docker compose logs db
```

---

## 💡 Handige Commando's

```powershell
# Bekijk logs (real-time)
docker compose logs -f

# Bekijk alleen API logs
docker compose logs -f api

# Check container status
docker compose ps

# Stop alles
docker compose down

# Start zonder rebuild
docker compose up -d

# Complete cleanup (verwijdert alles)
docker compose down -v
```

---

## 📚 Meer Informatie

- **Volledige docs**: README.md
- **Troubleshooting**: SETUP_FIX_README.md
- **Quick start**: QUICK_START.md
- **Windows guide**: WINDOWS_SETUP.md

---

## 🎉 Proficiat!

Je hebt nu een volledig werkend ML Trading System:
- ✅ Autonome data collection (elk uur)
- ✅ Real-time feature engineering
- ✅ Ensemble ML models
- ✅ Automated retraining bij drift
- ✅ Risk management
- ✅ Live dashboard
- ✅ Performance tracking

**Geniet van je trading systeem! 🚀📈**

---

## ⚠️ Disclaimer

Dit is een educatief/experimenteel trading systeem. Gebruik op eigen risico. Niet bedoeld voor live trading zonder grondige testing en validatie.
