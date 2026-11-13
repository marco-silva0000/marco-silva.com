import os
import re
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML-like frontmatter and body from markdown."""
    frontmatter = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2].strip()
            for line in fm_text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().strip('"').strip("'")
                    frontmatter[key.strip()] = val
    return frontmatter, body


def extract_bullets(text: str) -> list[str]:
    """Extract work/education bullets, filtering out metadata headers."""
    bullets = []
    # If there is a responsibilities section, take from there
    if "## Key Responsibilities & Achievements" in text:
        text = text.split("## Key Responsibilities & Achievements", 1)[1]
    elif "## Curriculum & Focus Areas" in text:
        text = text.split("## Curriculum & Focus Areas", 1)[1]
    elif "## Core Areas of Study" in text:
        text = text.split("## Core Areas of Study", 1)[1]

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            bullet = line[2:].strip()
            meta_prefixes = (
                "**Company**",
                "**Dates**",
                "**Location**",
                "**Mode",
                "**Product**",
                "**Status**",
                "**Period**",
                "**Institution**",
            )
            if any(bullet.startswith(m) for m in meta_prefixes):
                continue
            # Strip markdown bolding for raw text if needed or keep clean
            bullets.append(bullet)
    return bullets


class Command(BaseCommand):
    help = "Sync CV from Obsidian notes in ~/vault/70 Personal to templates/cv.html and generate Typst PDF"

    def add_arguments(self, parser):
        parser.add_argument(
            "--vault",
            type=str,
            default=os.environ.get(
                "OBSIDIAN_PERSONAL_DIR",
                str(Path.home() / "vault" / "70 Personal"),
            ),
            help="Path to 70 Personal vault directory",
        )
        parser.add_argument(
            "--no-pdf",
            action="store_true",
            help="Skip compiling PDF with Typst",
        )

    def handle(self, *args, **options):
        vault_path = Path(options["vault"]).expanduser().resolve()
        if not vault_path.exists():
            raise CommandError(f"Vault path not found: {vault_path}")

        self.stdout.write(f"Reading personal notes from: {vault_path}")

        # 1. Profile
        profile_file = vault_path / "Profile.md"
        profile_fm, profile_body = parse_frontmatter(
            profile_file.read_text(encoding="utf-8") if profile_file.exists() else ""
        )

        name = "Marco Silva"
        location = profile_fm.get("location", "Helsinki, Finland")
        email = profile_fm.get("email", "inbox@marco-silva.com")
        website = profile_fm.get("website", "https://marco-silva.com")
        github = profile_fm.get("github", "https://github.com/marco-silva0000")
        linkedin = profile_fm.get("linkedin", "https://linkedin.com/in/marco-silva0000/")

        # 2. Work Experience
        work_dir = vault_path / "Work"
        work_entries = []
        if work_dir.exists():
            # Define sort order for known companies or parse period
            company_order = {
                "Ericsson": 1,
                "Black Duck": 2,
                "Hubel Positive Lightning": 3,
            }
            for f in work_dir.glob("*.md"):
                fm, body = parse_frontmatter(f.read_text(encoding="utf-8"))
                company = fm.get("company", f.stem)
                role = fm.get("role", "Developer")
                period = fm.get("period", "")
                loc = fm.get("location", "")
                site = fm.get("website", "")
                bullets = extract_bullets(body)
                # Filter out tech stack line from bullets
                bullets = [b for b in bullets if not b.startswith("**Platform Architecture**:") or True]
                work_entries.append(
                    {
                        "company": company,
                        "role": role,
                        "period": period,
                        "location": loc,
                        "website": site,
                        "bullets": bullets,
                        "order": company_order.get(company, 99),
                    }
                )
        work_entries.sort(key=lambda x: x["order"])

        # 3. Education
        edu_dir = vault_path / "Education"
        edu_entries = []
        if edu_dir.exists():
            for f in sorted(edu_dir.glob("*.md")):
                fm, body = parse_frontmatter(f.read_text(encoding="utf-8"))
                institution = fm.get("institution", "University of the Algarve")
                degree = fm.get("degree", f.stem)
                period = fm.get("period", "")
                loc = fm.get("location", "Faro, Portugal")
                level = fm.get("level", "")
                bullets = extract_bullets(body)
                edu_entries.append(
                    {
                        "institution": institution,
                        "degree": degree,
                        "period": period,
                        "location": loc,
                        "level": level,
                        "bullets": bullets,
                    }
                )

        # 4. Skills
        skills_file = vault_path / "Skills.md"
        skills_list = [
            "Django",
            "DRF",
            "Celery",
            "Python",
            "Angular",
            "React",
            "JavaScript",
            "Rust",
            "Kubernetes",
            "Helm",
            "Docker",
            "Robot Framework",
            "Neovim",
            "Git",
        ]
        if skills_file.exists():
            # Could parse skills dynamically or keep curated list
            pass

        # 5. Hobbies
        outdoors_bullets = ["Photography", "Kayak, surf, SUP, windsurf", "Hiking and climbing"]
        techy_bullets = [
            "Electronics/embedded (some rust embedded)",
            "Custom split keyboards (colemak + nvim)",
            "Ham radio, UK foundation license",
            "Home automation and homelab",
        ]

        # 6. CTFs
        htb_base = "https://ctf.hackthebox.com/event/details"
        ctfs = [
            (
                "HTB Business CTF 2025",
                f"{htb_base}/global-cyber-skills-benchmark-ctf-2025-operation-blackout-2174",
                "#19",
            ),
            ("Cyber Apocalypse 2025", f"{htb_base}/cyber-apocalypse-ctf-2025-tales-from-eldoria-2107", "#86"),
            ("HTB Business CTF 2024", f"{htb_base}/htb-business-ctf-2024-the-vault-of-hope-1474", "#14"),
            ("Cyber Apocalypse 2024", f"{htb_base}/cyber-apocalypse-2024-hacker-royale-1386", "#38"),
            ("HTB Business CTF 2023", f"{htb_base}/htb-business-ctf-2023-the-great-escape-997", "#12"),
            ("Cyber Apocalypse 2023", f"{htb_base}/cyber-apocalypse-2023-the-cursed-mission-821", "#15"),
            ("Synopsys CSAM 2022", f"{htb_base}/synopsys-csam-2022-ctf-613", "#2"),
        ]

        # 7. Advent of Code
        aoc = [
            ("2024", "50⭐"),
            ("2023", "42⭐"),
            ("2022", "40⭐"),
        ]

        # Render HTML
        html_out = self._render_html(
            name,
            location,
            email,
            website,
            github,
            linkedin,
            skills_list,
            outdoors_bullets,
            techy_bullets,
            work_entries,
            edu_entries,
            ctfs,
            aoc,
        )

        template_path = Path(settings.BASE_DIR) / "templates" / "cv.html"
        template_path.write_text(html_out, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Updated HTML CV: {template_path}"))

        # Render Typst
        typst_out = self._render_typst(
            name,
            location,
            email,
            website,
            github,
            linkedin,
            skills_list,
            work_entries,
            edu_entries,
            ctfs,
            aoc,
        )
        typst_file = Path(settings.BASE_DIR) / "cv.typ"
        typst_file.write_text(typst_out, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Generated Typst CV: {typst_file}"))

        # Compile PDF if typst is installed
        if not options.get("no_pdf"):
            typst_bin = shutil.which("typst") or str(Path.home() / ".nix-profile" / "bin" / "typst")
            if Path(typst_bin).exists():
                pdf_target = Path(settings.BASE_DIR) / "static" / "cv.pdf"
                pdf_target.parent.mkdir(parents=True, exist_ok=True)
                cmd = [typst_bin, "compile", str(typst_file), str(pdf_target)]
                try:
                    subprocess.run(cmd, check=True)
                    self.stdout.write(self.style.SUCCESS(f"Compiled PDF resume via Typst: {pdf_target}"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Typst compilation failed: {e}"))
            else:
                self.stdout.write("typst binary not found, skipped PDF compilation.")

    def _render_html(
        self, name, location, email, website, github, linkedin, skills, outdoors, techy, work, edu, ctfs, aoc
    ) -> str:
        def md_to_html(text: str) -> str:
            t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
            t = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', t)
            return t

        skills_html = "\n".join(f'        <span class="skill">{s}</span>' for s in skills)
        outdoors_html = "\n".join(f"        <li>{md_to_html(item)}</li>" for item in outdoors)
        techy_html = "\n".join(f"        <li>{md_to_html(item)}</li>" for item in techy)

        ctfs_html = "\n".join(
            f'        <li class="ctf-entry"><a href="{link}">{title}</a> <span>{rank}</span></li>'
            for title, link, rank in ctfs
        )
        aoc_html = "\n".join(f"        <li>{year} — {stars}</li>" for year, stars in aoc)

        work_sections = []
        for w in work:
            site_clean = re.sub(r"^https?://(www\.)?", "", w["website"]).rstrip("/")
            site_link = f' · <a href="{w["website"]}">{site_clean}</a>' if w["website"] else ""
            bullets_li = "\n".join(f"        <li>{md_to_html(b)}</li>" for b in w["bullets"])
            work_sections.append(f"""      <h3>{w["role"]} — {w["company"]}</h3>
      <p class="meta">{w["period"]} · {w["location"]}{site_link}</p>
      <ul>
{bullets_li}
      </ul>""")
        work_html = "\n\n".join(work_sections)

        edu_sections = []
        for e in edu:
            level_str = f" · {e['level']}" if e["level"] else ""
            bullets_li = "\n".join(f"        <li>{md_to_html(b)}</li>" for b in e["bullets"]) if e["bullets"] else ""
            bullets_block = f"\n      <ul>\n{bullets_li}\n      </ul>" if bullets_li else ""
            edu_sections.append(f"""      <h3>{e["degree"]} — {e["institution"]}</h3>
      <p class="meta">{e["period"]} · {e["location"]}{level_str}</p>{bullets_block}""")
        edu_html = "\n\n".join(edu_sections)

        return f"""{{% extends "base.html" %}}

