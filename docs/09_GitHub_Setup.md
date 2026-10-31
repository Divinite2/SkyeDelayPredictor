# 09 · GitHub Setup (one-time, done by the repo operator)

**You need:** a GitHub account, and **either** GitHub Desktop (easiest) **or** git on the command line. You also need `atc-weather-risk.bundle` from the lead's outputs.
**Don't** upload the files through the GitHub website. It rejects files over 25 MB, and the data CSV is 64 MB. Use Desktop or the command line.

---

## Step 1: Create an empty private repo
1. Go to github.com and sign in, then click **+** (top right) → **New repository**.
2. Name: `atc-weather-risk` · choose **Private**.
3. **Leave every "Initialize" box unticked** (no README, no .gitignore, no licence). The repo must be empty.
4. Click **Create repository** and copy the URL, e.g. `https://github.com/<you>/atc-weather-risk.git`.

## Step 2: Push the lead's repo

### Option A: command line
```bash
git clone atc-weather-risk.bundle atc-weather-risk
cd atc-weather-risk
git switch backend && git switch frontend && git switch main
git remote set-url origin https://github.com/<you>/atc-weather-risk.git
git push -u origin main backend frontend
git push origin --tags
```
If git asks for a password, use a **personal access token** (GitHub → Settings → Developer settings → Personal access tokens), not your account password. **Never paste the token into this chat.**

### Option B: GitHub Desktop
1. Unzip `atc-weather-risk.zip`. It already contains the full git history and branches.
2. GitHub Desktop → **File → Add local repository** → pick the folder.
3. **Repository → Repository settings → Remote** → paste the URL from Step 1.
4. Click **Publish / Push origin**. Then switch the branch selector to `backend` and push, then to `frontend` and push.
5. Tags: Desktop doesn't push tags by itself. Either run `git push origin --tags` once in a terminal, or skip it, because the lead keeps the tag list in `docs/VERSION_LOG.md`.

**Check:** on GitHub you should see 3 branches (`main`, `backend`, `frontend`). With tags pushed you should see 5 tags (`cp0-draft`, `cp0-contract`, `b1-data`, `f1-ui`, plus any added later). GitHub may warn that the 64 MB CSV is larger than 50 MB. That's fine.

## Step 3: Invite the team
Repo → **Settings → Collaborators → Add people** → the back-end and front-end developers.

## Step 4: Protect `main` (so only lead-approved work lands there)
Repo → **Settings → Branches → Add branch protection rule** (or **Rulesets**):
- Branch name pattern: `main`
- ✅ Require a pull request before merging
- ✅ Require approvals: 1 (the repo operator approves **only after the lead says "approved"**)
- ✅ Do not allow bypassing the above settings

> Branch protection on **private** repos needs a paid plan (GitHub Pro, Team, or Education). If it's not available, the same rule applies **by agreement**: nobody pushes to `main` except the repo operator, after the lead's approval.

## Step 5: How each developer starts
```bash
git clone https://github.com/<you>/atc-weather-risk.git
cd atc-weather-risk
git switch backend          # or: git switch frontend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_all.py           # rebuilds data/processed (not stored in git)
python -m pytest -q         # expect 54 passed
```
**Back end:** next work is in `docs/08_Next_Checkpoints.md` (B-2). **Front end:** F-2 and F-3.

## Step 6: The checkpoint loop (how the lead runs version control)
1. The developer works on their branch, committing small and often, and **pulls `main` into their branch** whenever `main` changes.
2. At a checkpoint, they open a **pull request** `backend → main` (or `frontend → main`) and send the lead the checkpoint report **plus a zip of the branch** uploaded here. The lead can't see your private GitHub.
3. The lead reviews and replies with either **"approved: merge and tag `<name>`"** or a list of fixes.
4. The repo operator merges the PR, then runs:
   ```bash
   git switch main && git pull
   git tag -a <name> -m "<checkpoint> approved by lead"
   git push origin <name>
   ```
5. Both developers pull `main` into their branches.

**Shared files** (`config/`, `contract/`, `requirements.txt`): changed only in a **joint** pull request, with the lead approving.
