#!/bin/bash
TOKEN=$(cat /home/aidam/.gemini/antigravity/scratch/token.txt)
git remote set-url origin https://${TOKEN}@github.com/AidamZzzZ/code-insight-bot.git
git push origin main
git remote set-url origin https://github.com/AidamZzzZ/code-insight-bot.git
