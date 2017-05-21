-- Exports all the data for a given corpus_tag (given as input :tag)
\COPY (SELECT 
    d.id,
    d.updated,
    d.title,
    d.doc_date,
    d.doc_length,
    d.doc_digest,
    gloss
    FROM document d,
         document_tag t
    WHERE d.doc_id = t.doc_id
    AND t.tag = :tag
    ORDER BY t.doc_id)
TO 'document.tsv' CSV HEADER DELIMITER E'\t';

\COPY (SELECT 
    t.doc_id,
    t.tag
    FROM document_tag t
    WHERE  t.tag = :tag
    ORDER BY t.doc_id)
TO 'document_tag.tsv' CSV HEADER DELIMITER E'\t';

\COPY (SELECT 
    s.id,
    s.updated,

    s.doc_id,
    s.span,
    s.sentence_index,

    s.token_spans,
    s.words,
    s.lemmas,
    s.pos_tags,
    s.ner_tags,
    s.gloss,
    s.dependencies,

    FROM sentence s,
    document_tag t
    WHERE s.doc_id = t.doc_id
    AND t.tag = :tag
    ORDER BY t.doc_id)
TO 'sentence.tsv' CSV HEADER DELIMITER E'\t';

\COPY (SELECT 
    m.doc_id,
    m.span,
    m.updated,

    m.sentence_id,

    m.mention_type,
    m.canonical_span,
    m.gloss

    FROM suggested_mention m,
    document_tag t
    WHERE m.doc_id = t.doc_id
    AND t.tag = :tag
    ORDER BY t.doc_id)
TO 'suggested_mention.tsv' CSV HEADER DELIMITER E'\t';

\COPY (SELECT 
    m.doc_id,
    m.span,
    m.updated,

    m.link_name,
    m.confidence

    FROM suggested_link m,
    document_tag t
    WHERE m.doc_id = t.doc_id
    AND t.tag = :tag
    ORDER BY t.doc_id)
TO 'suggested_link.tsv' CSV HEADER DELIMITER E'\t';
