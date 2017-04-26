#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import unittest
import db
"""
Utilities connecting the web interface to database
"""
def constructMentionPairs(doc_id):
    """
    Construct mention pairs from a given @doc_id
    """
    raise NotImplementedError

class TestInterfaceMethods(unittest.TestCase):
    """
    Test suite for methods in interface module
    """
    def constructMentionPairs_reference(self, mentions, sentences):
        """Reference implementation for creating mention pairs"""

        pairs = []
        sentence_spans = [(s[0]['doc_char_begin'], s[-1]['doc_char_end']) for s in sentences]
        sentence_to_mention_map = defaultdict(list)
        for mention in mentions:
            found = False
            for sid, span in enumerate(sentence_spans):
                if span[0]<=mention['doc_char_begin'] and span[1]>=mention['doc_char_end']:
                    sentence_to_mention_map[sid].append(mention)
                    found = True
                    break
            if not found:
                assert False
                #print "[Warning] No sentence found for mention: "+str(mention)#+"; first sentence "+str(doc['sentences'][0])
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

    def test_constructMentionPairs(self):
        """
        Tests the construction to make sure it aligns with the previously used function
        """
        sentences = db.query_doc('NYT_ENG_20131221.0115', sentence_table = 'kbpo.sentence')
        mentions = db.query_mentions('NYT_ENG_20131221.0115', sentence_table = 'kbpo.mention')
        print(constructMentionPairs_reference(mentions, sentences))
        return 


if __name__ == '__main__':
    unittest.main()

