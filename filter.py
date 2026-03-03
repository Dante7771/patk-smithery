"""
PFC Token Killer - Filter Pipeline v2.0
Entropie-basierte Terminal-Output-Verdichtung für Claude-Kontext-Optimierung.

Unterschied zu PFC v1.5: Kein Byte-Kompressor!
Dieser Filter verdichtet *Information* für KI-Verständlichkeit, nicht Bytes für Speicher.
PFC-Entropie-Algorithmen dienen als Scoring-Engine.

v2.0 — Pattern Condensation:
  Gruppt ähnliche (nicht-identische) Zeilen desselben Musters zu einer Zusammenfassungszeile.
  Massive Verbesserung für npm install, pip install, pytest, cargo, apt-get Output.
  Benchmark-Verbesserung: npm install 0% → ~85%+, pip install 0% → ~70%+
"""

import re
import math
from collections import Counter


# ============================================================
# WICHTIGE KEYWORDS — werden IMMER behalten, egal was
# ============================================================
IMPORTANT_KEYWORDS = [
    "error", "err:", "exception", "traceback", "failed", "failure",
    "warning", "warn:", "deprecated",
    "success", "successfully", "done", "complete", "finished",
    "installed", "added", "removed", "updated",
    "version", "v0.", "v1.", "v2.", "v3.",
    "found", "not found", "missing",
    "connected", "disconnected", "timeout",
    "permission denied", "access denied",
    "address in use", "eaddrinuse", "econnrefused",
    "memory", "cpu", "disk",
]


# ============================================================
# PATTERN CONDENSATION — Ähnliche-aber-verschiedene Zeilen
# ============================================================
# Format: (compiled_regex, min_count_to_condense, summary_fn(matched_lines) -> str)
# Reihenfolge matters: Spezifischere Patterns ZUERST!

