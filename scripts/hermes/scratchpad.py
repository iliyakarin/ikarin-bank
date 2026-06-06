#!/usr/bin/env python3
"""
Context Scratchpad Engine

Manages a .hermes_scratchpad.md file storing:
  - Current Status (overwritten each run)
  - Task Backlog (preserved across runs)
  - Error Log (compressed terminal output)
  - File State Snapshots

Usage:
    python3 scripts/hermes/scratchpad.py init
    python3 scripts/hermes/scratchpad.py update --status "text"
    python3 scripts/hermes/scratchpad.py update --add-task "do X"
    python3 scripts/hermes/scratchpad.py update --done-task "do X"
    python3 scripts/hermes/scratchpad.py log < terminal_output.txt
    python3 scripts/hermes/scratchpad.py log test.log
    python3 scripts/hermes/scratchpad.py status
    python3 scripts/hermes/scratchpad.py compact
    python3 scripts/hermes/scratchpad.py add-file "lib/x.ts" "Modified: fixed bug"

"""
import argparse
import hashlib
import re
import sys
import os
from datetime import datetime, timezone

SCRATCHPAD_FILE = ".hermes_scratchpad.md"
MAX_BACKLOG = 50
MAX_ERRORS = 30
MAX_FILES = 20


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class Scratchpad:
    def __init__(self):
        self.path = os.path.join(os.getcwd(), SCRATCHPAD_FILE)
        self.created = ""
        self.last_updated = _now()
        self.session_hash = ""
        self.status = ""
        self.tasks = []       # list of {"done": bool, "text": str}
        self.errors = []      # list of str
        self.file_states = [] # list of "FILE_PATH — summary"

        raw = _read(self.path)
        if raw:
            self._parse(raw)

    # ── Parsing ─────────────────────────────────────────────────────
    def _parse(self, raw):
        sections = {}
        current_section = None
        current_lines = []

        for line in raw.split("\n"):
            if line.startswith("# "):
                if current_section is not None:
                    sections[current_section] = current_lines
                current_section = re.sub(r'^#+\s*', '', line).strip()
                current_lines = []
            elif line.startswith("## "):
                if current_section is not None:
                    sections[current_section] = current_lines
                current_section = re.sub(r'^#+\s*', '', line).strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_section is not None:
            sections[current_section] = current_lines

        # Current Status
        if "Current Status" in sections:
            self.status = " ".join(
                l.strip() for l in sections["Current Status"] if l.strip()
            )

        # Session Info
        if "Session Info" in sections:
            for l in sections["Session Info"]:
                if l.startswith("- Created:"):
                    self.created = l.replace("- Created:", "").strip()
                if l.startswith("- Hash:"):
                    self.session_hash = l.replace("- Hash:", "").strip()

        # Task Backlog
        if "Task Backlog" in sections:
            for l in sections["Task Backlog"]:
                l = l.strip()
                if not l:
                    continue
                done = False
                if l.startswith("[X]") or l.startswith("[x]"):
                    done = True
                    l = l[3:].strip()
                elif l.startswith("[ ]"):
                    l = l[3:].strip()
                # Strip leading markers
                for prefix in ("→", "-", "•", "*", ">"):
                    if l.startswith(prefix):
                        l = l[len(prefix):].strip()
                        break
                self.tasks.append({"done": done, "text": l})

        # Error Log
        if "Error Log" in sections:
            for l in sections["Error Log"]:
                l = l.strip()
                if l and l != "(none)" and l != "---":
                    self.errors.append(l)

        # File States
        if "File States" in sections:
            for l in sections["File States"]:
                l = l.strip()
                if l and l != "(none - run `log` to capture)":
                    self.file_states.append(l)

    # ── Serialization ───────────────────────────────────────────────
    def render(self):
        self.last_updated = _now()
        lines = [
            "# Hermes Scratchpad",
            "",
            "## Current Status",
            self.status,
            "",
            "## Session Info",
            f"- Created: {self.created}",
            f"- Last updated: {self.last_updated}",
            f"- Hash: {self.session_hash}",
            "",
            "## Task Backlog",
        ]
        for t in self.tasks[-MAX_BACKLOG:]:
            tick = "[X]" if t["done"] else "[ ]"
            lines.append(f'{tick} {t["text"]}')
        lines.append("")
        lines.append("## Error Log")
        if not self.errors:
            lines.append("(none)")
        else:
            lines.extend(self.errors[-MAX_ERRORS:])
        lines.append("")
        lines.append("## File States")
        if not self.file_states:
            lines.append("(none - run `log` to capture)")
        else:
            lines.extend(self.file_states[-MAX_FILES:])
        lines.append("")
        return "\n".join(lines)

    def save(self):
        _write(self.path, self.render())

    # ── Commands ────────────────────────────────────────────────────
    def init(self):
        self.__init__()  # reset everything
        self.created = _now()
        self.session_hash = hashlib.md5(os.urandom(16)).hexdigest()[:12]
        self.status = "Fresh scratchpad initialized"
        self.save()
        print(f"Created scratchpad: {self.path}")
        print(f"Session: {self.session_hash}")

    def update_status(self, text):
        self.status = text
        self.save()
        print("Status updated.")

    def add_task(self, text):
        self.tasks.append({"done": False, "text": text})
        self.save()
        print(f'Task added: "{text}"')

    def done_task(self, keyword):
        for t in self.tasks:
            if keyword.lower() in t["text"].lower():
                t["done"] = True
                print(f'Task marked done: "{t["text"]}"')
                self.save()
                return
        print(f'No task matching "{keyword}"')

    def add_file_state(self, filepath, summary):
        entry = f"{filepath} — {summary}"
        self.file_states.append(entry)
        self.save()
        print(f'File state recorded: {entry}')

    def log_errors(self, text_or_path):
        # Accept file path or stdin text
        if os.path.isfile(text_or_path):
            raw = _read(text_or_path) or ""
        else:
            raw = text_or_path

        compressed = _compress_errors(raw)
        self.errors.extend(compressed[-MAX_ERRORS:])
        self.errors = self.errors[-MAX_ERRORS:]
        self.save()
        print(f"Logged {len(compressed)} error lines. Total: {len(self.errors)}")

    def compact(self):
        self.tasks = self.tasks[-MAX_BACKLOG:]
        self.errors = self.errors[-MAX_ERRORS:]
        self.file_states = self.file_states[-MAX_FILES:]
        self.status = self.status[:500]
        self.save()
        size = os.path.getsize(self.path)
        print(f"Compacted scratchpad: {size / 1024:.1f} KB")

    def show(self):
        print(self.render())


