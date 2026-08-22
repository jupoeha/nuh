#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import socket
import asyncio
from aiohttp import web
from n import (
    logger, more_posts
)

PORT = int(os.environ.get('PORT') or 5000)

def is_port_available(port, host='0.0.0.0'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


async def http_handler(request):
    path = request.path

    pages = {
        '/': page_home,
        '/about': page_about,
        '/blog': page_blog,
        '/blog/hello-world': page_post_hello,
        '/blog/python-tips': page_post_python,
        '/blog/life-in-2025': page_post_life,
        '/projects': page_projects,
        '/reading': page_reading,
        '/contact': page_contact,
    }

    handler = pages.get(path)
    if handler:
        return web.Response(text=handler(), content_type='text/html', charset='utf-8')

    return web.Response(status=404, text=page_404(), content_type='text/html', charset='utf-8')

NAV = """
<nav>
  <div class="nav-inner">
    <a class="logo" href="/">✦ Alex Chen</a>
    <ul>
      <li><a href="/blog">Blog</a></li>
      <li><a href="/projects">Projects</a></li>
      <li><a href="/reading">Reading</a></li>
      <li><a href="/about">About</a></li>
      <li><a href="/contact">Contact</a></li>
    </ul>
  </div>
</nav>
"""

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #faf9f7; --text: #1a1a1a; --muted: #6b6b6b;
  --accent: #2563eb; --border: #e5e5e5; --card: #ffffff;
  --sans: 'Georgia', serif;
}
body { background: var(--bg); color: var(--text); font-family: var(--sans);
       line-height: 1.75; font-size: 17px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
nav { border-bottom: 1px solid var(--border); background: var(--bg);
      padding: 20px 0; margin-bottom: 60px; }
nav .nav-inner { max-width: 800px; margin: 0 auto; display: flex;
                 justify-content: space-between; align-items: center; }
nav .logo { font-weight: bold; font-size: 1.2rem; }
nav ul { display: flex; list-style: none; gap: 30px; }
main { max-width: 800px; margin: 0 auto; padding: 0 20px; }
h1 { font-size: 2.5rem; margin: 40px 0 20px; font-weight: 400; }
h2 { font-size: 1.6rem; margin: 40px 0 20px; font-weight: 400; margin-top: 60px; }
h3 { font-size: 1.2rem; margin: 20px 0 10px; font-weight: 500; }
p { margin-bottom: 20px; }
.section-label { color: var(--muted); font-size: 0.9rem; text-transform: uppercase;
                 letter-spacing: 1px; margin-bottom: 10px; }
.lead { font-size: 1.1rem; color: var(--muted); margin-bottom: 30px; }
.card { border: 1px solid var(--border); padding: 25px; border-radius: 8px;
        margin-bottom: 20px; background: var(--card); }
.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
          gap: 20px; margin-bottom: 20px; }
blockquote { border-left: 4px solid var(--accent); padding-left: 20px;
            margin: 30px 0; color: var(--muted); font-style: italic; }
code { background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-family: monospace;
       font-size: 0.9rem; }
pre { background: #f0f0f0; padding: 20px; border-radius: 8px; overflow-x: auto;
      margin: 20px 0; }