{{% block title %}}{name}'s CV{{% endblock %}}

{{% block extra_css %}}
.cv {{ max-width: 720px; }}
.cv h2 {{
  font-size: 1.1rem;
  font-weight: 600;
  border-bottom: 1px solid #ddd;
  padding-bottom: 0.3rem;
  margin-top: 2rem;
  margin-bottom: 0.75rem;
}}
.cv h3 {{ font-size: 0.95rem; font-weight: 600; margin-top: 1rem; margin-bottom: 0.25rem; }}
.cv ul {{ padding-left: 1.2rem; margin: 0.25rem 0; }}
.cv p {{ margin: 0.2rem 0; }}
.cv .meta {{ font-size: 0.85rem; color: #666; }}
.cv .sidebar {{ font-size: 0.9rem; }}
.cv .sidebar ul {{ list-style: none; padding: 0; }}
.cv .sidebar li {{ margin: 0.15rem 0; }}
.cv .skills {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }}
.cv .skill {{ font-size: 0.8rem; padding: 0.15rem 0.5rem; border: 1px solid #ccc; border-radius: 3px; }}
.cv .conf-group {{ margin-bottom: 1rem; }}
.cv .conf-group strong {{ font-size: 0.9rem; }}
.cv .conf-group ul {{ margin-top: 0.25rem; }}
.cv .ctf-entry {{ display: flex; justify-content: space-between; }}
.cv .ctf-entry span {{ color: #666; font-size: 0.85rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 0.5rem 0; font-size: 0.85rem; }}
th, td {{ border: 1px solid #ddd; padding: 0.3rem 0.5rem; text-align: left; }}
th {{ background: #f5f5f5; }}
.cv-actions {{ margin: 0.75rem 0 1.5rem 0; }}
.cv-actions a {{
  font-size: 0.85rem;
  text-decoration: none;
  border: 1px solid #333;
  padding: 0.25rem 0.6rem;
  border-radius: 3px;
}}
.cv-actions a:hover {{ background: #222; color: #fff; }}
@media (min-width: 600px) {{ .cv-grid {{ display: grid; grid-template-columns: 1fr 2fr; gap: 2rem; }} }}
{{% endblock %}}

{{% block content %}}
<div class="cv">
  <div style="display: flex; justify-content: space-between; align-items: baseline;">
    <h1 style="font-size: 1.3rem; margin-bottom: 0.5rem;">{name}</h1>
    <div class="cv-actions">
      <a href="/static/cv.pdf" download>↓ Download PDF</a>
    </div>
  </div>
  <p class="meta">Portuguese · {location}</p>
  <p class="meta">
    inbox at marco-silva dot com ·
    <a href="{website}">marco-silva.com</a> ·
    <a href="{github}">github</a> ·
    <a href="{linkedin}">linkedin</a>
  </p>

  <div class="cv-grid">
    <div class="sidebar">

      <h2>Hobbies</h2>
      <h3>Outdoors</h3>
      <ul>
{outdoors_html}
      </ul>
      <h3>Techy</h3>
      <ul>
{techy_html}
      </ul>

      <h2>Skills</h2>
      <div class="skills">
{skills_html}
      </div>

      <h2>Conferences</h2>
      <div class="conf-group">
        <strong>DjangoCon EU</strong>
        <ul>
          <li>2025 — Dublin</li>
          <li>2024 — Vigo</li>
          <li>2023 — Edinburgh</li>
          <li>2022 — Porto</li>
          <li>2021 — Porto (virtual)</li>
          <li>2019 — Copenhagen</li>
          <li>2018 — Heidelberg</li>
          <li>2017 — Florence</li>
        </ul>
      </div>
      <div class="conf-group">
        <strong>BSides</strong>
        <ul>
          <li>Belfast 2024</li>
          <li>Belfast 2023</li>
          <li>Dublin 2023</li>
          <li>Belfast 2019</li>
        </ul>
      </div>
      <div class="conf-group">
        <strong>Other</strong>
        <ul>
          <li>RootedCon PT 2025</li>
          <li>EuroPython 2025</li>
        </ul>
      </div>

      <h2>CTFs</h2>
      <ul>
{ctfs_html}
      </ul>

      <h2>Advent of Code</h2>
      <ul>
{aoc_html}
      </ul>

    </div>
    <div>

      <h2>Work Experience</h2>

{work_html}

      <h2>Education</h2>

{edu_html}

      <h2>Languages</h2>
      <table>
        <thead>
          <tr><th></th><th>Listening</th><th>Reading</th><th>Speaking</th><th>Writing</th></tr>
        </thead>
        <tbody>
          <tr><td>English</td><td>C2</td><td>C2</td><td>C2</td><td>C2</td></tr>
          <tr><td>Spanish</td><td>B1</td><td>B1</td><td>B1</td><td>A2</td></tr>
        </tbody>
      </table>

    </div>
  </div>
</div>
{{% endblock %}}
"""

    def _render_typst(self, name, location, email, website, github, linkedin, skills, work, edu, ctfs, aoc) -> str:
        skills_str = ", ".join(skills)

        def md_to_typst(text: str) -> str:
            # Replace **bold** with *bold*
            t = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
            # Escape @ to avoid being treated as a label
            t = t.replace("@", r"\@")
            # Replace markdown links [text](url) with #link("url")[text]
            t = re.sub(r"\[(.+?)\]\((.+?)\)", r'#link("\2")[\1]', t)
            return t

        work_blocks = []
        for w in work:
            bullets = [f"  - {md_to_typst(b)}" for b in w["bullets"] if b.strip()]
            bullets_str = "\n".join(bullets)
            work_blocks.append(f"""=== {w["role"]} — {w["company"]}
#text(size: 8.5pt, fill: rgb("#555555"))[{w["period"]} | {w["location"]}]

{bullets_str}""")
        work_typ = "\n\n".join(work_blocks)

        edu_blocks = []
        for e in edu:
            bullets = [f"  - {md_to_typst(b)}" for b in e["bullets"] if b.strip()]
            bullets_str = "\n".join(bullets) if bullets else ""
            edu_blocks.append(f"""=== {e["degree"]} — {e["institution"]}
#text(size: 8.5pt, fill: rgb("#555555"))[{e["period"]} | {e["location"]}]
{bullets_str}""")
        edu_typ = "\n\n".join(edu_blocks)

        clean_email = email.replace("@", r"\@")

        return f"""#set document(title: "{name} - CV", author: "{name}")
#set page(
  paper: "a4",
  margin: (x: 1.6cm, y: 1.6cm),
)
#set text(
  font: "DejaVu Sans",
  size: 9.5pt,
  fill: rgb("#222222"),
)

#show heading.where(level: 1): it => text(size: 15pt, weight: "bold", it.body)
#show heading.where(level: 2): it => [
  #v(0.3cm)
  #text(size: 11pt, weight: "bold", it.body)
  #line(length: 100%, stroke: 0.5pt + rgb("#cccccc"))
  #v(0.1cm)
]
#show heading.where(level: 3): it => text(size: 9.5pt, weight: "bold", it.body)

= {name}
#text(size: 8.5pt, fill: rgb("#555555"))[
  Portuguese | {location} \\
  Email: {clean_email} | Web: #link("{website}")[marco-silva.com] \\
  GitHub: #link("{github}")[github] | LinkedIn: #link("{linkedin}")[linkedin]
]

== Work Experience
{work_typ}

== Education
{edu_typ}

== Core Technical Skills
#text(size: 9pt)[{skills_str}]

== Competitive Achievements & CTFs
- *HTB Business CTF 2025*: Global rank \\#19 | *HTB Business CTF 2024*: \\#14 | *HTB Business CTF 2023*: \\#12
- *Cyber Apocalypse CTF*: 2025 (\\#86) | 2024 (\\#38) | 2023 (\\#15)
- *Synopsys CSAM 2022*: \\#2
- *Advent of Code*: 2024 (50 stars) | 2023 (42 stars) | 2022 (40 stars)

== Languages
- *Portuguese*: Native
- *English*: C2 Proficient
- *Spanish*: B1 Intermediate
"""
