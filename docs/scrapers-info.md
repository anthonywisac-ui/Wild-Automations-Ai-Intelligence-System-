# 🌐 Comprehensive Scrapers & APIs Registry

## Table of Contents
1. [General Web Scraping Frameworks](#1-general-web-scraping-frameworks)
2. [Job Board Scrapers](#2-job-board-scrapers)
3. [Visa & Immigration Scrapers](#3-visa--immigration-scrapers)
4. [Car Auction Scrapers](#4-car-auction-scrapers)
5. [Higher Education APIs & Scrapers](#5-higher-education-apis--scrapers)
6. [Architecture Strategy](#6-architecture-strategy)


1. Firecrawl
GitHub Link: https://github.com/firecrawl/firecrawl

Core Positioning: A web data API designed specifically for AI applications, turning entire websites into LLM-ready Markdown or structured data.

Key Features: Provides core functions like search, scraping, crawling, and interaction. It boasts industry-leading reliability, covering over 96% of web pages (including JavaScript-heavy ones). It offers diverse output formats such as clean Markdown, structured JSON, and screenshots, while handling complex issues like proxies and rate limiting.

2. Crawl4AI
GitHub Link: https://github.com/unclecode/crawl4ai

Core Positioning: An open-source, LLM-friendly web crawler and scraper.

Key Features: Built for RAG (Retrieval-Augmented Generation), AI agents, and data pipelines, it converts web pages into clean Markdown. It is extremely popular in the open-source community. It provides both a Python package and Docker installation options.

3. Browser Use
GitHub Link: https://github.com/browser-use/browser-use

Core Positioning: Enables AI agents to easily access and automate interactions with websites.

Key Features: Uses LLMs to analyze on-screen content and execute browser actions (clicking, typing, searching, etc.) based on natural language instructions. It makes websites "accessible" to AI agents, allowing them to automate online tasks just like a human would.

4. Crawlee
GitHub Link: https://github.com/suryatmodulus/crawlee

Core Positioning: A Node.js web crawling and browser automation library for building reliable scrapers.

Key Features: Provides end-to-end crawling and scraping solutions. Its default configuration makes crawlers behave like real humans to evade modern bot protections. It is a TypeScript rewrite of the Apify SDK and also offers a Python version.

5. Scrapy
GitHub Link: https://github.com/scrapy/scrapy

Core Positioning: A fast, high-level web crawling and scraping framework written in Python.

Key Features: A long-established and widely adopted framework used to extract structured data from websites. It is released under the BSD license and is maintained by Zyte (formerly Scrapinghub).

6. MarkItDown
GitHub Link: https://github.com/microsoft/markitdown

Core Positioning: A Python tool by Microsoft for converting various file types into Markdown format.

Key Features: A lightweight utility focused on preserving essential document structure and content (such as headings, lists, and tables) for LLMs and text-analysis pipelines.

7. Scrapling
GitHub Link: https://github.com/AbdulNasir-NuZ/Scrapling

Core Positioning: An adaptive web scraping framework that handles everything from single requests to large-scale crawling.

Key Features: Its parser learns website structures and automatically re-locates elements when pages update. Its scraper works out-of-the-box to bypass anti-bot systems like Cloudflare Turnstile.

8. Scrcpy
GitHub Link: https://github.com/Genymobile/scrcpy

Core Positioning: Displays and controls Android devices connected via USB or TCP/IP.

Key Features: This application mirrors your Android device's video and audio to your computer and allows you to control it using your keyboard and mouse. It requires no root access and does not need any app to be installed on the device.

Summary List
Tool Name	GitHub Link	Core Positioning
Firecrawl	github.com/firecrawl/firecrawl	Web data API designed for AI applications
Crawl4AI	github.com/unclecode/crawl4ai	Open-source, LLM-friendly web crawler
Browser Use	github.com/browser-use/browser-use	Enables AI agents to automate website interactions
Crawlee	github.com/suryatmodulus/crawlee	Node.js library for web crawling and automation
Scrapy	github.com/scrapy/scrapy	High-level Python web scraping framework
MarkItDown	github.com/microsoft/markitdown	Microsoft's file-to-Markdown conversion tool
Scrapling	github.com/AbdulNasir-NuZ/Scrapling	Adaptive web scraping framework
Scrcpy	github.com/Genymobile/scrcpy	Android device display and control tool

 Job Board Scrapers
Repository	Link	What It Scrapes	Language	Stars	Last Update
JobSpy	speedyapply/JobSpy	LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter, Bayt, Naukri, BDJobs	Python	Not shown	Active
GulfTalent Job Scraper	varinrdudas1eat/gulftalent-job-scraper	GulfTalent job listings (GCC region)	Python (Apify)	Not shown	Not shown
Dubizzle API	aksiksi/dubizzle	Dubizzle UAE classifieds (motors/cars)	Python	Not shown	⚠️ Broken (2016)
Notes:

JobSpy is the most comprehensive multi-site job scraper — actively maintained with proxy support.

GulfTalent is built on Apify and extracts structured job data (title, company, location, description) for GCC hiring analysis.

Dubizzle is no longer maintained and broken due to site changes.

🛂 Visa & Immigration Scrapers
🇺🇸 United States
Repository	Link	What It Scrapes	Language	Stars	Last Update
visa_dates	DavidBellamy/visa_dates	US employment-based visa bulletin data → clean CSVs by country	Python	9	Sep 2023
visa-bulletin	btran12/visa-bulletin	Full-stack dashboard + scraper for US State Department Visa Bulletin	Python	Not shown	Active (2026)
VisaBulletinReader	aravindk777/VisaBulletinReader	Web scraper + Flask app for USCIS visa bulletin dates	Python	2	Active
🇨🇦 Canada
Repository	Link	What It Scrapes	Language	Stars	Last Update
processing-times	kellywaldro/processing-times	Canadian PR processing times from IRCC (Playwright + BeautifulSoup)	Python	1	May 2023
🇬🇧 United Kingdom
Repository	Link	What It Scrapes	Language	Stars	Last Update
only-sponsored-scraper	adityak74/only-sponsored-scraper	UK computer-related jobs eligible for Skilled Worker visa sponsorship	JavaScript	2	Dec 2021
news-scraper	codephilics/news-scraper	BBC News articles (all categories)	Python	3	Not shown
BBCNews-scraper-nlp	ElfatihZiad/BBCNews-scraper-nlp	BBC News → MongoDB → NLP (topic modeling, sentiment analysis) with Airflow	Python	Not shown	Active
🇪🇺 Europe
Repository	Link	What It Scrapes	Language	Stars	Last Update
eu-visa-policy	mogenshobolth/eu-visa-policy	EU Schengen short-stay visa statistics (2005–2022) from official EU sources	Python	1	Dec 2021
🌍 Global Visa Data
Repository	Link	What It Scrapes	Language	Stars	Last Update
visa-req-wiki-scraper	vinaygopinath/visa-req-wiki-scraper	Wikipedia visa requirements for all countries (JSON output by visa type)	TypeScript	16	Active
Passport-Index-Dataset	alsonpr/Passport-Index-Dataset	Passport Index data — visa-free, visa-on-arrival, ETA scores (monthly updated)	Python	8	Active
visa-map	ChengCPU/visa-map	Visa policy map using visaPolicy.json dataset (React/Next.js)	JavaScript	15	Active
🇦🇺 Australia
Repository	Link	What It Scrapes	Language	Stars	Last Update
us-visa-crawler-aus	kenziyuliu/us-visa-crawler-aus	US visa appointment times in Australia (E-3 and F-1 only)	Python	3	Jul 2020
⚠️ Note: No strong Australia-specific immigration policy scraper found in this search.

🚗 Car Auction Scrapers
Repository	Link	What It Scrapes	Language	Stars	Last Update
salvagescraper	bwdq/salvagescraper	Copart salvage auction data → Dockerized MySQL (~100k lots)	Python	0	Feb 2023
copart-dataset	rebrowser/copart-dataset	Copart listings with damage types, title status, mileage, repair costs (daily updates)	Dataset	Not shown	Active (2025–2026)
CarData	azmikamis/CarData	Used car sites: Manheim, OVE, AutoTrader, CarGurus	C#	4	⚠️ May 2013 (very old)
IAA_info_parser	briskspirit/IAA_info_parser	IAA auction HTML parser + photo downloader	—	—	❌ Failed to fetch
scrape-a-trailer	jgrochulski/scrape-a-trailer	Bring a Trailer auction listings API	Node.js	—	❌ Failed to fetch
Regional auction coverage gaps:

Japan: No strong public GitHub repo found for USS, Aucnet, or other major Japanese auction networks.

GCC: No auction-specific scraper found — car data is typically handled via classifieds/dealer platforms.

Europe/Canada: No single region-wide auction scraper — best approach is per-site scrapers for local auction houses.

✅ Best Copy-Paste Shortlist (Top Picks)
text
https://github.com/speedyapply/JobSpy
https://github.com/DavidBellamy/visa_dates
https://github.com/btran12/visa-bulletin
https://github.com/kellywaldro/processing-times
https://github.com/adityak74/only-sponsored-scraper
https://github.com/mogenshobolth/eu-visa-policy
https://github.com/vinaygopinath/visa-req-wiki-scraper
https://github.com/varinrdudas1eat/gulftalent-job-scraper
https://github.com/rebrowser/copart-dataset
📋 Summary by Region
Region	Best Repo	What It Does
US (Visa)	DavidBellamy/visa_dates	Employment visa bulletin data → CSVs
US (Visa Dashboard)	btran12/visa-bulletin	Full web dashboard + scraper
Canada	kellywaldro/processing-times	IRCC PR processing times
UK (Jobs)	adityak74/only-sponsored-scraper	Skilled Worker visa-sponsored jobs
UK (News)	ElfatihZiad/BBCNews-scraper-nlp	BBC News → NLP pipeline
Europe	mogenshobolth/eu-visa-policy	EU Schengen visa statistics
GCC (Jobs)	varinrdudas1eat/gulftalent-job-scraper	GulfTalent job listings
Global Visa	vinaygopinath/visa-req-wiki-scraper	Wikipedia visa requirements
US Copart	rebrowser/copart-dataset	Salvage auction dataset (daily)

Category 1: Official APIs & Direct Lookups (Easiest to Implement)
These are ready-made APIs that return structured JSON—no scraping logic required, just integration.

Tool	Link	Type	Key Data	Notes
College Scorecard API	collegescorecard.ed.gov/data/api/	Official U.S. Government API (JSON)	Admission rates, 25th/75th SAT/ACT, cost parameters, financial profiles	Requires free API key; definitive source for U.S. institutions
International University API	github.com/ibrahimpelumi6142/international-university-api	Open-source MIT-licensed schema	Entry requisites, global grade certificates, tuition structures for USA/UK/Canada/Australia	Programmatic normalization across major study destinations
HIPO Labs University Domains API	universities.hipolabs.com/search	Completely open, no API key	University names, alpha codes, top-level domain websites (global)	High-availability; perfect for auto-complete dashboards and domain validation
🏆 Category 2: Ranking & Aggregator Scrapers (THE, QS, US News)
These repos extract structured ranking data from the world's top university ranking platforms.

Repository	Link	Language / Tech	What It Scrapes	Notes
university_ranking_scraper	lowweihong/university_ranking_scraper (also referenced as lowieihong in some docs)	Python (Requests, Pandas)	US News, THE, QS rankings → country, global rank, subject clusters	Clean Pandas DataFrames; great as a seed list generator for institutional domains
THE-World-University-Rankings	c3nk/THE-World-University-Rankings	Python (Direct API endpoint JSON)	Times Higher Education backend JSON → score breakdowns, historical records	Bypasses Selenium/browser overhead; outputs CSV + JSON
qs-ranking-by-subject-crawler	poppoping/qs-ranking-by-subject-crawler	Python (Scrapy)	QS rankings by subject (Engineering, Arts, Medicine) → regional allocations, academic reputation, citation matrices	Handles front-end virtualization without heavy browser automation
qs-world-university-rankings-scraper	s-dilip/qs-world-university-rankings-scraper	Python (BeautifulSoup, JSON API)	TopUniversities platform → global lists, metrics, regional ranks	Bypasses pagination by hitting underlying payloads directly
🏛️ Category 3: Admissions & Institutional Profile Scrapers
These target individual university pages to extract GPA thresholds, test requirements, acceptance rates, and capacity metrics.

Repository	Link	Language / Tech	What It Scrapes	Notes
collegedatascraper	vertuli/collegedatascraper	Python (BeautifulSoup)	GPA thresholds, test requirements, loan acceptance, application fees, intake percentages	Specialized for deep admission pages → Pandas DataFrames
College-Data-Scraper	tejack3098/College-Data-Scraper	Python/Flask (BeautifulSoup4)	Student capacity, programmatic distributions, raw baseline acceptance profiles	Handles unstructured data across domestic and international domains
Web-Scrapper-for-University-Websites	Rayed14/Web-Scrapper-for-University-Websites	Python (Scrapy/Crawler Spiders)	Recursive crawling of root institutional URLs; regex/XPath matching for admission keywords	Production-ready spider boilerplate for multi-threaded deep crawling
📚 Category 4: Course Catalogs & Prerequisite Extractors
For scraping detailed course offerings, prerequisites, and departmental structures.

Repository	Link	Language / Tech	What It Scrapes	Notes
Bilkent-Syllabus-Scraper	TunaCuma/Bilkent-Syllabus-Scraper	Python (Requests, Concurrent Processing)	Entire course offering systems, class prerequisite dependencies, department mappings	Elite reference blueprint for deeply nested institutional portals
📋 Summary Table (Best Copy-Paste Links)
text
https://collegescorecard.ed.gov/data/api/
https://github.com/ibrahimpelumi6142/international-university-api
http://universities.hipolabs.com/search
https://github.com/lowweihong/university_ranking_scraper
https://github.com/c3nk/THE-World-University-Rankings
https://github.com/poppoping/qs-ranking-by-subject-crawler
https://github.com/s-dilip/qs-world-university-rankings-scraper
https://github.com/vertuli/collegedatascraper
https://github.com/tejack3098/College-Data-Scraper
https://github.com/Rayed14/Web-Scrapper-for-University-Websites
https://github.com/TunaCuma/Bilkent-Syllabus-Scraper
🧠 Architecture Strategy (Synthesized from Your PDFs)
The documents provide a clear, modern blueprint for building a scalable global university data engine. Here's the recommended pipeline:

1. Caching Strategy (Avoid Rate Limits)
"Never hit third-party API networks directly inside an active user session."

Set up a scheduled script (cron job) to download data batches weekly.

Store locally in MongoDB or PostgreSQL.

Your backend then queries your local cache in milliseconds.

2. The Modern Scraping Pipeline (LLM + Scrapy)
"Traditional CSS/XPath selectors break at scale because university DOM structures shift continuously."

Step	Action	Tool/Repo
1. Seed List	Generate a master list of university domains and names	university_ranking_scraper (THE/QS/US News)
2. Raw Extraction	Crawl institutional pages to extract raw HTML strings	Simple Python spiders (e.g., Rayed14/... or requests)
3. Structured Parsing	Feed raw text into a locally hosted LLM to extract deadlines, GPA, test metrics, and prerequisites into dynamic JSON schemas	Local LLM (e.g., Llama, Mistral) or a structured parser
4. Storage	Store cleaned JSON into your cached database	PostgreSQL / MongoDB
Why this works:
The ranking scrapers give you a continually updated list of target schools.

The raw spiders are resilient to minor DOM changes (they fetch full pages).

The LLM handles the interpretation of unstructured human-readable text (e.g., "We require a minimum 3.0 GPA" → {"gpa_min": 3.0}) without needing brittle XPath selectors for every single university.

🎯 Final Verdict: Best Picks by Use Case
Use Case	Best Tool
Quick U.S. university data (official)	College Scorecard API
Global domain/name lookup	HIPO Labs API
Generating a master university list	lowweihong/university_ranking_scraper
Deep admissions metrics (GPA, tests, fees)	vertuli/collegedatascraper
Course prerequisites & catalogs	TunaCuma/Bilkent-Syllabus-Scraper (blueprint)
Production-scale global crawling	Rayed14/Web-Scrapper-for-University-Websites + LLM parser