import json


with open("chunk_test.json", "r", encoding="utf-8") as f:
    test_obj = json.load(f)
    print(len(test_obj["content"]["img"]))