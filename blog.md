---
layout: page
title: blog
permalink: /blog/
---

{% if site.posts and site.posts.size > 0 %}
<div class="card-grid">
  {% for post in site.posts %}
  {% assign card_image = post.image %}
  {% assign card_summary = post.summary | default: post.excerpt | strip_html | truncate: 180 %}
  <div class="card" data-original-url="{{ post.original_url }}">
    {% if card_image %}
    <img src="{{ card_image }}" alt="{{ post.title }}" style="width: 100%; border-radius: 8px; margin-bottom: 0.5rem;" />
    {% endif %}
    <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    {% if card_summary %}
    <p class="card-summary">{{ card_summary }}</p>
    {% else %}
    <p class="card-summary"></p>
    {% endif %}
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

          if (imgMatch && imgMatch[1]) {
            const img = card.querySelector("img");
            if (img) img.src = imgMatch[1];
          }

          if (descMatch && descMatch[1]) {
            const summary = card.querySelector(".card-summary");
            if (summary) summary.textContent = descMatch[1];
          }
        })
        .catch(() => {});
    });
  })();
</script>
{% else %}
No posts yet. Medium posts will appear here after import.
{% endif %}
