import logging

from collections import defaultdict

from . import db
from . import evaluation
from . import distribution as PD
from .schema import Score


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_updated_scores(corpus_tag, mode='joint', interval=90, num_epochs=500):
    """
    Returns updates scores.
    """
    systems = []
    Ps, Xhs, Y0 = [], [], []

    logger.info("Getting distributions")
    Ps_ = {
        "entity": PD.submission_entity(corpus_tag),
        "relation": PD.submission_relation(corpus_tag),
        }

    logger.info("Getting samples")
    Y0_ = PD.Y0(corpus_tag)

    for score_type in ["entity", "relation"]:
        for submission_id, Xh in PD.Xh(corpus_tag, score_type).items():
            Ps.append(Ps_[score_type][submission_id])
            Xhs.append(Xh)
            Y0.append(Y0_[submission_id])
            systems.append((submission_id, score_type))
    P0 = defaultdict(lambda: 1.0) # TODO: maybe this should change?

    if mode == "joint":
        metrics = evaluation.joint_score_with_intervals(P0, Ps, Y0, Xhs, interval=interval, num_epochs=num_epochs)
    elif mode == "simple":
        metrics = evaluation.simple_score_with_intervals(P0, Ps, Y0, Xhs, interval=interval, num_epochs=num_epochs)
    else:
        raise ValueError("Unknown scoring mode {}", mode)

    return list(zip(systems, metrics))

def update_score(submission_id, score_type, entry, cur=None):
    """
    Actually update the in the table.
    """
    db.execute("""
        INSERT INTO submission_score (submission_id, score_type, score, left_interval, right_interval) VALUES
            (%(submission_id)s, %(score_type)s, %(score)s::score, %(left_interval)s::score, %(right_interval)s::score)""",
               submission_id=submission_id,
               score_type=score_type,
               score=(entry.p, entry.r, entry.f1),
               left_interval=(entry.p_left, entry.r_left, entry.f1_left),
               right_interval=(entry.p_right, entry.r_right, entry.f1_right),
               cur=cur)

def test_update_score():
    try:
        with db.CONN:
            with db.CONN.cursor() as cur:
                update_score(1, "entity", Score(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9), cur=cur)
                assert False

    except AssertionError:
        pass
