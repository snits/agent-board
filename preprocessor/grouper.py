# ABOUTME: Flattens parsed transcript records into a sorted message list.
# ABOUTME: Resolves promptId via parentUuid chain and attaches teamName.


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


def flatten_messages(
    records: list[dict],
    team_names: dict[str, str],
) -> list[dict]:
    """Flatten parsed records into a sorted message list with teamName."""
    records_by_uuid = {r["uuid"]: r for r in records if r.get("uuid")}

    result = []
    for record in records:
        prompt_id = resolve_prompt_id(record, records_by_uuid)
        if not prompt_id:
            prompt_id = "__main__"
        default_name = "Main Conversation" if prompt_id == "__main__" else "Unnamed Meeting"
        record["teamName"] = team_names.get(prompt_id, default_name)
        result.append(record)

    result.sort(key=lambda m: m.get("timestamp") or "")
    return result
