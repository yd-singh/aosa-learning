from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup, Tag

BASE_URL = 'https://aosabook.org/en/'
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'
CONTENT_DIR = ROOT / 'content'
CHAPTERS_DIR = CONTENT_DIR / 'chapters'
ASSETS_DIR = CONTENT_DIR / 'assets'
OUTPUT_PATH = DATA_DIR / 'aosa_dataset.json'
OUTPUT_JS_PATH = DATA_DIR / 'aosa_dataset.js'
USER_AGENT = 'ArchitectureArcadeOfflineBuilder/1.0'

COLLECTION_META = {
    'v1': {
        'name': 'AOSA Volume 1',
        'tagline': 'Foundational case studies in systems, tools, and platforms.',
        'tone': 'foundation',
    },
    'v2': {
        'name': 'AOSA Volume 2',
        'tagline': 'More ambitious software architectures across infra, product, and data.',
        'tone': 'expansion',
    },
    'posa': {
        'name': 'Performance of Open Source Applications',
        'tagline': 'A performance-first lens on scale, observability, and efficiency.',
        'tone': 'optimization',
    },
    '500L': {
        'name': '500 Lines or Less',
        'tagline': 'Compact builds that make hard ideas concrete with working code.',
        'tone': 'builder',
    },
}

THEME_RULES = [
    ('distributed-systems', ['distributed', 'cluster', 'riak', 'hadoop', 'hdfs', 'storm', 'zeromq', 'network', 'telepathy', 'jitsi', 'search', 'storage', 'replication']),
    ('developer-tooling', ['cmake', 'llvm', 'bash', 'eclipse', 'mercurial', 'packaging', 'testing', 'continuous integration', 'selenium', 'vcs', 'build', 'compiler']),
    ('data-and-ml', ['qr', 'numenta', 'vistrails', 'scikit', 'pandas', 'machine', 'data', 'cluster', 'objects', 'sampler', 'image']),
    ('product-and-ui', ['openoffice', 'socialcalc', 'battle for wesnoth', 'web crawler', 'flow shop', 'crawler', 'browser', 'wiki', 'dagoba', 'template', 'modeller', 'text editor', 'static site', 'ci']),
    ('runtime-and-languages', ['lua', 'erlang', 'python', 'interpreter', 'virtual machine', 'spreadsheet', 'regex', 'template engine']),
    ('performance-and-ops', ['performance', 'monitor', 'graphite', 'memsharded', 'font tools', 'sendmail', 'suricata', 'seccomp', 'freebsd', 'parallel']),
]

PM_LENSES = {
    'distributed-systems': [
        'trade reliability, latency, and operator burden explicitly',
        'translate failure modes into SLAs, rollout plans, and customer risk',
        'spot where architecture choices become roadmap constraints',
    ],
    'developer-tooling': [
        'understand how toolchain choices shape team velocity',
        'connect developer experience bottlenecks to delivery risk',
        'reason about maintainability, extensibility, and ecosystem lock-in',
    ],
    'data-and-ml': [
        'separate data pipeline complexity from user-facing product value',
        'identify the feedback loops needed for model or analytics quality',
        'frame measurement, correctness, and trust as product requirements',
    ],
    'product-and-ui': [
        'connect technical architecture to collaboration patterns and user workflows',
        'see where UI and domain abstractions leak into operations and support',
        'turn implementation details into better product discovery questions',
    ],
    'runtime-and-languages': [
        'build intuition for abstraction costs and where performance cliffs appear',
        'understand how language/runtime decisions affect ecosystem growth',
        'spot platform choices that influence hiring, tooling, and extensibility',
    ],
    'performance-and-ops': [
        'tie observability and efficiency work to product outcomes',
        'identify optimization work worth prioritizing versus polishing',
        'understand where operational excellence changes customer trust',
    ],
}

ACTIVITY_BANK = {
    'distributed-systems': [
        'Draw the critical request path and mark every probable failure boundary.',
        'Write a PM brief describing the worst customer-visible outage this design could trigger.',
        'Map the consistency, throughput, and complexity tradeoffs into a release memo.',
    ],
    'developer-tooling': [
        'Trace the developer workflow end to end and identify hidden waiting states.',
        'Draft a platform investment case for the subsystem that most improves team leverage.',
        'List the extension points and decide which would need product-level governance.',
    ],
    'data-and-ml': [
        'Sketch the data lifecycle from input to decision and call out validation points.',
        'Write three success metrics and three failure metrics for this system.',
        'Turn the chapter architecture into a one-page analytics or ML product spec.',
    ],
    'product-and-ui': [
        'Reverse-engineer the core user workflow and identify the dominant object model.',
        'Define the top three UX failure cases the architecture must avoid.',
        'Translate implementation choices into a product requirement checklist.',
    ],
    'runtime-and-languages': [
        'Explain the main abstraction layers as if you were onboarding a new PM to the team.',
        'Identify where the runtime hides complexity well and where it leaks.',
        'Write a short memo on how extensibility affects ecosystem strategy here.',
    ],
    'performance-and-ops': [
        'List the likely bottlenecks before reading further, then compare with the chapter.',
        'Write an incident review template tailored to this architecture.',
        'Specify the minimum observability dashboard a PM should demand.',
    ],
}

