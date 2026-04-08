"""Processing pipeline — orchestrates classification, PII detection, scoring, and reflection."""

import logging
import threading

from backend.app import database as db
from backend.app.services import classifier, pii

logger = logging.getLogger(__name__)

_processing = False
_processing_lock = threading.Lock()


def is_processing() -> bool:
    return _processing


def process_captures(batch_size: int = 5) -> None:
    """Process unclassified captures through the full pipeline.

    Runs in a background thread to avoid blocking the API.
    """
    global _processing

    with _processing_lock:
        if _processing:
            return
        _processing = True

    thread = threading.Thread(target=_run_pipeline, args=(batch_size,), daemon=True)
    thread.start()


def _run_pipeline(batch_size: int) -> None:
    """Run the classification pipeline on unclassified or low-confidence captures."""
    global _processing

    try:
        # Get captures that need processing (no category or low confidence)
        all_captures = db.list_captures(limit=500)
        to_process = [
            c for c in all_captures
            if not c.get("category") or c.get("confidence", 0) < 0.3
        ][:batch_size]

        if not to_process:
            # Re-process low confidence captures
            to_process = sorted(
                [c for c in all_captures if c.get("confidence", 0) < 0.7],
                key=lambda x: x.get("confidence", 0),
            )[:batch_size]

        if not to_process:
            db.add_activity("CAPTURE", f"All {len(all_captures)} captures look good! Nothing to reprocess.")
            return

        db.add_activity("CAPTURE", f"Starting pipeline on {len(to_process)} captures...")

        for capture in to_process:
            cap_id = capture["id"]
            content = capture.get("content", "")

            # Step 1: Classify
            db.add_activity("AIRIA", f"Classifying capture {cap_id}...", cap_id)
            result = classifier.classify_content(content, capture.get("type", "text"))

            updates = {
                "category": result["category"],
                "tags": result["tags"],
                "summary": result["summary"],
                "confidence": result["confidence"],
            }
            if result.get("source_app"):
                updates["source_app"] = result["source_app"]

            db.update_capture(cap_id, updates)
            db.add_activity(
                "AIRIA",
                f"Classified as '{result['category']}' ({result['confidence']:.0%} confident) — {result.get('summary', '')[:80]}",
                cap_id,
            )

            # Step 2: PII Detection
            db.add_activity("DLP", f"Scanning for PII in {cap_id}...", cap_id)
            has_pii, pii_types = pii.detect_pii(content)
            if has_pii:
                db.update_capture(cap_id, {"has_pii": True, "pii_details": pii_types})
                db.add_activity("DLP", f"⚠️ Found PII: {', '.join(pii_types)} in {cap_id}", cap_id)

                # Create protection feed card
                db.insert_feed_card({
                    "id": f"protect-{cap_id}",
                    "type": "protection",
                    "title": "I protected your personal info",
                    "body": f"Found {', '.join(pii_types)} in a capture. I've flagged it for your review.",
                    "reasoning": f"Detected {len(pii_types)} type(s) of sensitive data.",
                    "actions": [{"id": "review", "label": "Review"}, {"id": "dismiss", "label": "Dismiss"}],
                })
            else:
                db.add_activity("DLP", f"No PII found in {cap_id} ✓", cap_id)

            # Step 3: Self-evaluate
            db.add_activity("BRAINTRUST", f"Scoring my classification of {cap_id}...", cap_id)
            eval_result = classifier.self_evaluate(
                content, result["category"], result["tags"], result.get("summary", "")
            )
            quality = eval_result.get("quality", "B")
            confidence = eval_result.get("confidence", result["confidence"])
            db.update_capture(cap_id, {"quality": quality, "confidence": confidence})
            db.add_activity(
                "BRAINTRUST",
                f"Quality: {quality} · Confidence: {confidence:.0%} — {eval_result.get('reasoning', '')}",
                cap_id,
            )

            # Step 4: Reflect if low confidence
            if confidence < 0.7:
                db.add_activity(
                    "REFLECTION",
                    f"Only {confidence:.0%} confident about {cap_id}... let me rethink this.",
                    cap_id,
                )
                improved = classifier.reflect_and_reclassify(
                    content, result["category"], result["tags"], confidence
                )
                if improved:
                    db.update_capture(cap_id, {
                        "category": improved["category"],
                        "tags": improved["tags"],
                        "summary": improved.get("summary", result.get("summary", "")),
                        "confidence": improved["confidence"],
                    })
                    db.add_activity(
                        "REFLECTION",
                        f"Reclassified to '{improved['category']}' with {improved['confidence']:.0%} confidence ✓",
                        cap_id,
                    )

                    # Create insight feed card about the reflection
                    db.insert_feed_card({
                        "id": f"reflect-{cap_id}",
                        "type": "insight",
                        "title": "I improved my understanding",
                        "body": f"Reclassified a capture from '{result['category']}' to '{improved['category']}' — confidence went from {confidence:.0%} to {improved['confidence']:.0%}.",
                        "reasoning": "Self-reflection detected a better classification.",
                        "actions": [{"id": "dismiss", "label": "Got it"}],
                    })
                else:
                    db.add_activity("REFLECTION", f"Couldn't improve — keeping original classification.", cap_id)

        # Generate synthesis insight
        _generate_synthesis()

        db.add_activity("CAPTURE", f"Pipeline complete! Processed {len(to_process)} captures.")

    except Exception as e:
        logger.error("Pipeline error: %s", e)
        db.add_activity("CAPTURE", f"Pipeline encountered an error: {str(e)[:100]}")
    finally:
        _processing = False


def _generate_synthesis() -> None:
    """Generate cross-capture insights."""
    counts = db.category_counts()
    total = db.capture_count()

    if total < 3:
        return

    # Find dominant category
    if counts:
        top_cat = max(counts, key=counts.get)
        top_count = counts[top_cat]

        if top_count >= 3:
            db.insert_feed_card({
                "id": f"synthesis-{top_cat}",
                "type": "synthesis",
                "title": f"I noticed a pattern in your saves",
                "body": f"You have {top_count} captures in '{top_cat}' — that's {top_count/total:.0%} of your knowledge base. Looks like this is a focus area for you.",
                "reasoning": f"Detected concentration in {top_cat} category across {total} total captures.",
                "actions": [{"id": "dismiss", "label": "Interesting!"}],
            })

    db.add_activity("SYNTHESIS", f"Analyzed patterns across {total} captures in {len(counts)} categories.")
