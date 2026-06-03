from rapidfuzz import fuzz, process
t1 = """
[SECTION]: Why Software Engineering? > 1.8 How Has Software Engineering Changed? > Wasserman's Discipline of Software Engineering
[CONTENT]: Reuse. In software development and maintenance, we often take advantage of the commonalities across applications by reusing items from previous development. For example, we use the same operating system or database management system from one development project to the next, rather than building a new one each time. Similarly, we reuse sets of requirements, parts of designs, and groups of test scripts or data when we build systems that are similar to but not the same as what we have done before. Barnes and Bollinger (1991) point out that reuse is not a new idea, and they provide many interesting examples of how we reuse much more than just code.
Prieto-Díaz (1991) introduced the notion of reusable components as a business asset. Companies and organizations invest in items that are reusable and then gain quantifiable benefit when those items are used again in subsequent projects. However,
establishing a long-term, effective reuse program can be difficult, because there are several barriers:
 - It  is  sometimes  faster  to  build  a  small  component  than  to  search  for  one  in  a repository of reusable components.
 - It may take extra time to make a component general enough to be reusable easily by other developers in the future.
 - It is difficult to document the degree of quality assurance and testing that have been done, so that a potential reuser can feel comfortable about the quality of the component.
 - It is not clear who is responsible if a reused component fails or needs to be updated.
 - It can be costly and time-consuming to understand and reuse a component written by someone else.
 - There is often a conflict between generality and specificity.
We will look at reuse in more detail in Chapter 12, examining several examples of successful reuse.

"""

t2 = """
there are several barriers: - It is sometimes faster to build a small component than to search for one in a repository of reusable components. - It is not clear who is responsible if a reused component fails or needs to be updated. - It can be costly and time-consuming to understand and reuse a component written by someone else.
"""


a = fuzz.partial_ratio_alignment(t2, t1)
print(a)
