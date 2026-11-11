const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, AlignmentType,
  LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType, VerticalAlign,
  Footer, Header, PageNumber, ImageRun,
} = require('docx');
const FIG_DIR = path.join(__dirname, '..', 'figures');

const OUT = process.argv[2];
const W = 10080; // usable width: Letter, 0.75" margins
const FONT = 'Arial', MONO = 'Consolas';

// ---------- helpers ----------
const runs = (spec, base = {}) => (Array.isArray(spec) ? spec : [spec]).map(s => {
  if (typeof s === 'string') return new TextRun({ text: s, ...base });
  const o = { ...base, text: s.t };
  if (s.b) o.bold = true;
  if (s.i) o.italics = true;
  if (s.code) { o.font = MONO; o.size = (base.size || 21) - 2; }
  if (s.ph) { o.highlight = 'yellow'; o.bold = true; }
  if (s.color) o.color = s.color;
  return new TextRun(o);
});
const P = (spec, opts = {}) => new Paragraph({ spacing: { after: 120 }, ...opts, children: runs(spec, opts.run || {}) });
const H1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun(t)] });
const H1nb = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = t => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const B = (spec, lvl = 0) => new Paragraph({ numbering: { reference: 'bul', level: lvl }, spacing: { after: 60 }, children: runs(spec) });
let numRef = 0;
const numbered = items => { const ref = `num${numRef++}`; numConfigs.push(ref); return items.map(s => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60 }, children: runs(s) })); };
const numConfigs = [];
const code = lines => lines.map((l, i) => new Paragraph({
  shading: { fill: 'F3F3F3', type: ShadingType.CLEAR },
  spacing: { before: i === 0 ? 60 : 0, after: i === lines.length - 1 ? 140 : 0, line: 240 },
  indent: { left: 200, right: 200 },
  children: [new TextRun({ text: l.length ? l : ' ', font: MONO, size: 16, color: l.startsWith('+') ? '1B5E20' : l.startsWith('-') ? 'B71C1C' : '222222' })],
}));
const placeholder = (text, label = '[INSERT SCREENSHOT] ') => new Table({
  columnWidths: [W], width: { size: W, type: WidthType.DXA },
  rows: [new TableRow({ children: [new TableCell({
    width: { size: W, type: WidthType.DXA },
    shading: { fill: 'FFF8E1', type: ShadingType.CLEAR },
    borders: Object.fromEntries(['top', 'bottom', 'left', 'right'].map(k => [k, { style: BorderStyle.DASHED, size: 6, color: 'F9A825' }])),
    margins: { top: 300, bottom: 300, left: 200, right: 200 },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: runs([{ t: label, b: true, color: 'E65100' }, text], { size: 19 }) })],
  })] })],
});
// Embeds a PNG from case3_trackB/figures, scaled to fit the page (size read from the PNG header).
const figure = (file, maxW = 660, maxH = 800) => {
  const data = fs.readFileSync(path.join(FIG_DIR, file));
  const w = data.readUInt32BE(16), h = data.readUInt32BE(20);
  const s = Math.min(maxW / w, maxH / h);
  return new Paragraph({
    alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 160, after: 0 },
    children: [new ImageRun({ type: 'png', data, transformation: { width: Math.round(w * s), height: Math.round(h * s) } })],
  });
};
const caption = t => P([{ t, i: true }], { alignment: AlignmentType.CENTER, run: { size: 18, color: '555555' }, spacing: { before: 60, after: 200 } });

const border = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, size = 17) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (spec, w, hdr, fill) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders, verticalAlign: VerticalAlign.TOP,
    shading: hdr ? { fill: '1F3864', type: ShadingType.CLEAR } : fill ? { fill, type: ShadingType.CLEAR } : undefined,
    children: (Array.isArray(spec) && Array.isArray(spec[0]) ? spec : [spec]).map(p => new Paragraph({
      spacing: { after: 30 }, children: runs(p, hdr ? { bold: true, color: 'FFFFFF', size } : { size }),
    })),
  });
  return new Table({
    columnWidths: widths, width: { size: total, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], false, ri % 2 ? 'F7F9FC' : undefined)) })),
    ],
  });
}
const gap = () => new Paragraph({ spacing: { after: 120 }, children: [] });

// ---------- data ----------
const Y = (n) => ({ t: `Yes (${n})`, b: true, color: '1B5E20' });
const PART = (n) => ({ t: `Partial (${n})`, color: 'E65100' });
const N = { t: 'No', color: 'B71C1C' };
const st = (a, b, c) => [[a], [b], [c]].map((x, i) => [['MTS50 exact: ', 'MTS25 exact: ', 'MTS50 ign-id: '][i], ...x]);

