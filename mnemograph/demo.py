from .models import Memory, Write, Message
from .store import fingerprint


SAMPLES = [
    ("A shared memory, independent agents", "decision", "Agents share durable project knowledge through one service. MCP and REST use the same identity and scope checks.", ["agent integration", "shared memory"]),
    ("PACE starts with a small handle", "procedure", "Recall compact memory handles, inspect the evidence path, then expand only the source needed for the current step.", ["shared memory", "progressive recall"]),
    ("Four cameras approved", "decision", "The six-camera rig was rejected because of physical mounting complexity. A four-camera configuration was accepted for the prototype.", ["camera rig", "hardware constraints"]),
    ("Mounting trial found unstable brackets", "episode", "Synthetic bench observation: extra brackets increased setup effort and calibration drift. This supports the camera count decision.", ["hardware constraints", "calibration"]),
    ("Calibration before capture", "procedure", "Run a calibration check before collecting camera images. Record the calibration result with each batch.", ["calibration", "camera rig"]),
    ("Storage follows the workload", "fact", "SQLite is the supported local store. FalkorDB is optional and requires separate server verification. Database choice does not change the memory contract.", ["storage", "shared memory"]),
    ("Conflicts preserve the accepted revision", "fact", "An update must include expected_version. Conflicting writers get a conflict response and must inspect current evidence before retrying.", ["coordination", "shared memory"]),
    ("Handoffs carry source references", "procedure", "Assign a task to a provisioned agent with memory IDs, unresolved work, and a version. The receiving agent recalls and expands its evidence.", ["coordination", "agent integration"]),
]


def seed(service, scope):
    receipts = []
    for index, (title, kind, content, cues) in enumerate(SAMPLES):
        memory = Memory(title=title, kind=kind, content=content, cues=cues, status="accepted", synthetic=True,
                        source={"title": "Synthetic design notebook", "text": content, "uri": "demo:design-notebook"})
        receipts.append(service.save(scope, Write(memory=memory, idempotency_key=f"sample-v{3 if index == 5 else 1}-{index}")))
    return {"synthetic": True, "memories": len(receipts), "receipts": receipts}


SCENARIOS = {
    "personal-assistant": {
        "label": "Everyday assistant", "platform": "ChatGPT-style synthetic demo",
        "messages": [
            ("user", "I am Maya. I prefer vegetarian meals and quick dinners after work."),
            ("assistant", "I will use vegetarian, quick-to-cook recipes when you ask for dinner ideas."),
            ("user", "For my coastal weekend I want to take the Saturday train. Keep the trip relaxed."),
            ("assistant", "Your current travel plan is a relaxed weekend using the Saturday train."),
            ("user", "Please help me study Spanish for twenty minutes each weekday evening."),
            ("assistant", "A short weekday routine can start with vocabulary, then listening, then a recap."),
            ("user", "I usually forget chargers. Put a charger check into my packing checklist."),
            ("assistant", "Before you leave: check your bag, charger, ticket, and weather forecast."),
            ("user", "The coastal rail line is closed for maintenance. Change my plan to the express coach instead of the train."),
            ("assistant", "The revised plan should use the express coach. Preserve the earlier train plan as history."),
        ],
        "memories": [
            ("Vegetarian dinners after work", "core", "Maya prefers quick vegetarian dinners after work.", ["Maya", "dinner", "vegetarian"], 0, []),
            ("Original coastal travel preference", "episode", "Maya initially planned a relaxed coastal weekend by Saturday train.", ["coastal weekend", "train"], 2, []),
            ("Weekend transport plan", "decision", "The current weekend plan uses the Saturday train.", ["coastal weekend", "train", "travel plan"], 2, [(1,"DERIVED_FROM")]),
            ("Weekday Spanish routine", "procedure", "Study Spanish for twenty minutes each weekday evening.", ["Spanish", "weekday learning"], 4, []),
            ("Packing checklist includes chargers", "procedure", "Check the charger before leaving for a trip.", ["packing", "charger", "coastal weekend"], 6, []),
            ("Rail maintenance changes available routes", "episode", "The coastal rail line is closed for maintenance; the user requests the express coach.", ["coastal weekend", "rail maintenance", "express coach"], 8, []),
        ],
        "evolution": {"index":2,"message":8,"content":"The revised weekend plan uses the express coach because the coastal rail line is closed for maintenance.",
                      "cues":["coastal weekend","express coach","rail maintenance"],"link_index":5},
    },
    "camera-lab": {
        "label":"Camera lab", "platform":"Synthetic engineering assistant",
        "messages":[("user","The six-camera prototype has unstable brackets and calibration drift."),
                    ("assistant","Record the mounting result before choosing the final camera count."),
                    ("user","Use four cameras for the next test. The bench has four stable mounting points."),
                    ("assistant","The current proposal uses four cameras and a calibration check before capture."),
                    ("user","New coverage tests show the two overhead cameras cover the required angles. Change the prototype to two cameras.")],
        "memories":[("Unstable six-camera bench", "episode","The six-camera rig had unstable brackets and calibration drift.",["camera rig","mounting","calibration"],0,[]),
                    ("Camera architecture", "decision","Four cameras were selected for the next prototype test.",["camera rig","four cameras","mounting"],2,[(0,"DERIVED_FROM")]),
                    ("Calibrate before capture", "procedure","Run a calibration check before collecting a camera batch.",["camera rig","calibration"],3,[]),
                    ("Overhead coverage result", "episode","Two overhead cameras covered the required angles in the new test.",["coverage test","two cameras"],4,[])],
        "evolution":{"index":1,"message":4,"content":"The prototype now uses two overhead cameras after the new coverage test.",
                     "cues":["camera rig","two cameras","coverage test"],"link_index":3},
    },
    "team-planning": {
        "label":"Team planning", "platform":"Synthetic team assistant",
        "messages":[("user","We will run the Atlas release workshop in person on Friday."),
                    ("assistant","Keep the release checklist and workshop notes connected."),
                    ("user","The meeting room is unavailable. Move the Friday workshop online."),
                    ("assistant","Use a video call, share the release checklist, and record open blockers.")],
        "memories":[("Original workshop agreement","episode","The Atlas release workshop was initially planned in person on Friday.",["Atlas","workshop","meeting room"],0,[]),
                    ("Workshop format","decision","The release workshop is planned in person.",["Atlas","in person","meeting room"],0,[(0,"DERIVED_FROM")]),
                    ("Room booking changed","episode","The meeting room is unavailable and the workshop must move online.",["Atlas","online workshop","room unavailable"],2,[]),
                    ("Release workshop procedure","procedure","Share the release checklist and record open blockers.",["Atlas","release checklist","workshop"],3,[])],
        "evolution":{"index":1,"message":2,"content":"The Atlas Friday workshop now runs online because the meeting room is unavailable.",
                     "cues":["Atlas","online workshop","room unavailable"],"link_index":2},
    },
}