PATTERN_CONDENSERS = [

    # --- NPM ---
    # npm warn deprecated X@version: message  (spezifisch, zuerst!)
    (re.compile(r'^npm\s+warn\s+deprecated\s+', re.IGNORECASE), 2,
     lambda ms: f"[{len(ms)}× npm warn deprecated — run 'npm audit fix']"),

    # npm warn / npm notice (allgemein, nach deprecated)
    (re.compile(r'^npm\s+(?:warn|notice)\s+(?!deprecated)', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× npm warnings — e.g.: {ms[0].strip()[:60]}]"),

    # npm http fetch (Registry-Requests)
    (re.compile(r'^npm\s+http\s+fetch\s+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× npm http fetch requests]"),

    # --- PIP ---
    # pip: Collecting + Downloading interleaved block (ZUERST prüfen!)
    # Real pip output: Collecting X / Downloading X.whl alternierend → Combined Pattern!
    (re.compile(r'^\s*(?:Collecting|Downloading)\s+\S+', re.IGNORECASE), 4,
     lambda ms: f"[{len(ms)}× pip install: Collecting/Downloading packages]"),

    # pip: Collecting packages (einzeln, fallback)
    (re.compile(r'^\s*Collecting\s+\S+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× pip: Collecting packages]"),

    # pip: Downloading .whl files (einzeln, fallback)
    (re.compile(r'^\s*Downloading\s+\S+.*\.whl', re.IGNORECASE), 2,
     lambda ms: f"[{len(ms)}× pip: Downloading .whl files]"),

    # pip: Using cached
    (re.compile(r'^\s*Using cached\s+', re.IGNORECASE), 2,
     lambda ms: f"[{len(ms)}× pip: Using cached packages]"),

    # pip: Requirement already satisfied
    (re.compile(r'^\s*Requirement already satisfied:', re.IGNORECASE), 2,
     lambda ms: f"[{len(ms)}× requirements already satisfied]"),

    # pip: Obtaining / Building wheels
    (re.compile(r'^\s*(Obtaining|Building wheels?)\s+', re.IGNORECASE), 2,
     lambda ms: f"[{len(ms)}× pip: Building/Obtaining]"),

    # --- PYTEST / UNITTEST ---
    # pytest: PASSED tests
    (re.compile(r'^\s*PASSED\s+', re.IGNORECASE), 2,
     lambda ms: f"[{len(ms)}× PASSED]"),

    # pytest: SKIPPED tests
    (re.compile(r'^\s*SKIPPED\s+', re.IGNORECASE), 2,
     lambda ms: f"[{len(ms)}× SKIPPED]"),

    # pytest: collecting test items
    (re.compile(r'^\s*<\s*(?:Module|Function|Class|Item)\s+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× test items collected]"),

    # pytest: running test ... ok (unittest style)
    (re.compile(r'^(?:test\w+)\s*\(.*\)\s*\.\.\.\s*ok', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× test ... ok]"),

    # --- CARGO / RUST ---
    # cargo: Compiling crates
    (re.compile(r'^\s*Compiling\s+\S+\s+v\d+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× Compiling crates]"),

    # cargo: Downloading crates.io
    (re.compile(r'^\s*Downloading\s+\S+\s+v\d+', re.IGNORECASE), 2,
     lambda ms: f"[{len(ms)}× Downloading crates]"),

    # cargo: Checking crates
    (re.compile(r'^\s*Checking\s+\S+\s+v\d+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× Checking crates]"),

    # --- YARN ---
    # yarn: info/warning lines
    (re.compile(r'^yarn\s+(?:info|warning)\s+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× yarn info/warnings]"),

    # yarn: Fetching package
    (re.compile(r'^yarn\s+(?:fetch|link|add|remove)\s+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× yarn package operations]"),

    # --- APT-GET / DEBIAN ---
    # apt-get: Get: N http://... (Fetch-Zeilen)
    (re.compile(r'^Get:\d+\s+http', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× apt-get: Fetching packages from repos]"),

    # apt-get: Preparing to unpack / Unpacking
    (re.compile(r'^\s*(Preparing to unpack|Unpacking)\s+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× apt-get: Unpacking packages]"),

    # --- GIT ---
    # git: remote counting/compressing objects (progress lines)
    (re.compile(r'^\s*(?:remote:\s+)?(?:Counting|Compressing|Enumerating|Resolving|Receiving|Writing)\s+objects:', re.IGNORECASE), 2,
     lambda ms: f"[git transfer: {ms[-1].strip()[:70]}]"),

    # --- DOCKER (vorsichtig — Steps sind oft unterschiedlich) ---
    # docker: --> Running in ... (layer hash lines)
    (re.compile(r'^-+>\s+Running in\s+[a-f0-9]+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× docker: Running build steps]"),

    # docker: Removing intermediate container
    (re.compile(r'^Removing intermediate container\s+', re.IGNORECASE), 3,
     lambda ms: f"[{len(ms)}× docker: Removing intermediate containers]"),

]


def shannon_entropy(text: str) -> float:
    """Shannon-Entropie eines Strings. Höher = mehr Information."""
    if not text or len(text) < 3:
        return 0.0
    counts = Counter(text)
    length = len(text)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def remove_ansi_codes(text: str) -> str:
    """Entfernt ANSI Escape Sequences (Farben, Cursor-Bewegungen etc.)."""
    ansi = re.compile(
        r'\x1b'           # ESC
        r'(?:'
        r'\[[0-9;]*[A-Za-z]'   # CSI sequences: ESC [ ... letter
        r'|\([AB012]'           # Charset sequences
        r'|\][0-9]*;[^\x07]*\x07'  # OSC sequences
        r'|[PX^_].*?\x1b\\'    # String sequences
        r'|[0-9;]*[Jm]'        # Simple sequences
        r'|.)'                  # Any other ESC+char
    )
    return ansi.sub('', text)


def is_progress_bar_line(line: str) -> bool:
    """Erkennt Ladebalken-Zeilen zuverlässig."""
    stripped = line.strip()
    if not stripped:
        return False

    # Typische Ladebalken-Muster
    patterns = [
        r'^[#=\-_\.oO\*\+\|]{5,}',           # ########## oder =====>
        r'[█░▓▒▏▎▍▌▋▊▉]{3,}',                # Unicode Block-Chars (Block Elements)
        r'[━─═]{5,}',                          # Box Drawing Lines (pip/tqdm ━━━━━━)
        r'^\[[\s=\->#\.oO\*]{5,}\]',           # [=====>   ]
        r'^\d+[%/]\s*\|',                       # 47% |
        r'\|\s*\d+\s*%',                        # | 47%
        r'^\s*\d+\s*/\s*\d+\s*\[',             # 100/200 [
        r'Downloading.*\d+%',
        r'Progress.*\d+%',
        r'\d+\.\d+\s*(MB|GB|KB)\s*/\s*\d+',   # 1.2 MB / 5.0 MB  (alt. Format)
        r'\d+\.\d+/\d+\.\d+\s*(MB|GB|KB)',     # 894.6/894.6 kB (pip/tqdm Format)
    ]
    for p in patterns:
        if re.search(p, stripped, re.IGNORECASE):
            # Nur entfernen wenn keine wichtigen Keywords
            if not any(kw in stripped.lower() for kw in IMPORTANT_KEYWORDS):
                return True
    return False


def compress_duplicates(lines: list) -> list:
    """Fasst aufeinanderfolgende exakt identische Zeilen zusammen."""
    if not lines:
        return lines
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        count = 1
        while (i + count < len(lines) and
               lines[i + count].strip() == line):
            count += 1
        if count > 2:
            preview = line[:60] + "..." if len(line) > 60 else line
            result.append(f"[{count}× identische Zeile: {preview}]")
        elif count == 2:
            result.append(lines[i])
            result.append(lines[i])
        else:
            result.append(lines[i])
        i += count
    return result


def condense_similar_patterns(lines: list) -> list:
    """
    Kondensiert ähnliche (nicht-identische) Zeilen desselben Musters
    zu einer einzigen Zusammenfassungszeile.

    Beispiele:
      - 15× 'npm warn deprecated X@1.0.0: ...' → '[15× npm warn deprecated — run npm audit fix]'
      - 8×  'Collecting requests (from ...)' → '[8× pip: Collecting packages]'
      - 20× 'PASSED tests/test_foo.py::test_bar' → '[20× PASSED]'
      - 5×  'Compiling serde v1.0.195' → '[5× Compiling crates]'

    Läuft VOR Entropie-Scoring: Verhindert, dass Pattern-Wiederholungen den Kontext fluten.
    Matcht konsekutive Zeilen — passt zu typischem Terminal-Output (alle Warnings zusammen etc.).
    """
    result = []
    i = 0
    while i < len(lines):
        condensed = False
        for pattern, min_count, summary_fn in PATTERN_CONDENSERS:
            if pattern.search(lines[i]):
                # Alle konsekutiven Matches sammeln
                group = [lines[i]]
                j = i + 1
                while j < len(lines) and pattern.search(lines[j]):
                    group.append(lines[j])
                    j += 1

                if len(group) >= min_count:
                    # Genug für Kondensierung!
                    result.append(summary_fn(group))
                    i = j
                    condensed = True
                    break
                # Nicht genug für Kondensierung → break (zur nächsten Zeile)
                break

        if not condensed:
            result.append(lines[i])
            i += 1

    return result


def compress_timestamp_clusters(lines: list) -> list:
    """Verdichtet große Cluster von Timestamp-Log-Zeilen."""
    ts_pattern = re.compile(
        r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'  # ISO: 2026-03-02T12:00:00
        r'|^\[\d{2}:\d{2}:\d{2}\]'                     # [12:00:00]
        r'|^\d{2}:\d{2}:\d{2}\s'                        # 12:00:00 log...
        r'|^\d{10,13}\s'                                 # Unix timestamp
    )
    result = []
    ts_cluster = []

    def flush_cluster():
        if len(ts_cluster) > 4:
            preview = ts_cluster[0].strip()[:70]
            result.append(
                f"[{len(ts_cluster)}× Timestamp-Logs | erste: {preview}]"
            )
        else:
            result.extend(ts_cluster)
        ts_cluster.clear()

    for line in lines:
        if ts_pattern.match(line.strip()):
            # Bei wichtigen Keywords trotzdem behalten und Cluster unterbrechen
            if any(kw in line.lower() for kw in IMPORTANT_KEYWORDS):
                flush_cluster()
                result.append(line)
            else:
                ts_cluster.append(line)
        else:
            flush_cluster()
            result.append(line)

    flush_cluster()
    return result


def score_lines(lines: list) -> list:
    """
    Gibt jeder Zeile einen Score: Hoher Score = wichtig behalten.
    Nutzt Shannon-Entropie + Keyword-Matching.
    """
    scored = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        score = shannon_entropy(stripped)

        # Bonus für wichtige Keywords
        lower = stripped.lower()
        if any(kw in lower for kw in IMPORTANT_KEYWORDS):
            score += 5.0

        # Bonus für Pattern-Condensation Zusammenfassungen (z.B. "[15× npm warn deprecated ...]")
        if re.match(r'^\[', stripped) and '×' in stripped:
            score += 3.0

        # Bonus für Zeilen die wie Code/Output aussehen
        if re.search(r'^\s*(def |class |import |from |return |raise |if |for |    )', stripped):
            score += 2.0

        # Bonus für Zeilen mit Pfaden, URLs, Versionsnummern (wahrscheinlich relevant)
        if re.search(r'https?://|/\w+/\w+|\d+\.\d+\.\d+', stripped):
            score += 1.5

        # Malus für sehr kurze, nichtssagende Zeilen
        if len(stripped) < 5:
            score -= 2.0

        scored.append((line, score))
    return scored


def filter_pipeline(raw_text: str, max_lines: int = 50) -> dict:
    """
    Vollständige Filter-Pipeline v2.0. Gibt gefilterten Text + Statistiken zurück.

    Schritte:
    1. ANSI Codes entfernen
    2. Ladebalken-Zeilen entfernen
    3. [NEU v2.0] Ähnliche Muster kondensieren (npm warn, pip collect, pytest PASSED...)
       → VOR Duplikat-Komprimierung, damit Pattern-Gruppen nicht gesplittet werden!
    4. Exakte Duplikate komprimieren
    5. Timestamp-Cluster komprimieren
    6. Entropie-Scoring → nur High-Score Zeilen behalten
    7. Cap bei max_lines
    """
    original_chars = len(raw_text)
    original_lines = raw_text.count('\n') + 1

    # Schritt 1: ANSI entfernen
    text = remove_ansi_codes(raw_text)

    # In Zeilen aufteilen
    lines = text.split('\n')

    # Schritt 2: Ladebalken entfernen
    lines = [l for l in lines if not is_progress_bar_line(l)]

    # Schritt 3: Ähnliche Muster kondensieren [NEU v2.0]
    # WICHTIG: Vor Duplikat-Komprimierung laufen, damit konsekutive Pattern-Gruppen
    # nicht durch [N× identische Zeile:] unterbrochen werden!
    lines = condense_similar_patterns(lines)

    # Schritt 4: Exakte Duplikate komprimieren (nach Pattern Condensation)
    lines = compress_duplicates(lines)

    # Schritt 5: Timestamp-Cluster komprimieren
    lines = compress_timestamp_clusters(lines)

    # Schritt 6: Entropie-Scoring
    scored = score_lines(lines)

    # Zeilen mit Score < 1.5 fallen raus (außer sie haben Keyword-Bonus)
    MIN_SCORE = 1.5
    filtered = [(line, score) for line, score in scored if score >= MIN_SCORE]

    # Wenn nach dem Filtern zu viel übrig, nur Top-N nach Score behalten
    # Aber: Reihenfolge wird beibehalten (Original-Sequenz bleibt)
    if len(filtered) > max_lines:
        # Wichtigste Zeilen nach Score bestimmen
        top_indices = sorted(
            range(len(filtered)),
            key=lambda i: filtered[i][1],
            reverse=True
        )[:max_lines]
        top_indices_set = set(top_indices)
        # In Original-Reihenfolge ausgeben
        filtered = [filtered[i] for i in sorted(top_indices_set)]

    filtered_lines_text = [line for line, _ in filtered]
    filtered_text = '\n'.join(filtered_lines_text).strip()
    filtered_chars = len(filtered_text)

    reduction_pct = round(
        (1 - filtered_chars / original_chars) * 100, 1
    ) if original_chars > 0 else 0.0

    return {
        "filtered_text": filtered_text,
        "original_lines": original_lines,
        "filtered_lines": len(filtered_lines_text),
        "original_chars": original_chars,
        "filtered_chars": filtered_chars,
        "reduction_pct": reduction_pct,
    }
