import json
with open("abstain_set.json", "r", encoding="utf-8") as f:
    result = json.load(f)

print(len(result))    

# 50 câu fact-based
# 16 câu multi modal
# 30 câu reasoning
# 20 câu abstain

