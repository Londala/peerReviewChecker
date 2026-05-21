import json
from models import Verdict


def format_human(verdict: Verdict, article_label: str = "") -> str:
    prefix = f"{article_label}: " if article_label else ""
    if verdict.peer_reviewed is True and verdict.confidence >= 0.6:
        status = f"✓ Peer-reviewed (confidence: {verdict.confidence:.0%})"
    elif verdict.peer_reviewed is False and verdict.confidence >= 0.6:
        status = f"✗ Not peer-reviewed (confidence: {verdict.confidence:.0%})"
    elif verdict.confidence < 0.4:
        status = f"~ Likely Not Reviewed (confidence: {verdict.confidence:.0%})"
    else:
        status = f"? Inconclusive (best confidence: {verdict.confidence:.0%})"

    lines = [prefix + status]
    for src in verdict.sources:
        if src.found:
            lines.append(f"  [{src.source}] {src.evidence}")
    return "\n".join(lines)


def format_json(verdict: Verdict) -> str:
    return json.dumps(
        {
            "peer_reviewed": verdict.peer_reviewed,
            "confidence": round(verdict.confidence, 4),
            "sources": [
                {
                    "source": s.source,
                    "found": s.found,
                    "peer_reviewed": s.peer_reviewed,
                    "confidence": round(s.confidence, 4),
                    "evidence": s.evidence,
                }
                for s in verdict.sources
            ],
        },
        indent=2,
    )
