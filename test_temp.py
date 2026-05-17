from transformers import pipeline

nli = pipeline("text-classification", model="roberta-large-mnli")

result = nli({
    "text": hypo,
    "text_pair": premise
})

print(result)