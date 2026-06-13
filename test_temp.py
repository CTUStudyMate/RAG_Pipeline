from rapidfuzz import fuzz, process
t1 = """
The context mentions that the International Software Engineering Research Network publishes studies of replicated investigations and that the journal Empirical Software Engineering publishes studies, data, and guidelines for empirical research, but it does not provide specific data on the number of articles presenting new techniques with empirical evidence or details on the types of empirical studies and variables used.

Therefore, the chatbot can't answer this question. Please try again with another question.
"""

t2 = """
The chatbot can't answer this question. Please try again with another question.
"""


a = fuzz.partial_ratio_alignment(t2, t1)
print(a)
