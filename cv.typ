#set document(title: "Marco Silva - CV", author: "Marco Silva")
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

= Marco Silva
#text(size: 8.5pt, fill: rgb("#555555"))[
  Portuguese | Helsinki, Finland \
  Email: inbox\@marco-silva.com | Web: #link("https://marco-silva.com")[marco-silva.com] \
  GitHub: #link("https://github.com/marco-silva0000")[github] | LinkedIn: #link("https://linkedin.com/in/marco-silva0000/")[linkedin]
]

== Work Experience
=== Senior Cybersecurity Software Developer — Ericsson
#text(size: 8.5pt, fill: rgb("#555555"))[08/2025 – Present | Remote · Helsinki, Finland]

  - *Platform Architecture*: Development on ESM (Ericsson Security Manager), managing complex security posture, compliance, and telemetry for large-scale telecommunications networks.
  - *Microservices on Kubernetes*: Architecting and maintaining Django microservices containerized and orchestrated on Kubernetes (`k8s` / `k3s`).
  - *High-Performance Reporting*: Integrated automated reporting pipeline with *Typst* for high-quality, high-throughput PDF backend document generation.
  - *Framework Uplifts & Modernization*: Leading major framework uplifts, dependency modernization, and structural refactoring across platform services.
  - *Dynamic Configuration*: Implementing and managing Kubernetes `ConfigMaps` and secret injection patterns for runtime service configuration.
  - *Automated Testing*: Designing end-to-end integration and system test suites using *Robot Framework*.
  - *AI Integration*: Architectural planning and feature prototyping for AI-assisted capabilities within the platform.

=== Fullstack Developer — Black Duck
#text(size: 8.5pt, fill: rgb("#555555"))[07/2019 – 08/2025 | Belfast, Northern Ireland, UK]

  - *Internal Vulnerability Platform*: Fullstack engineering of high-throughput internal platform used by security researchers and analysts to discover, triage, and score open-source software vulnerabilities.
  - *Unified Taxonomy System*: Designed and implemented a unified taxonomy system categorizing security vulnerabilities, CWE/CAPEC patterns, and exploit vectors across diverse ecosystems.
  - *SCA Analysis in Rust*: Developed a dedicated Software Composition Analysis (SCA) checker tool written in *Rust* for performance-critical manifest and binary parsing.
  - *Standards Integration*: Embedded industry cybersecurity standards (*OWASP*, *CWE*, *CAPEC*, *CVSS*) into daily tooling and automated workflows.
  - *Testing Leadership*: Introduced and built an extensive automated test suite from scratch using *pytest* and factory patterns, elevating code quality and reliability.
  - *Team Mentoring*: Mentored team members on Python architecture, clean code practices, asynchronous programming, and REST API design.

=== Fullstack Developer & SCRUM Master — Hubel Positive Lightning
#text(size: 8.5pt, fill: rgb("#555555"))[10/2015 – 07/2019 | Faro, Algarve, Portugal]

  - *Leadership & Agile*: Served as technical project lead and certified/practicing Agile SCRUM Master across cross-functional engineering teams.
  - *Real-Time IoT Backend*: Engineered robust Python/Django backends utilizing *Celery* for distributed asynchronous workloads and *Django Channels* (WebSockets) for real-time telemetry streaming from industrial machinery.
  - *Industrial Systems*: Deployed mission-critical monitoring and control platforms for industrial factories, commercial automated farms, and municipal water treatment facilities.
  - *LoRa & Hardware Integration*: Managed long-range, low-power *LoRa* wireless networks and integrated remote telemetry sensors and PLCs.
  - *Fullstack Web Apps*: Built interactive frontends in *Angular* and *React*, backed by structured REST APIs using *Django REST Framework (DRF)*.
  - *Infrastructure & DevOps*: Managed on-premise and cloud Linux server deployments, introducing containerization with *Docker* and *Docker Compose*.
  - *Mentorship*: Guided university interns and junior engineers through practical software engineering, code reviews, and Git collaboration.

== Education
=== Postgraduate Diploma in Cybersecurity — University of the Algarve (Universidade do Algarve)
#text(size: 8.5pt, fill: rgb("#555555"))[09/2024 – 06/2025 | Faro, Portugal]
  - Cryptographic algorithms, public key infrastructure (PKI), TLS/SSL protocols.
  - Secure software development lifecycle (SSDLC), threat modeling, and defense-in-depth principles.
  - Penetration testing methodology, network security assessments, vulnerability scanning.
  - Incident detection, SIEM log analysis, containment, malware triage, and digital forensics.
  - Security standards and frameworks (ISO 27001, NIST CSF, NIS2, GDPR).
  - Risk management matrices, compliance auditing, business continuity planning.

=== Master in Electronics and Telecommunications Engineering (Coursework completed) — University of the Algarve (Universidade do Algarve)
#text(size: 8.5pt, fill: rgb("#555555"))[09/2009 – 09/2015 | Faro, Portugal]
  - *Computer Science & Software*: Algorithms, data structures, object-oriented programming, operating systems, embedded systems C/C++.
  - *Signals & Control Systems*: Discrete-time signal processing (DSP), linear dynamical systems, digital filtering, control theory.
  - *Telecommunications & Networks*: RF and antenna design, modulation schemes, TCP/IP networking, wireless transmission systems, cellular network architectures.
  - *Machine Learning & AI*: Neural networks, pattern recognition, regression models, supervised/unsupervised learning.

== Core Technical Skills
#text(size: 9pt)[Django, DRF, Celery, Python, Angular, React, JavaScript, Rust, Kubernetes, Helm, Docker, Robot Framework, Neovim, Git]

== Competitive Achievements & CTFs
- *HTB Business CTF 2025*: Global rank \#19 | *HTB Business CTF 2024*: \#14 | *HTB Business CTF 2023*: \#12
- *Cyber Apocalypse CTF*: 2025 (\#86) | 2024 (\#38) | 2023 (\#15)
- *Synopsys CSAM 2022*: \#2
- *Advent of Code*: 2024 (50 stars) | 2023 (42 stars) | 2022 (40 stars)

== Languages
- *Portuguese*: Native
- *English*: C2 Proficient
- *Spanish*: B1 Intermediate
