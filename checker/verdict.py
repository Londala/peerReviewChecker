from models import SourceResult, Verdict

CONFIDENCE_THRESHOLD = 0.6


def aggregate(results: list[SourceResult]) -> Verdict:
    conclusive = [r for r in results if r.peer_reviewed is not None]
    if not conclusive:
        best_conf = max((r.confidence for r in results), default=0.0)
        return Verdict(peer_reviewed=None, confidence=best_conf, sources=results)

    best = max(conclusive, key=lambda r: r.confidence)
    if best.confidence < CONFIDENCE_THRESHOLD:
        return Verdict(peer_reviewed=None, confidence=best.confidence, sources=results)

    return Verdict(peer_reviewed=best.peer_reviewed, confidence=best.confidence, sources=results)
