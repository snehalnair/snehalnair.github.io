---
layout: page
title: portfolio
permalink: /portfolio/
---

{% for item in site.portfolio %}
### [{{ item.title }}]({{ item.url | relative_url }})
{{ item.excerpt | strip_html }}

{% endfor %}
