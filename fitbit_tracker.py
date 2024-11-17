# .github/workflows/fitbit_tracker.yml
name: Daily Fitbit Tracking
on:
  schedule:
    - cron: '0 23 * * *'  # Runs at 11 PM UTC daily
  workflow_dispatch:  # Allows manual trigger

jobs:
  track-fitbit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests python-dotenv
          
      - name: Run Fitbit tracker
        env:
          FITBIT_CLIENT_ID: ${{ secrets.FITBIT_CLIENT_ID }}
          FITBIT_CLIENT_SECRET: ${{ secrets.FITBIT_CLIENT_SECRET }}
          FITBIT_ACCESS_TOKEN: ${{ secrets.FITBIT_ACCESS_TOKEN }}
          NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
          NOTION_DATABASE_ID: ${{ secrets.NOTION_DATABASE_ID }}
        run: python fitbit_tracker.py