QUIZ_BANK = {
    'distributed-systems': [
        'Where does this architecture prefer availability over consistency, or vice versa?',
        'Which component would you instrument first during a production incident?',
        'What customer promise is hardest to uphold if one subsystem degrades?',
    ],
    'developer-tooling': [
        'Which extension point is most likely to create long-term maintenance cost?',
        'What single workflow delay hurts team throughput the most?',
        'If you could fund one internal platform improvement here, what would it be?',
    ],
    'data-and-ml': [
        'What data quality assumption could silently undermine outcomes here?',
        'Which metric would best reveal a regression before users complain?',
        'What feedback loop is essential for this system to keep improving?',
    ],
    'product-and-ui': [
        'What domain abstraction appears central to the user experience?',
        'Where could architecture constraints bleed into UX in a harmful way?',
        'What product decision depends most on understanding this system deeply?',
    ],
    'runtime-and-languages': [
        'Which abstraction provides the most leverage and what does it cost?',
        'Where would performance tuning likely require breaking a clean abstraction?',
        'What ecosystem bet does this implementation make?',
    ],
    'performance-and-ops': [
        'What bottleneck would you test first and why?',
        'Which optimization seems likely to improve cost without harming clarity?',
        'What monitoring signal would you put on a PM dashboard?',
    ],
}


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={'User-Agent': USER_AGENT})
    with urlopen(request) as response:
        return response.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode('utf-8', 'ignore')


def clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    return value.strip('-') or 'section'


def is_biography_paragraph(text: str) -> bool:
    lowered = text.lower()
    bio_markers = [
        'works at ',
        'worked at ',
        'has worked at ',
        'started using ',
        'maintains ',
        'is the founder',
        'is a software engineer',
        'lives in ',
        'is currently ',
        'has been working',
        'has maintained ',
        'received his ',
        'received her ',
        'is a phd',
        'works on ',
    ]
    return any(marker in lowered for marker in bio_markers)


def infer_theme(title: str, summary: str) -> str:
    haystack = f'{title} {summary}'.lower()
    for theme, keywords in THEME_RULES:
        if any(keyword in haystack for keyword in keywords):
            return theme
    return 'product-and-ui'


def estimate_minutes(session_kind: str, theme: str, headings: list[dict[str, str]]) -> int:
    base = 55 if session_kind == 'introduction' else 85
    if session_kind == 'bibliography':
        return 35
    if theme in {'distributed-systems', 'performance-and-ops'}:
        base += 15
    if len(headings) >= 10:
        base += 15
    elif len(headings) >= 6:
        base += 10
    return min(base, 130)


def estimate_difficulty(session_kind: str, theme: str, headings: list[dict[str, str]]) -> int:
    if session_kind == 'bibliography':
        return 1
    score = 2
    if theme in {'distributed-systems', 'runtime-and-languages', 'performance-and-ops'}:
        score += 1
    if len(headings) >= 9:
        score += 1
    return min(score, 5)


def to_asset_path(asset_url: str) -> Path:
    parsed = urlparse(asset_url)
    raw_path = parsed.path.lstrip('/')
    if not raw_path:
        raw_path = 'asset.bin'
    return ASSETS_DIR / Path(raw_path)


def parse_homepage() -> list[tuple[str, list[tuple[int, str, str, str]]]]:
    soup = BeautifulSoup(fetch_text(BASE_URL), 'html.parser')
    sections: list[tuple[str, list[tuple[int, str, str, str]]]] = []

    for heading in soup.select('h2'):
        heading_text = clean(heading.get_text(' ', strip=True))
        table = heading.find_next('table')
        if not table:
            continue
        key = None
        if 'Volume 1' in heading_text:
            key = 'v1'
        elif 'Volume 2' in heading_text:
            key = 'v2'
        elif 'Performance of Open Source Applications' in heading_text:
            key = 'posa'
        elif '500 Lines or Less' in heading_text:
            key = '500L'
        if not key:
            continue

        rows = []
        local_index = 1
        for tr in table.select('tr'):
            cells = tr.select('td')
            if len(cells) < 3:
                continue
            anchor = cells[1].select_one('a[href]')
            if not anchor:
                continue
            href = clean(anchor.get('href', ''))
            title = clean(anchor.get_text(' ', strip=True))
            authors = clean(cells[2].get_text(' ', strip=True))
            if not href or not title:
                continue
            rows.append((local_index, title, authors, urljoin(BASE_URL, href)))
            local_index += 1
        sections.append((key, rows))
    return sections


