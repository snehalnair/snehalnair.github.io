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


def extract_subtitle(raw: str) -> str:
    m = re.search(r'<section[^>]*data-field="subtitle"[^>]*>(.*?)</section>', raw, re.DOTALL)
    if not m:
        m = re.search(r'<section[^>]*data-field="description"[^>]*>(.*?)</section>', raw, re.DOTALL)
    if not m:
        return ""
    text = re.sub(r"<[^>]+>", "", m.group(1))
    return html.unescape(text).strip()


def extract_body(raw: str) -> str:
    m = re.search(r'<section[^>]*data-field="body"[^>]*>(.*)</section>\s*<footer', raw, re.DOTALL)
    if not m:
        m = re.search(r'<section[^>]*data-field="body"[^>]*>(.*)</section>\s*</article>', raw, re.DOTALL)
    return m.group(1) if m else ""


def extract_first_image(body: str) -> str:
    m = re.search(r'<img[^>]*src="([^"]+)"', body)
    return m.group(1) if m else ""


def extract_first_paragraph(body: str) -> str:
    m = re.search(r"<p[^>]*>(.*?)</p>", body, re.DOTALL)
    if not m:
        return ""
    text = re.sub(r"<[^>]+>", "", m.group(1))
    return html.unescape(text).strip()


def update_front_matter(post_path: Path, image: str, summary: str) -> None:
    content = post_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return
    parts = content.split("---", 2)
    if len(parts) < 3:
        return
    fm = parts[1]
    body = parts[2].lstrip("\n")

    def ensure_field(fm_text: str, key: str, value: str) -> str:
        if not value:
            return fm_text
        if re.search(rf"^{re.escape(key)}:\s*", fm_text, re.MULTILINE):
            fm_text = re.sub(rf"^{re.escape(key)}:.*$", f'{key}: "{value}"', fm_text, flags=re.MULTILINE)
        else:
            fm_text = fm_text.rstrip() + f'\n{key}: "{value}"\n'
        return fm_text

    fm = ensure_field(fm, "image", image)
    fm = ensure_field(fm, "summary", summary)
    post_path.write_text(f"---{fm}---\n\n{body}", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="Path to Medium export posts directory")
    parser.add_argument("--posts", required=True, help="Path to Jekyll _posts directory")
    args = parser.parse_args()

    src_dir = Path(args.src)
    posts_dir = Path(args.posts)

    for html_path in sorted(src_dir.glob("*.html")):
        if html_path.name.startswith("draft_"):
            continue
        raw = html_path.read_text(encoding="utf-8")
        title = extract_title(raw)
        date = extract_date(html_path.name, raw)
        slug = slugify(title)
        post_path = posts_dir / f"{date}-{slug}.md"
        if not post_path.exists():
            continue
        body = extract_body(raw)
        image = extract_first_image(body)
        summary = extract_subtitle(raw) or extract_first_paragraph(body)
        update_front_matter(post_path, image, summary)


if __name__ == "__main__":
    main()