const clones = [
  ['C01', [[{ t: 'httpie/core.py:86-96', code: 1 }], [{ t: '↔ httpie/core.py:104-114', code: 1 }], ['raw_main(): Ctrl-C / SystemExit handlers in the parse phase and the run phase']], '51 / 51 tok\n11 / 11 ln', 'Type 1', st(Y(51), Y(51), Y(51)), 'Yes', [[{ t: 'Refactored (Issue 1, §2.4)', b: true }], ['Extract Method']]],
  ['C02', [[{ t: 'httpie/cli/argparser.py:90-106', code: 1 }], [{ t: '↔ argparser.py:151-167', code: 1 }], ['parse_args() preamble in BaseHTTPieArgumentParser and HTTPieArgumentParser']], '110 / 113 tok\n17 / 17 ln', 'Type 3', st(N, PART(33), N), 'Yes', [[{ t: 'Refactored (Issue 2, §2.4)', b: true }], ['Extract / Pull Up Method (Template Method)']]],
  ['C03', [[{ t: 'httpie/cli/argparser.py:59-69', code: 1 }], [{ t: '↔ argparser.py:580-591', code: 1 }], ['"Which argparse action failed" inspection in add_usage() and print_usage(), copied comment included']], '59 / 71 tok\n11 / 12 ln', 'Type 3', st(N, PART(44), N), 'Yes', [[{ t: 'Refactored (Issue 3, §2.4)', b: true }], ['Extract Function']]],
  ['C04', [[{ t: 'httpie/manager/cli.py:61-70', code: 1 }], [{ t: '↔ :71-79 ↔ :80-88', code: 1 }], ['Plugin TARGET argument specs for install, upgrade and uninstall. The uninstall copy says "targets to install" (a bug caused by the copy-paste).']], '27 / 26 / 26 tok\n9–10 ln', 'Type 2', st(N, N, PART('27 @MTS25')), 'Yes + defect', [[{ t: 'Refactored (Issue 4, §2.4)', b: true }], ['Extract Function; help-text bug fixed']]],
  ['C05', [[{ t: 'httpie/legacy/v3_1_0_session_cookie_format.py:36-81', code: 1 }], [{ t: '↔ legacy/v3_2_0_session_header_format.py:26-64', code: 1 }], ['pre_process / post_process / warning assembly for legacy session layouts']], '178 / 162 tok\n46 / 39 ln', 'Type 2/3', st(N, N, Y(80)), 'Yes', [[{ t: 'Not refactored', b: true }], ['Friction: frozen per-version migration modules (§4.2)']]],
  ['C06', [[{ t: 'httpie/cli/argparser.py:431-434', code: 1 }], [{ t: '↔ argparser.py:459-462', code: 1 }], ['"if traceback: raise; else self.error(e.args[0])" idiom']], '26 / 24 tok\n4 / 4 ln', 'Type 1', st(N, PART(28), N), 'Yes', [[{ t: 'Backlog', b: true }], ['Small; fold into an error_or_raise() helper']]],
  ['C07', [[{ t: 'httpie/cli/requestitems.py:130-131', code: 1 }], [{ t: '↔ :146-147 (also :142-143 ↔ :189-190)', code: 1 }], ['Per-separator processor functions with identical bodies; only the function names differ']], '20 / 20 tok\n2 / 2 ln', 'Type 2', st(N, N, PART('29 @MTS25')), 'Yes', [[{ t: "Won't fix", b: true }], ['Intentional dispatch-table entries (§4.2)']]],
  ['C08', [[{ t: 'httpie/output/streams.py:198-217', code: 1 }], [{ t: '↔ streams.py:238-254', code: 1 }], ['PrettyStream vs BufferedPrettyStream iter_body(): binary detection, converter fallback, formatting']], '134 / 89 tok\n20 / 17 ln', 'Type 3/4', st(N, N, N), 'Yes', [[{ t: 'Not refactored', b: true }], ['Friction: streaming vs buffered semantics']]],
  ['C09', [[{ t: 'httpie/output/writer.py:61-76', code: 1 }], [{ t: '↔ writer.py:79-97', code: 1 }], ['write_stream() vs write_stream_with_colors_win()']], '54 / 64 tok\n16 / 19 ln', 'Type 3', st(N, N, N), 'Yes', [[{ t: 'Not refactored', b: true }], ['Friction: Windows-only path']]],
  ['C10', [[{ t: 'httpie/uploads.py:65-69', code: 1 }], [{ t: '↔ uploads.py:257-262 ↔ models.py:164-169', code: 1 }], ['str → bytes body normalisation, written three different ways']], '33 / 45 / 32 tok\n5–6 ln', 'Type 4', st(N, N, N), 'Yes', [[{ t: 'Not refactored', b: true }], ['Friction: edge-case semantics differ']]],
  ['C11', [[{ t: 'httpie/output/formatters/json.py:12-34', code: 1 }], [{ t: '↔ formatters/xml.py:59-79', code: 1 }], ['format_body(): check mime, parse, pretty-print, fall back silently']], '111 / 90 tok\n23 / 21 ln', 'Type 4 (+T2 __init__)', st(N, N, PART('50, __init__ only')), 'Yes', [[{ t: 'Not refactored', b: true }], ['Friction: public FormatterPlugin API']]],
  ['C12', [[{ t: 'httpie/output/ui/rich_progress.py:86-94', code: 1 }], [{ t: '↔ rich_progress.py:132-141', code: 1 }], ['StatusDisplay.stop() vs ProgressDisplay.stop()']], '51 / 55 tok\n9 / 10 ln', 'Type 3', st(N, N, N), 'Yes', [[{ t: 'Backlog', b: true }], ['Form Template Method in BaseDisplay']]],
  ['C13', [[{ t: 'httpie/__main__.py:6-14', code: 1 }], [{ t: '↔ httpie/manager/__main__.py:51-57', code: 1 }], ['Entry-point wrappers mapping KeyboardInterrupt → ERROR_CTRL_C']], '36 / 22 tok\n9 / 7 ln', 'Type 3', st(N, N, N), 'Yes', [[{ t: 'Not refactored', b: true }], ['Different return contracts (int vs ExitStatus)']]],
  ['C14', [[{ t: 'httpie/manager/tasks/plugins.py:105-109', code: 1 }], [{ t: '↔ plugins.py:132-139', code: 1 }], ['install() vs upgrade(): announce, flush, call _install()']], '46 / 48 tok\n5 / 8 ln', 'Type 3', st(N, N, PART('43 @MTS25')), 'Yes', [[{ t: 'Backlog', b: true }], ['Extract Method']]],
  ['C15', [[{ t: 'legacy/v3_1_0_session_cookie_format.py:42-48', code: 1 }], [{ t: '↔ same file :88-94', code: 1 }], ['dict → list-of-cookies comprehension']], '22 / 28 tok\n7 / 7 ln', 'Type 2', st(N, N, N), 'Yes', [[{ t: 'Not refactored', b: true }], ['Bundled with C05']]],
  ['C16', [[{ t: 'httpie/cli/argparser.py:294-299', code: 1 }], [{ t: '↔ argparser.py:312-317', code: 1 }], ['AuthCredentials(...) built from the URL and from .netrc']], '33 / 35 tok\n6 / 6 ln', 'Type 2', st(N, N, N), 'Yes', [[{ t: 'Backlog', b: true }], ['Inside _process_auth(), which already carries a "TODO: refactor"']]],
].map(r => [r[0], r[1], r[2].split('\n').map(x => [x]), r[3], r[4], r[5], r[6]]);

const staticOnly = [
  ['S1', [[{ t: 'cli/constants.py:10-30', code: 1 }], [{ t: '↔ output/formatters/colors.py:208-225', code: 1 }]], '51 tok, MTS50 ign-id', 'Unrelated NAME = \'literal\' constant blocks (HTTP separators vs Solarized colours) produce the same normalised token sequence.', [[{ t: 'False positive', b: true }], ['Coincidental token sequence']]],
  ['S2', [[{ t: 'output/ui/palette.py:114-166', code: 1 }], [{ t: '↔ palette.py:179-231', code: 1 }]], '205 tok, MTS50/100 ign-id', 'Brand colour palette dictionaries (hex shades 50–900).', [[{ t: 'False positive', b: true }], ['Declarative data. Accounts for most of the 90 palette.py/colors.py reports.']]],
  ['S3', [[{ t: 'output/formatters/colors.py:235-245', code: 1 }], [{ t: '↔ colors.py:255-265', code: 1 }]], '108 tok, MTS50/100 ign-id', 'Pygments style dictionaries (token → colour).', [[{ t: 'False positive', b: true }], ['Data table, required by the Pygments API']]],
  ['S4', [[{ t: 'cli/definition.py:411-446', code: 1 }], [{ t: '↔ definition.py:446-471', code: 1 }]], '57 tok, MTS50 ign-id', 'Consecutive add_argument() declarations (--headers, --meta, --body).', [[{ t: 'Boilerplate', b: true }], ['Declarative CLI spec. Not worth abstracting.']]],
  ['S5', [[{ t: 'core.py:146-149 ↔ manager/__main__.py:32', code: 1 }], [{ t: 'rich_progress.py:14-16 ↔ :63-65 / :98-100', code: 1 }]], '25–30 tok, MTS25 exact', 'Identical function signatures (main(args, env) and start(*, total, at, description)).', [[{ t: 'False positive', b: true }], ['Interface conformance, not duplicated logic']]],
  ['S6', [[{ t: 'output/formatters/{headers,json,xml}.py __init__', code: 1 }]], '30–50 tok, MTS25/50', 'FormatterPlugin constructors: super().__init__(); self.enabled = format_options[...]', [[{ t: 'Accepted boilerplate', b: true }], ['Plugin idiom (Type 2). Removing it would change the public plugin pattern.']]],
];

// ---------- document ----------
const children = [];
const add = (...x) => children.push(...x.flat());

