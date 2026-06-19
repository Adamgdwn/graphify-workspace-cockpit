"""Decision, recommendation, and queue overlays for map nodes."""

from __future__ import annotations

import hashlib
import json
import re


def overlay_text(value: object, max_len: int = 220) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    if max_len <= 3:
        return text[:max_len]
    return text[: max_len - 3].rstrip() + "..."


def _normalize(value: object) -> str:
    text = str(value or "").replace("\\", "/").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip("`[]()")


def _path_prefixes(value: object) -> list[str]:
    text = _normalize(value)
    if "/" not in text:
        return []
    parts = [part for part in text.split("/") if part]
    return ["/".join(parts[:index]) for index in range(1, len(parts) + 1)]


def overlay_add_term(terms: set[str], value: object) -> None:
    text = _normalize(value)
    if not text:
        return
    terms.add(text)
    for prefix in _path_prefixes(text):
        terms.add(prefix)
    if "/" in text:
        for part in text.split("/"):
            if len(part) >= 3:
                terms.add(part)


def overlay_terms_for_node(
    node: dict,
    *,
    workspace_label: str = "",
    cluster_id: str = "",
) -> set[str]:
    terms: set[str] = set()
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    for key in (
        "id",
        "label",
        "source_file",
        "source_location",
        "source_root",
        "source_root_name",
        "repo_project_name",
        "repo",
        "container",
        "relative_path",
        "cluster",
        "_origin",
        "origin",
    ):
        overlay_add_term(terms, node.get(key))
    for key in ("kind", "language", "name", "path"):
        overlay_add_term(terms, metadata.get(key))
    overlay_add_term(terms, workspace_label)
    overlay_add_term(terms, cluster_id)
    return terms


def _split_record_text(value: object) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    chunks = re.split(r"↔|<->|-->|->|→|—|\n|,", text)
    cleaned: list[str] = []
    for chunk in chunks:
        item = re.sub(r"\s*\(\d+%?\)\s*$", "", chunk).strip(" `[]")
        if item:
            cleaned.append(item)
    return cleaned


def _record_terms(record: dict, keys: tuple[str, ...]) -> set[str]:
    terms: set[str] = set()
    for key in keys:
        raw = record.get(key)
        values = raw if isinstance(raw, list) else [raw]
        for value in values:
            if isinstance(value, dict):
                for nested in value.values():
                    for part in _split_record_text(nested):
                        overlay_add_term(terms, part)
                continue
            for part in _split_record_text(value):
                overlay_add_term(terms, part)
    return terms


def _recommendation_terms(rec: dict) -> set[str]:
    terms = _record_terms(
        rec,
        ("id", "title", "summary", "proposed_action", "mode", "evidence"),
    )
    action_plan = rec.get("action_plan") if isinstance(rec.get("action_plan"), dict) else {}
    for key in (
        "canonical_target",
        "merge_sources",
        "source_pairs",
        "concrete_steps",
        "acceptance_criteria",
        "open_questions",
    ):
        raw = action_plan.get(key)
        values = raw if isinstance(raw, list) else [raw]
        for value in values:
            for part in _split_record_text(value):
                overlay_add_term(terms, part)

    overlap = rec.get("overlap") if isinstance(rec.get("overlap"), dict) else {}
    for key in ("cluster_a", "cluster_b"):
        overlay_add_term(terms, overlap.get(key))
    top_pairs = overlap.get("top_pairs") if isinstance(overlap.get("top_pairs"), list) else []
    for pair in top_pairs:
        if not isinstance(pair, dict):
            continue
        for key in ("source", "target", "label_a", "label_b", "file_a", "file_b"):
            overlay_add_term(terms, pair.get(key))
    return terms


def _action_terms(action: dict) -> set[str]:
    terms = _record_terms(
        action,
        (
            "id",
            "description",
            "proposed_action_text",
            "evidence",
            "rec_title",
            "rec_summary",
            "target_path",
            "action_type",
        ),
    )
    action_plan = action.get("action_plan") if isinstance(action.get("action_plan"), dict) else {}
    for key in ("canonical_target", "merge_sources", "source_pairs", "concrete_steps"):
        raw = action_plan.get(key)
        values = raw if isinstance(raw, list) else [raw]
        for value in values:
            for part in _split_record_text(value):
                overlay_add_term(terms, part)
    return terms


def _meaningful(term: str) -> bool:
    if "/" in term:
        return len(term) >= 3
    return len(term) >= 3 and term not in {"src", "lib", "app", "api", "web", "the", "and"}


def _terms_match(target_terms: set[str], record_terms: set[str]) -> bool:
    target = {term for term in target_terms if _meaningful(term)}
    record = {term for term in record_terms if _meaningful(term)}
    if not target or not record:
        return False
    if target & record:
        return True
    path_targets = [term for term in target if "/" in term]
    path_records = [term for term in record if "/" in term]
    for left in path_targets:
        for right in path_records:
            if left.startswith(f"{right}/") or right.startswith(f"{left}/"):
                return True
            if left.endswith(f"/{right}") or right.endswith(f"/{left}"):
                return True
    return False


