# Engineering Pulse Report

This tool generates a daily or weekly engineering pulse report for a GitHub repository or organization. The report includes commit and pull request activity, grouped by developer, and outputs in Markdown or JSON format. It also uses a free, local LLM for natural language summaries and flags anomalies using heuristics.

## Features
- Fetches commits and PRs for the past X days (default: 7)
- Groups commits and PRs by developer
- Outputs a structured report (Markdown/JSON)
- Configurable via `.env` or CLI
- AI-powered summary and anomaly detection

## Project Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd pulseai
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file** in the project root:
   ```env
   GITHUB_TOKEN=your_github_token_if_any
   GITHUB_ORG=CODEREXLTD
   DAYS_RANGE=7
   ```
   - For a single repo, use `GITHUB_REPO=owner/repo` instead of `GITHUB_ORG`.

5. **Run the tool**
   - For all repos in an org:
     ```bash
     python main.py --org CODEREXLTD
     ```
   - For a single repo:
     ```bash
     python main.py --repo CODEREXLTD/creator-lms
     ```
   - Output will be saved in the `reports/` folder as `report-YYYY-MM-DD.md` or `.json`.

6. **Optional CLI arguments**
   - `--days 14` to change the reporting window
   - `--output json` for JSON output
   - `--file custom_path.md` to specify a custom output file

## Output
- Markdown or JSON report saved to the `reports/` folder by default.
- Includes AI summary and alerts for anomalies.

---

**Note:**
- The first run will download the summarization model from HuggingFace (no API key required for public models).
- If you encounter HuggingFace credential errors, ensure you have no invalid HuggingFace tokens set in your environment. 