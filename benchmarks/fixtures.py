"""Fixed templates and seeded distractors. Labels never enter retrieval state."""

import random


SEEDS = (11, 29, 47)
SCALES = (24, 96, 240)
CATEGORIES = ("direct", "associative", "temporal_update", "procedure", "abstention")


def make_fixture(seed=11, scale=24):
    rng = random.Random(seed)
    entities, history, questions = {}, [], []
    created, revised = "2026-09-01T09:00:00+00:00", "2026-09-04T09:00:00+00:00"

    def record(dataset, name, title, content, *, kind="fact", cues=(), links=(), version=1, at=created):
        key = f"{dataset}-{seed}-{name}"
        payload = {"title": title, "content": content, "kind": kind, "cues": list(cues), "links": list(links),
                   "related_ids": [], "dataset": dataset, "status": "accepted", "synthetic": True,
                   "visibility": "shared", "source_trust": "system_event", "valid_from": at,
                   "source": {"title": "Synthetic fixture evidence", "text": content, "occurred_at": at,
                              "speaker": "synthetic-user", "platform": "synthetic", "session_id": dataset}}
        item = {"id": key, "kind": "memory", "version": version, "updated_at": at, "payload": payload}
        entities[key] = item
        history.append(item)
        return key

    scenarios = (
        ("personal", "Lumen", "amber hinge", "holiday rail reservation", "evening sleeper", "morning express",
         "Meals are vegan and contain no peanuts.", "Sleeper berths failed the accessibility inspection.",
         "Verify passenger names, request accessible seating, then save the confirmation code."),
        ("team", "Cedar", "cobalt lantern", "weekly review location", "west annex", "east studio",
         "All reviews require a written agenda.", "An acoustic survey measured excessive background noise.",
         "Collect agenda items, assign a facilitator, then publish the meeting notes."),
        ("technical", "Nimbus", "silver orchard", "sensor capture configuration", "six lenses", "four lenses",
         "Calibration artifacts require a signed checksum.", "Thermal measurements exceeded the enclosure limit.",
         "Disconnect power, align the reference target, then record the calibration matrix."),
    )
    for dataset, project, nickname, subject, old, current, preference, reason, steps in scenarios:
        preference_id = record(dataset, "constraint", f"{project} standing constraint", preference, kind="core")
        decision_id = record(dataset, "decision", f"{project} {subject}", f"Selected {old}.", kind="decision")
        record(dataset, "decision", f"{project} {subject}", f"Selected {current}.", kind="decision", version=2, at=revised)
        evidence_id = record(dataset, "evidence", "Instrument receipt", reason, kind="episode")
        episode_id = record(dataset, "episode", f"{project} retired approach {nickname}",
                            "The previous arrangement was abandoned after the recorded inspection.", kind="episode",
                            cues=(nickname,), links=({"target_id": evidence_id, "relation": "DERIVED_FROM"},))
        procedure_id = record(dataset, "procedure", f"{project} {subject} workflow", steps, kind="procedure")
        for index in range(scale):
            words = rng.sample(("archive", "inventory", "draft", "ledger", "review", "booking", "sensor", "agenda",
                                "shipment", "receipt", "enclosure", "meeting", "passenger", "calibration", "noise"), 5)
            record(dataset, f"noise-{index:04}", f"{rng.choice(('Archive', 'Draft', 'Inventory'))} {index}",
                   " ".join(words) + f" Batch {rng.randrange(1000, 9999)} is unrelated to the requested decision.")

        def question(name, category, query, relevant, **options):
            questions.append({"id": f"{dataset}-{name}", "dataset": dataset, "category": category, "query": query,
                              "relevant_ids": relevant, "as_of": options.get("as_of"),
                              "expected_versions": options.get("expected_versions", {}), "unanswerable": not relevant})

        question("constraint", "direct", f"{project} standing constraint", [preference_id])
        question("reason", "associative", f"Why did {project} retire the {nickname} approach?", [episode_id, evidence_id])
        question("cue", "associative", f"Explain {nickname}", [episode_id, evidence_id])
        question("current", "temporal_update", f"{project} {subject}", [decision_id], expected_versions={decision_id: 2})
        question("past", "temporal_update", f"{project} {subject}", [decision_id],
                 as_of="2026-09-02T12:00:00+00:00", expected_versions={decision_id: 1})
        question("steps", "procedure", f"How does {project} {subject} workflow work?", [procedure_id])
        question("missing", "abstention", f"xylophonicquartz{seed} zetaquantumreceipt", [])
        question("missing-in-scope", "abstention", f"What is the {project} archive decryption secret?", [])

    return {"revision": len(history), "entities": entities, "history": history}, questions
