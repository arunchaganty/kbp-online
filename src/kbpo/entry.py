"""
Classes and functions to process entry files.

mention_id TYPE gloss * weight
mention_id canonical_mention mention_id * weight
mention_id link link_name * weight
subject_id reln object_id prov weight
"""

import pdb
import csv
import re
import logging
from collections import namedtuple, defaultdict

from .defs import TYPES, RELATION_MAP, RELATIONS, ALL_RELATIONS, INVERTED_RELATIONS, STRING_VALUED_RELATIONS
from .schema import Provenance
from . import db

import sys
from tqdm import tqdm

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_MFile = namedtuple('_MFile', ['types', 'links', 'canonical_mentions', 'relations'])
class MFile(_MFile):
    def __new__(cls, types, links, cmentions, relations):
        self = super(MFile, cls).__new__(cls, types, links, cmentions, relations)
        self._type_map = {row.subj: row.reln for row in types}
        self._gloss_map = {row.subj: row.obj for row in types}
        self._link_map = {row.subj: row.obj for row in links}
        self._cmention_map = {row.subj: row.obj for row in cmentions}
        self.mention_ids = set(row.subj for row in self.types)
        return self

    @classmethod
    def _make(cls, iterable, new=tuple.__new__, len=len):
        'Make a new A object from a sequence or iterable'
        result = super(MFile, cls)._make(iterable, new, len)
        return cls.__new__(cls, *result)

    def get_gloss(self, m_id):
        return self._gloss_map.get(m_id)
    def get_type(self, m_id):
        return self._type_map.get(m_id)
    def get_link(self, m_id):
        return self._cmention_map.get(m_id) and  self._link_map.get(self._cmention_map.get(m_id))
    def get_cmention(self, m_id):
        return self._cmention_map.get(m_id)

    def normalize_relation(self, entry):
        subj, reln, obj = entry.subj, entry.reln, entry.obj
        if reln in RELATIONS:
            return entry
        elif reln not in RELATIONS and reln in INVERTED_RELATIONS:
            for reln_ in INVERTED_RELATIONS[reln]:
                if reln_.startswith(self.get_type(obj).lower()):
                    return entry._replace(subj = obj, reln = reln_, obj = subj)
        else:
            raise ValueError("Couldn't map relation for {}".format(entry))

    @classmethod
    def parse_prov(cls, prov):
        if len(prov) == 0:
            return None
        doc_id, beg, end =  re.match(r"([A-Za-z0-9_.]+):([0-9]+)-([0-9]+)", prov).groups()
        return Provenance(doc_id, int(beg), int(end))

    @classmethod
    def to_prov(cls, prov):
        assert len(prov) == 3
        return "{}:{}-{}".format(*prov)

    @classmethod
    def from_stream(cls, stream, input_format='mfile', corpus_tag='kbp2016'):
        """
        Split input into type, link, canonical_mention and relation definitions.
        @input_format can be mfile or tackb
            tackb input format is
                :<e1> type <type>
                :<e1> mention <string> <provenance>
                :<e1> canonical_mention <string> <provenance>
                :<e1> nominal_mention <string> <provenance> (ignored)
                :<e1> <predicate> :<e2> <provenance> <weight>
                :<e1> <predicate> <string> <provenance> <weight>
            mfile input format is 
                <m1:prov> <predicate> <m2:prov> <rel:prov> weight
                <m1:prov> <type> <gloss> weight
                <m1:prov> canonical_mention <m2:prov> weight
                <m1:prov> link <wiki-link> weight
        """
        mentions = []
        links = []
        canonical_mentions = []
        relations = []

        #Take the first two underscore separated strings as the corpus prefix
        #Allows ENG_NW and NYT_ENG but not ENG_DF for instance within kbp2016 corpus
        corpus_prefixes = [row.prefix for row in db.select("""SELECT distinct array_to_string(split_doc_id[1:2], '_') as prefix FROM 
                        (SELECT regexp_split_to_array(s.doc_id, '_') AS split_doc_id 
                            FROM sentence AS s 
                            LEFT JOIN document_tag AS t 
                            ON s.doc_id = t.doc_id 
                            WHERE t.tag = %(corpus_tag)s
                            ) as t""", corpus_tag = corpus_tag)]
        print(corpus_prefixes)


        rows = []
        if input_format == 'tackb':
            class EntryLine(namedtuple('Entry', ['subj', 'reln', 'obj', 'prov', 'weight', 'line_num'])):
                @property
                def pair(self):
                    return (self.subj, self.obj)

                @property
                def inv_pair(self):
                    return (self.obj, self.subj)
            counter = 0
            raw_mentions = []
            raw_nominal_mentions = []
            raw_relations = []
            subj_2_type = {}
            doc_id_subj_2_canonical_mention = {}
            subj_doc_id_2_mention = defaultdict(list)
            for row in tqdm(stream):
                counter += 1
                if counter == 1:
                    continue
                assert len(row) <= 5, "Invalid number of columns, %d instead of %d"%(len(row), 5)
                row = row + [None] * (5-len(row)) + [counter]
                reln = row[1]
                if reln == 'mention':
                    #TODO: throw error if doesn't exist
                    row[3] = cls.parse_prov(row[3])
                    row = EntryLine(*row)
                    raw_mentions.append(row)
                    subj_doc_id_2_mention[(row.subj, row.prov.doc_id)].append(row)
                elif reln == 'canonical_mention':
                    #raw_canonical_mentions.append(row)
                    #TODO: throw error if doesn't exist
                    row[3] = cls.parse_prov(row[3])
                    row = EntryLine(*row)
                    doc_id_subj_2_canonical_mention[(row.prov.doc_id, row.subj)] = row
                    raw_mentions.append(row)

                elif reln == 'nominal_mention':
                    row = EntryLine(*row)
                    raw_nominal_mentions.append(row)

                elif reln == 'type':
                    #raw_types.append(row)
                    #TODO: Throw warning for multiple types for same entity
                    row = EntryLine(*row)
                    subj_2_type[row.subj] = row
                else:
                    row = EntryLine(*row)
                    raw_relations.append(row)

            #mentions
            mentions = []
            canonical_mentions = []
            links = []
            #types
            for row in tqdm(raw_mentions):
                type_row = subj_2_type[row.subj]
                mentions.append(Entry(row.prov, type_row.obj, row.obj, None, row.weight))

            #canonical-mentions
            for row in tqdm(raw_mentions):
                canonical_row = doc_id_subj_2_canonical_mention[(row.prov.doc_id, row.subj)]
                canonical_mentions.append(Entry(row.prov, 'canonical_mention', canonical_row.prov, None, canonical_row.weight))

            #entity_links
            for row in tqdm(raw_mentions):
                links.append(Entry(row.prov, 'link', row.subj, None, row.weight))
            def first_contained_entity_prov(reln_prov, entity):
                for m in subj_doc_id_2_mention[(entity, reln_prov.doc_id)]:
                    if m.prov.begin > reln_prov.begin and m.prov.end < reln_prov.end:
                        return m.prov

            ##relations
            all_relations = set(RELATION_MAP.keys()) - set(['no_relation'])
            ignored_relations = set(['per:alternate_names', 'org:alternate_names'])
            all_relations -= ignored_relations
            for row in tqdm(raw_relations):
                if row.reln not in all_relations:
                    if row.reln in ignored_relations:
                        #logger.warning("LINE %d: Ignored relation %s", row.line_num, row.reln)
                        pass
                    else:
                        #logger.warning("LINE %d: Unsupported relation %s", row.line_num, row.reln)
                        pass
                else:
                    mapped_reln = RELATION_MAP[row.reln]
                    split_prov = row.prov.split(',')
                    prov_idx = 0
                    o_prov = None
                    r_prov = None
                    if mapped_reln in STRING_VALUED_RELATIONS:
                        #First provenance would give object provenance 
                        o_prov = cls.parse_prov(split_prov[0])
                        #TODO: make sure gloss is the same as the first provenance
                        mentions.append(Entry(o_prov, STRING_VALUED_RELATIONS[mapped_reln], row.obj, None, row.weight))
                        canonical_mentions.append(Entry(o_prov, 'canonical_mention', o_prov, None, row.weight))
                        links.append(Entry(o_prov, 'link', row.obj, None, row.weight))
                        for idx in range(1,len(split_prov)):
                            r_prov = cls.parse_prov(split_prov[idx])
                            m = first_contained_entity_prov(r_prov, row.subj)
                            if m is not None:
                                s_prov = m
                                break
                    else:
                        for idx in range(len(split_prov)):
                            r_prov = cls.parse_prov(split_prov[idx])
                            s_prov = first_contained_entity_prov(r_prov, row.subj)
                            o_prov = first_contained_entity_prov(r_prov, row.obj)
                            if s_prov is not None and o_prov is not None:
                                break

                    if s_prov is None or o_prov is None:
                        #TODO: throw error
                        pass
                    else:
                        relations.append(Entry(s_prov, mapped_reln, o_prov, r_prov, row.weight))
        

            #with db.CONN:
            #    with db.CONN.cursor() as cur:
            #        #db.execute("""DROP TABLE IF EXISTS _submission_tackb;""", cur = cur)
            #        #db.execute("""CREATE TABLE _submission_tackb(
            #        #                line_num integer,
            #        #                e1 text, 
            #        #                reln text,
            #        #                e2 text,
            #        #                doc_id text, 
            #        #                span int4range, 
            #        #                prov_num integer,
            #        #                weight real);""", cur = cur)
            #        #values = []
            #        #counter = 0
            #        #for row in tqdm(stream):
            #        #    counter+=1
            #        #    if counter == 1:
            #        #        #Ignore the first line as it contains submission name
            #        #        continue
            #        #    assert len(row) <= 5, "Invalid number of columns, %d instead of %d"%(len(row), 5)
            #        #    row = row + [None] * (5-len(row))
            #        #    row = Entry(*row)
            #        #    weight = float(row.weight) if row.weight else 0.0
            #        #    if row.prov is not None:
            #        #        for prov_idx, split_prov in enumerate(row.prov.split(',')):
            #        #            try:
            #        #                prov = cls.parse_prov(split_prov)
            #        #                doc_id = prov.doc_id
            #        #                if '_'.join(doc_id.split('_')[:2]) not in corpus_prefixes:
            #        #                    #Filter out ENG_DF provenances which aren't supported
            #        #                    continue
            #        #               
            #        #                span = db.Int4NumericRange(prov.begin, prov.end, bounds = '[]')
            #        #                values.append(db.mogrify("(%(line_num)s, %(e1)s, %(reln)s, %(e2)s, %(doc_id)s, %(span)s, %(weight)s, %(prov_num)s)", 
            #        #                line_num = counter, e1 = row.subj, reln = row.reln, e2 = row.obj, doc_id = doc_id, span=span, weight = weight, prov_num = prov_idx, verbose = False))
            #        #            except AssertionError as e:
            #        #                logger.warning(e)
            #        #    else:
            #        #        doc_id = None
            #        #        span = None
            #        #        values.append(db.mogrify("""(%(line_num)s, %(e1)s, %(reln)s, %(e2)s, %(doc_id)s, %(span)s, %(weight)s, %(prov_num)s)""", 
            #        #        line_num = counter, e1 = row.subj, reln = row.reln, e2 = row.obj, doc_id = doc_id, span=span, weight = weight, prov_num = 0, verbose = False))
            #        #    if counter % 10000 == 0:
            #        #        args_str = b','.join(values)
            #        #        #Need to call using cur because % present in strings causes it to expect input values
            #        #        cur.execute(b"INSERT INTO _submission_tackb (line_num, e1, reln, e2, doc_id, span, weight, prov_num) VALUES "+ args_str)
            #        #        values = []

            #        #args_str = b','.join(values)
            #        #cur.execute(b"INSERT INTO _submission_tackb (line_num, e1, reln, e2, doc_id, span, weight, prov_num) VALUES "+ args_str)
            #        #cur.execute("""CREATE INDEX _submission_tackb_line_num_idx ON _submission_tackb(line_num)""");
            #        #cur.execute("""CREATE INDEX _submission_tackb_e1_idx ON _submission_tackb(e1)""");
            #        #cur.execute("""CREATE INDEX _submission_tackb_reln_idx ON _submission_tackb(reln)""");
            #        #cur.execute("""CREATE INDEX _submission_tackb_e1_doc_id_idx ON _submission_tackb(doc_id, e1)""");

            #        #db.execute("""
            #        #            DROP TABLE IF EXISTS _submission_tackb_unique_mention CASCADE;
            #        #            CREATE TABLE _submission_tackb_unique_mention AS 
            #        #                (SELECT DISTINCT ON (e1, e2, doc_id, span) line_num, e1, e2, doc_id, span
            #        #                    FROM _submission_tackb 
            #        #                    WHERE reln = 'mention' 
            #        #                        OR reln = 'canonical_mention' 
            #        #                ORDER BY e1, e2, doc_id, span, reln DESC);
            #        #            CREATE INDEX _submission_tackb_unique_mention_e1_doc_idx ON _submission_tackb_unique_mention(doc_id, e1);
            #        #            CREATE INDEX _submission_tackb_unique_mention_e1_idx ON _submission_tackb_unique_mention(e1);
            #        #                """, cur = cur)
            #        ##mentions (from entities)
            #        #for row in tqdm(db.select("""SELECT a.line_num, a.e1 as entity, a.doc_id, a.span, a.e2 as gloss, b.e2 AS type, a.weight 
            #        #                FROM _submission_tackb_unique_mention AS a 
            #        #                LEFT JOIN _submission_tackb as b 
            #        #                    ON a.e1 = b.e1 
            #        #                      WHERE b.reln = 'type';""", cur = cur)):
            #        #    prov = Provenance(row.doc_id, row.span.lower, row.span.upper)
            #        #    if row.type is None:
            #        #        logging.error("LINE %d: Missing type for entity %s", row.line_num, row.entity)
            #        #    if row.gloss is None:
            #        #        logging.error("LINE %d: Missing gloss for mention @ %s", row.line_num, prov)
            #        #    #Add error for gloss not matching
            #        #    mentions.append(Entry(prov,row.type, row.gloss, None, row.weight))

            #        #Takes around 4 minutes with Stanford submission
            #        #canonical-mentions
            #        db.execute("""DROP TABLE IF EXISTS _submission_tackb_canonical_mention; 
            #                      CREATE TEMP TABLE _submission_tackb_canonical_mention AS 
            #                      (SELECT * FROM _submission_tackb WHERE reln = 'canonical_mention');
            #                      CREATE INDEX _submission_tackb_canonical_mentions_e1_doc_id_idx ON _submission_tackb_canonical_mentions(doc_id, e1);""")
            #        for row in tqdm(db.select("""SELECT DISTINCT m.line_num, m.e1, m.doc_id, m.span, cm.doc_id AS cm_doc_id, cm.span AS cm_span, cm.weight
            #                      FROM _submission_tackb AS m 
            #                      LEFT JOIN _submission_tackb AS cm 
            #                        ON m.e1 = cm.e1 AND m.doc_id = cm.doc_id 
            #                      WHERE m.reln = 'mention' OR cm.reln = 'canonical_mention'
            #                        AND cm.reln = 'canonical_mention';""", cur = cur)):
            #            prov1 = Provenance(row.doc_id, row.span.lower, row.span.upper)
            #            if row.cm_doc_id is None:
            #                logger.error("LINE %d: No canonical mention exists for %s entity in document %s mentioned at %s", row.line_num, row.e1, row.doc_id, prov1)
            #            prov2 = Provenance(row.cm_doc_id, row.cm_span.lower, row.cm_span.upper)
            #            canonical_mentions.append(Entry(prov1, 'canonical_mention', prov2, None, row.weight))

            #        #mentions (string_valued from relations)
            #        #relations

            #        all_relations = set(RELATION_MAP.keys()) - set(['no_relation'])
            #        ignored_relations = set(['per:alternate_names', 'org:alternate_names'])
            #        all_relations -= ignored_relations
            #        #% sign in the query conflicts with kwargs in which are implicitly passed in db.select
            #        cur.execute("""
            #                                            SELECT                                                                                                                                                                                     DISTINCT ON (r.line_num) r.line_num, r.prov_num, r.span, 
            #                                                s.doc_id AS s_doc_id, s.span AS s_span, r.e1 as s_entity,
            #                                                o.doc_id AS o_doc_id, o.span AS o_span, r.e2 as o_entity,
            #                                                r.reln, r.doc_id AS r_doc_id, r.span AS r_span, 
            #                                                r.weight, sen.gloss as sen_gloss, sen.span as sen_span,
            #                                                prov1.span as prov1_span
            #                                            FROM _submission_tackb as r 
            #                                            LEFT JOIN _submission_tackb_unique_mention AS s 
            #                                                ON s.e1 = r.e1 AND s.doc_id = r.doc_id AND s.span && r.span 
            #                                            LEFT JOIN _submission_tackb_unique_mention as o 
            #                                                ON o.e1 = r.e2 AND o.doc_id = r.doc_id AND o.span && r.span 
            #                                            LEFT JOIN _submission_tackb as prov1 
            #                                                ON prov1.reln NOT IN ('mention', 'canonical_mention', 'type', 'nominal_mention') 
            #                                                   AND prov1.line_num = r.line_num AND prov1.prov_num = 0
            #                                            LEFT JOIN sentence as sen on sen.doc_id = r.doc_id AND sen.span && r.span
            #                                            WHERE r.reln NOT IN ('mention', 'canonical_mention', 'type', 'nominal_mention') 
            #                                            ORDER BY r.line_num, s.doc_id IS NOT NULL DESC, (substring(sen.gloss from (r.span).lower
            #                                             - (sen.span).lower +1 for (r.span).upper - (r.span).lower) LIKE '%'||r.e2||'%' OR o.doc_id IS NOT NULL) DESC, r.prov_num """)
            #        for row in tqdm(cur.fetchall()):
            #            assert row.r_doc_id is not None
            #            r_prov = Provenance(row.r_doc_id, row.r_span.lower, row.r_span.upper)
            #            errors = False
            #            if row.reln not in all_relations:
            #                if row.reln in ignored_relations:
            #                    #logger.warning("LINE %d: Ignored relation %s", row.line_num, row.reln)
            #                    pass
            #                else:
            #                    #logger.warning("LINE %d: Unsupported relation %s", row.line_num, row.reln)
            #                    pass
            #                errors = True
            #                continue
            #            if row.s_doc_id is None:
            #                logger.error("LINE %d: No subject mention for entity %s found for predicate %s in provenance %s", row.line_num, row.s_entity, row.reln, cls.to_prov(r_prov))
            #                errors = True
            #            else:
            #                s_prov = Provenance(row.s_doc_id, row.s_span.lower, row.s_span.upper)
            #            mapped_reln = RELATION_MAP[row.reln]
            #            if row.o_doc_id is None:
            #                #entity valued object entity (we have already confirmed that it is a supported relation
            #                if mapped_reln not in STRING_VALUED_RELATIONS:
            #                    logger.error("LINE %d: No object mention for entity %s found for predicate %s in provenance %s", row.line_num, row.o_entity, row.reln, cls.to_prov(r_prov))
            #                    errors = True
            #                #string valued relation

            #                else:
            #                    pass
            #                    #TACKB format imposes that the first provenance should be for the string object
            #                    if row.prov1_span is None:
            #                        logger.error("LINE %d: No mention for string valued object %s found for predicate %s in provenance %s", row.line_num, row.o_entity, row.reln, cls.to_prov(r_prov))
            #                        errors = True

            #                    #string valued object entity found
            #                    else:

            #                        o_prov = Provenance(row.r_doc_id, row.prov1_span.lower, row.prov1_span.upper)
            #                        o_type = STRING_VALUED_RELATIONS[mapped_reln]
            #                        #TODO: What should be the weight ofr a string valued slotfill here? 0 or 1
            #                        if not errors:
            #                            mentions.append(Entry(o_prov, o_type, row.o_entity, None, 1))
            #                            canonical_mentions.append(Entry(o_prov, 'canonical_mention', o_prov, None, 1))
            #            else:
            #                #Object entity found
            #                o_prov = Provenance(row.o_doc_id, row.o_span.lower, row.o_span.upper)
            #            if not errors:
            #                relations.append(Entry(s_prov, mapped_reln, o_prov, r_prov, row.weight))
                        
        elif input_format == 'mfile':
            for row in stream:
                assert len(row) <= 5, "Invalid number of columns, %d instead of %d"%(len(row), 5)
                row = row + [None] * (5-len(row))
                row = Entry(*row)
                row = row._replace(
                    subj = cls.parse_prov(row.subj),
                    weight = float(row.weight) if row.weight else 0.0
                    )

                if row.reln in TYPES:
                    mentions.append(row)
                elif row.reln == "link":
                    links.append(row)
                elif row.reln == "canonical_mention":
                    row = row._replace(obj = cls.parse_prov(row.obj))
                    canonical_mentions.append(row)
                else:
                    provs = tuple(cls.parse_prov(p) for p in row.prov.split(',') if p)
                    row = row._replace(obj = cls.parse_prov(row.obj), prov=provs)
                    relations.append(row)
        else:
            assert True, "Invalid file format, should be tackb or mfile"
        return cls(mentions, links, canonical_mentions, relations)

    def to_stream(self, stream):
        for row in self.types:
            stream.writerow([MFile.to_prov(row.subj), row.reln, row.obj, row.prov, row.weight])
        for row in self.links:
            stream.writerow([MFile.to_prov(row.subj), row.reln, row.obj, row.prov, row.weight])
        for row in self.canonical_mentions:
            stream.writerow([MFile.to_prov(row.subj), row.reln, MFile.to_prov(row.obj), row.prov, row.weight])
        for row in self.relations:
            stream.writerow([MFile.to_prov(row.subj), row.reln, MFile.to_prov(row.obj), ",".join([MFile.to_prov(p) for p in row.prov]), row.weight])
