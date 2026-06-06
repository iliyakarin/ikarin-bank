#!/usr/bin/env node
/**
 * Context Scratchpad Engine
 *
 * Manages a .hermes_scratchpad.md file that stores:
 *   - Current Status (overwritten each run)
 *   - Task Backlog (preserved across runs)
 *   - Error Log (compressed terminal output)
 *   - File State Snapshot
 *
 * Usage:
 *   node scripts/hermes/scratchpad.js init
 *   node scripts/hermes/scratchpad.js update [--status TEXT] [--add-task TEXT] [--done-task TEXT]
 *   node scripts/hermes/scratchpad.js log <terminal_output.txt>
 *   node scripts/hermes/scratchpad.js status
 *   node scripts/hermes/scratchpad.js compact
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SCRATCHPAD_PATH = path.join(process.cwd(), '.hermes_scratchpad.md');
const MAX_BACKLOG = 50;
const MAX_ERRORS = 30;
const MAX_FILES = 20;

// ── Argument Parsing ──────────────────────────────────────────────
function parseArgs(argv) {
  const args = argv.slice(2);
  const result = { command: args[0] || 'status', flags: {} };
  for (let i = 1; i < args.length; i++) {
    if (args[i].startsWith('--')) {
      const key = args[i].slice(2);
      const val = args[i + 1] && !args[i + 1].startsWith('--') ? args[++i] : true;
      result.flags[key] = val;
    } else {
      result.positional = result.positional || [];
      result.positional.push(args[i]);
    }
  }
  return result;
}

// ── Scratchpad I/O ────────────────────────────────────────────────
function readScratchpad() {
  if (!fs.existsSync(SCRATCHPAD_PATH)) {
    return createFresh();
  }
  try {
    const raw = fs.readFileSync(SCRATCHPAD_PATH, 'utf8');
    return parseMarkdown(raw);
  } catch {
    return createFresh();
  }
}

function createFresh() {
  return {
    version: 1,
    created: new Date().toISOString(),
    lastUpdated: new Date().toISOString(),
    currentStatus: 'Initialized',
    sessionHash: crypto.randomBytes(8).toString('hex'),
    tasks: [],
    errors: [],
    fileStates: [],
  };
}

function parseMarkdown(raw) {
  const data = {
    version: 1,
    created: '',
    lastUpdated: new Date().toISOString(),
    currentStatus: '',
    sessionHash: '',
    tasks: [],
    errors: [],
    fileStates: [],
  };

  // Extract sections by header
  const sections = raw.split('## ').slice(1);
  for (const section of sections) {
    const [title, ...bodyLines] = section.split('\n');
    const body = bodyLines.join('\n').trim();

    switch (title.toLowerCase()) {
      case 'current status':
        data.currentStatus = body;
        break;
      case 'session info':
        const hashMatch = body.match(/Hash: ([a-f0-9]+)/);
        if (hashMatch) data.sessionHash = hashMatch[1];
        const dateMatch = body.match(/Created: (.+)/);
        if (dateMatch) data.created = dateMatch[1];
        break;
      case 'task backlog':
        data.tasks = body
          .split('\n')
          .filter(Boolean)
          .map(line => {
          const match = line.match(/^\[([ xX])\]\s*(.*)$/);
          return match
            ? { done: match[1].toLowerCase() === 'x', text: match[2] }
            : { done: false, text: line.replace(/^[>\-•*]\s*/, '') };
        });
        break;
      case 'error log':
        data.errors = body
          .split('\n')
          .filter(l => l.trim().length > 0 && l.trim() !== '---')
          .slice(-MAX_ERRORS);
        break;
      case 'file states':
        data.fileStates = body
          .split('\n')
          .filter(Boolean)
          .slice(-MAX_FILES);
        break;
    }
  }
  return data;
}

function writeScratchpad(data) {
  data.lastUpdated = new Date().toISOString();
  const lines = [];
  lines.push('# Hermes Scratchpad');
  lines.push('');
  lines.push('## Current Status');
  lines.push(data.currentStatus);
  lines.push('');
  lines.push('## Session Info');
  lines.push(`- Created: ${data.created}`);
  lines.push(`- Last updated: ${data.lastUpdated}`);
  lines.push(`- Hash: ${data.sessionHash}`);
  lines.push('');
  lines.push('## Task Backlog');
  for (const task of data.tasks.slice(-MAX_BACKLOG)) {
    const tick = task.done ? '[X]' : '[ ]';
    lines.push(`${tick} ${task.text}`);
  }
  lines.push('');
  lines.push('## Error Log');
  if (data.errors.length === 0) {
    lines.push('(none)');
  } else {
    lines.push(data.errors.join('\n'));
  }
  lines.push('');
  lines.push('## File States');
  if (data.fileStates.length === 0) {
    lines.push('(none - run `log` to capture)');
  } else {
    lines.push(data.fileStates.join('\n'));
  }
  fs.writeFileSync(SCRATCHPAD_PATH, lines.join('\n') + '\n', 'utf8');
}