pre code { background: none; padding: 0; }
ul { margin-left: 30px; margin-bottom: 20px; }
ul.plain { list-style: none; margin-left: 0; }
ul.plain li::before { content: "→ "; margin-right: 10px; color: var(--accent); }
.tag { display: inline-block; background: #e5e5e5; padding: 4px 10px;
       border-radius: 4px; font-size: 0.85rem; margin: 5px 8px 5px 0;
       color: #666; }
.star { color: #fbbf24; }
.contact-links { display: flex; flex-direction: column; gap: 12px; margin: 20px 0; }
.contact-links a { display: inline-block; padding: 10px 0; }
hr { border: none; border-top: 1px solid var(--border); margin: 40px 0; }
@media (max-width: 600px) {
  h1 { font-size: 1.8rem; }
  h2 { font-size: 1.3rem; }
  nav ul { gap: 15px; }
  .grid-2 { grid-template-columns: 1fr; }
}
"""

FOOTER = """
<hr>
<footer style="text-align:center;color:#6b6b6b;font-family:sans-serif;font-size:.9rem;padding:40px 0">
  <p>© 2025 Alex Chen. Built with Python + aiohttp.</p>
</footer>
"""

def layout(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{CSS}</style>
</head>
<body>
  {NAV}
  {body}
  {FOOTER}
</body>
</html>"""


def page_home():
    body = """
<main>
  <h1>Alex Chen</h1>
  <p class="lead">Writing about software engineering, building things, and occasional book reviews.</p>
  
  <p>I spend most of my time thinking about how to build systems that don't require heroics to operate. The last decade of my career has been a gradual shift from "how do I build this" to "how do I build this in a way that makes sense to the next person who touches it."</p>
  
  <p>When I'm not writing code or prose, you'll find me:</p>
  <ul class="plain">
    <li>Reading. Slowly working through the backlog of technical books I keep accumulating.</li>
    <li>Cooking. Genuinely surprised by how much I enjoy this.</li>
    <li>Hiking around the Bay Area. Best thinking happens on a trail.</li>
  </ul>
  
  <h2>Recent Posts</h2>
  <div class="card">
    <h3><a href="/blog/hello-world">Hello, World</a></h3>
    <p>Launching this blog. Why now, why this way, what I hope to write about.</p>
  </div>
  <div class="card">
    <h3><a href="/blog/python-tips">Python Tips for Performance</a></h3>
    <p>Small optimizations that compound. Most of these I learned the hard way.</p>
  </div>
  <div class="card">
    <h3><a href="/blog/life-in-2025">Halfway Through 2025</a></h3>
    <p>Goals, wins, failures, and what surprised me so far.</p>
  </div>
</main>"""
    return layout("Alex Chen", body)


def page_about():
    body = """
<main>
  <p class="section-label">About</p>
  <h1>About Me</h1>
  <p class="lead">A software engineer, writer, and occasional maker of things.</p>
  
  <h2>The Professional Version</h2>
  <p>I'm a senior engineer with 10+ years of experience building and scaling backend systems. Most recently, I've focused on distributed systems, observability, and the unglamorous work of making databases not explode at 3am.</p>
  
  <p>I've shipped things in Python, Go, Rust, and JavaScript. I have strong opinions about all of them.</p>
  
  <h2>The Real Version</h2>
  <p>I got into programming because I wanted to build things. Still do. Over the years, I've learned that building things is 10% inspiration and 90% dealing with edge cases nobody thought about.</p>
  
  <p>I started this blog because I kept writing long Slack messages that deserved better formatting. Turns out I have thoughts about software engineering.</p>
  
  <h2>What I Care About</h2>
  <ul class="plain">
    <li>Writing code that's easy to understand (not clever)</li>
    <li>Building systems that fail gracefully</li>
    <li>Documentation that developers actually read</li>
    <li>Mentoring people to be better engineers</li>
    <li>Getting to the hiking trail by 9am</li>
  </ul>
</main>"""
    return layout("About Me", body)


def page_blog():
    body = """
<main>
  <p class="section-label">Blog</p>
  <h1>All Posts</h1>
  <p class="lead">Thoughts on engineering, architecture, and the business of building software.</p>

  <div class="card">
    <h3><a href="/blog/hello-world">Hello, World</a></h3>
    <p>Launching this blog. Why now, why this way, what I hope to write about.</p>
  </div>
  <div class="card">
    <h3><a href="/blog/python-tips">Python Tips for Performance</a></h3>
    <p>Small optimizations that compound. Most of these I learned the hard way.</p>
  </div>
  <div class="card">
    <h3><a href="/blog/life-in-2025">Halfway Through 2025</a></h3>
    <p>Goals, wins, failures, and what surprised me so far.</p>
  </div>
</main>"""
    return layout("Blog", body)


def page_post_hello():
    body = """
<main>
  <p class="section-label">Blog</p>
  <h1>Hello, World</h1>
  <p class="lead">Why I'm starting a blog in 2025</p>
  
  <h2>The Motivation</h2>
  <p>I've been writing code professionally for a decade. I've read hundreds of blog posts, and I've found that the best ones share a quality: they think out loud. They don't pretend to have all the answers, but they do the hard work of explaining how they arrived at theirs.</p>
  
  <p>Most technical writing falls into two categories: the tutorial (here's how to build X) and the research paper (here are peer-reviewed findings). Both are valuable. But there's something missing — the gap between "I just learned this" and "here's a polished treatment in a conference talk."</p>
  
  <p>This blog is my attempt to fill that gap. It's where I'll write about things I'm learning, systems I'm building, and ideas that I'm still working through.</p>
  
  <h2>What You'll Find Here</h2>
  <p>I'll be writing about:</p>
  <ul class="plain">
    <li>Building systems that scale (and scale well)</li>
    <li>Design patterns and anti-patterns I've discovered</li>
    <li>The messy reality of shipping software</li>
    <li>Technical book reviews and notes</li>
    <li>Occasional adventures in cooking and hiking</li>
  </ul>
  
  <h2>What You Won't</h2>
  <p>I'm not going to write listicles, hot takes, or framework of the week posts. I'm not here to get Hacker News points (though that would be nice). I'm writing for the person who wants to think deeply about problems and isn't afraid of complexity.</p>
  
  <p>If that sounds like you, welcome.</p>
</main>"""
    return layout("Hello, World", body)


def page_post_python():
    body = """
<main>
  <p class="section-label">Blog</p>
  <h1>Python Tips for Performance</h1>
  <p class="lead">Small optimizations that compound over time</p>
  
  <h2>The Premise</h2>
  <p>Most people don't start with a performance problem in Python. They start with readable, idiomatic code. Then, months later, they're debugging why a script that "should take seconds" is taking minutes.</p>
  
  <p>This post is about the low-hanging fruit — small changes that often deliver outsized benefits and don't require you to rewrite everything in Rust.</p>
  
  <h2>1. Use Generators Instead of Lists</h2>
  <p>If you're building a list just to iterate once, use a generator instead. The memory savings can be substantial with large datasets.</p>
  
  <pre><code># Bad
def get_large_data():
    result = []
    for i in range(1000000):
        result.append(expensive_operation(i))
    return result

for item in get_large_data():
    process(item)

# Good
def get_large_data():
    for i in range(1000000):
        yield expensive_operation(i)

for item in get_large_data():
    process(item)</code></pre>
  
  <h2>2. Profile Before Optimizing</h2>
  <p>Use <code>cProfile</code> or <code>line_profiler</code> to find actual bottlenecks. I've spent hours optimizing the wrong function.</p>
  
  <h2>3. Batch Database Operations</h2>
  <p>If you're doing thousands of database inserts, batch them. A single bulk insert can be 100x faster than individual inserts.</p>
  
  <h2>4. Cache Expensive Computations</h2>
  <p>Python's <code>functools.lru_cache</code> is your friend. It's dead simple to use and surprisingly effective.</p>
  
  <blockquote>Premature optimization is the root of all evil. Late optimization is expensive. The trick is knowing when to profile and optimize.</blockquote>
</main>"""
    return layout("Python Tips", body)


def page_post_life():
    body = """
<main>
  <p class="section-label">Blog</p>
  <h1>Halfway Through 2025</h1>
  <p class="lead">Goals, wins, failures, and what surprised me</p>
  
  <h2>The Goals</h2>
  <p>At the start of the year, I made a list. Five major things I wanted to accomplish:</p>
  <ul class="plain">
    <li>Ship a meaningful open source project</li>
    <li>Read 12 books (one per month)</li>
    <li>Write 12 blog posts</li>
    <li>Get back into hiking seriously</li>
    <li>Learn to cook five dishes really well</li>
  </ul>
  
  <p>I won't claim I'm on pace for all of them. But the ones that matter most are happening.</p>
  
  <h2>The Wins</h2>
  <p>The open source project is shipping. It's not going to change the world, but it's solving a real problem, and people are using it. That feels good.</p>
  
  <p>I'm on pace for books — currently on my 8th. They're getting longer, but I'm picking better ones.</p>
  
  <p>Hiking is back. I'm out most weekends, and it's become the thing I look forward to most.</p>
  
  <h2>The Failures</h2>
  <p>Blog posts are behind. I thought I'd be much further along. But I'm learning that shipping takes more time than I estimated.</p>
  
  <p>Cooking is going better than expected, but I'm learning that mastery is harder than I thought.</p>
  
  <h2>The Surprise</h2>
  <p>Cooking. I started seriously learning to cook in January — not because I thought it would be life-changing, but because takeout was getting expensive. It <em>has</em> been life-changing. There is something deeply satisfying about making a good meal from scratch.</p>
  
  <blockquote>Most of the best things that happened this year weren't on any list I made.</blockquote>
  
  <h2>Goals for H2</h2>
  <p>Finish the reading list. Ship one more project. Call my parents more. Write at least one post a month. That's enough.</p>
</main>"""
    return layout("Life in 2025", body)


def page_projects():
    body = """
<main>
  <p class="section-label">Projects</p>
  <h1>Things I've Built</h1>
  <p class="lead">Side projects, open source contributions, and experiments — some finished, some ongoing, some abandoned with dignity.</p>

  <div class="card">
    <h3>dotforge <span class="tag">Rust</span><span class="tag">CLI</span></h3>
    <p>A dotfile manager that actually handles symlinks, secrets, and per-machine overrides without a 500-line bash script. Work in progress.</p>
    <p><a href="#">GitHub →</a></p>
  </div>

  <div class="card">
    <h3>marksnip <span class="tag">Python</span><span class="tag">Browser Extension</span></h3>
    <p>A browser extension + local API server for saving highlighted text as Markdown to a local folder. I use this daily for reading notes.</p>
    <p><a href="#">GitHub →</a></p>
  </div>

  <div class="card">
    <h3>aqi-desk <span class="tag">Python</span><span class="tag">Hardware</span></h3>
    <p>A Raspberry Pi project that displays real-time air quality index on a small e-ink display. Built during wildfire season. Genuinely useful.</p>
    <p><a href="#">GitHub →</a></p>
  </div>

  <div class="card">
    <h3>This Blog <span class="tag">Python</span><span class="tag">aiohttp</span></h3>
    <p>Handbuilt with aiohttp, zero JavaScript frameworks, and a perhaps excessive amount of inline CSS. Fast, simple, mine.</p>
  </div>

  <h2>Graveyard</h2>
  <p style="color:#6b6b6b;font-family:sans-serif;font-size:.9rem">Projects I started, learned from, and let rest in peace.</p>
  <ul class="plain">
    <li>habit-cli — a terminal habit tracker. Replaced by a paper notebook.</li>
    <li>recipe-graph — graph database for recipes. Overengineered. Delicious results though.</li>
    <li>font-pairer — ML model to suggest font combinations. Worked okay. Nobody used it.</li>
  </ul>
</main>"""
    return layout("Projects", body)


def page_reading():
    body = """
<main>
  <p class="section-label">Reading</p>
  <h1>What I'm Reading</h1>
  <p class="lead">Books I've read, am reading, or am definitely going to read soon (probably).</p>

  <h2>Currently Reading</h2>
  <div class="card">
    <h3>The Pragmatic Programmer <span style="color:#6b6b6b;font-weight:400;font-size:.9rem">— Hunt & Thomas</span></h3>
    <p>Second read-through. Somehow more relevant than the first time. "Your knowledge portfolio" chapter alone is worth the price.</p>
  </div>

  <h2>Finished in 2025</h2>
  <div class="grid-2">
    <div class="card">
      <h3>Four Thousand Weeks</h3>
      <p style="font-size:.88rem;color:#6b6b6b;font-family:sans-serif">Oliver Burkeman</p>
      <p>The anti-productivity productivity book. Genuinely changed how I think about time and finitude. <span class="star">★★★★★</span></p>
    </div>
    <div class="card">
      <h3>A Philosophy of Software Design</h3>
      <p style="font-size:.88rem;color:#6b6b6b;font-family:sans-serif">John Ousterhout</p>
      <p>Dense, opinionated, correct. The chapter on deep vs. shallow modules is required reading. <span class="star">★★★★★</span></p>
    </div>
    <div class="card">
      <h3>Exhalation</h3>
      <p style="font-size:.88rem;color:#6b6b6b;font-family:sans-serif">Ted Chiang</p>
      <p>Short stories that linger. "Story of Your Life" remains one of the best things I've ever read. <span class="star">★★★★★</span></p>
    </div>
    <div class="card">
      <h3>Staff Engineer</h3>
      <p style="font-size:.88rem;color:#6b6b6b;font-family:sans-serif">Will Larson</p>
      <p>Useful and honest. Good complement to the Pragmatic Programmer for the career side of engineering. <span class="star">★★★★☆</span></p>
    </div>
    <div class="card">
      <h3>The Art of Doing Science and Engineering</h3>
      <p style="font-size:.88rem;color:#6b6b6b;font-family:sans-serif">Richard Hamming</p>
      <p>How to have a meaningful career. Demanding in the best way. <span class="star">★★★★★</span></p>
    </div>
    <div class="card">
      <h3>Never Split the Difference</h3>
      <p style="font-size:.88rem;color:#6b6b6b;font-family:sans-serif">Chris Voss</p>
      <p>Surprisingly useful for engineering — design reviews, salary conversations, stakeholder management. <span class="star">★★★★☆</span></p>
    </div>
  </div>

  <h2>Up Next</h2>
  <ul class="plain">
    <li>An Elegant Puzzle — Will Larson</li>
    <li>The Dream Machine — M. Mitchell Waldrop</li>
    <li>Project Hail Mary — Andy Weir</li>
    <li>Thinking in Systems — Donella Meadows</li>
  </ul>
</main>"""
    return layout("Reading", body)


def page_contact():
    body = """
<main>
  <p class="section-label">Contact</p>
  <h1>Say Hello</h1>
  <p class="lead">I'm always happy to hear from readers, collaborators, or people who want to argue about Python style guides.</p>

  <p>The best way to reach me is email. I try to respond to everything, though it might take a week or two during busy stretches.</p>

  <h2>Find Me Online</h2>
  <div class="contact-links">
    <a href="mailto:alex@example.com">📧 alex@example.com</a>
    <a href="#">🐙 GitHub</a>
    <a href="#">💼 LinkedIn</a>
    <a href="#">🐦 Twitter / X</a>
    <a href="#">📚 Goodreads</a>
  </div>

  <h2>What I'm Open To</h2>
  <ul class="plain">
    <li>Interesting engineering problems and collaborations</li>
    <li>Book recommendations (please, send them)</li>
    <li>Feedback on anything I've written here</li>
    <li>Coffee chats if you're in San Francisco</li>
  </ul>

  <h2>What I'm Not Open To</h2>
  <ul class="plain">
    <li>Recruitment emails for jobs I didn't apply for</li>
    <li>Link exchanges and SEO pitches</li>
    <li>Requests to promote products I don't use</li>
  </ul>

  <p style="margin-top:40px;color:#6b6b6b;font-family:sans-serif;font-size:.88rem">Response time: usually within a week. Timezone: PST (UTC−8).</p>
</main>"""
    return layout("Contact", body)


def page_404():
    body = """
<main style="text-align:center;padding-top:80px">
  <div style="font-size:4rem;margin-bottom:24px">🗺️</div>
  <h1>404 — Page Not Found</h1>
  <p class="lead">This page doesn't exist. Maybe it moved, maybe it never existed.</p>
  <p><a href="/">← Go home</a> &nbsp;·&nbsp; <a href="/blog">Read the blog</a></p>
</main>"""
    return layout("404 Not Found", body)


async def main():
    app = web.Application()

    for route in ['/', '/about', '/blog', '/blog/hello-world',
                  '/blog/python-tips', '/blog/life-in-2025',
                  '/projects', '/reading', '/contact']:
        app.router.add_get(route, http_handler)
    app.router.add_get('/more-posts', more_posts)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"server is running on port {PORT}")
    
    try:
        await asyncio.Future()
    except KeyboardInterrupt:
        pass
    finally:
        await runner.cleanup()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