def select_chapter_nodes(body: Tag) -> list[Tag]:
    nodes: list[Tag] = []
    for child in body.find_all(recursive=False):
        if not isinstance(child, Tag):
            continue
        classes = set(child.get('class') or [])
        if 'titlebox' in classes or 'banner' in classes:
            continue
        if child.name in {'script', 'noscript'}:
            continue
        nodes.append(copy.copy(child))
    return nodes


def build_fragment(nodes: list[Tag]) -> BeautifulSoup:
    fragment = BeautifulSoup('<div class="chapter-body"></div>', 'html.parser')
    wrapper = fragment.select_one('.chapter-body')
    assert wrapper is not None
    for node in nodes:
        wrapper.append(node)
    return fragment


def extract_summary(fragment: BeautifulSoup) -> str:
    paragraphs: list[str] = []
    for p in fragment.select('p'):
        if 'author' in (p.get('class') or []):
            continue
        text = clean(p.get_text(' ', strip=True))
        if len(text) < 80:
            continue
        if 'Software Design by Example' in text:
            continue
        if is_biography_paragraph(text):
            continue
        if text.startswith('Figure '):
            continue
        paragraphs.append(text)
        if len(paragraphs) == 2:
            break
    return ' '.join(paragraphs)


def assign_heading_ids(fragment: BeautifulSoup) -> list[dict[str, str]]:
    headings: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for heading in fragment.select('h2, h3'):
        text = clean(heading.get_text(' ', strip=True))
        if not text:
            continue
        heading_id = heading.get('id')
        if not heading_id:
            parent_with_id = heading.find_parent(attrs={'id': True})
            heading_id = parent_with_id.get('id') if parent_with_id else None
        if not heading_id:
            heading_id = slugify(text)
        base_id = heading_id
        counter = 2
        while heading_id in seen_ids:
            heading_id = f'{base_id}-{counter}'
            counter += 1
        heading['id'] = heading_id
        seen_ids.add(heading_id)
        headings.append({'id': heading_id, 'text': text, 'level': heading.name})
    return headings


def rewrite_assets(fragment: BeautifulSoup, chapter_dir: Path, asset_manifest: list[dict[str, str]]) -> tuple[int, int]:
    image_count = 0
    missing_assets = 0
    for img in fragment.select('img[src]'):
        src = img.get('src', '').strip()
        if not src:
            continue
        image_count += 1
        asset_url = urljoin(BASE_URL, src)
        asset_path = to_asset_path(asset_url)
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if not asset_path.exists():
                asset_path.write_bytes(fetch_bytes(asset_url))
            img['src'] = str(asset_path.relative_to(ROOT)).replace(os.sep, '/')
            asset_manifest.append({
                'sourceUrl': asset_url,
                'localPath': str(asset_path.relative_to(ROOT)).replace(os.sep, '/'),
                'kind': 'image',
            })
        except Exception:
            missing_assets += 1
            img['data-missing-src'] = asset_url
    return image_count, missing_assets


def rewrite_links(fragment: BeautifulSoup, url_to_session: dict[str, str]) -> None:
    for anchor in fragment.select('a[href]'):
        href = anchor.get('href', '').strip()
        if not href:
            continue
        if href.startswith('#'):
            continue

        absolute = urljoin(BASE_URL, href)
        normalized, frag = urldefrag(absolute)
        session_id = url_to_session.get(normalized)
        if session_id:
            local_href = f'?session={session_id}&view=reader'
            if frag:
                local_href = f'{local_href}#{frag}'
            anchor['href'] = local_href
            anchor['data-session-link'] = session_id
            continue

        if normalized.startswith(BASE_URL):
            anchor['href'] = absolute
            anchor['target'] = '_blank'
            anchor['rel'] = 'noreferrer'
            continue

        anchor['target'] = '_blank'
        anchor['rel'] = 'noreferrer'