// Title page
const DONE = t => ({ t, b: true, color: '1B5E20' });
const FORK = 'https://github.com/ABCWarrior/SOEN-6431-Group-Project';
add(
  new Paragraph({ spacing: { before: 2200, after: 200 }, alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'SOEN 6431 – Software Maintenance and Evolution', size: 26, color: '595959' })] }),
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun('Case Study #3')] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new TextRun({ text: 'Comparative Code Clone Analysis, AI-Driven Duplication Detection & Automated Refactoring Audit', size: 30, bold: true, color: '1F3864' })] }),
  table(['Item', 'Details'], [
    ['Target system', 'HTTPie CLI (httpie/cli) v3.2.4. Python, 78 source files, 9,817 LOC, 39,112 tokens in httpie/'],
    ['Repository fork', [{ t: 'github.com/ABCWarrior/SOEN-6431-Group-Project', code: 1 }]],
    ['Working branch', [{ t: 'case3-groupB', code: 1 }, ' (based on master @ 5b604c3)']],
    ['Sub-team / track', 'Subgroup B, Track B: Agentic AI & GenAI clone auditing and refactoring'],
    ['Tool used', 'Claude Code (Anthropic), desktop app with repository tool access. Clone audit, refactoring and tests: model Claude Opus 5.5. Re-verification and report completion: model Claude Fable 5.2.'],
    ['Role rotation', [['Satisfied. In Case Study #2 the Track B members worked on the traditional static-analysis track (branch ', { t: 'Case2-groupA', code: 1 }, ': commits ', { t: '5f1bfe9', code: 1 }, ' by Chen Qian, ', { t: '77dae91', code: 1 }, ' and ', { t: 'e91856e', code: 1 }, ' by @Lanre-Rung). In Case Study #3 they use the agentic toolset.'], [{ t: FORK + '/commits/Case2-groupA', code: 1 }]]],
    ['Scope of this document', 'Track B content for Sections 1 to 5. Parts that belong to Track A (PMD/CPD) are marked "Reserved for Subgroup A" and were not written by Track B.'],
    ['Deadline', '30/11/2026 23:55'],
    ['Status', [['Track B analysis, refactoring and tests are complete and were re-verified on 2026-11-11.'], [{ t: 'Still open (highlighted yellow): GitHub issue, commit and PR links, which the team posts from github_drafts.md; student IDs; the other members\' contribution entries.', ph: 1 }]]],
  ], [2600, W - 2600], 19),
);

// Core tasks
add(H1('Core Code Clone Analysis & Refactoring Tasks'),
  P('The assignment (§4) sets four core clone tasks. The list below gives Track B\'s result for each task and the part of this report that holds the evidence.'),
  table(['#', 'Core task (assignment §4)', 'Track B result', 'Evidence', 'Status'], [
    ['1', [[{ t: 'Clone Inventory & Hotspot Identification', b: true }], ['Top clone pairs/clusters with token counts, line lengths and affected files']],
      '16 clone pairs/clusters (C01–C16) in 16 files of httpie/. Fragment sizes range from 20 to 178 tokens and from 2 to 46 lines. Five hotspots are ranked; the largest is httpie/cli/argparser.py with 4 clones.',
      '§1.2 table, §1.3 hotspots', [DONE('Done')]],
    ['2', [[{ t: 'Clone Classification & Semantic Audit', b: true }], ['Type 1 to 4; static detection vs GenAI insight']],
      '2 Type 1, 5 Type 2, 7 Type 3 and 2 Type 4. A deterministic token cross-check finds 1 of the 16 at 50 tokens (exact) and at least a fragment of 8 across all of its settings. The AI audit also recorded its own rejected and corrected claims.',
      '§1.2 Type column, §1.4, §3.1, §4.1', [DONE('Done')]],
    ['3', [[{ t: 'Issue Tracking & Refactoring Execution', b: true }], ['GitHub Issues, refactoring with design patterns, Pull Request with passing tests']],
      '4 clone pairs refactored (C01–C04) with Extract Method, Pull Up Method (Template Method style) and Extract Function. 14 new regression tests; the full suite gives 1031 passed, with the same 2 pre-existing failures as before the change. One user-facing defect caused by a clone was fixed (C04).',
      '§2.4, Figures B3 to B5, refactoring.diff',
      [[DONE('Refactoring done and verified locally.')], [{ t: '4 issues, commit and PR are written in github_drafts.md and are posted by the team after review.', ph: 1 }]]],
    ['4', [[{ t: 'Remediation Friction & Risk Discussion', b: true }], ['Blockers and attempted solutions for clones that cannot be refactored cleanly']],
      '8 clones were left unrefactored on purpose (C05, C07, C08, C09, C10, C11, C13, C15). Each has a blocker, the solution that was tried or considered, and a decision. Friction met during the 4 completed refactorings is also recorded.',
      '§4.2', [DONE('Done')]],
  ], [420, 2500, 3760, 1700, 1700], 17),
  gap(),
  P([{ t: 'Disposition of the 16 clones: ', b: true }, '4 refactored (C01–C04), 4 on the backlog (C06, C12, C14, C16), 7 not refactored because of the blockers in §4.2 (C05, C08, C09, C10, C11, C13, C15) and 1 marked won\'t-fix (C07).']),
  P([{ t: 'Supporting evidence in the repository: ', b: true }, { t: 'case3_trackB/', code: 1 }, ' holds the prompt log, the scanner tool, raw scan outputs, the detection matrix, the refactoring diff, test logs, figures and the GitHub issue/PR drafts (listed in Appendix A).']),
);

// ---------------- SECTION 1 ----------------
add(H1('Section 1: Code Clone Inventory & Identification Report'),
  H2('1.1 Scope and detection set-up'),
  B(['Scope: the production package ', { t: 'httpie/', code: 1 }, ' (78 .py files, 9,817 LOC, 39,112 lexical tokens). tests/, docs/ and extras/ were excluded so that test fixtures do not inflate the counts.']),
  B([{ t: 'Track B (AI): ', b: true }, 'Claude Code read the argument-parsing, execution, upload, output-pipeline, session and plugin-manager modules and reported clone pairs with exact file:line ranges, a clone type and a refactoring recommendation. It then checked each candidate against the source (§4.1).']),
  B([{ t: 'Token cross-check (Track B): ', b: true }, 'to test its own findings, the agent wrote a deterministic token scanner (', { t: 'case3_trackB/tools/token_clone_scan.py', code: 1 }, '): Rabin-Karp window hashing with maximal extension over Python tokens, run at minimum tile sizes (MTS) of 25, 50 and 100, in exact mode and in ignore-identifiers+literals mode. It follows the CPD approach but it is not PMD/CPD. The official CPD detection status and CPD token lengths come from Subgroup A.']),
  B('Token counts below are lexical tokens counted by that scanner (comments, newlines and indentation excluded). Line ranges refer to the original code at commit 5b604c3, before refactoring.'),
  H2('1.2 Clone summary table'),
  P([{ t: 'Token cross-check key: ', b: true }, '"MTS50 exact" is a 50-token minimum with exact matching. "ign-id" means identifiers and literals are normalised. "Yes (n)" means the pair was reported with an n-token match; "Partial (n)" means only an n-token fragment of the pair was reported.'], { run: { size: 18 } }),
  table(['ID', 'Clone pair: files, line ranges, description', 'Size', 'Type', 'Token cross-check (Track B scanner)', 'AI (Claude)', 'Disposition'],
    clones, [520, 3180, 1060, 820, 1900, 760, 1840], 15),
  gap(),
  H3('Token-scan-only reports (flagged by the Track B scanner, not reported by the AI)'),
  table(['ID', 'Location', 'Tokens / config', 'What it actually is', 'Verdict'], staticOnly, [520, 3000, 1300, 3060, 2200], 15),
  gap(),
  H2('1.3 Hotspots'),
  table(['Rank', 'Hotspot (module)', 'Clone pairs', 'Why it matters'], [
    ['1', [{ t: 'httpie/cli/argparser.py', code: 1 }], 'C02, C03, C06, C16 (4)', 'The central argument-parsing pipeline (the HTTPie task focus). Duplicated parse preamble, usage-error inspection, error idiom and credential construction.'],
    ['2', [{ t: 'httpie/core.py + entry points', code: 1 }], 'C01, C13 (2)', 'The command-line execution block. Exit-status semantics (Ctrl-C, SystemExit, --traceback) are spread over 4 places.'],
    ['3', [{ t: 'httpie/legacy/*', code: 1 }], 'C05, C15 (2)', 'Largest clones by size (178/162 tokens). One module per session-format version, built by copy-and-modify.'],
    ['4', [{ t: 'httpie/output/{streams,writer,formatters}', code: 1 }], 'C08, C09, C11 (3)', 'Output pipeline. Mostly Type 3/4 clones that token tools cannot see.'],
    ['5', [{ t: 'httpie/manager/*', code: 1 }], 'C04, C14 (2)', 'Plugin manager CLI. Data-structure clones, including one that shipped a wrong help text.'],
  ], [700, 2900, 1800, 4680], 17),
  H2('1.4 Clone analysis: architectural impact on maintainability'),
  P([{ t: 'Overall duplication is low, but it sits in critical places. ', b: true }, 'At a 50-token minimum with exact matching, the token cross-check reports one duplication in 39k tokens, which suggests a clean codebase. The AI audit nonetheless found 16 clone pairs. 14 of them are Type 2, 3 or 4 (9 are Type 3/4) and fall below or outside token-matching thresholds. They sit in the control-flow layers that every request passes through: argument parsing, the main execution loop, and output streaming.']),
  P([{ t: 'Change amplification in error and exit semantics (C01, C06, C13). ', b: true }, 'The mapping of KeyboardInterrupt and SystemExit to an exit code, newline and optional traceback was written four times. Changing it, for example to print a "cancelled" hint, required edits in four places. A missed copy would make exit codes differ between "Ctrl-C during parsing" and "Ctrl-C during the request", and scripts depend on those exit codes.']),
  P([{ t: 'Diverging copies are already causing defects (C04, C03). ', b: true }, 'The clearest maintainability cost appears in C04. The uninstall argument was copied from install and its help text was never updated, so the shipped man page and ', { t: 'httpie plugins uninstall --help', code: 1 }, ' told users the TARGET was a "target to install". C03 carries the same comment, with the same typos, in two classes, which shows copy-paste rather than shared design. The second copy has already gained an extra condition (option_strings).']),
  P([{ t: 'Inheritance not exploited (C02, C12). ', b: true }, 'HTTPieArgumentParser re-implements the base-class parse_args() instead of extending it. It also swaps defensive getattr() calls for direct attribute access, so the two copies are only nearly identical. A fix to stdin detection in the base class would silently skip the main http/https parser.']),
  P([{ t: 'Intentional or structural duplication (C05, C07, C11, S2–S6). ', b: true }, 'Some duplication is a deliberate design choice. Per-version legacy migration modules are frozen snapshots, separator processors are dispatch-table extension points, and formatter plugins follow a public plugin contract. Colour tables are data. Treating these as debt would raise coupling without improving maintainability. The audit therefore separates actionable clones (C01–C04, backlog C06/C12/C14/C16) from accepted ones.']),
);

