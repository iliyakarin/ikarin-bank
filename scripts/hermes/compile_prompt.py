#!/usr/bin/env python3
"""
Structural Prompt Builder

Assembles a cache-optimized prompt payload:
  1. Static system instructions (top — pins to KV prefix cache)
  2. Scratchpad state (middle)
  3. Target file / skeleton content
  4. Volatile data — test errors, recent terminal output (bottom — cache miss zone)

Usage:
    python3 scripts/hermes/compile_prompt.py \\
        --system "Your system instructions..." \\
        --scratchpad .hermes_scratchpad.md \\
        --file lib/routingUtils.ts \\
        [--skeletonize] \\
        [--errors test_output.txt] \\
        [--output compiled_prompt.txt]

Layout:
    [TOP: System Instructions]
    [MID: Scratchpad State]
    [MID: Target File / Skeleton]
    [BOTTOM: Volatile Data]

This ordering ensures Ollama/llama.cpp gets near-100% prefix cache hits
on the static instructions across repeated calls.
"""
import argparse
import os
import sys
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _skeletonize(source, filepath):
    """Inline skeletonizer for TS/JS/Python files."""
    ext = os.path.splitext(filepath)[1].lower()

    lines = source.split("\n")
    result = []
    i = 0

    import re

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Keep blank lines, comments, imports
        if not stripped or stripped.startswith("//") or stripped.startswith("*") or \
           stripped.startswith("##") or stripped.startswith("# ") or \
           stripped.startswith("import ") or stripped.startswith("from ") or \
           stripped.startswith("export ") or stripped.startswith('"""') or \
           stripped.startswith("'''"):
            result.append(line)
            i += 1
            continue

        # Detect function/class/method — keep signature, skip body
        is_sig = False
        if ext in (".ts", ".js", ".tsx", ".jsx"):
            if re.match(r'^\s*(export\s+)?(async\s+)?(function|const\s+\w+\s*[=:])', line):
                is_sig = True
            elif re.match(r'^\s*\w+\s*\(.*\)\s*(?::\s*\S+)?\s*\{', stripped):
                is_sig = True
            elif re.match(r'^\s*(export\s+)?(interface|type|enum)\s+', stripped):
                is_sig = True
        elif ext == ".py":
            if re.match(r'^(\s*)(async\s+)?def\s+', line):
                is_sig = True
            elif re.match(r'^\s*class\s+', line):
                is_sig = True

        if is_sig:
            result.append(line)
            if "{" in stripped and "}" not in stripped:
                result.append("  // ...body elided...")
                depth = stripped.count("{") - stripped.count("}")
                i += 1
                while i < len(lines) and depth > 0:
                    depth += lines[i].count("{") - lines[i].count("}")
                    i += 1
                if i < len(lines):
                    result.append(lines[i])  # closing brace
                i += 1
                continue
            elif ext == ".py" and not stripped.endswith(":"):
                i += 1
                continue

        result.append(line)
        i += 1

    return "\n".join(result)


def build_prompt(system_instructions, scratchpad_path, file_path,
                 skeletonize=False, error_path=None, extra_volatile=""):
    """Build a cache-optimized prompt payload.

    Layout:
        TOP:    System instructions (static — KV cache hit)
        MID:    Scratchpad state (semi-static)
        MID:    Target file skeleton or full content
        BOTTOM: Volatile data: errors, terminal output
    """
    sections = []

    # ── TOP: System Instructions ──────────────────────
    if system_instructions:
        if os.path.isfile(system_instructions):
            content = _read(system_instructions) or system_instructions
        else:
            content = system_instructions
        sections.append(("SYSTEM_INSTRUCTIONS", content))

    # ── MID: Scratchpad State ──────────────────────────
    if scratchpad_path:
        sp_content = _read(scratchpad_path)
        if sp_content:
            sections.append(("SCRATCHPAD_STATE", sp_content))
        else:
            sections.append(("SCRATCHPAD_STATE", "# Scratchpad not found — fresh session"))

    # ── MID: Target File ──────────────────────
    if file_path:
        raw = _read(file_path)
        if raw:
            if skeletonize:
                skeleton = _skeletonize(raw, file_path)
                section_content = f"## File: {file_path} (skeleton)\n```typescript\n{skeleton}\n```"
            else:
                section_content = f"## File: {file_path} (full)\n```typescript\n{raw}\n```"
            sections.append(("TARGET_FILE", section_content))
        else:
            sections.append(("TARGET_FILE", f"# File not found: {file_path}"))

    # ── BOTTOM: Volatile Data ────────────────
    volatile_parts = []

    if error_path:
        err_content = _read(error_path)
        if err_content:
            # Compress errors
            err_lines = [l for l in err_content.split("\n") if l.strip()]
            compressed = err_lines[-50:]  # Last 50 lines max
            volatile_parts.append(f"## Test/Build Errors ({len(compressed)} lines)\n" +
                                 "\n".join(compressed))

    if extra_volatile:
        volatile_parts.append(f"## Additional Volatile Data\n{extra_volatile}")

    if volatile_parts:
        sections.append(("VOLATILE_DATA", "\n\n".join(volatile_parts)))

    # ── Assemble with timestamps ────────
    output_lines = []
    output_lines.append(f"=== COMPILED PROMPT — {_now()} ===")
    output_lines.append("")

    for name, content in sections:
        output_lines.append(f"--- {name} ---")
        output_lines.append(content)
        output_lines.append("")

    return "\n".join(output_lines)


def main():
    parser = argparse.ArgumentParser(
        description="Build a cache-optimized prompt payload"
    )
    parser.add_argument("--system", type=str,
                        help="System instructions text or file path")
    parser.add_argument("--scratchpad", type=str,
                        help="Path to .hermes_scratchpad.md")
    parser.add_argument("--file", type=str,
                        help="Target source file to include")
    parser.add_argument("--skeletonize", action="store_true",
                        help="Skeletonize the target file instead of including full content")
    parser.add_argument("--errors", type=str,
                        help="Path to error/test output file")
    parser.add_argument("--volatile", type=str,
                        help="Extra volatile data to append at bottom")
    parser.add_argument("--output", type=str,
                        help="Write to file instead of stdout")
    parser.add_argument("--stats", action="store_true",
                        help="Print size stats instead of full output")

    args = parser.parse_args()

    prompt = build_prompt(
        system_instructions=args.system,
        scratchpad_path=args.scratchpad,
        file_path=args.file,
        skeletonize=args.skeletonize,
        error_path=args.errors,
        extra_volatile=args.volatile,
    )

    if args.stats:
        lines = prompt.count("\n") + 1
        chars = len(prompt)
        # Rough token estimate: 1 token ≈ 4 chars in most models
        est_tokens = chars // 4
        print(f"Prompt built: {lines} lines, {chars} chars, ~{est_tokens} tokens (est.)")
        if args.file:
            full = _read(args.file)
            if full:
                print(f"Full file: {len(full)} chars, ~{len(full)//4} tokens")
                if args.skeletonize:
                    skel = _skeletonize(full, args.file)
                    print(f"Skeleton:  {len(skel)} chars, ~{len(skel)//4} tokens")
                    print(f"Saved:     {len(full) - len(skel)} chars, ~{(len(full) - len(skel))//4} tokens")
    else:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(prompt)
            print(f"Written to {args.output} ({len(prompt)} chars)")
        else:
            print(prompt)


if __name__ == "__main__":
    main()
