---
layout: page
title: portfolio
permalink: /portfolio/
---

<div class="card-grid">
  {% for item in site.portfolio %}
  <div class="card">
    <h3><a href="{{ item.url | relative_url }}">{{ item.title }}</a></h3>
    <p>{{ item.excerpt | strip_html }}</p>
  </div>
  {% endfor %}
</div>
