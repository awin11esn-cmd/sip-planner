# GOD_OF_MF SIP Planner (self-updating, free)

A copy of the planner that runs for free on GitHub Pages. NAVs refresh by themselves every weekday night, with no Claude subscription needed.

## One-time setup (about 10 minutes)

1. Create a free account at https://github.com.
2. Click **+ → New repository**. Name it e.g. `sip-planner`, pick **Public**, and click **Create repository**.
3. On the new repo page, click **uploading an existing file**. Drag in everything from this zip: `index.html`, `README.md` and the `scripts` and `.github` folders. Then click **Commit changes**.
   - If the `.github` folder doesn't upload (it's hidden on some computers), create it by hand: **Add file → Create new file**, name it `.github/workflows/refresh-nav.yml`, paste in that file's contents and commit.
4. Go to **Settings → Pages**. Under *Branch*, choose `main` and `/ (root)` and click **Save**.
   After a minute your link appears there: `https://<your-username>.github.io/sip-planner/`
5. Go to **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions**, and click **Save**.
6. Go to the **Actions** tab, click **Refresh fund NAVs → Run workflow** once to test it. A green tick means it worked, and the page shows the new date within a minute or two.

## What updates automatically

- **NAV, NAV date and 1-year return** for all 11 funds: every Tue–Sat at 12:15 AM IST. The data comes from AMFI's official NAV file and mfapi.in.
- **Expense ratio (cost) and AUM** don't update automatically. Change them by hand when an AMC changes its fee: open `index.html` on GitHub, click the pencil icon, find the fund's `"cost":` value, edit it and commit.
- **Stock overlap and correlation numbers** stay as they were on the day of export.

If a run fails, GitHub emails you. Open the Actions tab and read the log. The script prints which AMFI scheme it matched for each fund.
To pin a fund to an exact AMFI scheme code, add `"amfi": "123456",` inside that fund's entry in `index.html`.

Note: GitHub pauses scheduled runs if a public repo has no commits for 60 days. The daily NAV commits keep it active, so this shouldn't happen.