def _compact_decision(decision: dict) -> dict:
    return {
        "id": decision.get("id", ""),
        "target_id": decision.get("target_id", ""),
        "label": decision.get("label", ""),
        "classification": decision.get("classification", ""),
        "rationale": overlay_text(decision.get("rationale"), 240),
        "status": decision.get("status", ""),
        "updated_at": decision.get("updated_at") or decision.get("created_at", ""),
    }


def _compact_recommendation(rec: dict) -> dict:
    return {
        "id": rec.get("id", ""),
        "title": overlay_text(rec.get("title"), 140),
        "mode": rec.get("mode", ""),
        "status": rec.get("status", ""),
        "summary": overlay_text(rec.get("summary"), 260),
        "proposed_action": overlay_text(rec.get("proposed_action"), 260),
        "confidence": rec.get("confidence", 0.0),
        "risk": rec.get("risk", ""),
        "effort": rec.get("effort", ""),
        "updated_at": rec.get("updated_at") or rec.get("created_at", ""),
    }


def _compact_action(action: dict) -> dict:
    return {
        "id": action.get("id", ""),
        "source_recommendation_id": action.get("source_recommendation_id", ""),
        "status": action.get("status", ""),
        "action_type": action.get("action_type", ""),
        "description": overlay_text(action.get("description"), 180),
        "proposed_action_text": overlay_text(action.get("proposed_action_text"), 260),
        "target_path": action.get("target_path", ""),
        "updated_at": action.get("updated_at") or action.get("created_at", ""),
    }


def _state_hash(records: dict) -> str:
    payload = json.dumps(records, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()


def build_decision_overlay_context(
    *,
    decisions: list[dict],
    recommendations: list[dict],
    actions: list[dict],
) -> dict:
    active_decisions = [decision for decision in decisions if decision.get("status") == "active"]
    active_recommendations = [
        rec for rec in recommendations
        if str(rec.get("status", "pending")) in {"pending", "accepted", "deferred"}
    ]

    rec_terms: dict[str, set[str]] = {}
    compact_recommendations: dict[str, dict] = {}
    for rec in active_recommendations:
        rec_id = str(rec.get("id") or "")
        if not rec_id:
            continue
        rec_terms[rec_id] = _recommendation_terms(rec)
        compact_recommendations[rec_id] = _compact_recommendation(rec)

    action_terms: dict[str, set[str]] = {}
    compact_actions: dict[str, dict] = {}
    for action in actions:
        action_id = str(action.get("id") or "")
        if not action_id:
            continue
        action_terms[action_id] = _action_terms(action)
        compact_actions[action_id] = _compact_action(action)

    return {
        "decisions": [
            {
                "record": decision,
                "terms": _record_terms(decision, ("target_id", "label")),
                "compact": _compact_decision(decision),
            }
            for decision in sorted(
                active_decisions,
                key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
                reverse=True,
            )
        ],
        "recommendations": active_recommendations,
        "recommendation_terms": rec_terms,
        "compact_recommendations": compact_recommendations,
        "actions": actions,
        "action_terms": action_terms,
        "compact_actions": compact_actions,
        "hash": _state_hash({
            "decisions": active_decisions,
            "recommendations": active_recommendations,
            "actions": actions,
        }),
    }


def decision_overlay_for_terms(target_terms: set[str], context: dict) -> dict:
    matched_decisions: list[dict] = []
    for decision in context.get("decisions", []):
        if _terms_match(target_terms, decision["terms"]):
            matched_decisions.append(decision["compact"])

    matched_recs: list[dict] = []
    matched_rec_ids: set[str] = set()
    for rec_id, terms in context.get("recommendation_terms", {}).items():
        if _terms_match(target_terms, terms):
            matched_rec_ids.add(rec_id)
            matched_recs.append(context["compact_recommendations"][rec_id])

    matched_actions: list[dict] = []
    for action in context.get("actions", []):
        action_id = str(action.get("id") or "")
        source_rec_id = str(action.get("source_recommendation_id") or "")
        direct_match = _terms_match(
            target_terms,
            context.get("action_terms", {}).get(action_id, set()),
        )
        if direct_match or (source_rec_id and source_rec_id in matched_rec_ids):
            compact = context.get("compact_actions", {}).get(action_id)
            if compact:
                matched_actions.append(compact)

    primary_classification = (
        matched_decisions[0].get("classification")
        if matched_decisions
        else ""
    )
    next_actions: list[str] = []
    for rec in matched_recs[:2]:
        action_text = rec.get("proposed_action") or rec.get("summary") or rec.get("title")
        if action_text:
            next_actions.append(overlay_text(action_text, 180))
    for action in matched_actions[:2]:
        action_text = action.get("proposed_action_text") or action.get("description")
        if action_text:
            next_actions.append(overlay_text(action_text, 180))

    return {
        "decision_classification": primary_classification,
        "decision_count": len(matched_decisions),
        "recommendation_count": len(matched_recs),
        "queued_action_count": len(matched_actions),
        "decisions": matched_decisions[:4],
        "recommendations": matched_recs[:4],
        "queued_actions": matched_actions[:4],
        "next_actions": next_actions[:4],
    }
