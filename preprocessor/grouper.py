# ABOUTME: Groups parsed transcript records into meetings by promptId.
# ABOUTME: Handles promptId inheritance via parentUuid chain walking.


def resolve_prompt_id(record: dict, records_by_uuid: dict) -> str | None:
    """Resolve the promptId for a record by walking the parentUuid chain."""
    current = record
    seen = set()
    while current:
        uid = current.get("uuid")
        if uid in seen:
            break
        seen.add(uid)

        prompt_id = current.get("promptId")
        if prompt_id:
            return prompt_id

        parent_uuid = current.get("parentUuid")
        if not parent_uuid:
            break
        current = records_by_uuid.get(parent_uuid)

    return None


def group_into_meetings(
    records: list[dict],
    team_names: dict[str, str],
) -> dict[str, dict]:
    """Group parsed records into meetings keyed by promptId."""
    records_by_uuid = {r["uuid"]: r for r in records if r.get("uuid")}

    meetings: dict[str, list] = {}
    for record in records:
        prompt_id = resolve_prompt_id(record, records_by_uuid)
        if not prompt_id:
            continue
        meetings.setdefault(prompt_id, []).append(record)

    result = {}
    for prompt_id, msgs in meetings.items():
        sorted_msgs = sorted(msgs, key=lambda m: m.get("timestamp", ""))

        timestamps = [m["timestamp"] for m in sorted_msgs if m.get("timestamp")]
        start_time = timestamps[0] if timestamps else None
        end_time = timestamps[-1] if timestamps else None

        agent_counts: dict[str, int] = {}
        for m in sorted_msgs:
            aid = m.get("agentId")
            if aid:
                agent_counts[aid] = agent_counts.get(aid, 0) + 1

        result[prompt_id] = {
            "id": prompt_id,
            "teamName": team_names.get(prompt_id, "Unnamed Meeting"),
            "startTime": start_time,
            "endTime": end_time,
            "agentIds": list(agent_counts.keys()),
            "messages": sorted_msgs,
        }

    return result
