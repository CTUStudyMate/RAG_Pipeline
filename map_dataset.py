import json

from PIPELINE.compare.fixedsize_normal import load_questions


questions = load_questions("./experiment_data/questions_gradingnotes.csv")
print(len(questions))

def map():
    with open ("my_dataset.json", "r", encoding="utf-8") as f:
        objs = json.load(f)
    
    print(len(objs)) 
    
    mapped = []
    for i in range (0, 70):
        question = questions[i]
        obj = objs[i]
        obj["question"] = question
        mapped.append(obj)
        
    with open ("mapped_data.json", "w", encoding="utf-8") as f:
        json.dump(mapped, f, indent=2)
            

map()       