def bundle_session(session_id: str, collection_id: str, collection_name: str, title: str, homepage_authors: str, url: str, session_kind: str, url_to_session: dict[str, str]) -> dict:
    chapter_dir = CHAPTERS_DIR / session_id
    chapter_dir.mkdir(parents=True, exist_ok=True)

    raw_html = fetch_text(url)
    page_path = chapter_dir / 'page.html'
    page_path.write_text(raw_html, encoding='utf-8')

    soup = BeautifulSoup(raw_html, 'html.parser')
    body = soup.body or soup
    author_el = soup.select_one('p.author')
    author = clean(author_el.get_text(' ', strip=True)) if author_el else homepage_authors

    nodes = select_chapter_nodes(body)
    fragment = build_fragment(nodes)
    summary = extract_summary(fragment)
    headings = assign_heading_ids(fragment)
    asset_manifest: list[dict[str, str]] = []
    image_count, missing_assets = rewrite_assets(fragment, chapter_dir, asset_manifest)
    rewrite_links(fragment, url_to_session)

    for tag in fragment.select('script, link[rel~=stylesheet], style'):
        tag.decompose()

    content_path = chapter_dir / 'content.html'
    wrapper = fragment.select_one('.chapter-body')
    assert wrapper is not None
    content_html = wrapper.decode_contents(formatter='html')
    content_path.write_text(content_html, encoding='utf-8')

    plain_text = clean(wrapper.get_text(' ', strip=True))
    word_count = len(re.findall(r'\b\w+\b', plain_text))
    table_count = len(fragment.select('table'))
    code_block_count = len(fragment.select('pre, code.programlisting'))
    has_footnotes = bool(fragment.select('.footnotes, a[href^="#footnote"]'))

    meta = {
        'sessionId': session_id,
        'sourceUrl': url,
        'title': title,
        'author': author,
        'contentPath': str(content_path.relative_to(ROOT)).replace(os.sep, '/'),
        'rawPagePath': str(page_path.relative_to(ROOT)).replace(os.sep, '/'),
        'assets': asset_manifest,
        'anchors': headings,
        'wordCount': word_count,
        'imageCount': image_count,
        'tableCount': table_count,
        'codeBlockCount': code_block_count,
        'hasFootnotes': has_footnotes,
        'missingAssetCount': missing_assets,
    }
    (chapter_dir / 'meta.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')

    theme = infer_theme(title, summary)
    estimated_minutes = estimate_minutes(session_kind, theme, headings)
    difficulty = estimate_difficulty(session_kind, theme, headings)

    return {
        'id': session_id,
        'collectionId': collection_id,
        'collectionName': collection_name,
        'title': title,
        'author': author,
        'url': url,
        'sessionKind': session_kind,
        'summary': summary,
        'headings': [item['text'] for item in headings[:10]],
        'headingAnchors': headings,
        'theme': theme,
        'pmFocus': PM_LENSES[theme],
        'activities': ACTIVITY_BANK[theme],
        'quiz': QUIZ_BANK[theme],
        'estimatedMinutes': estimated_minutes,
        'difficulty': difficulty,
        'searchText': plain_text[:12000],
        'offline': {
            'available': True,
            'contentPath': str(content_path.relative_to(ROOT)).replace(os.sep, '/'),
            'rawPagePath': str(page_path.relative_to(ROOT)).replace(os.sep, '/'),
            'assetCount': len(asset_manifest),
            'wordCount': word_count,
            'imageCount': image_count,
            'tableCount': table_count,
            'codeBlockCount': code_block_count,
            'hasFootnotes': has_footnotes,
            'missingAssetCount': missing_assets,
        },
    }


def build_dataset() -> dict:
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    sections = parse_homepage()
    url_to_session: dict[str, str] = {}
    for collection_id, rows in sections:
        for local_index, _title, _authors, url in rows:
            url_to_session[url] = f'{collection_id}-{local_index:02d}'

    collections_output = []
    all_sessions = []
    global_index = 1

    for collection_id, rows in sections:
        meta = COLLECTION_META[collection_id]
        sessions_output = []
        for local_index, title, homepage_authors, url in rows:
            lower = title.lower()
            if title == 'Introduction':
                kind = 'introduction'
            elif 'bibliography' in lower:
                kind = 'bibliography'
            else:
                kind = 'chapter'

            session_id = f'{collection_id}-{local_index:02d}'
            session = bundle_session(session_id, collection_id, meta['name'], title, homepage_authors, url, kind, url_to_session)
            session['globalIndex'] = global_index
            session['localIndex'] = local_index
            session['collectionTagline'] = meta['tagline']
            session['collectionTone'] = meta['tone']
            sessions_output.append(session)
            all_sessions.append(session)
            global_index += 1

        collections_output.append({
            'id': collection_id,
            'name': meta['name'],
            'tagline': meta['tagline'],
            'tone': meta['tone'],
            'sessionCount': len(sessions_output),
            'sessions': sessions_output,
        })

    dataset = {
        'generatedFrom': BASE_URL,
        'offlineMode': True,
        'collections': collections_output,
        'sessions': all_sessions,
        'totalSessions': len(all_sessions),
    }
    OUTPUT_PATH.write_text(json.dumps(dataset, indent=2), encoding='utf-8')
    OUTPUT_JS_PATH.write_text('window.AOSA_DATA = ' + json.dumps(dataset, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    return dataset


def main() -> None:
    dataset = build_dataset()
    print(f'Wrote {dataset["totalSessions"]} sessions to {OUTPUT_PATH}')
    print(f'Wrote browser bundle to {OUTPUT_JS_PATH}')


if __name__ == '__main__':
    main()