// ── Compression ───────────────────────────────────────────────────
function compressLines(lines, maxLines = 20) {
  if (lines.length <= maxLines) return lines;
  const kept = lines.slice(0, 5);
  const skipped = lines.length - 10;
  kept.push(`... (${skipped} lines elided) ...`);
  kept.push(...lines.slice(-5));
  return kept;
}

function compressError(text) {
  const lines = text.split('\n').filter(Boolean);
  // Keep only stack trace lines and error messages
  const significant = lines.filter(l =>
    l.includes('Error') ||
    l.includes('FAIL') ||
    l.includes('assertion') ||
    l.match(/\w+\.ts:\d+:\d+/) ||
    l.includes('expected') ||
    l.includes('received')
  );
  return significant.length > 0 ? significant.slice(0, 15) : lines.slice(0, 5);
}

// ── Commands ──────────────────────────────────────────────────────
function cmdInit() {
  const data = createFresh();
  data.currentStatus = 'Fresh scratchpad initialized';
  writeScratchpad(data);
  console.log(`Created scratchpad: ${SCRATCHPAD_PATH}`);
  console.log(`Session: ${data.sessionHash}`);
}

function cmdUpdate(data, flags) {
  if (flags.status) data.currentStatus = flags.status;
  if (flags['add-task']) {
    if (!Array.isArray(flags['add-task'])) {
      flags['add-task'] = [flags['add-task']];
    }
    for (const task of flags['add-task']) {
      data.tasks.push({ done: false, text: task });
    }
  }
  if (flags['done-task']) {
    const doneText = flags['done-task'];
    const target = data.tasks.find(
      t => t.text.toLowerCase().includes(doneText.toLowerCase())
    );
    if (target) target.done = true;
  }
  // Prune very old completed tasks
  const undone = data.tasks.filter(t => !t.done);
  const done = data.tasks.filter(t => t.done).slice(-10);
  data.tasks = [...undoneslice(-MAX_BACKLOG), ...done];
  writeScratchpad(data);
  console.log('Scratchpad updated.');
}

function cmdLog(data, logPath) {
  if (!logPath) {
    // Read from stdin
    console.log('Reading terminals output from stdin...');
    let input = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => (input += chunk));
    process.stdin.on('end', () => {
      const compressed = compressError(input);
      data.errors = [...data.errors, ...compressed].slice(-MAX_ERRORS);
      writeScratchpad(data);
      console.log(`Logged ${compressed.length} error lines. Total: ${data.errors.length}`);
    });
    return;
  }
  const raw = fs.readFileSync(logPath, 'utf8');
  const compressed = compressError(raw);
  data.errors = [...data.errors, ...compressed].slice(-MAX_ERRORS);
  writeScratchpad(data);
  console.log(`Logged ${compressed.length} error lines. Total: ${data.errors.length}`);
}

function cmdStatus(data) {
  console.log('=== Hermes Scratchpad ===');
  console.log(`Session: ${data.sessionHash}`);
  console.log(`Status: ${data.currentStatus}`);
  console.log(`Tasks: ${data.tasks.filter(t => !t.done).length} pending, ${data.tasks.filter(t => t.done).length} done`);
  console.log(`Errors: ${data.errors.length} logged`);
  console.log(`File states: ${data.fileStates.length} tracked`);
  if (fs.existsSync(SCRATCHPAD_PATH)) {
    console.log(`\nFull content:`);
    console.log(fs.readFileSync(SCRATCHPAD_PATH, 'utf8'));
  }
}

function cmdCompact(data) {
  data.currentStatus = data.currentStatus.slice(0, 500);
  data.tasks = data.tasks.slice(-MAX_BACKLOG);
  data.errors = data.errors.slice(-MAX_ERRORS);
  data.fileStates = data.fileStates.slice(-MAX_FILES);
  writeScratchpad(data);
  const stat = fs.statSync(SCRATCHPAD_PATH);
  console.log(`Compacted scratchpad: ${(stat.size / 1024).toFixed(1)} KB`);
}

// ── Main ──────────────────────────────────────────────────────────
function main() {
  const args = parseArgs(process.argv);
  const data = readScratchpad();

  switch (args.command) {
    case 'init':
      cmdInit();
      break;
    case 'update':
    case 'upd':
      cmdUpdate(data, args.flags);
      break;
    case 'log':
      cmdLog(data, args.positional?.[0]);
      break;
    case 'status':
    case 'cat':
    case 'show':
      cmdStatus(data);
      break;
    case 'compact':
    case 'prune':
      cmdCompact(data);
      break;
    default:
      console.error('Usage:');
      console.error('  scratchpad.js init                    - Create fresh scratchpad');
      console.error('  scratchpad.js update --status "..."    - Update status');
      console.error('  scratchpad.js update --add-task "..."   - Add task');
      console.error('  scratchpad.js update --done-task "..."  - Mark task done');
      console.error('  scratchpad.js log <file.txt>            - Log terminal output');
      console.error('  scratchpad.js status                   - Show full scratchpad');
      console.error('  scratchpad.js compact                   - Prune old entries');
      process.exit(1);
  }
}

main();
