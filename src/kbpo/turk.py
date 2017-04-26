import boto
from boto.mturk.connection import MTurkConnection
from boto.mturk.question  import ExternalQuestion
import variablePricing

def mentionType(mention):
    return mention['type'] if isinstance(mention['type'], basestring) else mention['type']['name']
def mentionSpan(mention):
    return (mention['doc_char_begin'], mention['doc_char_end']) 
def isRelationCandidate(mentionPair):
    #mentionPair comes as a tuple
    (mention1, mention2) = mentionPair
    if mention1['gloss'] == mention2['gloss']: return False
    elif mention1['entity']['link'] == mention2['entity']['link']: return False
    m1type = mentionType(mention1)
    m2type = mentionType(mention2)
    if m1type == "PER": return True
    elif m1type == "ORG":
        return (not m2type == "PER") and (not m2type == "TITLE")
    else: return False

def constructMentionPairs(mentions, doc):
    pairs = []
    #print doc['sentences']
    sentence_spans = [(s[0]['doc_char_begin'], s[-1]['doc_char_end']) for s in doc['sentences']]
    sentence_to_mention_map = defaultdict(list)
    for mention in mentions:
        found = False
        for sid, span in enumerate(sentence_spans):
            if span[0]<=mention['doc_char_begin'] and span[1]>=mention['doc_char_end']:
                sentence_to_mention_map[sid].append(mention)
                found = True
                break
        if not found:
            print "[Warning] No sentence found for mention: "+str(mention)#+"; first sentence "+str(doc['sentences'][0])
    for sid, s in sentence_to_mention_map.iteritems():
        candidates = filter(isRelationCandidate, itertools.permutations(s, 2))
        temp_map = set()
        unique_candidates = []
        #Sentence ordering is preserved while generating permutations. We assume that json code has done the same
        for c in candidates:
            fs = frozenset([mentionSpan(c[0]), mentionSpan(c[1])])
            if fs not in temp_map:
                unique_candidates.append(c)
                temp_map.add(fs)
        
        pairs.extend(unique_candidates)
    return pairs

def unitAsToken(doc):
    return sum(map(len, doc['sentences']))

def unitAsMentionPair(doc):
    return len(constructMentionPairs(doc['mentions'], doc))

def connect(host_str):
    SANDBOX_HOST = 'mechanicalturk.sandbox.amazonaws.com'
    HOST = 'mechanicalturk.amazonaws.com'
    if  host_str == 'sandbox':
        host = SANDBOX_HOST
    elif host_str == 'actual':
        host = HOST

    mtc = MTurkConnection(host = host)
    return mtc

def compute_reward(batch_params):
    if 'units_function' in batch_params and 'unit_reward' in batch_params:
        length = getattr(variablePricing, config.get('default', 'units_function'))(doc)
        reward = config.getfloat('default', 'unit_reward') * length
        est_time = int(config.getfloat('default', 'unit_time') * length)
        reward = float("{0:.2f}".format(reward))
        params['est_time'] = est_time
        params['reward'] = "{0:.2f}".format(reward)
        print length,  reward, params
    else:
        reward = config.getfloat('default', 'doc_reward')
        length = 1
        print reward, params
def create_hit(params):
    question = ExternalQuestion(url, config.get('default', 'frame_height'))
    response = mtc.create_hit(
            question=question,
            title=config.get('default', 'title'),
            description = config.get('default', 'description'),
            max_assignments = config.get('default', 'max_assignments'), 
            duration = config.get('default', 'duration'), 
            annotation = params['doc_id'], 
            lifetime = config.get('default', 'lifetime'), 
            reward = reward)
    batch_info.append({'docId': params['doc_id'], 'HITTypeId': response[0].HITTypeId, 'HITId': response[0].HITId, 'reward': reward, 'length': length})
def create_batch():
def retrieve_assignments():
def approve_assignments():