// ---------------- SECTION 2 ----------------
add(H1('Section 2: Methodology Log, Screenshots & GitHub Evidence'),
  H2('2.1 Environment and baseline'),
  table(['Item', 'Value'], [
    ['Host', 'macOS (Darwin 27.2), Python 3.11.6 virtualenv (venv/), requests 2.34.2, charset-normalizer 3.5.2, flake8 7.5.0'],
    ['Agent', 'Claude Code desktop app. Session 1 (2026-11-11, 15:47 to 16:02 UTC, Claude Opus 5.5): audit, cross-check, refactoring, tests. Session 2 (2026-11-11, Claude Fable 5.2): re-verification, figures, report completion.'],
    ['Repository state', [{ t: 'case3-groupB', code: 1 }, ' @ 5b604c3 (HTTPie 3.2.4). The refactoring sits in the working tree: 4 files changed, 81 insertions, 77 deletions, plus the new tests/test_clone_refactorings.py (91 lines). It is not committed yet.']],
    ['Baseline tests', [{ t: 'pytest -q', code: 1 }, ' → 1017 passed, 2 failed, 5 skipped, 4 xfailed (67.7 s). Both failures exist before any change: test_encoding.py::test_terminal_output_{request,response}_charset_detection[big5-…], caused by the installed charset-normalizer version guessing a different encoding.']],
    ['Evidence folder', [{ t: 'case3_trackB/', code: 1 }, ' (see Appendix A)']],
  ], [2400, W - 2400], 18),
  H2('2.2 Track A artifacts (PMD / CPD)'),
  placeholder('PMD/CPD command logs, configuration flags and at least 2 screenshots are supplied by Subgroup A. Track B did not run PMD/CPD.', '[RESERVED FOR SUBGROUP A] '),
  gap(),
  H2('2.3 Track B artifacts (Agentic AI: Claude Code)'),
  H3('Tool selection'),
  P('Track B used one agentic tool, Claude Code, running inside the local clone of the fork. It was chosen over a chat-only workflow because it reads files with tools, runs the test suite and scripts, and edits code in place. Every line range in this report therefore comes from a file the agent opened, and every refactoring was executed against the tests.'),
  H3('Context ingestion steps'),
  ...numbered([
    'The agent was given the assignment (C3 deliverable.docx) and the repository workspace. It extracted the requirements with pandoc.',
    'It listed the httpie/ package (78 files) and ranked modules by size and by the HTTPie task focus ("argument parsing duplication and command-line execution blocks").',
    'It read the full source of the argument-parsing, execution, upload, output, session, legacy and plugin-manager modules with file tools (module list in prompt_log.md).',
    'It recorded a test baseline before any edits.',
    'It wrote and ran a deterministic token scanner to check its own findings, then measured every reported fragment (fragment_tokens.txt, detection_matrix.txt).',
    'It refactored four clone pairs, added regression tests, and re-ran the full suite, flake8 and the scanner.',
    'In a second session it re-ran the suite and the scanner, compared a sample of the reported line ranges with the original commit, corrected one clone-type label (§4.1, AI-5) and completed this report.',
  ]),
  H3('Prompt log (full log in case3_trackB/prompt_log.md)'),
  P('Rows marked "User" are quoted as typed. Rows marked "Agent" are steps the agent planned and ran on its own inside that prompt.', { run: { size: 18 } }),
  table(['#', 'Who', 'Prompt / instruction', 'Agent action', 'Result'], [
    ['P1', 'User', '"For case study 3 we are group B which are using agentic AI tools. we will use claude. first I want to analyze the deliverable3 and draft a docx for deliverable submission section 1, 2, 3,4,5. and make sure we have address the Core Code Clone Analysis & Refactoring Tasks." (C3 deliverable.docx attached)', 'Parsed the deliverable; inspected repository, branches and size', 'Requirements checklist: 4 core tasks, 5 sections'],
    ['A1', 'Agent', 'Scan for Type 1 to 4 clones, focusing on argument parsing and command-line execution blocks', 'Read the modules listed in prompt_log.md', '18 candidates, 16 kept as C01–C16'],
    ['A2', 'Agent', 'Baseline the build before touching code', 'pytest -q', '1017 pass, 2 pre-existing failures'],
    ['A3', 'Agent', 'Cross-check the AI findings with a deterministic token scan', 'Wrote token_clone_scan.py; ran 6 configurations; measured each fragment', 'scan_results/, detection matrix (Figure B2)'],
    ['A4', 'Agent', 'Triage what only the token scan reports', 'Read constants.py, palette.py, colors.py, definition.py, metadata.py', 'S1–S6 classified as data or boilerplate'],
    ['A5', 'Agent', 'Refactor C01–C04 with design patterns, keeping behaviour', 'Edited core.py, cli/argparser.py, manager/cli.py; regenerated extras/man/httpie.1', 'refactoring.diff (Figures B3, B4)'],
    ['A6', 'Agent', 'Add regression tests for the de-duplicated paths', 'Wrote tests/test_clone_refactorings.py. The first draft failed and was fixed (§4.1, AI-3). Ran the C01 tests against the original core.py.', '14/14 pass; 7/7 C01 tests pass on the original code'],
    ['A7', 'Agent', 'Re-verify', 'Full pytest, flake8, token re-scan', '1031 pass; exact MTS 50 clones 1 → 0'],
    ['P2', 'User', '"based on the requirement decliverable, you need to help me to fill the real content we need to submit and we are TeamB use claude from section 1 to 5 and make sure we have list(Core Code Clone Analysis & Refactoring Tasks)."', 'Re-ran pytest and the scanner; compared a sample of line ranges with commit 5b604c3; rendered Figures B1 to B5; completed the report', '1031 pass confirmed; C07 relabelled Type 1 → Type 2'],
    ['P3', 'User', '"leave the commits, pr, branch in github_draft.md. I will check everything first then push the PR by myself." and "we are only do Track B. do not touch any Track A."', 'No git or GitHub action taken; Track A parts left reserved; github_drafts.md extended with commit, push and PR steps', 'Human keeps commit and merge authority'],
  ], [520, 680, 3880, 2900, 2100], 15),
  gap(),
  P([{ t: 'About the figures. ', b: true }, 'Figures B2 to B5 are text captures of commands run in the repository on 2026-11-11, rendered as images. Figure B1 is rendered from the Claude Code session log. None of the text in them was typed by hand.'], { run: { size: 18 } }),
  figure('figB1_session_clone_discovery.png'),
  caption('Figure B1: AI clone discovery. User prompt P1 and the agent\'s reply, quoted from the Claude Code session log. The reply counts C07 as Type 1; this report corrects it to Type 2 (§4.1, AI-5).'),
  figure('figB2_ai_fragments_vs_token_scan.png'),
  caption('Figure B2: AI clone discovery checked against the code. Every fragment the agent reported exists at the stated lines (token and line counts), and the matrix shows which pairs the token scan finds in each configuration.'),
  figure('figB3_patch_core_C01.png'),
  caption('Figure B3: AI-generated refactoring patch for C01 (httpie/core.py, Extract Method). Red lines are the two duplicated handler blocks; green lines are the shared helper and its two call sites.'),
  figure('figB4_patch_manager_C04.png'),
  caption('Figure B4: AI-generated refactoring patch for C04 (httpie/manager/cli.py, Extract Function) with the regenerated man page. The "targets to install" defect in the uninstall command is fixed.'),
  figure('figB5_regression_verification.png'),
  caption('Figure B5: Regression verification. The 14 new tests pass, the full suite gives 1031 passed with the 2 pre-existing failures, and exact duplications at 50 tokens drop from 1 to 0 (13 to 9 at 25 tokens).'),
  H2('2.4 GitHub lifecycle: issues, commits, pull request'),
  P('The refactoring is finished and verified in the local working tree. The team decided to review it before anything is posted, so the issues, the commit and the Pull Request are not on GitHub yet. Their full text and the exact commands are in case3_trackB/github_drafts.md. Issues are currently disabled on the fork; the repository owner (@ABCWarrior) has to enable them before the four tickets can be created.'),
  table(['Artifact', 'Clone', 'Link / hash', 'State'], [
    ['Issue 1', 'C01: duplicated Ctrl-C/SystemExit handlers (core.py)', [{ t: '[issue URL]', ph: 1 }], 'Text ready'],
    ['Issue 2', 'C02: duplicated parse_args() preamble (argparser.py)', [{ t: '[issue URL]', ph: 1 }], 'Text ready'],
    ['Issue 3', 'C03: duplicated failed-action inspection (argparser.py)', [{ t: '[issue URL]', ph: 1 }], 'Text ready'],
    ['Issue 4', 'C04: plugin TARGET specs + help-text defect (manager/cli.py)', [{ t: '[issue URL]', ph: 1 }], 'Text ready'],
    ['Commit(s)', 'C01–C04 + tests + regenerated man page; evidence folder', [{ t: '[commit hash(es)]', ph: 1 }], 'Changes in working tree'],
    ['Pull request', 'case3-groupB → master of the fork: "Refactor duplicated CLI error handling and argument-parsing code (clones C01–C04)"', [{ t: '[PR URL]', ph: 1 }], 'Text ready'],
  ], [1400, 4200, 2600, 1880], 17),
  P(['Full patch: ', { t: 'case3_trackB/refactoring.diff', code: 1 }, ' (3 source files and the man page). New tests: ', { t: 'tests/test_clone_refactorings.py', code: 1 }, '. The before-and-after state of each refactoring follows; Figures B3 and B4 show the same diffs as produced by git.'], { run: { size: 19 } }),
  H3('Refactoring 1 (C01, Type 1): Extract Method in httpie/core.py'),
  P('Before: the same two handlers appear in both the parse phase and the execution phase.'),
  ...code([
    '    except KeyboardInterrupt:                    # identical at lines 86-96 and 104-114',
    '        env.stderr.write(\'\\n\')',
    '        if include_traceback:',
    '            raise',
    '        exit_status = ExitStatus.ERROR_CTRL_C',
    '    except SystemExit as e:',
    '        if e.code != ExitStatus.SUCCESS:',
    '            env.stderr.write(\'\\n\')',
    '            if include_traceback:',
    '                raise',
    '            exit_status = ExitStatus.ERROR',
  ]),
  P('After: one helper, called from both phases.'),
  ...code([
    '+    def handle_interrupt_or_exit(e: BaseException) -> ExitStatus:',
    '+        if isinstance(e, SystemExit) and e.code == ExitStatus.SUCCESS:',
    '+            return ExitStatus.SUCCESS',
    '+        env.stderr.write(\'\\n\')',
    '+        if include_traceback:',
    '+            raise',
    '+        if isinstance(e, KeyboardInterrupt):',
    '+            return ExitStatus.ERROR_CTRL_C',
    '+        return ExitStatus.ERROR',
    '     ...',
    '+    except (KeyboardInterrupt, SystemExit) as e:   # parse phase',
    '+        exit_status = handle_interrupt_or_exit(e)',
    '     ...',
    '+        except (KeyboardInterrupt, SystemExit) as e:   # execution phase',
    '+            exit_status = handle_interrupt_or_exit(e)',
  ]),
  H3('Refactoring 2 (C02, Type 3): Extract / Pull Up Method in httpie/cli/argparser.py'),
  ...code([
    ' class BaseHTTPieArgumentParser(argparse.ArgumentParser):',
    '     def parse_args(self, env, args=None, namespace=None):',
    '+        self._parse_common_args(env, args, namespace)',
    '+        return self.args',
    '+',
    '+    def _parse_common_args(self, env, args=None, namespace=None) -> List[str]:',
    '+        self.env = env',
    '+        self.args, no_options = self.parse_known_args(args, namespace)',
    '+        if self.args.debug: self.args.traceback = True',
    '+        self.has_stdin_data = (...)        # single copy of stdin / --raw detection',
    '+        return no_options',
    '',
    ' class HTTPieArgumentParser(BaseHTTPieArgumentParser):',
    '     def parse_args(self, env, args=None, namespace=None):',
    '-        self.env = env',
    '-        self.env.args = namespace = namespace or argparse.Namespace()',
    '-        self.args, no_options = super().parse_known_args(args, namespace)',
    '-        ... (9 duplicated lines) ...',
    '+        env.args = namespace = namespace or argparse.Namespace()',
    '+        no_options = self._parse_common_args(env, args, namespace)',
    '         self._apply_no_options(no_options)   # subclass-specific pipeline continues',
  ]),
  H3('Refactoring 3 (C03, Type 3): Extract Function in httpie/cli/argparser.py'),
  ...code([
    '+def get_failed_action() -> Optional[argparse.Action]:',
    '+    _, exception, _ = sys.exc_info()',
    '+    if (isinstance(exception, argparse.ArgumentError)',
    '+            and len(exception.args) >= 1',
    '+            and isinstance(exception.args[0], argparse.Action)):',
    '+        return exception.args[0]',
    '+    return None',
    '',
    '   # HTTPieHelpFormatter.add_usage():',
    '+        failed_action = get_failed_action()',
    '+        if failed_action is not None:',
    '+            displayed_actions.insert(0, failed_action)',
    '   # HTTPieArgumentParser.print_usage():',
    '+        failed_action = get_failed_action()',
    '+        if failed_action is not None and failed_action.option_strings:',
    '+            whitelist.add(failed_action.option_strings[0])',
  ]),
  H3('Refactoring 4 (C04, Type 2): Extract Function in httpie/manager/cli.py (fixes a defect)'),
  ...code([
    '+def plugin_targets_argument(verb: str) -> dict:',
    '+    return {\'dest\': \'targets\', \'metavar\': \'TARGET\',',
    '+            \'nargs\': Qualifiers.ONE_OR_MORE, \'help\': f\'targets to {verb}\'}',
    '',
    '     \'uninstall\': [',
    '         \'Uninstall the given HTTPie plugins.\',',
    '-        {..., \'help\': \'targets to install\'}       # copy-paste defect',
    '+        plugin_targets_argument(\'uninstall\'),',
    '',
    ' extras/man/httpie.1 (regenerated):  -targets to install  +targets to uninstall',
  ]),
  H3('Verification results'),
  table(['Check', 'Before', 'After'], [
    ['pytest (full suite)', '1017 passed, 2 failed*, 5 skipped, 4 xfailed', '1031 passed (+14 new), 2 failed*, 5 skipped, 4 xfailed. Re-run on 2026-11-11 with the same result.'],
    ['New regression tests (tests/test_clone_refactorings.py)', 'C01 tests: 7/7 pass on the original core.py (behaviour pinned)', '14/14 pass'],
    ['Token scan, exact MTS 50 / MTS 25', '1 / 13 duplications', '0 / 9 duplications'],
    ['Total tokens in httpie/', '39,112', '39,047'],
    ['Cognitive complexity: raw_main()', '49', '40'],
    ['Cognitive complexity: HTTPieArgumentParser.parse_args()', '11', '8'],
    ['flake8 (project config)', 'pre-existing warnings only', 'no new warnings'],
  ], [3800, 3140, 3140], 17),
  P('* Pre-existing big5 charset-detection failures, unrelated to the refactoring (§2.1).', { run: { size: 17, italics: true } }),
  placeholder('Fig. G1: GitHub Issues list showing the four clone tickets', '[TO ADD AFTER POSTING] '),
  caption('Figure G1: Clone issues in the fork'),
  placeholder('Fig. G2: Pull Request "Files changed" view and test status', '[TO ADD AFTER POSTING] '),
  caption('Figure G2: Pull Request with the before/after diff'),
);

