#!/usr/bin/env python3
import html
import re
from pathlib import Path


def extract_canonical(raw: str) -> str:
    m = re.search(r'<a[^>]*class="p-canonical"[^>]*href="([^"]+)"', raw)
    return m.group(1) if m else ""


def extract_post_id_from_url(url: str) -> str:
    m = re.search(r"-([0-9a-f]{12})$", url)
    return m.group(1) if m else ""


def extract_post_id_from_filename(name: str) -> str:
    m = re.search(r"-([0-9a-f]{12})\\.html$", name)
    return m.group(1) if m else ""


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
    src_dir = Path("/Users/snnair/Downloads/medium-export-2b4008a7025548e1e80427a0df87a3a320800049388c97c0d38547a4546e530b/posts")
    posts_dir = Path("/Users/snnair/Documents/snehalnair.github.io/_posts")

    original_to_post = {}
    id_to_post = {}
    for post_path in posts_dir.glob("*.md"):
        content = post_path.read_text(encoding="utf-8")
        m = re.search(r'^original_url:\s*"(.*?)"', content, re.MULTILINE)
        if m:
            original_to_post[m.group(1)] = post_path
            post_id = extract_post_id_from_url(m.group(1))
            if post_id:
                id_to_post[post_id] = post_path

    updated = 0
    for html_path in sorted(src_dir.glob("*.html")):
        if html_path.name.startswith("draft_"):
            continue
        raw = html_path.read_text(encoding="utf-8")
        canonical = extract_canonical(raw)
        post_path = None
        if canonical and canonical in original_to_post:
            post_path = original_to_post[canonical]
        if not post_path:
            post_id = extract_post_id_from_filename(html_path.name)
            if post_id and post_id in id_to_post:
                post_path = id_to_post[post_id]
        if not post_path:
            continue
        body = extract_body(raw)
        image = extract_first_image(body)
        summary = extract_subtitle(raw) or extract_first_paragraph(body)
        update_front_matter(post_path, image, summary)
        updated += 1

    print(f"Updated {updated} posts")


if __name__ == "__main__":
    main()
