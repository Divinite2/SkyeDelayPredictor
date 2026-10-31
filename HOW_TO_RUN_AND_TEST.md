# How to Run and Test (non-technical guide)

## 1. Before you start
- **Python 3.11** must be installed.
  - Windows: install from python.org and tick **"Add Python to PATH"**.
  - Mac: `brew install python@3.11`, or the python.org installer.
- An **internet connection the first time only** (to install packages).

## 2. Start the dashboard
- **Windows:** double-click **`RUN_DASHBOARD.bat`**
- **Mac/Linux:** open Terminal in this folder and run `./run_dashboard.sh`

The first start takes a few minutes while it installs packages. Then your browser opens **http://localhost:8501**. If it doesn't, open that address yourself. To stop the dashboard, close the terminal window.

## 3. Test it (about 6 clicks)

### A. Demo cases (top drop-down "Demo cases" → pick one → press Check)
| Pick | You should see |
|---|---|
| **True RED…** (DFW) | **● RED** · Middle estimate **15–30 min** · Bad case **more than 60 min (33%)** · confidence **HIGH** · WHY lists the evening hour, an earlier thunderstorm (with its date) and rain |
| **True GREEN…** (ATL) | **■ GREEN** · Middle estimate **under 15 min** · confidence **HIGH** |
| **Known failure case…** (ATL, 28 Jun) | **■ GREEN** with confidence **LOW**. Severe delays actually happened here. This is our honest miss, and the LOW confidence is the warning sign. |
| **Refused: only 2 h ahead** | Grey card "Too soon to forecast" with no numbers |
| **Refused: 13 h ahead** | Grey card "Too far ahead to forecast" with no numbers |

### B. Your own date and time
1. Choose **Airport**, the **Now** date and hour, and a **Target hour** (the list offers +3 to +12 h).
2. Press **Check**.
3. For dates where severe delays really happened, open **`reports/severe_delay_dates.md`**. Each row says which "Now" to set. It also lists misses.

### C. Things to check on every result card
- [ ] A colour badge with the word (RED / AMBER / GREEN)
- [ ] **LIKELY DELAY** with a middle estimate and a bad case
- [ ] Four percentage bars, with **> 45 min** marked "severe"
- [ ] Capacity line plus a grey note explaining why no range is shown
- [ ] WHY times are before "now". Older readings show their date.
- [ ] The footer says **"Back end: real · answered in … s"**

### D. Refusal in test mode
Tick **Test mode**, type airport **ORD**, press Check → "Airport not in data".

## 4. If something goes wrong
| Problem | Fix |
|---|---|
| "Python 3.11 not found" | Install Python 3.11 (see §1), then start again |
| The page shows "Back end: mock" | Start with `RUN_DASHBOARD.bat` / `run_dashboard.sh`, which set the real back end |
| Red error card "Do not rely on this tool" | The model files are missing. Run `python run_all.py` once (about 2 minutes). |
| Browser doesn't open | Go to http://localhost:8501 yourself |
| Port already in use | Close the other dashboard window, or run `streamlit run frontend/app.py --server.port 8502` |

## 5. Optional full check (technical)
```
python run_all.py            # rebuild everything from the data (~2 min)
python -m pytest -q          # 134 passed
python scripts/smoke_real.py # end-to-end check
```