// ---------------- SECTION 3 ----------------
const win = (w, rest) => [[{ t: w, b: true, color: '1F3864' }], [rest]];
const RES_A = [{ t: 'Reserved for Subgroup A (PMD/CPD results)', i: true, color: '808080' }];
add(H1('Section 3: Comparative Evaluation Matrix'),
  P('Track B column: measured on the 16 verified clone pairs of §1.2. Where a comparison with token matching is needed, Track B uses its own deterministic token cross-check as a baseline; it is not PMD/CPD. The Track A column is left for Subgroup A, and the verdicts in the last column are Track B\'s assessment until the two sub-teams reconcile.'),
  table(['Evaluation metric', 'Track A: Traditional static tools (PMD/CPD)', 'Track B: Agentic AI / GenAI (Claude Code)', 'Winner & justification (Track B assessment)'], [
    ['Precision & false-positive rate', RES_A,
      [['18 clone candidates raised. The agent\'s own source check rejected 2 before reporting (AI-1, AI-2), so 16 were reported: candidate precision 16/18 = 89%.'],
       ['16/16 reported pairs exist at the stated file:line ranges (34 fragments measured, Figure B2). 0 invented files, functions or line ranges.'],
       ['1 clone-type label was corrected on re-verification (AI-5) and 1 refactoring recommendation was withdrawn (AI-4).'],
       ['Token baseline: at 50 tokens exact, 1 report and 1 real clone. At 25 tokens exact, 13 reports, 5 of which overlap a real clone. At 50 tokens with identifiers and literals ignored, 96 reports, 90 of them colour and style tables.']],
      win('Track B (provisional)', 'Where token matching is precise it reports a single clone; where it reports more, most reports are data tables or signatures. The agent\'s errors were over-generalisations, not invented code, and its own source check removed them.')],
    ['Semantic & Type 3/4 clone detection', RES_A,
      [['Found 7 Type 3 and 2 Type 4 clones, including the cross-file cluster C10 (three str→bytes normalisations in uploads.py and models.py) and C11 (parse, pretty-print, fall back silently in the JSON and XML formatters).'],
       ['Explained how the copies differ, for example getattr() versus direct attribute access in C02.'],
       ['Token baseline: none of the 9 found in full. Fragments of 3 (C02, C03, C14) at 25 tokens. C08, C09, C10, C12 and C13 are not reported in any configuration.']],
      win('Track B', '9 of the 16 clones are Type 3 or 4, and token matching did not report any of them in full. Equivalent logic written differently has no common token run to match.')],
    ['Actionability of refactoring advice', RES_A,
      [['A named pattern per clone, a working patch for 4 pairs, 14 regression tests, a regenerated man page, and a blocker analysis for the 8 clones left alone.'],
       ['Found a user-facing defect caused by a clone (C04, wrong help text).'],
       ['Limits: every patch still needs human review, and one generated test was wrong on its first run (AI-3).']],
      win('Track B', 'The output is a tested patch with a stated pattern and risk notes. A token report gives a location and a length, and cannot tell a refactorable clone from a data table.')],
    ['Setup & configuration friction', RES_A,
      [['Nothing to install beyond the Claude Code app and the project virtualenv. Session 1 took about 15 minutes from the first prompt to a verified patch.'],
       ['Friction: a paid model and network access are needed; results are not reproducible run to run; every claim and patch has to be checked; a test baseline is needed first; the audit needed a second verification pass.']],
      win('Likely Track A (to confirm)', 'A token scanner is deterministic, offline and free, and its output can be diffed between runs. Track B\'s own token scan was one command and needed no review of generated code.')],
    ['Scalability across large repositories', RES_A,
      [['Bounded by context window, time and cost. The agent read a targeted subset of the 78 files, chosen by size and task focus, so coverage depends on which files it opens.'],
       ['A larger repository needs chunking or a deterministic pre-filter.'],
       ['For comparison, Track B\'s token scan covered all 78 files (39,112 tokens) in about 0.25 s.']],
      win('Likely Track A (to confirm)', 'Exhaustive scanning is cheap and scales with code size. The agent is better spent on the regions that a scanner or a change set points to (§4.3).')],
  ], [1500, 1700, 3800, 3080], 16),
  gap(),
  H2('3.1 Detection summary by clone type (Track B data)'),
  table(['Clone type', '# pairs (verified)', 'Token cross-check, MTS50 exact', 'Token cross-check, best configuration', 'AI (Claude Code)'], [
    ['Type 1 (exact)', '2 (C01, C06)', '1', '2 (C01 in full; C06 as a 28-token fragment at MTS25)', '2'],
    ['Type 2 (renamed / literals)', '5 (C04, C05, C07, C15, C16)', '0', '3 partial, only with identifiers and literals ignored (C04, C05, C07)', '5'],
    ['Type 3 (gapped / modified)', '7 (C02, C03, C08, C09, C12, C13, C14)', '0', '3 partial at MTS25 (C02, C03, C14)', '7'],
    ['Type 4 (semantic)', '2 (C10, C11)', '0', '0 (for C11 only the __init__ boilerplate matches)', '2'],
    [{ t: 'Total', b: true }, { t: '16', b: true }, { t: '1 (6%)', b: true }, { t: '8 (50%), 7 of them partial', b: true }, { t: '16 (100%)', b: true }],
  ], [2000, 2500, 1500, 2600, 1480], 17),
  P('C05 and C08 are mixed-type pairs; each is counted under its dominant type. The set of 16 was built by the AI audit and then checked against the source, so the AI figure is an upper bound on recall: clones that neither method found cannot be counted. PMD/CPD figures per type are supplied by Subgroup A.', { run: { size: 17, italics: true } }),
);