def test_tackb_input():
    old_logger = logger
    logger = logging.getLogger("test-tackb")
    logger.setLevel(logging.DEBUG)
    input_format = 'tackb'



class Entry(namedtuple('Entry', ['subj', 'reln', 'obj', 'prov', 'weight'])):
    @property
    def pair(self):
        return (self.subj, self.obj)

    @property
    def inv_pair(self):
        return (self.obj, self.subj)

def verify_mention_ids(mfile):
    # Construct definitions of mentions.
    if len(mfile.mention_ids) != len(mfile.types):
        logger.warning("%d Duplicate definitions of mentions", len(mfile.types) - len(mfile.mention_ids))
        seen_ids = set([])
        new_types = []
        for row in mfile.types:
            if row.subj not in seen_ids:
                seen_ids.add(row.subj)
                new_types.append(row)
        mfile = mfile._replace(types=new_types)

    failed = False
    for r in mfile.canonical_mentions:
        subj, _, obj, _, _ = r
        if subj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", subj, r)
        if obj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", obj, r)

    for r in mfile.links:
        subj, _, _, _, _ = r
        if subj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", subj, r)

    for r in mfile.relations:
        subj, _, obj, _, _ = r
        if subj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", subj, r)
        if obj not in mfile.mention_ids:
            failed = True
            logger.error("Couldn't find definition of mention %s in: %s", obj, r)
    assert not failed, "Couldn't find definitions of some mentions"
    return mfile

