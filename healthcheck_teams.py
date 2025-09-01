import csv

import requests

import os

import sys

import time

TEAMS_URL = os.getenv("TEAMS_WEBHOOK_URL")

def load_apps(file_path):

    apps = []

    with open(file_path, newline='', encoding="utf-8") as f:

        reader = csv.DictReader(f)

        for row in reader:

            apps.append({

                "AppName": row["AppName"],

                "URL": row["URL"],

                "Expected": row["Expected"]

            })

    return apps

def check_app(app):

    try:

        response = requests.get(app["URL"], timeout=8, verify=False)

        status = response.status_code

        content = response.text.strip()

        if app["Expected"] in content:

            return (app["AppName"], app["URL"], status, "✅ OK", "green")

        else:

            return (app["AppName"], app["URL"], status, "❌ Invalid response", "red")

    except Exception as e:

        return (app["AppName"], app["URL"], "N/A", f"❌ Error: {e}", "red")

def build_markdown_table(results):

    header = "| AppName | URL | Status | Result |\n|---------|-----|--------|--------|"

    rows = [f"| {app} | {url} | {status} | {result} |" for app, url, status, result, _ in results]

    return header + "\n" + "\n".join(rows)

def send_to_teams(results, attempt=1, recovered=None):

    if not TEAMS_URL:

        print("⚠️ No Teams Webhook URL set, skipping send")

        return

    md_table = build_markdown_table(results)

    sections = []

    for app, url, status, result, color in results:

        sections.append({

            "activityTitle": f"**{app}** → {result}",

            "activitySubtitle": f"URL: {url}\nStatus: {status}",

            "markdown": True

        })

    if recovered:

        sections.append({

            "activityTitle": f"💚 **Recovered Apps**",

            "text": ", ".join(recovered),

            "markdown": True

        })

    payload = {

        "@type": "MessageCard",

        "@context": "http://schema.org/extensions",

        "themeColor": "0076D7",

        "summary": "Health Check Results",

        "sections": [

            {

                "activityTitle": f"📊 **Health Check Summary (Attempt {attempt})**",

                "text": md_table,

                "markdown": True

            }

        ] + sections

    }

    try:

        r = requests.post(TEAMS_URL, json=payload, timeout=10)

        print("Teams response:", r.status_code, r.text)

    except Exception as e:

        print("❌ Teams send failed:", e)

def run_checks(apps, attempt=1):

    results = [check_app(app) for app in apps]

    for r in results:

        print(r)  # log to console

    send_to_teams(results, attempt=attempt)

    return results

def main():

    apps = load_apps("apps.csv")

    # Attempt 1

    results1 = run_checks(apps, attempt=1)

    if any("❌" in result for _, _, _, result, _ in results1):

        print("⚠️ Failures detected, retrying in 30 seconds...")

        time.sleep(30)

        # Attempt 2

        results2 = [check_app(app) for app in apps]

        # Find recovered apps

        recovered = []

        for (a1, _, _, r1, _), (a2, _, _, r2, _) in zip(results1, results2):

            if "❌" in r1 and "✅" in r2:

                recovered.append(a2)

        send_to_teams(results2, attempt=2, recovered=recovered)

        if any("❌" in result for _, _, _, result, _ in results2):

            sys.exit(1)  # still failing → fail workflow

        else:

            sys.exit(0)  # recovered → success

    else:

        sys.exit(0)  # all OK

if __name__ == "__main__":

    main()
 
