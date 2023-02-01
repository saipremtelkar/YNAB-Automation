# YNAB-Automation

This script is a Python script that fetches email data from a Gmail account using IMAP protocol, extracts the required data and stores it in a list. It also categorizes the expenses using a predefined dictionary of payee and category names, and uses the fuzzywuzzy library to match the descriptions to the predefined payees. It then sends the data to YNAB (You Need A Budget) using its API to categorize the expenses in the budget.

You can deploy this in Google Cloud on Google Functions and use Google Cloud scheduler + Pub/Sub to run it every 30 Mins

P.S Just remember to uncomment Main function and indent the code while deploying