// ---------------- SECTION 4 ----------------
add(H1('Section 4: Critical Audit & Hybrid Clone Management Strategy'),
  H2('4.1 False-positive & hallucination audit'),
  P('Rows AI-1 to AI-5 are errors made by the AI agent, found by checking its output against the source and by running its code. Rows FP-1 to FP-3 are false positives of Track B\'s own token cross-check. False positives of PMD/CPD itself are reported by Subgroup A.'),
  table(['#', 'Source', 'Claim', 'Ground truth (verified in source)', 'Verdict'], [
    ['AI-1', 'AI (Claude), candidate', 'client.collect_messages() and manager/tasks/sessions.upgrade_session() duplicate session loading.', 'Both call the shared get_httpie_session() with different arguments. This is reuse, not a clone.', [{ t: 'Hallucinated duplication (over-generalisation); rejected before reporting', b: true }]],
    ['AI-2', 'AI (Claude), candidate', 'HTTPRequest.headers and HTTPResponse.headers (models.py) are Type 3 clones.', 'They share a purpose but not an algorithm: request line + Host injection + skippable-header filter vs status line + Set-Cookie splitting.', [{ t: 'Semantic over-claim; rejected before reporting', b: true }]],
    ['AI-3', 'AI (Claude), generated test', 'A generated regression test read env.stderr after calling the http() test helper.', 'The helper closes the stream, so the test raised ValueError. It was caught by running the test and then fixed. AI patches need execution, not only review.', [{ t: 'Generated-code error; corrected', b: true }]],
    ['AI-4', 'AI (Claude), advice', 'Merge the identical processors in requestitems.py (C07).', 'Each function is a separate entry in the separator dispatch table and an extension point. Merging saves 4 lines and couples unrelated separators.', [{ t: 'Over-eager DRY advice; downgraded to won\'t-fix', b: true }]],
    ['AI-5', 'AI (Claude), classification', 'C07 is a Type 1 (exact) clone, so the pairs split 3 / 4 / 7 / 2 (as in Figure B1).', [{ t: 'requestitems.py:130-131', code: 1 }, ' and ', { t: ':146-147', code: 1 }, ' have identical bodies, but the function names differ (process_embed_header_arg vs process_embed_query_param_arg). That is a renamed identifier, and the token scan only matches the pair when identifiers are ignored.'], [{ t: 'Mislabelled type; corrected to Type 2 (split is 2 / 5 / 7 / 2)', b: true }]],
    ['FP-1', 'Token scan (ign-id, MTS50)', [{ t: 'cli/constants.py:10-30 ≡ formatters/colors.py:208-225', code: 1 }, ' (51 tokens)'], 'HTTP separator constants vs Solarized colour constants. Both are runs of NAME = \'string\' that become identical once identifiers and literals are normalised.', [{ t: 'False positive: coincidental token sequence', b: true }]],
    ['FP-2', 'Token scan (ign-id, MTS50/100)', [{ t: 'palette.py:114-166 ≡ :179-231', code: 1 }, ' (205 tokens, the largest report) + 89 similar reports'], 'Colour palette dictionaries of hex values. They are data, not logic; "refactoring" them would only obscure the brand palette.', [{ t: 'False positive: data-table boilerplate', b: true }]],
    ['FP-3', 'Token scan (exact, MTS25)', [{ t: 'core.py:146-149 ≡ manager/__main__.py:32', code: 1 }, ' (30 tokens)'], 'Two main(args, env) functions with the same signature and different bodies.', [{ t: 'False positive: signature match', b: true }]],
  ], [620, 1500, 2700, 3460, 1800], 15),
  gap(),
  P([{ t: 'Observation. ', b: true }, 'Token-scan false positives come from too much lexical similarity: data tables, signatures, declarative specs. The AI errors come from too much semantic generalisation: shared purpose treated as shared code, DRY applied where duplication is intentional, and a type label assigned from the look of the code instead of a token comparison. Because the agent read files with tools, it did not invent a file path, a function or a line range in this study. Chat-only use, where code is pasted or uploaded, is more likely to produce stale or invented line ranges, so every AI claim must be checked against the source (guardrails in §4.3).']),
  H2('4.2 Remediation friction & risk (Core Task 4)'),
  table(['Clone', 'Blocker', 'Attempted / considered solution', 'Decision'], [
    ['C05 / C15 legacy session formats', 'Each module is a frozen snapshot of one on-disk session format (v3.1.0 cookies, v3.2.0 headers) and is used by the "httpie cli sessions upgrade" fixers. A shared base would couple old migrations to future ones, so a change for v3.3 could silently change how v3.1 files are upgraded.', 'Drafted a generic LegacyLayout(normaliser, warning_template, link) helper. Rejected because the messages, normalisation and post-processing differ in kind, and session-file round-trip tests cover only part of these paths.', 'Accept the duplication; document it as intentional (versioned-migration pattern).'],
    ['C08 PrettyStream vs BufferedPrettyStream', 'One streams line by line (--stream, text/event-stream) and must emit before EOF; the other buffers the full body before formatting. A shared helper would need generators with look-ahead (chain([(line, lf)], iter_lines)), which risks latency regressions for streaming output.', 'Considered a Template Method with a _detect_binary(first_chunk) hook. Its complexity was higher than the duplication it removed (about 6 lines).', 'Deferred; needs streaming benchmarks first.'],
    ['C09 write_stream vs _with_colors_win', 'Windows-only colorama path. The CI host is macOS, so behaviour cannot be verified here; mistakes would corrupt coloured output for Windows users.', 'A strategy object for chunk writing (bytes vs decoded text) was sketched.', 'Deferred until it can be tested on Windows (test_windows.py).'],
    ['C10 str→bytes normalisation', 'The three variants differ at the edges: HTTPRequest.body maps None to b\'\'; as_bytes passes None through; compress_request also reads file-like bodies. A single helper would change behaviour for empty and streamed bodies.', 'Unifying as_bytes(data, *, none_as=b\'\', read_files=False) was considered; the flags remove most of the benefit.', 'Not refactored; document the semantics instead.'],
    ['C11 JSON vs XML formatters', 'Both implement the public FormatterPlugin API that third-party plugins copy. Pulling up a parse/pretty/fallback template would change the plugin base class contract.', 'A ParsingFormatterPlugin mix-in was considered.', 'Out of scope; would need a deprecation cycle.'],
    ['C13 entry points', 'httpie.__main__.main() returns an int (.value) for sys.exit; manager program() returns ExitStatus. Both are console-script targets in setup.cfg.', 'A shared run_with_ctrl_c(fn) wrapper.', 'Low value, packaging risk; backlog.'],
    ['C07 identical processors', 'Dispatch-table extension points (see AI-4).', '—', "Won't fix."],
  ], [1650, 3150, 3080, 2200], 15),
  gap(),
  H3('Friction met during the four refactorings that were done'),
  B([{ t: 'C01: ', b: true }, 'the extracted handler uses a bare ', { t: 'raise', code: 1 }, ' to keep the original traceback, so it must be called from inside an except block. This is documented in its docstring, and two tests check that --traceback still re-raises in both phases.']),
  B([{ t: 'C02: ', b: true }, 'order-sensitive side effect. ', { t: 'env.args', code: 1 }, ' must point at the namespace before parsing starts. argparse fills that namespace in place, and Environment._make_rich_console() reads env.args.style when usage or error output is rendered in the middle of parsing. The assignment stays in the subclass rather than being pulled up, so the manager parser behaves exactly as before.']),
  B([{ t: 'C04: ', b: true }, 'changing the help text affects generated content. ', { t: 'extras/man/httpie.1', code: 1 }, ' had to be regenerated (generate_man_pages.py); the diff touches only the two intended lines.']),
  H2('4.3 Hybrid clone management strategy'),
  P('Proposed workflow: deterministic scanning sets the gate and narrows the search, the LLM agent handles semantic triage and patch generation, and humans keep merge authority.'),
  table(['Stage', 'Trigger', 'Tool', 'Output / gate'], [
    ['1. Gate', 'Every PR (CI)', 'PMD CPD, exact, --minimum-tokens 50, on httpie/. Data files excluded with // CPD-OFF markers or --exclude (palette.py, colors.py styles).', 'Fail the build if duplicated tokens rise above the committed baseline (ratchet). Deterministic and fast (well under 1 s at this size).'],
    ['2. Wide net', 'Nightly / weekly', 'CPD at MTS 25 with ignore-identifiers/literals', 'Non-blocking report of candidate regions, including Type 2/3 fragments.'],
    ['3. Semantic triage', 'Changed modules + stage 2 report', 'LLM agent (Claude Code / Copilot) with repository tool access', 'Classifies each report (Type 1–4, actionable, boilerplate, intentional); adds Type 3/4 clones in the touched modules; opens a GitHub Issue per actionable clone with file:line evidence.'],
    ['4. Patch generation', 'Issue labelled "clone"', 'LLM agent on a feature branch', 'Refactoring patch + regression tests that are first run against the old code; PR linked to the issue.'],
    ['5. Verification', 'PR', 'Full test suite, flake8 / complexity, CPD re-scan', 'The PR must not increase duplicated tokens and must pass the tests; complexity is reported in the PR body.'],
    ['6. Review & merge', 'Human', 'Code review', 'A human approves; no auto-merge. Intentional clones are recorded in an allow-list so they are not re-reported.'],
  ], [1500, 1700, 3300, 3580], 15),
  gap(),
  H3('Guardrails against AI hallucination and over-refactoring'),
  B('Evidence requirement: every AI clone claim must cite file:line ranges that a script checks (fragment token count > 0, both ranges exist). Unverifiable claims are dropped automatically.'),
  B('Behaviour pinning: AI-generated tests for a refactored path must pass on the pre-refactor code before the refactor is accepted (as done for C01).'),
  B('Protected zones: public plugin APIs (httpie/plugins, formatters), legacy migration modules and platform-specific code require an explicit human-approved design note before the agent may change them.'),
  B('Metrics tracked per release: duplicated tokens (CPD), number of open clone issues, cognitive complexity of hotspot functions, and the agent false-claim rate (rejected claims / total claims).'),
);

