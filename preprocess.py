# ABOUTME: CLI entry point for the agent board preprocessor.
# ABOUTME: Scans claude's project storage and outputs browsable JSON.

import argparse
import json
import sys
from pathlib import Path

from preprocessor.config import load_config, apply_config
from preprocessor.paths import default_data_dir
from preprocessor.scanner import scan_projects
from preprocessor.parser import parse_record
from preprocessor.grouper import group_into_meetings
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
    all_records = []
    seen_uuids = set()
    for jsonl_file in sorted(Path(subagents_dir).glob("agent-*.jsonl")):
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
    """Process a single session into meeting data."""
    subagents_dir = Path(session["subagentsDir"])
    records = parse_agent_transcripts(subagents_dir)
    meetings = group_into_meetings(records, team_names)

    all_timestamps = []
    for meeting in meetings.values():
        if meeting.get("startTime"):
            all_timestamps.append(meeting["startTime"])
        if meeting.get("endTime"):
            all_timestamps.append(meeting["endTime"])
    all_timestamps.sort()

    return {
        "id": session["id"],
        "meetings": meetings,
        "agentMeta": agent_meta,
        "startTime": all_timestamps[0] if all_timestamps else None,
        "endTime": all_timestamps[-1] if all_timestamps else None,
    }


def run_preprocess(source_dir: Path, output_dir: Path) -> None:
    """Run the full preprocessing pipeline."""
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)

    projects = scan_projects(source_dir)
    all_agent_types = set()
    index_projects = []

    for project in projects:
        index_sessions = []
        for session in project["sessions"]:
            team_names = parse_main_conversation(session.get("mainJsonl"))
            agent_meta = parse_agent_meta(session["subagentsDir"])
            for meta in agent_meta.values():
                all_agent_types.add(meta.get("agentType", "unknown"))

            session_data = process_session(session, team_names, agent_meta)
            write_session(output_dir, session_data)

            unique_types = {m.get("agentType", "unknown") for m in agent_meta.values()}
            index_sessions.append({
                "id": session["id"],
                "startTime": session_data.get("startTime"),
                "endTime": session_data.get("endTime"),
                "meetingCount": len(session_data["meetings"]),
                "agentCount": len(unique_types),
            })

        index_projects.append({
            "slug": project["slug"],
            "displayName": project["displayName"],
            "sessions": index_sessions,
        })

    write_index(output_dir, index_projects)
    write_agent_types(output_dir, all_agent_types)

    total_meetings = sum(s["meetingCount"] for p in index_projects for s in p["sessions"])
    total_agents = sum(s["agentCount"] for p in index_projects for s in p["sessions"])
    print(f"Processed {len(index_projects)} projects, {total_meetings} meetings, {total_agents} agents")
    print(f"Output written to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Preprocess Claude Code agent teams transcripts")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / ".claude" / "projects",
        help="Source directory to scan (default: ~/.claude/projects/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_data_dir(),
        help="Output directory (default: ~/.local/share/agent-board/)",
    )
    apply_config(parser, load_config())
    args = parser.parse_args()
    run_preprocess(args.source, args.output)


if __name__ == "__main__":
    main()
