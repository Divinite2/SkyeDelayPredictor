# 07 · Version Control (GitHub)

**Ownership:** the **project lead (me) owns version control**. I decide what merges into `main`, I create every checkpoint tag, and I keep `docs/VERSION_LOG.md`. I can't push to GitHub myself, so one team member acts as **repo operator** and runs the exact commands I give, after I approve a checkpoint. Nobody else merges to `main` or creates tags.

**In plain words:** one shared GitHub repository holds all the code. Each path works on its own branch, merges into `main` when a checkpoint passes, and every passed checkpoint gets a **tag** (a named save point) we can always return to.

## Setup (Checkpoint 0, once)
0. **The lead has already built the starting repo** (`atc-weather-risk.bundle` / `.zip` in the outputs). It contains the folder layout, shared config, contract schema, 6 example responses, a passing contract test and all docs, tagged `cp0-draft`. The repo operator creates an **empty** private GitHub repo and pushes it:
   ```
   git clone atc-weather-risk.bundle atc-weather-risk && cd atc-weather-risk
   git switch backend && git switch frontend && git switch main
   git remote set-url origin https://github.com/<you>/atc-weather-risk.git
   git push -u origin main backend frontend --tags
   ```
1. (Done by the lead's starter repo.) The operator creates a **private** GitHub repo (e.g. `atc-weather-risk`) and invites the team. Keep it private until submission, because the dataset belongs to the hackathon.
2. Add a `.gitignore`:
   ```
   data/processed/
   __pycache__/
   .venv/
   *.pyc
   .DS_Store
   ```
3. Commit `data/raw/Flight_Data_With_Weather_Final.csv` (64 MB). That's under GitHub's 100 MB limit (GitHub warns above 50 MB, which is fine). Processed files aren't committed, because `run_all.py` rebuilds them.
4. **Model files** (`models/`): commit them **only** at the v1 tag, so the demo laptop and any hosted version run without retraining.

## Branches
| Branch | Who | Contains |
|---|---|---|
| `main` | Nobody pushes directly | Only work that passed a checkpoint |
| `backend` | Back-end path | `backend/`, `tests/`, `reports/`, `run_all.py` |
| `frontend` | Front-end path | `frontend/`, front-end tests, pitch files |

**Shared files** (`config/config.yaml`, `contract/`, `requirements.txt`): change them only **together**, in one pull request reviewed by both leads. That's how the data contract stays agreed.

## Daily rules
- **Commit small and often**, with clear messages: `fix: timezone repair for DFW winter`, not `update`.
- **Pull `main` into your branch** after every merge, so the two paths never drift apart.
- **Merge to `main` only after the lead approves the checkpoint report.** The repo operator merges the pull request and creates the tag the lead names. Tests must pass.
- **Never commit:** passwords or API keys, or anything in `data/processed/`.

## Checkpoint tags (save points)
| Tag | When |
|---|---|
| `cp0-contract` | Checkpoint 0 passed |
| `b1-data`, `b2-model` | Back-end checkpoints passed |
| `f1-ui`, `f2-story` | Front-end checkpoints passed |
| `v1-submitted` | Integration passed and submitted. **Code freeze starts here.** |
| `v1.1` | Only if a post-freeze fix still passes every gate |

Command: `git tag b1-data && git push origin b1-data`

**If something breaks during the freeze:** go back to `v1-submitted` (`git checkout v1-submitted`) and demo from there.

## For non-technical members
Use **GitHub Desktop** (a free app) instead of the command line. It covers pull, commit, push and switching branches with buttons. Pitch files can also live in the repo under `pitch/`.