// ---------------- SECTION 5 ----------------
add(H1('Section 5: Team Member Contributions'),
  P('Names and GitHub logins are taken from the collaborator list of the fork. Student IDs and the entries of the other members are filled in by each member. Issue, commit and PR links are added once the team has posted them (§2.4).'),
  table(['Name', 'Student ID', 'GitHub information', 'Detailed contribution & verifiable links'], [
    [[{ t: 'Chen Qian', b: true }], '', [{ t: '@L0veRamen', code: 1 }],
      [['Subgroup B, Track B (Agentic AI). Ran and directed the Claude Code clone audit (C01–C16) and its token cross-check; reviewed the AI findings against the source (§4.1); reviewed and verified the refactoring of C01–C04 and the 14 regression tests; prepared the issue and PR text; compiled the Track B content of Sections 1 to 5.'],
       ['Role rotation evidence (Track A in Case Study #2): ', { t: FORK + '/commit/5f1bfe9960f6ec814baecae5b18b2e15444544d5', code: 1 }],
       [{ t: '[Issue 1–4 links] | [commit link] | [PR link]', ph: 1 }]]],
    [[{ t: 'Yourun Lan', b: true }], '', [{ t: '@Lanre-Rung', code: 1 }],
      [['Subgroup B, Track B (Agentic AI). Role rotation evidence (Track A in Case Study #2): ', { t: FORK + '/commit/77dae91c9b4ef8e51308526121caf09963ce52ff', code: 1 }],
       [{ t: '[Contribution and links to be completed by the member]', ph: 1 }]]],
    [[{ t: 'Aakarsh Dhar', b: true }], '', [{ t: '@ABCWarrior', code: 1 }],
      [[{ t: '[Track, contribution and links to be completed by the member]', ph: 1 }]]],
    [[{ t: 'Syeda Fatima', b: true }], '', [{ t: '@syedasid11', code: 1 }],
      [[{ t: '[Track, contribution and links to be completed by the member]', ph: 1 }]]],
  ], [1500, 1200, 1500, 5880], 17),
  gap(),
  H3('AI tool usage disclosure'),
  P('Track B used Claude Code to inventory the clones, write the token cross-check scanner, generate the refactoring patches and regression tests, and draft this report (Claude Opus 5.5 for the audit and refactoring session, Claude Fable 5.2 for re-verification and report completion). All AI output was checked against the source code and the test suite; §4.1 lists the AI errors found during that check. No commit, push, issue or pull request was made by the agent.'),
);

