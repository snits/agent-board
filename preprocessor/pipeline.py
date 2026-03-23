# ABOUTME: Full preprocessing pipeline for agent board data.
# ABOUTME: Scans claude's project storage and outputs browsable JSON.

import json
from pathlib import Path

from preprocessor.scanner import scan_projects, scan_archive
from preprocessor.parser import parse_record
from preprocessor.grouper import flatten_messages
from preprocessor.writer import write_session, write_index, write_agent_types


def parse_main_conversation(jsonl_path: Path) -> dict[str, str]:
    """Parse main conversation JSONL to extract promptId → teamName mapping."""
    team_names = {}
    if not jsonl_path or not Path(jsonl_path).exists():
        return team_names

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            team_name = record.get("teamName")
            prompt_id = record.get("promptId")
            if team_name and prompt_id:
                team_names[prompt_id] = team_name

    return team_names


def parse_agent_meta(subagents_dir: Path) -> dict[str, dict]:
    """Parse all agent meta.json files in a subagents directory."""
    meta = {}
    for meta_file in sorted(Path(subagents_dir).glob("agent-*.meta.json")):
        agent_id = meta_file.stem.replace(".meta", "").replace("agent-", "")
        try:
            data = json.loads(meta_file.read_text())
            meta[agent_id] = data
        except json.JSONDecodeError:
            continue
    return meta


def parse_agent_transcripts(subagents_dir: Path) -> list[dict]:
    """Parse all agent JSONL files and return a deduplicated list of parsed records.

    Team lead broadcast messages appear in every agent's JSONL with the same UUID.
    We keep only the first occurrence of each UUID."""
    return _parse_jsonl_files(sorted(Path(subagents_dir).glob("agent-*.jsonl")))


def _parse_jsonl_files(jsonl_files: list[Path]) -> list[dict]:
    """Parse a list of JSONL files into deduplicated parsed records."""
    all_records = []
    seen_uuids = set()
    for jsonl_file in jsonl_files:
        with open(jsonl_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                parsed = parse_record(raw)
                if parsed:
                    uuid = parsed.get("uuid")
                    if uuid and uuid in seen_uuids:
                        continue
                    if uuid:
                        seen_uuids.add(uuid)
                    all_records.append(parsed)
    return all_records


def process_session(session: dict, team_names: dict, agent_meta: dict) -> dict:
    """Process a single session into a flat message list."""
    if session.get("agentJsonls"):
        records = _parse_jsonl_files([Path(p) for p in session["agentJsonls"]])
    elif session.get("subagentsDir"):
        records = parse_agent_transcripts(Path(session["subagentsDir"]))
    else:
        records = []
    messages = flatten_messages(records, team_names)

    timestamps = [m["timestamp"] for m in messages if m.get("timestamp")]
    timestamps.sort()

    return {
        "id": session["id"],
        "messages": messages,
        "agentMeta": agent_meta,
        "startTime": timestamps[0] if timestamps else None,
        "endTime": timestamps[-1] if timestamps else None,
    }


def _merge_projects(native: list[dict], archive: list[dict]) -> list[dict]:
    """Merge native and archive project lists, combining sessions for shared slugs."""
    by_slug = {}
    for project in native:
        by_slug[project["slug"]] = {
            "slug": project["slug"],
            "displayName": project["displayName"],
            "sessions": list(project["sessions"]),
        }
    for project in archive:
        if project["slug"] in by_slug:
            existing_ids = {s["id"] for s in by_slug[project["slug"]]["sessions"]}
            for session in project["sessions"]:
                if session["id"] not in existing_ids:
                    by_slug[project["slug"]]["sessions"].append(session)
        else:
            by_slug[project["slug"]] = {
                "slug": project["slug"],
                "displayName": project["displayName"],
                "sessions": list(project["sessions"]),
            }
    return sorted(by_slug.values(), key=lambda p: p["slug"])


def run_preprocess(source_dir: Path, output_dir: Path, archive_dir: Path | None = None) -> None:
    """Run the full preprocessing pipeline."""
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)

    native_projects = scan_projects(source_dir)
    archive_projects = scan_archive(archive_dir) if archive_dir else []
    projects = _merge_projects(native_projects, archive_projects)
    all_agent_types = set()
    index_projects = []

    for project in projects:
        index_sessions = []
        for session in project["sessions"]:
            team_names = parse_main_conversation(session.get("mainJsonl"))
            subagents_dir = session.get("subagentsDir")
            agent_meta = parse_agent_meta(subagents_dir) if subagents_dir else {}
            for meta in agent_meta.values():
                all_agent_types.add(meta.get("agentType", "unknown"))

            session_data = process_session(session, team_names, agent_meta)
            write_session(output_dir, session_data)

            if not session_data.get("startTime"):
                continue

            unique_types = {m.get("agentType", "unknown") for m in agent_meta.values()}
            index_sessions.append({
                "id": session["id"],
                "startTime": session_data.get("startTime"),
                "endTime": session_data.get("endTime"),
                "agentCount": len(unique_types),
            })

        index_projects.append({
            "slug": project["slug"],
            "displayName": project["displayName"],
            "sessions": index_sessions,
        })

    write_index(output_dir, index_projects)
    write_agent_types(output_dir, all_agent_types)

    total_agents = sum(s["agentCount"] for p in index_projects for s in p["sessions"])
    print(f"Processed {len(index_projects)} projects, {total_agents} agents")
    print(f"Output written to {output_dir}")
