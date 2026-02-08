#!/usr/bin/env python3
import argparse
import html
import re
from pathlib import Path


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "post"


def extract_title(raw: str) -> str:
    m = re.search(r'<h1[^>]*class="p-name"[^>]*>(.*?)</h1>', raw, re.DOTALL)
    if m:
        return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
    m = re.search(r"<title>(.*?)</title>", raw, re.DOTALL)
    return html.unescape(m.group(1)).strip() if m else "Medium Post"


def extract_date(name: str, raw: str) -> str:
    m = re.match(r"(\d{4}-\d{2}-\d{2})_", name)
    if m:
        return m.group(1)
    m = re.search(r'<time[^>]*datetime="(\d{4}-\d{2}-\d{2})', raw)
    return m.group(1) if m else "1970-01-01"


def extract_canonical(raw: str) -> str:
    m = re.search(r'<a[^>]*class="p-canonical"[^>]*href="([^"]+)"', raw)
    return m.group(1) if m else ""


def extract_body(raw: str) -> str:
    m = re.search(r'<section[^>]*data-field="body"[^>]*>(.*)</section>\s*<footer', raw, re.DOTALL)
    if not m:
        m = re.search(r'<section[^>]*data-field="body"[^>]*>(.*)</section>\s*</article>', raw, re.DOTALL)
    body = m.group(1).strip() if m else ""
    body = re.sub(r'^<section[^>]*>', "", body)
    body = re.sub(r"</section>\s*$", "", body)
    return body


def convert_post(path: Path) -> tuple[str, str, str, str]:
    raw = path.read_text(encoding="utf-8")
    title = extract_title(raw)
    date = extract_date(path.name, raw)
    canonical = extract_canonical(raw)
    body = extract_body(raw)
    return title, date, canonical, body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="Path to Medium export posts directory")
    parser.add_argument("--dest", default="_posts", help="Destination _posts directory")
    parser.add_argument("--include-drafts", action="store_true", help="Include draft_*.html files")
    args = parser.parse_args()

    src_dir = Path(args.src)
    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped = 0

    for path in sorted(src_dir.glob("*.html")):
        if path.name.startswith("draft_") and not args.include_drafts:
            skipped += 1
            continue

        title, date, canonical, body = convert_post(path)
        slug = slugify(title)
        out_path = dest_dir / f"{date}-{slug}.md"

        fm_lines = [
            "---",
            "layout: post",
            f'title: "{title.replace("\"", "\\\"")}"',
            f"date: {date}",
        ]
        if canonical:
            fm_lines.append(f'original_url: "{canonical}"')
        fm_lines.append("---")

        content = "\n".join(fm_lines) + "\n\n" + body + "\n"
        out_path.write_text(content, encoding="utf-8")
        converted += 1

    print(f"Converted {converted} posts. Skipped drafts: {skipped}.")


if __name__ == "__main__":
    main()
