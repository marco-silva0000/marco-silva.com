---
  title: Hello everyone
  description: This is how this website is made
  date: '2020-05-09'
---

# Hello!

I'm writing this as a test for my post system, might as well write something useful.

**This page was generated with staticjs.** I have to thank Ben Awad for his [tutorial](https://www.youtube.com/watch?v=pY0vWYLDDco).

<img height="200" width="200" src="avatar.png" />

## Goals

I first bought this server to have a place to have my own little place on the web but has been years since that and nothing was ever here, not even a 404. I started to use the server more recently to hose some demo telegram bots that I may write about in the future, and that made me search for options to actually have a page here.

## Tool

There were some requirements on the "tools" used to create this,
1. Something new, that made me learn. A tool that I don't use at work
1. Something simple to edit and on vim. Markdown blog posts, considered plain html, but nahh...
1. Something fast. A static site! Still want to "tree shake" the used CSS in the future
1. Something low maintenance. git is my backup, yarn2 and the markdown is all source controlled
1. Something easy to update. ssh, vim, yarn build, git add commit and push, done.

## Road
I first wanted to try out something new, so I decided to try out vue for the [initial draft](https://github.com/marco-silva0000/marco-silva.com/commit/80f7dc4f28f73d78f348249c27b8d55075f5a45b) of this website. It was fine, a quick afternoon was enough for the basics running, and it was online right away, as all was written directly on the server.

It worked fine, but when I decided to extend the features with this blog, and after getting inspiration from the above mentioned video, I wanted something more. Searched for some vue static generators after watching Ben's video, but the one I tried didn't work with yarn2(I want this to have it all in git, and to try it out..), so I said screw it let's go with react, I need to freshen up my react anyway.

After the initial work to get the basics working I had this website running that you can check out on my [github](https://github.com/marco-silva0000/marco-silva.com)