def seed_dataset(service, scope, dataset):
    scenario, message_ids, memory_ids, receipts = SCENARIOS[dataset], [], [], []
    for index, (role, text) in enumerate(scenario["messages"]):
        command = Message(role=role,text=text,at=f"2026-10-{14+index//4:02d}T{9+index%4:02d}:00:00+05:30",
                          platform=scenario["platform"],session_id=f"synthetic-{dataset}-{index//4}",dataset=dataset,
                          synthetic=True,idempotency_key=f"dataset-v2:{dataset}:message:{index}")
        message_ids.append(service.ingest_message(scope,command)["id"])
    for index, (title, kind, content, cues, source_index, links) in enumerate(scenario["memories"]):
        source_message = service.view(scope)["entities"][message_ids[source_index]]["payload"]
        memory = Memory(title=title,kind=kind,content=content,cues=cues,synthetic=True,dataset=dataset,status="accepted",
                        source_message_id=message_ids[source_index],source_trust="user_stated" if source_message["role"]=="user" else "agent_derived",
                        source={"title":f"Synthetic {source_message['role']} message", "text":source_message["text"],
                                "occurred_at":source_message["at"],"speaker":source_message["role"],"platform":source_message["platform"],"session_id":source_message["session_id"]},
                        links=[{"target_id":memory_ids[target],"relation":relation} for target,relation in links])
        receipt = service.save(scope,Write(memory=memory,idempotency_key=f"dataset-v2:{dataset}:memory:{index}"))
        memory_ids.append(receipt["id"])
        receipts.append(receipt)
    return {"dataset":dataset,"synthetic":True,"messages":len(message_ids),"memories":len(memory_ids),"memory_ids":memory_ids,"receipts":receipts}


def evolve_dataset(service, scope, dataset):
    seeded = seed_dataset(service,scope,dataset)
    evolution = SCENARIOS[dataset]["evolution"]
    memory_id = seeded["memory_ids"][evolution["index"]]
    state = service.view(scope)
    current = state["entities"][memory_id]
    key = f"dataset-v2:{dataset}:evolve"
    original = next(record for record in state["history"] if record["id"]==memory_id and record["version"]==1)
    payload = {**original["payload"],"content":evolution["content"],"cues":evolution["cues"],
               "links":[{"target_id":seeded["memory_ids"][evolution["link_index"]],"relation":"DERIVED_FROM"}]}
    source_id = "msg-"+fingerprint([scope.agent,f"dataset-v2:{dataset}:message:{evolution['message']}"])[:16]
    message = state["entities"][source_id]["payload"]
    payload.update(source_message_id=source_id,source={"title":"Synthetic change of plan","text":message["text"],"occurred_at":message["at"],
                   "speaker":message["role"],"platform":message["platform"],"session_id":message["session_id"]})
    receipt = service.save(scope,Write(memory=Memory(**payload),expected_version=1,idempotency_key=key),memory_id)
    return {"dataset":dataset,"id":memory_id,"before_version":1,"after_version":receipt["version"],"receipt":receipt,"synthetic":True}
