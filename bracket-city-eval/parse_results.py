import json
import os

results = []
for filename in os.listdir("results"):
    if filename.endswith(".json"):
        with open(os.path.join("results", filename)) as f:
            results.append(json.load(f))

with open("webapp/data/results.json", "w") as f:
    json.dump(results, f)