def _compress_errors(raw):
    """Compress terminal output / error logs into high-density summaries."""
    lines = [l for l in raw.split("\n") if l.strip()]
    if len(lines) <= 15:
        return lines

    # Keep only lines that carry signal
    significant = []
    for l in lines:
        lower = l.lower()
        if any(kw in lower for kw in [
            "error", "fail", "assertion", "assert", "expected",
            "received", "traceback", "exception", "syntax",
            "typeerror", "referenceerror", "cannot find",
        ]) or any(pat in l for pat in [".ts:", ".py:", ".js:", ":Error:"]):
            significant.append(l)

    if len(significant) == 0:
        significant = lines[:5]

    if len(significant) > 15:
        significant = significant[:5] + [f"...({len(significant) - 10} lines elided)..."] + significant[-5:]

    return significant


def main():
    parser = argparse.ArgumentParser(description="Hermes Context Scratchpad")
    parser.add_argument("command", nargs="?", default="status",
                        choices=["init", "update", "log", "status", "compact",
                                 "add-file", "show"])

    # Global options (work with any command, but mostly used with 'update' and 'add-file')
    parser.add_argument("--status", type=str, help="Set current status text")
    parser.add_argument("--add-task", type=str, nargs="*", help="Add one or more tasks")
    parser.add_argument("--done-task", type=str, help="Mark task as done by keyword")
    parser.add_argument("--file", type=str, help="File path (for add-file/commands)")
    parser.add_argument("--summary", type=str, help="Summary text (for add-file)")
    parser.add_argument("--errors", type=str, help="Error file path or text to log")

    args = parser.parse_args()
    sp = Scratchpad()

    if args.command == "init":
        sp.init()
    elif args.command == "update":
        updated = False
        if args.status:
            sp.update_status(args.status)
            updated = True
        if args.add_task:
            for t in args.add_task:
                sp.add_task(t)
            updated = True
        if args.done_task:
            sp.done_task(args.done_task)
            updated = True
        if not updated:
            print("Usage: update --status 'text' | --add-task 'x' 'y' | --done-task 'keyword'")
    elif args.command == "add-file":
        if args.file and args.summary:
            sp.add_file_state(args.file, args.summary)
        elif args.file:
            sp.add_file_state(args.file, "tracked")
        else:
            print("Usage: add-file --file <path> --summary 'description'")
    elif args.command == "log":
        target = args.errors if args.errors else None
        if target and os.path.isfile(target):
            sp.log_errors(target)
        elif target:
            sp.log_errors(target)
        else:
            stdin = sys.stdin.read()
            sp.log_errors(stdin)
    elif args.command == "compact":
        sp.compact()
    elif args.command in ("status", "show"):
        sp.show()


if __name__ == "__main__":
    main()
