import json
import os

results = []
for filename in os.listdir("results"):
    if filename.endswith(".json"):
        with open(os.path.join("results", filename)) as f:
            data = json.load(f)
            if 'model_name' in data and '/' in data['model_name']:
                provider, name = data['model_name'].split('/', 1)
                data['model_provider'] = provider
                data['model_name'] = name
            results.append(data)

with open("webapp/data/results.json", "w") as f:
    json.dump(results, f)