// Appendix
add(H1('Appendix A: Evidence Files (case3_trackB/)'),
  table(['Path', 'Content'], [
    ['prompt_log.md', 'Track B prompts (quoted), agent actions and outputs for both sessions'],
    ['github_drafts.md', 'Branch, commit plan, the text of the 4 issues and of the Pull Request, and the commands to post them'],
    ['pr_body.md', 'Pull Request body, ready for gh pr create --body-file'],
    ['refactoring.diff', 'Complete patch for C01–C04 (source and man page)'],
    ['figures/figB1…figB5 *.png', 'Figures B1 to B5 of this report'],
    ['tools/token_clone_scan.py', 'Token clone scanner used as the deterministic cross-check (exact / ignore-identifiers modes, fragment measurement)'],
    ['tools/detection_matrix.py', 'Cross-references the AI fragments with the scan results'],
    ['tools/build_report.js', 'Generator of this document'],
    ['scan_results/{exact,ignoreids}_mts{25,50,100}.txt', 'Raw scan output before refactoring'],
    ['scan_results/after_refactor/*.txt', 'Raw scan output after refactoring'],
    ['scan_results/fragments.json, fragment_tokens.txt', 'Line ranges and token counts of C01–C16'],
    ['scan_results/detection_matrix.txt', 'Token-scan detection status per clone and configuration'],
    ['scan_results/pytest_baseline.txt, pytest_after_refactor.txt', 'Full test-suite logs'],
    ['../tests/test_clone_refactorings.py', '14 regression tests for the refactored paths'],
  ], [4300, W - 4300], 17),
);

const doc = new Document({
  creator: 'Group B', title: 'SOEN 6431 Case Study 3 – Subgroup B (Track B) Deliverable',
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: 'Title', name: 'Title', basedOn: 'Normal', run: { size: 56, bold: true, color: '1F3864', font: FONT }, paragraph: { spacing: { before: 120, after: 200 }, alignment: AlignmentType.CENTER } },
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 32, bold: true, color: '1F3864', font: FONT }, paragraph: { spacing: { before: 120, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 26, bold: true, color: '2E74B5', font: FONT }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 22, bold: true, color: '404040', font: FONT }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
      ...Array.from({ length: 10 }, (_, i) => ({ reference: `num${i}`, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] })),
    ],
  },
  sections: [{
    properties: { page: { margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: 'SOEN 6431 · Case Study #3 · Subgroup B (Track B: Agentic AI)', size: 16, color: '808080' })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Page ', size: 16, color: '808080' }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: '808080' }), new TextRun({ text: ' of ', size: 16, color: '808080' }), new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, color: '808080' })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log('wrote', OUT, buf.length); });
