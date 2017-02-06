from kbpdoc import constructMentionPairs
def unitAsToken(doc):
    return sum(map(len, doc['sentences']))

def unitAsMentionPair(doc):
    return len(constructMentionPairs(doc['mentions'], doc))
