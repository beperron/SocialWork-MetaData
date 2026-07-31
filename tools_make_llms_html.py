#!/usr/bin/env python3
"""Regenerate llms.html (the HTML mirror) from llms.txt. Run after editing llms.txt."""
import html
txt = open("llms.txt").read()
tpl = open("llms.html").read()
head, _, rest = tpl.partition("<pre>")
_, _, tail = rest.partition("</pre>")
new = head + "<pre>" + html.escape(txt) + "</pre>" + tail
open("llms.html", "w").write(new)
print("llms.html refreshed from llms.txt")
