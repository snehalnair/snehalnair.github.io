---
layout: page
title: blog
permalink: /blog/
---

{% if site.posts and site.posts.size > 0 %}
<div class="card-grid">
  {% for post in site.posts %}
  {% assign card_image = post.image | default: "/Profile%20pic.jpeg" %}
  {% assign card_summary = post.summary | default: post.excerpt | strip_html | truncate: 180 %}
  <div class="card">
    <img src="{{ card_image }}" alt="{{ post.title }}" style="width: 100%; border-radius: 8px; margin-bottom: 0.5rem;" />
    <h3><a href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    {% if card_summary %}
    <p>{{ card_summary }}</p>
    {% endif %}
    <p><small>{{ post.date | date: "%b %-d, %Y" }}</small></p>
  </div>
  {% endfor %}
</div>
{% else %}
No posts yet. Medium posts will appear here after import.
{% endif %}