def verify_canonical_mentions(mfile):
    # Construct definitions of mentions.
    failed = False
    for m in mfile.mention_ids:
        if mfile.get_cmention(m) is None:
            logger.error("Didn't have a canonical mention for %s", m)
            failed = True
        if mfile.get_link(m) is None:
            logger.error("Didn't have a link for %s", m)
            pdb.set_trace()
            failed = True
    # TODO: link the first mention of this entity as the
    # canonical_mention
    assert not failed, "Couldn't find definitions of some mentions"
    return mfile

def verify_relations(mfile):
    """
    symmetrize relations
    """
    keys = set()
    relations_ = set()
    for r in mfile.relations:
        subj, reln, obj = r.subj, r.reln, r.obj

        if reln not in ALL_RELATIONS:
            logger.warning("Ignoring relation %s: %s", reln, r)
            continue
        if (subj, obj) in keys:
            logger.warning("Already have a relation between %s and %s", subj, obj)
            continue
        keys.add((subj, obj))
        relations_.add(r._replace(reln=RELATION_MAP[reln]))
    logger.info("Found %d relations", len(relations_))

    for r in mfile.relations:
        subj, reln, obj = r.subj, r.reln, r.obj

        if reln not in ALL_RELATIONS:
            continue

        if reln in INVERTED_RELATIONS:
            for reln_ in INVERTED_RELATIONS[reln]:
                if reln_.startswith(mfile.get_type(obj).lower()):
                    r_ = r._replace(subj=obj, reln=reln_, obj=subj)
                    if (obj, subj) not in keys:
                        logger.info("Adding symmetrized relation %s: %s", r_, r)
                        keys.add((obj,subj))
                        relations_.add(r_)
    logger.info("End with %d relations", len(relations_))
    return mfile._replace(relations=relations_)

