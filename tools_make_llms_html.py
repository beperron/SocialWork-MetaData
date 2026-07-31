#!/usr/bin/env python3
"""Regenerate llms.html (the HTML mirror) from llms.txt. Run after editing llms.txt."""
import html
txt = open("llms.txt").read()
tpl = open("llms.html").read()
import re
new = re.sub(r"<pre>.*</pre>", "<pre>" + html.escape(txt) + "</pre>", tpl, flags=re.S)
open("llms.html","w").write(new)
print("llms.html refreshed from llms.txt")
