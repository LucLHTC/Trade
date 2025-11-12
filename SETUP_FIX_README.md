# 🔧 AUTOMATISCHE FIX & SETUP

## ⚡ Gebruik Dit Als Je Problemen Had!

Dit script lost **automatisch** deze problemen op:
- ✅ OneDrive locatie (veroorzaakt Docker I/O errors)
- ✅ Docker cache problemen
- ✅ Container build fouten
- ✅ Configuratie issues

---

## 🚀 Hoe Te Gebruiken

### Stap 1: Zorg dat Docker Desktop draait
- Kijk rechtsonder bij de klok
- Zie je het whale icoontje? → Good!
- Zie je het niet? → Start Docker Desktop vanuit Start menu

### Stap 2: Dubbelklik SETUP_FIX.bat
- Dat is alles!
- Het script vraagt je om:
  - Je API key (gratis van alphavantage.co)
  - Of je Docker Desktop wilt herstarten (aangeraden)
  - Een paar Y/N vragen

### Stap 3: Wacht
- Eerste keer: ~25-35 minuten
- Het script laat precies zien wat het doet
- Je browser opent automatisch als alles klaar is

---

## 🎯 Wat Doet Dit Script?

### Automatische Fixes:

**1. OneDrive Detectie**
- Checkt of je project in OneDrive staat
- Kopieert automatisch naar `C:\Trading`
- Dit voorkomt Docker I/O errors

**2. Docker Cleaning**
- Stopt oude containers
- Ruimt cache op
- Voorkomt build errors

**3. Docker Restart Check**
- Vraagt of je Docker wilt herstarten
- Geeft duidelijke instructies
- Wacht tot Docker weer klaar is

**4. Slimme Setup**
- Maakt automatisch alle configuratie
- Bouwt containers
- Wacht tot alles ready is
- Verzamelt data
- Traint model
- Opent dashboard

### Wat Zie Je:

```
✓ Groene vinkjes = Stap succesvol
✗ Rode kruisjes = Probleem (met uitleg)
ℹ Blauwe info = Wat er gebeurt
⚠ Gele waarschuwing = Let op (maar geen blocker)
```

---

## 🕐 Tijdsindicatie

| Wat | Duur |
|-----|------|
| OneDrive detectie & kopiëren | ~30 sec |
| Docker cleaning | ~1 min |
| Docker restart (optioneel) | ~2 min |
| Containers bouwen | ~10 min |
| Data verzamelen | ~5 min |
| Features genereren | ~2 min |
| Labels maken | ~1 min |
| Model trainen | ~10 min |
| **Totaal** | **~30 min** |

---

## ❓ Veelgestelde Vragen

### Moet ik het oude START_SYSTEM.bat script verwijderen?
Nee, dat mag blijven staan. `SETUP_FIX.bat` is een verbeterde versie die problemen oplost.

### Wat als het mijn project kopieert naar C:\Trading?
Dat is goed! OneDrive veroorzaakt Docker problemen. Na de setup kun je:
- De OneDrive versie verwijderen
- Of beide houden (maar gebruik C:\Trading voor het systeem)

### Kan ik de locatie C:\Trading aanpassen?
Ja, maar dan moet je het PowerShell script bewerken. `C:\Trading` is veilig en werkt gegarandeerd.

### Wat als Docker niet start?
Het script wacht en geeft je tijd om Docker handmatig te starten. Start gewoon Docker Desktop en druk Enter.

### Kan ik de setup stoppen en later hervatten?
Ja! Druk Ctrl+C om te stoppen. Run het script opnieuw om verder te gaan vanaf waar je was.

### Hoeveel disk space heb ik nodig?
Minimaal **10GB vrij**. Check met: `Get-PSDrive C` in PowerShell.

---

## 🐛 Troubleshooting

### "Docker is not running"
**Oplossing:**
1. Open Docker Desktop vanuit Start menu
2. Wacht 2 minuten tot het volledig gestart is
3. Run `SETUP_FIX.bat` opnieuw

### "Failed to copy project"
**Oplossing:**
1. Sluit alle programma's die bestanden in de project folder gebruiken
2. Probeer opnieuw
3. Of kopieer handmatig naar C:\Trading en run script daar

### "Build failed with I/O error"
**Oplossing:**
1. Check disk space: `Get-PSDrive C`
2. Sluit OneDrive sync tijdelijk
3. Verhoog Docker memory naar 6GB (Docker Desktop → Settings → Resources)
4. Herstart Docker Desktop volledig
5. Run script opnieuw

### "API rate limit exceeded"
**Oplossing:**
- Alpha Vantage gratis tier: 25 calls/dag
- Wacht 24 uur
- Of gebruik `-Quick` mode: `.\setup-fixed.ps1 -Quick` (30 dagen data)

### "Database not ready"
**Oplossing:**
Het script vraagt of je door wilt gaan. Zeg ja (Y), meestal lost het zich op.

### "Model training failed"
**Oplossing:**
Mogelijk niet genoeg data. Check of stappen 1-3 (data, features, labels) wel werkten.

---

## 💡 Handmatige Opties

Als je meer controle wilt, kun je het PowerShell script direct gebruiken:

### Normale setup:
```powershell
.\setup-fixed.ps1
```

### Quick mode (30 dagen data, sneller):
```powershell
.\setup-fixed.ps1 -Quick
```

### API key meegeven (skip prompt):
```powershell
.\setup-fixed.ps1 -ApiKey "JOUW_KEY_HIER"
```

### Alleen containers starten (geen training):
```powershell
.\setup-fixed.ps1 -SkipTraining
```

### Custom aantal dagen:
```powershell
.\setup-fixed.ps1 -DataDays 60
```

---

## ✅ Checklist Voor Succesvol Opstart

Voordat je begint, check:
- [ ] Docker Desktop is geïnstalleerd
- [ ] Docker Desktop draait (whale icon zichtbaar)
- [ ] Je hebt Alpha Vantage API key (gratis: alphavantage.co/support/#api-key)
- [ ] Minimaal 10GB vrije disk space
- [ ] Minimaal 4GB RAM beschikbaar voor Docker

Als alle checks ✅ zijn → Dubbelklik `SETUP_FIX.bat` en wacht!

---

## 🎉 Na Succesvolle Setup

Het systeem draait! Je kunt:

### Dashboard Bekijken:
```
http://localhost:8501
```

5 tabs beschikbaar:
- 📊 Overview: Systeemstatus en recente trades
- 💰 Trading: Posities en trade history
- 📈 Performance: Win rate, drawdown, metrics
- 🤖 Model: Predictions en features
- ⚙️ System: Controls en health

### Logs Bekijken:
```powershell
docker compose logs -f
```

### Systeem Stoppen:
Dubbelklik `STOP_SYSTEM.bat`

Of:
```powershell
docker compose down
```

### Systeem Herstarten:
```powershell
docker compose up -d
```

---

## 📞 Hulp Nodig?

Als het nog steeds niet werkt:
1. Kopieer alle error messages
2. Check of je alle prerequisities hebt (checklist hierboven)
3. Probeer Docker Desktop volledig herstarten
4. Check disk space en memory in Docker settings

---

**Veel success! 🚀**

Dit script is speciaal gemaakt om alle veelvoorkomende setup problemen automatisch op te lossen.