# TODO: make this validator 10x more robust
# TODO: have validator report errors.
def validate(fstream, input_format = 'mfile'):
    mfile = MFile.from_stream(csv.reader(fstream, delimiter='\t'), input_format)
    mfile = verify_mention_ids(mfile)
    mfile = verify_canonical_mentions(mfile)
    mfile = verify_relations(mfile)
    return mfile

def upload_submission(submission_id, mfile):
    with db.CONN:
        with db.CONN.cursor() as cur:
            # Create the submission
            mentions, links, relations = [], [], []
            for mention_id in mfile.mention_ids:
                mention_type, gloss, canonical_id = mfile.get_type(mention_id), mfile.get_gloss(mention_id), mfile.get_cmention(mention_id)
                mention_id, canonical_id = mention_id, canonical_id
                doc_id = mention_id.doc_id
                mentions.append((submission_id, doc_id, mention_id, canonical_id, mention_type, gloss))
            for row in mfile.links:
                mention_id = row.subj
                doc_id = mention_id.doc_id
                link_name = row.obj
                weight = row.weight
                links.append((submission_id, doc_id, mention_id, link_name, weight))
            for row in mfile.relations:
                subject_id = row.subj
                object_id = row.obj
                doc_id = subject_id.doc_id

                relation = row.reln
                provs = list(row.prov) if row.prov else []
                weight = row.weight
                relations.append((submission_id, doc_id, subject_id, object_id, relation, provs, weight))

            # mentions
            db.execute_values(cur, """INSERT INTO submission_mention (submission_id, doc_id, mention_id, canonical_id, mention_type, gloss) VALUES %s """, mentions)

            # links
            db.execute_values(cur, """INSERT INTO submission_link (submission_id, doc_id, mention_id, link_name, confidence) VALUES %s """, links)

            # relations
            db.execute_values(cur, """INSERT INTO submission_relation (submission_id, doc_id, subject_id, object_id, relation, provenances, confidence) VALUES %s """, relations)


if __name__ == '__main__':
    input_format = 'tackb'
    #mfile = MFile.from_stream(csv.reader(sys.stdin, delimiter='\t'), input_format)
    validate(sys.stdin, input_format = 'tackb')
    #test_sanitize_mention_response()
