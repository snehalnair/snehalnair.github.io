---
layout: page
title: blog
permalink: /blog/
---

{% if site.posts and site.posts.size > 0 %}
<div class="card-grid">
  {% for post in site.posts %}
  {% assign card_image = post.image %}
  {% assign fallback_summary = post.excerpt | strip_html | truncate: 180 %}
  <div class="card" data-original-url="{{ post.original_url }}">
    <img
      src="{% if card_image %}{{ card_image }}{% endif %}"
      alt="{{ post.title }}"
      style="width: 100%; border-radius: 8px; margin-bottom: 0.5rem; {% if not card_image %}display: none;{% endif %}"
    />
    <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    <p class="card-summary" data-fallback="{{ fallback_summary }}"></p>
    <p><small>{{ post.date | date: "%b %-d, %Y" }}</small></p>
  </div>
  {% endfor %}
</div>

<script>
  (function () {
    const cards = document.querySelectorAll(".card[data-original-url]");
    cards.forEach((card) => {
      const originalUrl = card.getAttribute("data-original-url");
      if (!originalUrl) return;

      const proxyUrl = "https://r.jina.ai/http://";
      fetch(proxyUrl + originalUrl)
        .then((res) => res.text())
        .then((html) => {
          const imgMatch = html.match(/property=\"og:image\" content=\"([^\"]+)\"/i);
          const descMatch = html.match(/name=\"description\" content=\"([^\"]+)\"/i);

          const img = card.querySelector("img");
          if (imgMatch && imgMatch[1] && img) {
            img.src = imgMatch[1];
            img.style.display = "";
          }

          const summary = card.querySelector(".card-summary");
          if (descMatch && descMatch[1] && summary) {
            summary.textContent = descMatch[1];
          } else if (summary && summary.getAttribute("data-fallback")) {
            summary.textContent = summary.getAttribute("data-fallback");
          }
        })
        .catch(() => {
          const summary = card.querySelector(".card-summary");
          if (summary && summary.getAttribute("data-fallback")) {
            summary.textContent = summary.getAttribute("data-fallback");
          }
        });
    });
  })();
</script>
{% else %}
No posts yet. Medium posts will appear here after import.
{% endif %}
