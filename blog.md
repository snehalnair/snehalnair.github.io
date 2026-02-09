---
layout: page
title: blog
permalink: /blog/
---

{% if site.posts and site.posts.size > 0 %}
{% for post in site.posts %}
- [{{ post.title }}]({{ post.url | relative_url }}) — {{ post.date | date: "%b %-d, %Y" }}
{% endfor %}
{% else %}
No posts yet. Medium posts will appear here after import.
{% endif %}
