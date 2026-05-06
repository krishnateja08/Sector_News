#!/usr/bin/env python3
"""
Sectoral News Dashboard — Bloomberg Terminal Style
====================================================
Fetches REAL latest news via RSS feeds (no API key needed).
Generates a Bloomberg Terminal-themed HTML dashboard with:
  • 10 sector tabs + sidebar navigation
  • Expandable news items (click to expand)
  • Live multi-timezone clock bar
  • Ticker strip with live market prices
  • Economic indicators sidebar (USA + India)
  • Light/Dark theme toggle
  • Search/filter headlines
  • Event calendar panel

Run:
    pip install requests
    python sectoral_news_dashboard.py

Output: sectoral_news_dashboard.html  (open in any browser)
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import html as html_module
import re
import logging
import sys

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
MAX_NEWS_PER_SECTOR = 10
REQUEST_TIMEOUT     = 8
OUTPUT_FILE         = "sectoral_news_dashboard.html"

# ─────────────────────────────────────────────
#  SECTORS  — label, icon, accent color, RSS feeds
# ─────────────────────────────────────────────
SECTORS = [
    {
        "id":       "ai",
        "label":    "AI",
        "icon":     "🤖",
        "color":    "#00e5ff",
        "max_items": 20,
        "hours":     10,
        "feeds": [
            # Google News — broad AI (10h) — most reliable for freshness
            "https://news.google.com/rss/search?q=artificial+intelligence+OpenAI+ChatGPT+Gemini+when:10h&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=generative+AI+LLM+machine+learning+when:10h&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=Claude+Anthropic+GPT+Mistral+Llama+when:10h&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=NVIDIA+AI+chip+GPU+AI+startup+funding+when:10h&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=AI+regulation+policy+deepfake+robotics+when:10h&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=AI+model+benchmark+AGI+research+paper+when:10h&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=Grok+xAI+Meta+AI+Google+DeepMind+when:10h&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=AI+image+video+voice+agent+automation+when:10h&hl=en-US&gl=US&ceid=US:en",
            # VentureBeat AI
            "https://venturebeat.com/category/ai/feed/",
            # The Verge AI
            "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            # TechCrunch AI
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            # MIT Technology Review
            "https://www.technologyreview.com/feed/",
            # Wired AI
            "https://www.wired.com/feed/tag/ai/latest/rss",
            # Economic Times — AI India
            "https://economictimes.indiatimes.com/industry/tech/artificial-intelligence/rssfeeds/102930016.cms",
        ],
    },
    {
        "id":    "bank",
        "label": "Bank",
        "icon":  "🏦",
        "color": "#38bdf8",
        "feeds": [
            # Economic Times — Banking (confirmed working)
            "https://economictimes.indiatimes.com/industry/banking/finance/rssfeeds/13358259.cms",
            # Mint — Industry (confirmed working)
            "https://www.livemint.com/rss/industry",
            # Mint — Companies (covers bank stocks)
            "https://www.livemint.com/rss/companies",
            # Google News — Banking India (confirmed working)
            "https://news.google.com/rss/search?q=India+banking+RBI+HDFC+ICICI+SBI+Axis+Kotak+NPA+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=Nifty+Bank+PSU+bank+interest+rate+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "it",
        "label": "IT",
        "icon":  "💻",
        "color": "#4f9cf9",
        "feeds": [
            # Economic Times — Tech (confirmed working)
            "https://economictimes.indiatimes.com/industry/tech/rssfeeds/13357270.cms",
            # Mint — Technology (confirmed working)
            "https://www.livemint.com/rss/technology",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — IT India
            "https://news.google.com/rss/search?q=India+IT+TCS+Infosys+Wipro+HCL+Tech+Mahindra+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=India+software+exports+IT+hiring+LTIMindtree+Mphasis+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "auto",
        "label": "Auto",
        "icon":  "🚗",
        "color": "#a78bfa",
        "feeds": [
            # Economic Times — Auto (confirmed working)
            "https://economictimes.indiatimes.com/industry/auto/rssfeeds/13358302.cms",
            # Mint — Auto (confirmed working)
            "https://www.livemint.com/rss/auto",
            # Mint — Industry
            "https://www.livemint.com/rss/industry",
            # Google News — Auto India
            "https://news.google.com/rss/search?q=India+auto+Maruti+Tata+Motors+Mahindra+EV+Hero+Bajaj+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=India+automobile+sales+SIAM+electric+vehicle+TVS+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "pharma",
        "label": "Pharma",
        "icon":  "💊",
        "color": "#f87171",
        "feeds": [
            # Economic Times — Pharma (confirmed working)
            "https://economictimes.indiatimes.com/industry/healthcare/biotech/pharmaceuticals/rssfeeds/13358270.cms",
            # Mint — Science/Pharma (confirmed working)
            "https://www.livemint.com/rss/science",
            # Mint — Companies (covers pharma stocks)
            "https://www.livemint.com/rss/companies",
            # Google News — Pharma India
            "https://news.google.com/rss/search?q=India+pharma+Sun+Pharma+Cipla+Dr+Reddy+USFDA+approval+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=Lupin+Aurobindo+Divi+Labs+Biocon+India+pharma+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "metals",
        "label": "Metals",
        "icon":  "⚙️",
        "color": "#94a3b8",
        "feeds": [
            # Economic Times — Metals & Mining (confirmed working)
            "https://economictimes.indiatimes.com/industry/indl-goods/svs/metals-mining/rssfeeds/13358395.cms",
            # Mint — Industry (confirmed working, covers metals)
            "https://www.livemint.com/rss/industry",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — Metals India
            "https://news.google.com/rss/search?q=India+metals+Tata+Steel+JSW+Steel+Hindalco+Vedanta+SAIL+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=steel+prices+iron+ore+aluminium+copper+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "fmcg",
        "label": "FMCG",
        "icon":  "🛒",
        "color": "#fb923c",
        "feeds": [
            # Economic Times — FMCG (confirmed working)
            "https://economictimes.indiatimes.com/industry/cons-products/fmcg/rssfeeds/13358137.cms",
            # Mint — Consumer (confirmed working)
            "https://www.livemint.com/rss/consumer",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — FMCG India
            "https://news.google.com/rss/search?q=India+FMCG+HUL+ITC+Nestle+Dabur+Marico+Britannia+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=India+FMCG+rural+consumption+volume+growth+Godrej+Consumer+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "oil_gas",
        "label": "Oil & Gas",
        "icon":  "🛢️",
        "color": "#fbbf24",
        "feeds": [
            # Economic Times — Oil & Gas (confirmed working)
            "https://economictimes.indiatimes.com/industry/energy/oil-gas/rssfeeds/13358485.cms",
            # Mint — Industry (confirmed working, covers O&G)
            "https://www.livemint.com/rss/industry",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — Oil & Gas India
            "https://news.google.com/rss/search?q=India+oil+gas+ONGC+Reliance+BPCL+HPCL+IOC+crude+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=India+GAIL+Petronet+LNG+natural+gas+petrol+diesel+price+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "power",
        "label": "Power",
        "icon":  "⚡",
        "color": "#facc15",
        "feeds": [
            # Economic Times — Power (confirmed working)
            "https://economictimes.indiatimes.com/industry/energy/power/rssfeeds/13358476.cms",
            # Mint — Industry (confirmed working, covers power)
            "https://www.livemint.com/rss/industry",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — Power India
            "https://news.google.com/rss/search?q=India+power+NTPC+Adani+Power+Tata+Power+renewable+solar+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=India+electricity+wind+energy+PGCIL+discoms+tariff+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "infra",
        "label": "Infra",
        "icon":  "🏗️",
        "color": "#34d399",
        "feeds": [
            # Economic Times — Infrastructure (confirmed working)
            "https://economictimes.indiatimes.com/industry/indl-goods/svs/construction/rssfeeds/13358381.cms",
            # Mint — Industry (confirmed working, covers infra)
            "https://www.livemint.com/rss/industry",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — Infra India
            "https://news.google.com/rss/search?q=India+infrastructure+L%26T+NHAI+roads+railways+airports+capex+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=India+metro+rail+highways+ports+Adani+GMR+IRB+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "cement",
        "label": "Cement",
        "icon":  "🏛️",
        "color": "#d4a96a",
        "feeds": [
            # Economic Times — Cement (confirmed working)
            "https://economictimes.indiatimes.com/industry/indl-goods/svs/cement/rssfeeds/13358376.cms",
            # Mint — Industry (confirmed working, covers cement)
            "https://www.livemint.com/rss/industry",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — Cement India
            "https://news.google.com/rss/search?q=India+cement+UltraTech+ACC+Ambuja+Shree+Cement+Dalmia+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=cement+prices+demand+capacity+utilisation+India+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "paint",
        "label": "Paint",
        "icon":  "🎨",
        "color": "#f472b6",
        "feeds": [
            # Economic Times — Consumer Products (covers paints)
            "https://economictimes.indiatimes.com/industry/cons-products/rssfeeds/13357842.cms",
            # Mint — Consumer (confirmed working)
            "https://www.livemint.com/rss/consumer",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — Paint India
            "https://news.google.com/rss/search?q=India+paint+Asian+Paints+Berger+Kansai+Nerolac+Indigo+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=paint+coatings+raw+material+India+decorative+industrial+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "cons",
        "label": "Cons",
        "icon":  "🏠",
        "color": "#86efac",
        "feeds": [
            # Economic Times — Real Estate (confirmed working)
            "https://economictimes.indiatimes.com/industry/services/property-/-cstruction/rssfeeds/13358155.cms",
            # Mint — Consumer (confirmed working, covers real estate/durables)
            "https://www.livemint.com/rss/consumer",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — Real Estate & Consumer Durables India
            "https://news.google.com/rss/search?q=India+real+estate+DLF+Godrej+Properties+Oberoi+Prestige+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=India+consumer+durables+Havells+Voltas+Dixon+Blue+Star+Crompton+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "telecom",
        "label": "Telecom",
        "icon":  "📡",
        "color": "#c084fc",
        "feeds": [
            # Economic Times — Telecom (confirmed working)
            "https://economictimes.indiatimes.com/industry/telecom/rssfeeds/13358267.cms",
            # Mint — Technology (confirmed working, covers telecom)
            "https://www.livemint.com/rss/technology",
            # Mint — Companies
            "https://www.livemint.com/rss/companies",
            # Google News — Telecom India
            "https://news.google.com/rss/search?q=India+telecom+Jio+Airtel+Vi+Vodafone+Idea+5G+TRAI+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=India+telecom+spectrum+ARPU+tariff+hike+tower+Indus+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id":    "other",
        "label": "Other",
        "icon":  "📊",
        "color": "#888888",
        "feeds": [
            # Economic Times — Markets (confirmed working)
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            # Mint — Markets (confirmed working)
            "https://www.livemint.com/rss/markets",
            # Mint — Economy
            "https://www.livemint.com/rss/economy",
            # Google News — Indian Markets
            "https://news.google.com/rss/search?q=India+Nifty+Sensex+BSE+NSE+stock+market+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
            "https://news.google.com/rss/search?q=India+economy+GDP+RBI+Budget+inflation+when:1d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
]

# ─────────────────────────────────────────────
#  SECTOR KEYWORD FILTERS
#  At least ONE keyword must appear in the title
#  (case-insensitive) for the article to be kept.
#  Google News search feeds are already targeted,
#  so keywords are only enforced for generic feeds
#  (livemint.com/rss/industry, /companies, /consumer).
# ─────────────────────────────────────────────
SECTOR_KEYWORDS = {
    "ai":       ["ai", "artificial intelligence", "openai", "chatgpt", "gemini", "llm",
                 "anthropic", "claude", "gpt", "nvidia", "deepmind", "machine learning",
                 "generative", "mistral", "llama", "robot", "automation", "deep learning"],
    "bank":     ["bank", "rbi", "hdfc", "icici", "sbi", "axis", "kotak", "npa",
                 "lending", "credit", "nbfc", "financial", "loan", "deposit", "interest rate",
                 "psb", "psu bank", "banking", "microfinance", "yes bank", "idfc"],
    "it":       ["tcs", "infosys", "wipro", "hcl", "tech mahindra", "ltimindtree",
                 "mphasis", "coforge", "persistent", "it sector", "software", "it company",
                 "outsourcing", "digital", "saas", "cloud", "it services", "it hiring"],
    "auto":     ["maruti", "tata motors", "mahindra", "hero", "bajaj", "tvs",
                 "hyundai", "honda", "eicher", "auto", "automobile", "vehicle", "ev",
                 "electric vehicle", "car", "bike", "siam", "scooter", "suv", "ola electric"],
    "pharma":   ["pharma", "sun pharma", "cipla", "dr reddy", "lupin", "aurobindo",
                 "divi", "biocon", "usfda", "drug", "medicine", "healthcare", "hospital",
                 "clinical", "api", "formulation", "zydus", "alkem", "torrent pharma"],
    "metals":   ["tata steel", "jsw steel", "hindalco", "vedanta", "sail", "jindal",
                 "steel", "aluminium", "copper", "zinc", "iron ore", "metals", "mining",
                 "nalco", "nmdc", "coal", "smelter", "sterlite"],
    "fmcg":     ["hul", "itc", "nestle", "dabur", "marico", "britannia", "godrej consumer",
                 "colgate", "emami", "fmcg", "consumer goods", "rural demand",
                 "volume growth", "gsk consumer", "tata consumer", "patanjali"],
    "oil_gas":  ["ongc", "reliance", "bpcl", "hpcl", "ioc", "gail", "petronet",
                 "oil", "gas", "crude", "petrol", "diesel", "lng", "refinery",
                 "upstream", "downstream", "petroleum", "natural gas", "fuel"],
    "power":    ["ntpc", "adani power", "tata power", "power grid", "pgcil",
                 "electricity", "power", "solar", "wind energy", "renewable", "discoms",
                 "tariff", "hydro", "cesc", "torrent power", "green energy"],
    "infra":    ["l&t", "nhai", "roads", "railways", "airport", "capex", "metro",
                 "highways", "ports", "adani ports", "gmr", "irb", "infrastructure",
                 "construction", "bridge", "tunnel", "nh", "expressway"],
    "cement":   ["ultratech", "acc", "ambuja", "shree cement", "dalmia", "ramco",
                 "jk cement", "cement", "clinker", "capacity utilisation",
                 "cement prices", "india cement", "nuvoco"],
    "paint":    ["asian paints", "berger", "kansai", "nerolac", "indigo paints",
                 "akzo", "paint", "coatings", "decorative", "titanium dioxide",
                 "linseed", "varnish", "pidilite"],
    "cons":     ["dlf", "godrej properties", "oberoi realty", "prestige", "macrotech",
                 "lodha", "havells", "voltas", "dixon", "blue star", "crompton",
                 "real estate", "realty", "housing", "consumer durables", "property",
                 "appliances", "whirlpool", "lg electronics"],
    "telecom":  ["jio", "airtel", "vodafone idea", "vi", "5g", "trai", "spectrum",
                 "arpu", "tariff hike", "tower", "indus towers", "telecom", "broadband",
                 "fiber", "4g", "mobile", "stc", "bsnl"],
    "other":    [],   # catch-all — no filter
}

# Generic feed domains that need keyword filtering
# (targeted Google News search feeds are exempt)
GENERIC_FEED_DOMAINS = {
    "livemint.com",
    "economictimes.indiatimes.com",  # only if NOT a sector-specific ET feed
}

def _is_generic_feed(url: str) -> bool:
    """Return True if the URL is a broad/generic feed that needs keyword filtering."""
    domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
    if "livemint.com/rss" in url:
        return True
    # ET feeds without sector-specific path segments are generic;
    # sector-specific ET feeds contain a numeric ID like /rssfeeds/13358xxx.cms
    # We only mark ET generic-feed if it's the broad markets feed
    if "economictimes.indiatimes.com/markets/rssfeeds" in url:
        return True
    return False

def _title_matches_sector(title: str, sector_id: str) -> bool:
    """Return True if the article title contains at least one sector keyword."""
    keywords = SECTOR_KEYWORDS.get(sector_id, [])
    if not keywords:
        return True   # catch-all sector keeps everything
    title_lower = title.lower()
    return any(kw in title_lower for kw in keywords)


# ─────────────────────────────────────────────
#  RSS FETCHER
# ─────────────────────────────────────────────
SOURCE_MAP = {
    "cnbc.com":                     "CNBC",
    "cnbctv18.com":                 "CNBC TV18",
    "marketwatch.com":              "MarketWatch",
    "reuters.com":                  "Reuters",
    "finance.yahoo.com":            "Yahoo Finance",
    "economictimes.indiatimes.com": "Economic Times",
    "moneycontrol.com":             "MoneyControl",
    "livemint.com":                 "Mint",
    "business-standard.com":        "Business Standard",
    "businesstoday.in":             "Business Today",
    "financialexpress.com":         "Financial Express",
    "zeebiz.com":                   "Zee Business",
    "ndtvprofit.com":               "NDTV Profit",
    "ndtv.com":                     "NDTV",
    "indiainfoline.com":            "IIFL",
    "housing.com":                  "Housing.com",
    "steelmint.com":                "SteelMint",
    "rbi.org.in":                   "RBI",
    "news.google.com":              "Google News",
    "technologyreview.com":         "MIT Tech Review",
    "venturebeat.com":              "VentureBeat",
    "theverge.com":                 "The Verge",
    "wired.com":                    "Wired",
    "techcrunch.com":               "TechCrunch",
    "ft.com":                       "Financial Times",
    "bbc.co.uk":                    "BBC",
    "investing.com":                "Investing.com",
    "wsj.com":                      "WSJ",
}

DATE_FMTS = [
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
]

def parse_date(raw: str):
    for fmt in DATE_FMTS:
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            if dt.tzinfo is not None:
                dt = datetime(*dt.utctimetuple()[:6])
            return dt
        except ValueError:
            continue
    return None

def format_pub_date(raw: str) -> str:
    if not raw:
        return "Just now"
    dt = parse_date(raw)
    if not dt:
        return raw[:10]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = now - dt
    secs = diff.total_seconds()
    if secs < 0:    return "Just now"
    if secs < 3600: return f"{int(secs//60)} min ago"
    if secs < 86400:return f"{int(secs//3600)}h ago"
    if diff.days == 1: return "1 day ago"
    return dt.strftime("%b %d, %Y")

def fetch_rss(url: str, max_items: int = MAX_NEWS_PER_SECTOR) -> list:
    items = []
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; SectoralNewsDashboard/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        })
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        raw = re.sub(r'\s+xmlns[^"]*"[^"]*"', "", raw)
        raw = re.sub(r"<(/?)[\w]+:", r"<\1", raw)
        root = ET.fromstring(raw)
        _ch = root.find("channel")
        channel = _ch if _ch is not None else root

        domain = urllib.parse.urlparse(url).netloc.replace("www.", "").replace("feeds.", "")
        source = next((v for k, v in SOURCE_MAP.items() if k in domain), domain)

        for item in channel.findall("item")[:max_items]:
            title   = html_module.unescape((item.findtext("title") or "").strip())
            link    = (item.findtext("link") or "").strip()
            summary = re.sub(r"<[^>]+>", "", (item.findtext("description") or item.findtext("summary") or "").strip())
            summary = html_module.unescape(summary)
            pubdate = (item.findtext("pubDate") or item.findtext("date") or "").strip()

            # Strip trailing " - Source" from title
            if " - " in title:
                title = title.rsplit(" - ", 1)[0].strip()

            if title and len(title) > 10:
                items.append({
                    "title":   title,
                    "link":    link,
                    "summary": summary[:500] if summary else "Click to read the full article.",
                    "pubDate": pubdate,
                    "source":  source,
                })
    except Exception as e:
        logging.warning(f"  RSS failed ({url[:60]}): {e}")
    return items


def fetch_sector_news(sector_id: str, feeds: list, max_items: int = MAX_NEWS_PER_SECTOR, hours: int = 48) -> list:
    seen   = set()
    items  = []
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)

    for url in feeds:
        logging.info(f"    {url[:70]}")
        generic = _is_generic_feed(url)
        for item in fetch_rss(url, max_items * 3):   # fetch more per feed to have room to filter
            title = item.get("title", "")
            key   = title.lower()[:60]
            if key in seen:
                continue
            dt = parse_date(item.get("pubDate", ""))
            if dt and dt < cutoff:
                continue
            # ── KEYWORD FILTER: drop off-topic articles from generic feeds ──
            if generic and not _title_matches_sector(title, sector_id):
                logging.debug(f"      [SKIP] {title[:70]}")
                continue
            seen.add(key)
            item["_dt"] = dt  # attach parsed date for sorting
            items.append(item)

    # Sort newest first, then cap
    items.sort(key=lambda x: x.get("_dt") or datetime.min, reverse=True)
    return items[:max_items]


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def escape(text: str) -> str:
    return html_module.escape(str(text), quote=True)

def get_ist_time() -> str:
    utc = datetime.now(timezone.utc).replace(tzinfo=None)
    ist = utc + timedelta(hours=5, minutes=30)
    return ist.strftime("%B %d, %Y at %I:%M %p IST")

def build_news_json(all_news: dict) -> str:
    out = {}
    for s in SECTORS:
        sid   = s["id"]
        items = all_news.get(sid, [])
        out[sid] = {
            "label": s["label"],
            "icon":  s["icon"],
            "color": s["color"],
            "items": [
                {
                    "title":   escape(i.get("title", "Untitled")),
                    "source":  escape(i.get("source", "Unknown")),
                    "time":    format_pub_date(i.get("pubDate", "")),
                    "summary": escape(i.get("summary", "Click to read full article.")),
                    "link":    escape(i.get("link", "#")),
                }
                for i in items
            ],
        }
    return json.dumps(out, ensure_ascii=False)


# ─────────────────────────────────────────────
#  HTML GENERATION
# ─────────────────────────────────────────────
def generate_html(all_news: dict) -> str:
    current_time   = get_ist_time()
    total_articles = sum(len(v) for v in all_news.values())
    news_json      = build_news_json(all_news)
    sectors_json   = json.dumps(
        [{"id": s["id"], "label": s["label"], "icon": s["icon"], "color": s["color"]} for s in SECTORS],
        ensure_ascii=False
    )
    cat_counts_json = json.dumps({s["id"]: len(all_news.get(s["id"], [])) for s in SECTORS})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SectoralFeed – Industry News Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600;700&family=IBM+Plex+Sans:wght@300;400;600&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
/* ══════════════════════════════════════════
   BLOOMBERG TERMINAL THEME
   ══════════════════════════════════════════ */
:root {{
  --bg:         #000000;
  --panel:      #060608;
  --panel2:     #0a0a0e;
  --border:     #1e1e2a;
  --border2:    #111118;
  --accent:     #ff6a00;
  --accent-dim: rgba(255,106,0,0.10);
  --accent-mid: rgba(255,106,0,0.22);
  --green:      #00ff55;
  --green-dim:  rgba(0,255,85,0.08);
  --red:        #ff3355;
  --red-dim:    rgba(255,51,85,0.08);
  --yellow:     #ffd700;
  --blue:       #29b6ff;
  --muted:      #888888;
  --muted2:     #555555;
  --text:       #d0d0d0;
  --white:      #f0f0f0;
}}
*, *::before, *::after {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: #000000;
  color: var(--text);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 14px;
  min-height: 100vh;
  overflow-x: hidden;
}}

/* ── SPACE CANVAS ── */
#spaceCanvas {{
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  z-index: 0;
}}
.topbar, .clockbar, .shell, .statusbar, .scroll-top, .sb-overlay {{
  position: relative;
  z-index: 1;
}}

/* ── TOP BAR ── */
.topbar {{
  background: var(--accent);
  color: #000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 18px;
  font-weight: 700;
  font-size: 13px;
  letter-spacing: 1.5px;
  position: sticky;
  top: 0;
  z-index: 200;
}}
.topbar-left {{ display:flex; align-items:center; gap:12px; }}
.topbar-right {{ display:flex; gap:20px; font-size:12px; font-weight:600; }}
.tb-dot {{ width:7px; height:7px; border-radius:50%; background:#000; animation:blink 1.5s step-end infinite; }}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.15}} }}

/* ── CLOCK BAR ── */
.clockbar {{
  background: rgba(0,0,0,0.85);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 7px 18px;
  position: sticky;
  top: 34px;
  z-index: 190;
  gap: 0;
}}
.tz-block {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 28px;
  border-right: 1px solid var(--border);
}}
.tz-block:last-of-type {{ border-right: none; }}
.tz-tag {{ color: var(--accent); font-weight: 700; font-size: 11px; letter-spacing: 2.5px; }}
.tz-val {{ color: #f0f0f0; font-weight: 600; font-size: 14px; letter-spacing: 1px; }}
.tz-dot {{ color: var(--accent); font-size: 7px; animation: blink 1.5s step-end infinite; }}
.clockbar-date {{ position:absolute; right:18px; color:#c8c8c8; font-size:11px; letter-spacing:0.5px; font-weight:600; }}

/* ── SHELL ── */
.shell {{
  display: grid;
  grid-template-columns: 260px 1fr;
  height: calc(100vh - 62px);
}}

/* ── SIDEBAR ── */
.sidebar {{
  background: var(--panel);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  padding: 14px 0 60px;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}}
.sidebar::-webkit-scrollbar {{ width:3px; }}
.sidebar::-webkit-scrollbar-thumb {{ background: var(--border); border-radius:2px; }}

.sb-label {{
  color: var(--accent);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 3px;
  text-transform: uppercase;
  padding: 4px 12px 5px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2px;
}}
.sb-item {{
  padding: 6px 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-left: 3px solid transparent;
  transition: all 0.12s;
  font-size: 12px;
}}
.sb-item:hover {{ background: var(--accent-dim); border-left-color: rgba(255,106,0,0.4); }}
.sb-item.active {{ background: var(--accent-dim); border-left-color: var(--accent); }}
.sb-name {{ color: var(--white); font-weight: 500; display:flex; align-items:center; gap:6px; }}
.sb-count {{
  color: #aaa;
  font-size: 10px;
  background: var(--border2);
  padding: 1px 6px;
  border-radius: 2px;
  font-weight: 600;
}}
.sb-item.active .sb-count {{ background: var(--accent-mid); color: var(--accent); }}

/* ── SIDEBAR ECONOMIC INDICATORS ── */
.sb-econ-hdr {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 7px 12px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
}}
.sb-econ-hdr:hover {{ background: rgba(255,106,0,0.05); }}
.sb-econ-title {{ font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; display:flex; align-items:center; gap:5px; }}
.sb-econ-title.usa {{ color: #e05060; }}
.sb-econ-title.india {{ color: #ffaa44; }}
.sb-arrow {{ color: var(--accent); font-size: 10px; transition: transform 0.2s; }}
.sb-arrow.closed {{ transform: rotate(-90deg); }}

.sb-econ-body {{ overflow: hidden; transition: max-height 0.25s ease; }}
.sb-econ-body.closed {{ max-height: 0 !important; }}

.sb-econ-row {{
  padding: 6px 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  gap: 1px 8px;
  border-bottom: 1px solid var(--border2);
  align-items: center;
}}
.sb-econ-row:last-child {{ border-bottom: none; padding-bottom: 10px; }}
.sb-econ-key {{ grid-column:1; grid-row:1; color:#b0bec5; font-size:10.5px; font-weight:700; letter-spacing:0.5px; text-transform:uppercase; }}
.sb-econ-val {{ grid-column:2; grid-row:1; font-weight:700; font-size:13px; white-space:nowrap; text-align:right; }}
.sb-econ-val.pos {{ color:#00e868; }}
.sb-econ-val.neg {{ color:#ff4466; }}
.sb-econ-val.neu {{ color:#ccc; }}
.sb-econ-note {{ grid-column:2; grid-row:2; color:#e0c84a; font-size:9.5px; text-align:right; font-style:italic; }}

/* sidebar live prices */
.sb-price-row {{
  padding: 5px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border2);
  font-size: 12px;
}}
.sb-price-row:last-child {{ border-bottom: none; }}
.sb-price-name {{ color: #bbb; }}
.sb-price-val {{ font-weight: 700; }}
.sb-price-val.pos {{ color: var(--green); }}
.sb-price-val.neg {{ color: var(--red); }}
.sb-price-val.neu {{ color: #aaa; }}

/* ── MAIN ── */
.main {{
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}

/* ── CATEGORY TABS ── */
.cat-tabs-wrap {{ position: relative; flex-shrink:0; }}
.cat-tabs-wrap::after {{
  content:''; position:absolute; top:0; right:0; bottom:0; width:50px;
  background: linear-gradient(90deg, transparent, #101010);
  pointer-events:none; z-index:1;
}}
.cat-tabs {{
  display: flex;
  overflow-x: auto;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
  background: rgba(10,10,14,0.95);
  scrollbar-width: none;
  cursor: grab;
}}
.cat-tabs::-webkit-scrollbar {{ display:none; }}
.cat-tab {{
  flex-shrink: 0;
  padding: 10px 16px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  transition: all 0.15s;
}}
.cat-tab:hover {{ color: var(--white); }}
.cat-tab.active {{ color: var(--accent); border-bottom-color: var(--accent); }}

/* ── SEARCH ── */
.news-search {{
  padding: 10px 16px 8px;
  flex-shrink: 0;
  background: var(--bg);
  border-bottom: 1px solid var(--border2);
}}
.search-wrap {{ position: relative; }}
.search-icon {{ position:absolute; left:11px; top:50%; transform:translateY(-50%); color:var(--muted2); font-size:12px; pointer-events:none; }}
.news-search input {{
  width: 100%;
  background: var(--panel);
  border: 1px solid var(--border);
  color: var(--white);
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  padding: 8px 12px 8px 32px;
  border-radius: 3px;
  outline: none;
  transition: border-color 0.15s;
}}
.news-search input::placeholder {{ color: var(--muted2); }}
.news-search input:focus {{ border-color: var(--accent); }}

/* ── NEWS AREA ── */
.news-area {{
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}}
.news-area::-webkit-scrollbar {{ width:3px; }}
.news-area::-webkit-scrollbar-thumb {{ background: var(--border); border-radius:2px; }}

.news-hdr {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 9px;
  border-bottom: 1px solid var(--border);
}}
.news-hdr-title {{
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
}}
.news-hdr-meta {{ color: var(--muted); font-size: 11px; }}

/* ── NEWS COLUMN — EXPANDABLE ROWS ── */
.news-col {{ border: 1px solid var(--border); border-radius: 3px; overflow: hidden; }}

.nc-item {{
  border-bottom: 1px solid var(--border2);
  cursor: pointer;
  transition: background 0.12s;
  user-select: none;
}}
.nc-item:last-child {{ border-bottom: none; }}
.nc-item:hover {{ background: rgba(255,106,0,0.04); }}
.nc-item.open {{ background: rgba(255,106,0,0.06); border-left: 2px solid var(--accent); }}

.nc-row {{
  display: grid;
  grid-template-columns: 34px 1fr 22px;
  align-items: center;
  padding: 10px 12px 10px 0;
  gap: 3px;
}}
.nc-num {{
  font-size: 11px; font-weight: 700;
  color: var(--accent); opacity: 0.5;
  text-align: right; padding-right: 4px;
}}
.nc-headline {{
  font-family: 'DM Sans', sans-serif;
  font-size: 14px; font-weight: 500;
  color: #e0e0e0; line-height: 1.45;
}}
.nc-arrow {{
  color: #444; font-size: 11px;
  text-align: center; transition: transform 0.2s, color 0.15s;
}}
.nc-item:hover .nc-arrow {{ color: var(--accent); }}
.nc-item.open .nc-arrow {{ transform: rotate(180deg); color: var(--accent); }}

.nc-expand {{
  display: none;
  padding: 0 14px 12px 34px;
  border-top: 1px dashed var(--border2);
}}
.nc-expand.open {{ display: block; animation: fadeSlide 0.18s ease; }}
@keyframes fadeSlide {{ from{{opacity:0;transform:translateY(-4px)}} to{{opacity:1;transform:translateY(0)}} }}

.nc-meta {{
  display: flex; align-items: center; gap: 6px;
  padding: 8px 0 6px;
}}
.nc-src {{
  font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
  padding: 2px 7px; border-radius: 2px;
  background: rgba(255,106,0,0.14); color: var(--accent);
  text-transform: uppercase;
}}
.nc-sep {{ color: var(--border); font-size: 12px; }}
.nc-time {{ font-size: 11px; color: var(--muted2); }}
.nc-summary {{
  font-family: 'DM Sans', sans-serif;
  font-size: 13px; color: #999;
  line-height: 1.6; margin-bottom: 8px;
}}
.nc-link {{
  display: inline-block;
  font-family: 'DM Sans', sans-serif;
  color: var(--accent); font-size: 12px; font-weight: 600;
  text-decoration: none;
  border-bottom: 1px solid rgba(255,106,0,0.3);
  padding-bottom: 1px;
  transition: opacity 0.15s;
}}
.nc-link:hover {{ opacity: 0.7; }}

.nc-sector-badge {{
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 2px;
  margin-right: 6px;
  border: 1px solid;
}}

.no-news {{
  color: var(--muted);
  font-size: 13px;
  padding: 20px 14px;
  font-family: 'DM Sans', sans-serif;
}}

/* ── STATUS BAR ── */
.statusbar {{
  background: #111;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 16px;
  font-size: 10px;
  color: var(--muted2);
  letter-spacing: 0.5px;
  position: sticky;
  bottom: 0;
  z-index: 100;
  flex-shrink: 0;
}}

/* ── THEME TOGGLE ── */
.theme-btn {{
  cursor:pointer; font-size:14px; padding:2px 5px;
  border-radius:3px; user-select:none;
  transition: background 0.15s;
}}
.theme-btn:hover {{ background: rgba(0,0,0,0.15); }}

/* ── HAMBURGER ── */
.hamburger {{
  display: none;
  flex-direction: column; gap: 4px;
  width:30px; height:30px; cursor:pointer; padding:4px;
  border-radius:3px; transition: background 0.15s; flex-shrink:0;
}}
.hamburger:hover {{ background: rgba(0,0,0,0.2); }}
.hamburger span {{ display:block; width:18px; height:2px; background:#000; border-radius:2px; }}

/* ── SIDEBAR OVERLAY ── */
.sb-overlay {{
  display:none; position:fixed; inset:0;
  background:rgba(0,0,0,0.7); z-index:150;
}}
.sb-overlay.open {{ display:block; }}

/* ── SCROLL TOP ── */
.scroll-top {{
  position:fixed; bottom:38px; right:16px;
  width:36px; height:36px;
  background:var(--accent); color:#000;
  font-weight:700; font-size:16px;
  border:none; border-radius:50%;
  cursor:pointer; z-index:90;
  display:none; align-items:center; justify-content:center;
  box-shadow: 0 2px 10px rgba(0,0,0,0.5);
  transition: transform 0.2s;
}}
.scroll-top.show {{ display:flex; }}
.scroll-top:hover {{ transform: scale(1.1); }}

/* ── LIGHT MODE ── */
body.light {{
  --bg: #f0f2f5;
  --panel: #ffffff;
  --panel2: #f5f6f8;
  --border: #d0d4db;
  --border2: #e2e5ea;
  --muted: #666;
  --muted2: #999;
  --text: #1a1a1a;
  --white: #111;
}}
body.light .clockbar {{ background:#e8eaf0; border-color: #d0d4db; }}
body.light .ticker {{ background:#e2e5ea; }}
body.light .statusbar {{ background:#e2e5ea; color:#666; }}
body.light .nc-headline {{ color:#111; }}
body.light .nc-summary {{ color:#555; }}
body.light .cat-tabs {{ background:#f0f2f5; }}
body.light .cat-tabs-wrap::after {{ background: linear-gradient(90deg,transparent,#f0f2f5); }}
body.light .tz-val {{ color:#111; }}
body.light .sb-econ-key {{ color:#444; }}

/* ── RESPONSIVE ── */
@media (max-width: 860px) {{
  .shell {{ grid-template-columns:1fr; }}
  .sidebar {{
    position:fixed; top:0; left:-260px; bottom:0;
    width:260px; z-index:200;
    transition:left 0.25s ease;
    padding-top:48px;
  }}
  .sidebar.open {{ left:0; }}
  .hamburger {{ display:flex; }}
  .topbar-right span:nth-child(3) {{ display:none; }}
}}
@media (max-width: 560px) {{
  .topbar {{ padding:5px 10px; font-size:11px; }}
  .topbar-right {{ gap:10px; font-size:10px; }}
  .topbar-right span:nth-child(3), .topbar-right span:nth-child(4) {{ display:none; }}
  .cat-tab {{ padding:8px 10px; font-size:10px; }}
  .nc-headline {{ font-size:13px; }}
  .tz-block {{ padding:0 14px; }}
  .tz-val {{ font-size:12px; }}
}}
</style>
</head>
<body>

<!-- ── SPACE BACKGROUND CANVAS ── -->
<canvas id="spaceCanvas"></canvas>

<!-- ── TOP BAR ── -->
<div class="topbar">
  <div class="topbar-left">
    <div class="hamburger" onclick="toggleSidebar()">
      <span></span><span></span><span></span>
    </div>
    <div class="tb-dot"></div>
    <span>⚡ SECTORALFEED</span>
  </div>
  <div class="topbar-right">
    <span>🔴 LIVE FEED</span>
    <span>📅 {current_time}</span>
    <span>✅ {total_articles} ARTICLES</span>
    <span class="theme-btn" onclick="toggleTheme()" title="Toggle theme">🌓</span>
  </div>
</div>

<!-- ── CLOCK BAR ── -->
<div class="clockbar">
  <div class="tz-block"><span class="tz-tag">CST</span><span class="tz-val" id="ck-cst">--:--:--</span><span class="tz-dot">●</span></div>
  <div class="tz-block"><span class="tz-tag">IST</span><span class="tz-val" id="ck-ist">--:--:--</span><span class="tz-dot">●</span></div>
  <div class="tz-block"><span class="tz-tag">SGT</span><span class="tz-val" id="ck-sgt">--:--:--</span><span class="tz-dot">●</span></div>
  <div class="tz-block"><span class="tz-tag">EST</span><span class="tz-val" id="ck-est">--:--:--</span><span class="tz-dot">●</span></div>
  <div class="clockbar-date" id="ck-date">--</div>
</div>

<!-- ── SIDEBAR OVERLAY ── -->
<div class="sb-overlay" id="sbOverlay" onclick="toggleSidebar()"></div>

<!-- ── SHELL ── -->
<div class="shell">

  <!-- SIDEBAR -->
  <div class="sidebar" id="sidebar">

    <!-- SECTORS -->
    <div style="margin-bottom:14px;">
      <div class="sb-label">▶ SECTORS</div>
      <div id="sbSectorList"><!-- JS --></div>
    </div>

    <!-- INDIA ECON -->
    <div style="margin-bottom:14px;">
      <div class="sb-econ-hdr" onclick="toggleEcon('india')">
        <span class="sb-econ-title india">🇮🇳 INDIA ECONOMIC</span>
        <span class="sb-arrow" id="arr-india">▼</span>
      </div>
      <div class="sb-econ-body" id="body-india">
        <div class="sb-econ-row"><span class="sb-econ-key">Repo Rate</span><span class="sb-econ-val neu" id="sv-reporate">6.25%</span><span class="sb-econ-note">RBI</span></div>
        <div class="sb-econ-row"><span class="sb-econ-key">CPI</span><span class="sb-econ-val neu" id="sv-incpi">--</span><span class="sb-econ-note" id="sn-incpi">loading…</span></div>
        <div class="sb-econ-row"><span class="sb-econ-key">GDP Growth</span><span class="sb-econ-val pos" id="sv-ingdp">--</span><span class="sb-econ-note" id="sn-ingdp">loading…</span></div>
        <div class="sb-econ-row"><span class="sb-econ-key">Unemployment</span><span class="sb-econ-val neu" id="sv-inunemp">--</span><span class="sb-econ-note" id="sn-inunemp">loading…</span></div>
        <div class="sb-econ-row"><span class="sb-econ-key">USD/INR</span><span class="sb-econ-val neu" id="sv-usdinr">₹--</span><span class="sb-econ-note">live</span></div>
      </div>
    </div>

    <!-- USA ECON -->
    <div style="margin-bottom:14px;">
      <div class="sb-econ-hdr" onclick="toggleEcon('usa')">
        <span class="sb-econ-title usa">🇺🇸 USA ECONOMIC</span>
        <span class="sb-arrow" id="arr-usa">▼</span>
      </div>
      <div class="sb-econ-body" id="body-usa">
        <div class="sb-econ-row"><span class="sb-econ-key">Fed Funds</span><span class="sb-econ-val neu" id="sv-fed">4.25–4.50%</span><span class="sb-econ-note">target range</span></div>
        <div class="sb-econ-row"><span class="sb-econ-key">CPI YoY</span><span class="sb-econ-val neu" id="sv-cpi">--</span><span class="sb-econ-note" id="sn-cpi">loading…</span></div>
        <div class="sb-econ-row"><span class="sb-econ-key">GDP</span><span class="sb-econ-val neu" id="sv-gdp">--</span><span class="sb-econ-note" id="sn-gdp">loading…</span></div>
        <div class="sb-econ-row"><span class="sb-econ-key">Unemployment</span><span class="sb-econ-val neu" id="sv-unemp">--</span><span class="sb-econ-note" id="sn-unemp">loading…</span></div>
        <div class="sb-econ-row"><span class="sb-econ-key">NFP</span><span class="sb-econ-val neu" id="sv-nfp">--</span><span class="sb-econ-note" id="sn-nfp">loading…</span></div>
      </div>
    </div>

    <!-- LIVE PRICES -->
    <div>
      <div class="sb-label">▶ LIVE PRICES</div>
      <div class="sb-price-row"><span class="sb-price-name">S&amp;P 500</span><span class="sb-price-val neu" id="sbp-sp500">--</span></div>
      <div class="sb-price-row"><span class="sb-price-name">NASDAQ</span><span class="sb-price-val neu" id="sbp-nasdaq">--</span></div>
      <div class="sb-price-row"><span class="sb-price-name">Dow Jones</span><span class="sb-price-val neu" id="sbp-dow">--</span></div>
      <div class="sb-price-row"><span class="sb-price-name">VIX</span><span class="sb-price-val neu" id="sbp-vix">--</span></div>
      <div class="sb-price-row"><span class="sb-price-name">Gold</span><span class="sb-price-val neu" id="sbp-gold">--</span></div>
      <div class="sb-price-row"><span class="sb-price-name">Crude Oil</span><span class="sb-price-val neu" id="sbp-oil">--</span></div>
      <div class="sb-price-row"><span class="sb-price-name">Bitcoin</span><span class="sb-price-val neu" id="sbp-btc">--</span></div>
      <div class="sb-price-row"><span class="sb-price-name">USD/INR</span><span class="sb-price-val neu" id="sbp-inr">--</span></div>
    </div>

  </div><!-- /sidebar -->

  <!-- MAIN -->
  <div class="main">

    <!-- CATEGORY TABS -->
    <div class="cat-tabs-wrap">
      <div class="cat-tabs" id="catTabs"><!-- JS --></div>
    </div>

    <!-- SEARCH -->
    <div class="news-search">
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" placeholder="Filter headlines across all sectors…" oninput="filterNews()">
      </div>
    </div>

    <!-- NEWS AREA -->
    <div class="news-area" id="newsArea">
      <div class="news-hdr">
        <span class="news-hdr-title" id="newsTitle">▶ LOADING…</span>
        <span class="news-hdr-meta" id="newsMeta">Click any headline to expand · {current_time}</span>
      </div>
      <div class="news-col" id="newsCol"></div>
    </div>

  </div><!-- /main -->
</div><!-- /shell -->

<!-- STATUS BAR -->
<div class="statusbar">
  <span>SECTORALFEED · 10 SECTORS · RSS FEEDS · NO API KEY REQUIRED · NOT FINANCIAL ADVICE</span>
  <span id="statusTime">--:-- IST</span>
</div>

<!-- SCROLL TOP -->
<button class="scroll-top" id="scrollTopBtn" onclick="scrollTop()">↑</button>

<!-- ════════════════════════════════════════
     SCRIPTS
════════════════════════════════════════ -->
<script>
// ── Data injected by Python ──
const NEWS_DATA    = {news_json};
const SECTORS_META = {sectors_json};
const CAT_COUNTS   = {cat_counts_json};

let currentSector = SECTORS_META[0].id;

// ════════════════
// BUILD SIDEBAR + TABS
// ════════════════
function buildNav() {{
  const sbList = document.getElementById('sbSectorList');
  const tabs   = document.getElementById('catTabs');

  SECTORS_META.forEach((s, i) => {{
    // Sidebar item
    const item = document.createElement('div');
    item.className = 'sb-item' + (i === 0 ? ' active' : '');
    item.id = 'sb-' + s.id;
    item.innerHTML = `
      <span class="sb-name">
        <span style="font-size:13px">${{s.icon}}</span>
        ${{s.label}}
      </span>
      <span class="sb-count">${{CAT_COUNTS[s.id] || 0}}</span>`;
    item.onclick = () => switchSector(s.id);
    sbList.appendChild(item);

    // Tab
    const tab = document.createElement('div');
    tab.className = 'cat-tab' + (i === 0 ? ' active' : '');
    tab.id = 'tab-' + s.id;
    tab.textContent = s.icon + ' ' + s.label.toUpperCase();
    tab.onclick = () => switchSector(s.id);
    tabs.appendChild(tab);
  }});
}}

// ════════════════
// SWITCH SECTOR
// ════════════════
function switchSector(id) {{
  currentSector = id;
  document.querySelectorAll('.sb-item').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.cat-tab').forEach(e => e.classList.remove('active'));
  const sb = document.getElementById('sb-' + id);
  const tb = document.getElementById('tab-' + id);
  if (sb) sb.classList.add('active');
  if (tb) {{ tb.classList.add('active'); tb.scrollIntoView({{block:'nearest',inline:'center'}}); }}
  renderNews(id);
  // Close sidebar on mobile
  if (window.innerWidth <= 860) {{
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sbOverlay').classList.remove('open');
  }}
}}

// ════════════════
// RENDER NEWS
// ════════════════
function renderNews(id) {{
  const d = NEWS_DATA[id];
  if (!d) return;
  const query = (document.getElementById('searchInput')?.value || '').toLowerCase().trim();
  const items = query
    ? d.items.filter(i =>
        i.title.toLowerCase().includes(query) ||
        i.summary.toLowerCase().includes(query) ||
        i.source.toLowerCase().includes(query))
    : d.items;

  const col = document.getElementById('newsCol');
  document.getElementById('newsTitle').textContent =
    '▶ ' + d.icon + ' ' + d.label.toUpperCase() + ' — ' + items.length + ' ARTICLES';

  if (!items.length) {{
    col.innerHTML = '<div class="no-news">' + (query ? 'No articles match your search.' : 'No articles available right now. Re-run the script to refresh.') + '</div>';
    return;
  }}

  col.innerHTML = items.map((item, i) => {{
    const num  = String(i + 1).padStart(2, '0');
    const link = item.link && item.link !== '#'
      ? `<a class="nc-link" href="${{item.link}}" target="_blank" rel="noopener">Read Full Article ↗</a>` : '';
    return `<div class="nc-item" onclick="toggleItem(this)">
  <div class="nc-row">
    <span class="nc-num">${{num}}</span>
    <span class="nc-headline">${{item.title}}</span>
    <span class="nc-arrow">▼</span>
  </div>
  <div class="nc-expand">
    <div class="nc-meta">
      <span class="nc-src" style="background:${{d.color}}22;color:${{d.color}};border:1px solid ${{d.color}}44;">${{item.source}}</span>
      <span class="nc-sep">·</span>
      <span class="nc-time">${{item.time}}</span>
    </div>
    <div class="nc-summary">${{item.summary}}</div>
    ${{link}}
  </div>
</div>`;
  }}).join('');
}}

function toggleItem(el) {{
  el.classList.toggle('open');
  el.querySelector('.nc-expand').classList.toggle('open');
}}

// ════════════════
// SEARCH FILTER
// ════════════════
function filterNews() {{
  renderNews(currentSector);
}}

// ════════════════
// TOGGLE ECON SECTIONS
// ════════════════
function toggleEcon(id) {{
  const body  = document.getElementById('body-' + id);
  const arrow = document.getElementById('arr-' + id);
  body.classList.toggle('closed');
  arrow.classList.toggle('closed');
  body.style.maxHeight = body.classList.contains('closed') ? '0' : body.scrollHeight + 'px';
}}

// ════════════════
// THEME TOGGLE
// ════════════════
function toggleTheme() {{
  document.body.classList.toggle('light');
  localStorage.setItem('sf-theme', document.body.classList.contains('light') ? 'light' : 'dark');
}}
if (localStorage.getItem('sf-theme') === 'light') document.body.classList.add('light');

// ════════════════
// SIDEBAR TOGGLE (mobile)
// ════════════════
function toggleSidebar() {{
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sbOverlay').classList.toggle('open');
}}

// ════════════════
// SCROLL TOP
// ════════════════
function scrollTop() {{
  document.getElementById('newsArea').scrollTo({{top:0, behavior:'smooth'}});
}}
document.getElementById('newsArea')?.addEventListener('scroll', function() {{
  document.getElementById('scrollTopBtn').classList.toggle('show', this.scrollTop > 300);
}});

// ════════════════
// CLOCK
// ════════════════
function updateClock() {{
  const now = new Date();
  const fmt  = tz => now.toLocaleTimeString('en-US', {{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:true,timeZone:tz}});
  const fmtm = tz => now.toLocaleTimeString('en-US', {{hour:'2-digit',minute:'2-digit',hour12:true,timeZone:tz}});
  document.getElementById('ck-cst').textContent = fmt('America/Chicago');
  document.getElementById('ck-ist').textContent = fmt('Asia/Kolkata');
  document.getElementById('ck-sgt').textContent = fmt('Asia/Singapore');
  document.getElementById('ck-est').textContent = fmt('America/New_York');
  document.getElementById('ck-date').textContent = '📅 ' + now.toLocaleDateString('en-US', {{weekday:'short',month:'short',day:'numeric',year:'numeric',timeZone:'Asia/Kolkata'}});
  document.getElementById('statusTime').textContent = fmtm('Asia/Kolkata') + ' IST';
  document.getElementById('newsMeta').textContent = 'Click any headline to expand · Fetched: {current_time}';
}}

// ════════════════
// TICKER
// ════════════════
const TICKER_ITEMS = [
  ['S&P 500','sp500'], ['NASDAQ','nasdaq'], ['DOW','dow'],
  ['VIX','vix'], ['GOLD','gold'], ['CRUDE','oil'],
  ['BITCOIN','btc'], ['USD/INR','inr'],
];

function buildTicker() {{
  const track = document.getElementById('tickerTrack');
  const all   = [...TICKER_ITEMS, ...TICKER_ITEMS];
  track.innerHTML = all.map(([name, key]) =>
    `<span class="ticker-item" data-key="${{key}}">
      <span class="t-sym">${{name}}</span>
      <span class="t-val t-neu" data-tv="${{key}}">--</span>
    </span>`
  ).join('');
}}

function updateTicker(key, val, pct) {{
  const p   = parseFloat(pct);
  const txt = val + (pct ? ' (' + (p >= 0 ? '+' : '') + pct + '%)' : '');
  const cls = 't-val ' + (p > 0 ? 't-pos' : p < 0 ? 't-neg' : 't-neu');
  document.querySelectorAll('[data-tv="' + key + '"]').forEach(e => {{
    e.textContent = txt;
    e.className   = cls;
  }});
}}

function setSidebarPrice(key, val, pct) {{
  const el = document.getElementById('sbp-' + key);
  if (!el) return;
  el.textContent = val;
  const p = parseFloat(pct);
  el.className = 'sb-price-val ' + (p > 0 ? 'pos' : p < 0 ? 'neg' : 'neu');
}}

// ════════════════
// YAHOO FINANCE
// ════════════════
const SYMS = {{
  sp500:  '^GSPC', nasdaq: '^IXIC', dow:   '^DJI',
  vix:    '^VIX',  gold:   'GC=F',  oil:   'CL=F',
  btc:    'BTC-USD', inr:  'INR=X',
}};
const PROXIES = [
  u => 'https://corsproxy.io/?' + encodeURIComponent(u),
  u => 'https://api.allorigins.win/get?url=' + encodeURIComponent(u),
  u => 'https://thingproxy.freeboard.io/fetch/' + u,
];

async function fetchYahoo(key, sym) {{
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${{sym}}?interval=1d&range=1d`;
  for (const mkP of PROXIES) {{
    try {{
      const r = await fetch(mkP(url), {{mode:'cors', signal:AbortSignal.timeout(8000)}});
      if (!r.ok) continue;
      let d = await r.json();
      if (d.contents) d = JSON.parse(d.contents);
      const meta = d?.chart?.result?.[0]?.meta;
      if (!meta) continue;
      const cur  = meta.regularMarketPrice;
      const prev = meta.chartPreviousClose || meta.previousClose;
      if (!cur || !prev) continue;
      const chg = (cur - prev).toFixed(2);
      const pct = (((cur - prev) / prev) * 100).toFixed(2);
      let val;
      if (['sp500','nasdaq','dow'].includes(key)) val = cur.toLocaleString('en-US', {{minimumFractionDigits:2, maximumFractionDigits:2}});
      else if (key === 'vix')   val = cur.toFixed(2);
      else if (key === 'btc')   val = '$' + Math.round(cur).toLocaleString();
      else if (key === 'inr')   val = '₹' + cur.toFixed(2);
      else                      val = '$' + cur.toFixed(2);
      updateTicker(key, val, pct);
      setSidebarPrice(key, val, pct);
      if (key === 'inr') {{
        document.getElementById('sv-usdinr').textContent = '₹' + cur.toFixed(2);
        document.getElementById('sbp-inr').textContent   = '₹' + cur.toFixed(2);
      }}
      return;
    }} catch(e) {{}}
  }}
}}

// USA CPI via FRED CSV
async function fetchFredCPI() {{
  const url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL';
  for (const mkP of PROXIES) {{
    try {{
      const r = await fetch(mkP(url), {{signal:AbortSignal.timeout(8000)}});
      if (!r.ok) continue;
      let text = await r.text();
      try {{ const j = JSON.parse(text); if (j.contents) text = j.contents; }} catch(e) {{}}
      const lines = text.trim().split('\\n').filter(l => l && !l.startsWith('DATE'));
      if (lines.length < 13) continue;
      const last = lines[lines.length-1].split(',');
      const prev = lines[lines.length-13].split(',');
      const yoy  = (((parseFloat(last[1]) - parseFloat(prev[1])) / parseFloat(prev[1])) * 100).toFixed(1);
      const d    = new Date(last[0] + 'T12:00:00Z');
      const lbl  = d.toLocaleString('en-US', {{month:'short',year:'numeric',timeZone:'UTC'}});
      const el   = document.getElementById('sv-cpi');
      const sn   = document.getElementById('sn-cpi');
      if (el) {{ el.textContent = yoy + '%'; el.className = 'sb-econ-val ' + (parseFloat(yoy)>3?'neg':parseFloat(yoy)<=2?'pos':'neu'); }}
      if (sn) sn.textContent = 'YoY · ' + lbl;
      return;
    }} catch(e) {{}}
  }}
}}

// India GDP via World Bank
async function fetchIndiaGDP() {{
  const url = 'https://api.worldbank.org/v2/country/IN/indicator/NY.GDP.MKTP.KD.ZG?format=json&mrv=2';
  try {{
    const r = await fetch(url, {{signal:AbortSignal.timeout(8000)}});
    if (!r.ok) return;
    const d = await r.json();
    const rows = (d[1]||[]).filter(r => r.value !== null);
    if (!rows.length) return;
    const val = parseFloat(rows[0].value).toFixed(1);
    const yr  = rows[0].date;
    const el  = document.getElementById('sv-ingdp');
    const sn  = document.getElementById('sn-ingdp');
    if (el) {{ el.textContent = val + '%'; el.className = 'sb-econ-val ' + (parseFloat(val)>5?'pos':parseFloat(val)<0?'neg':'neu'); }}
    if (sn) sn.textContent = 'FY' + yr.slice(2) + ' (WB)';
  }} catch(e) {{}}
}}

async function loadMarketData() {{
  await Promise.all(Object.entries(SYMS).map(([k,s]) => fetchYahoo(k,s)));
  fetchFredCPI();
  fetchIndiaGDP();
}}

// ════════════════
// DRAG SCROLL TABS
// ════════════════
function initTabDrag() {{
  const tabs = document.getElementById('catTabs');
  let down = false, startX = 0, scrollStart = 0, dragged = false;
  tabs.addEventListener('mousedown', e => {{
    down = true; dragged = false; startX = e.pageX; scrollStart = tabs.scrollLeft;
    tabs.style.cursor = 'grabbing'; e.preventDefault();
  }});
  document.addEventListener('mouseup', () => {{ down = false; tabs.style.cursor = 'grab'; }});
  document.addEventListener('mousemove', e => {{
    if (!down) return;
    const dx = e.pageX - startX;
    if (Math.abs(dx) > 4) dragged = true;
    tabs.scrollLeft = scrollStart - dx;
  }});
  tabs.addEventListener('click', e => {{ if (dragged) {{ e.stopPropagation(); e.preventDefault(); dragged = false; }} }}, true);
  tabs.addEventListener('touchstart', e => {{ startX = e.touches[0].pageX; scrollStart = tabs.scrollLeft; }}, {{passive:true}});
  tabs.addEventListener('touchmove', e => {{ tabs.scrollLeft = scrollStart - (e.touches[0].pageX - startX); }}, {{passive:true}});
}}

// ════════════════════════════
// SPACE BACKGROUND — STARS & METEORS
// ════════════════════════════
(function() {{
  const canvas = document.getElementById('spaceCanvas');
  const ctx    = canvas.getContext('2d');

  function resize() {{
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }}
  window.addEventListener('resize', resize);
  resize();

  // ── Stars ──
  const STAR_COUNT = 280;
  const stars = Array.from({{length: STAR_COUNT}}, () => ({{
    x:     Math.random() * canvas.width,
    y:     Math.random() * canvas.height,
    r:     Math.random() * 1.4 + 0.2,
    alpha: Math.random() * 0.6 + 0.2,
    twinkleSpeed: 0.005 + Math.random() * 0.015,
    twinkleDir: Math.random() > 0.5 ? 1 : -1,
  }}));

  // ── Meteors ──
  const meteors = [];

  function spawnMeteor() {{
    const angle  = Math.PI / 5 + (Math.random() * Math.PI / 8);
    const startX = Math.random() * canvas.width * 1.5 - canvas.width * 0.2;
    meteors.push({{
      x:       startX,
      y:       -20,
      vx:      Math.cos(angle) * (6 + Math.random() * 6),
      vy:      Math.sin(angle) * (6 + Math.random() * 6),
      len:     80 + Math.random() * 120,
      width:   1 + Math.random() * 1.5,
      alpha:   1,
      fadeRate: 0.012 + Math.random() * 0.01,
      alive:   true,
    }});
  }}

  // Fire a burst of meteors after 1 minute, then every minute
  function spawnBurst() {{
    const count = 3 + Math.floor(Math.random() * 4); // 3-6 meteors
    for (let i = 0; i < count; i++) {{
      setTimeout(spawnMeteor, i * 220);
    }}
  }}
  setTimeout(() => {{ spawnBurst(); setInterval(spawnBurst, 60000); }}, 60000);

  function drawFrame() {{
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw stars
    stars.forEach(s => {{
      s.alpha += s.twinkleSpeed * s.twinkleDir;
      if (s.alpha >= 0.85 || s.alpha <= 0.1) s.twinkleDir *= -1;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${{s.alpha.toFixed(2)}})`;
      ctx.fill();
    }});

    // Draw meteors
    for (let i = meteors.length - 1; i >= 0; i--) {{
      const m = meteors[i];
      m.x += m.vx;
      m.y += m.vy;
      m.alpha -= m.fadeRate;
      if (m.alpha <= 0 || m.x > canvas.width + 200 || m.y > canvas.height + 200) {{
        meteors.splice(i, 1);
        continue;
      }}
      const tailX = m.x - Math.cos(Math.atan2(m.vy, m.vx)) * m.len;
      const tailY = m.y - Math.sin(Math.atan2(m.vy, m.vx)) * m.len;
      const grad  = ctx.createLinearGradient(tailX, tailY, m.x, m.y);
      grad.addColorStop(0, `rgba(255,255,255,0)`);
      grad.addColorStop(0.6, `rgba(200,220,255,${{(m.alpha * 0.4).toFixed(2)}})`);
      grad.addColorStop(1,   `rgba(255,255,255,${{m.alpha.toFixed(2)}})`);
      ctx.beginPath();
      ctx.moveTo(tailX, tailY);
      ctx.lineTo(m.x, m.y);
      ctx.strokeStyle = grad;
      ctx.lineWidth   = m.width;
      ctx.shadowBlur  = 8;
      ctx.shadowColor = 'rgba(180,210,255,0.7)';
      ctx.stroke();
      ctx.shadowBlur  = 0;
      // bright head dot
      ctx.beginPath();
      ctx.arc(m.x, m.y, m.width * 1.2, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${{m.alpha.toFixed(2)}})`;
      ctx.fill();
    }}

    requestAnimationFrame(drawFrame);
  }}

  drawFrame();
}})();

// ════════════════
// INIT
// ════════════════
window.addEventListener('DOMContentLoaded', () => {{
  buildNav();
  renderNews(currentSector);
  initTabDrag();
  updateClock();
  setInterval(updateClock, 1000);
  loadMarketData();
  setInterval(loadMarketData, 5 * 60 * 1000);

  // Set initial heights for collapsible sections
  ['usa','india'].forEach(id => {{
    const b = document.getElementById('body-' + id);
    if (b) b.style.maxHeight = b.scrollHeight + 'px';
  }});
}});
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    logging.info("")
    logging.info("=" * 60)
    logging.info("  SECTORALFEED — Bloomberg Terminal Style Dashboard")
    logging.info("  14 SECTORS (NSE/BSE) · RSS FEEDS · NO API KEY REQUIRED")
    logging.info("=" * 60)

    all_news = {}
    for s in SECTORS:
        logging.info(f"\nFetching [{s['label'].upper()}] …")
        items = fetch_sector_news(
            s["id"], s["feeds"],
            max_items=s.get("max_items", MAX_NEWS_PER_SECTOR),
            hours=s.get("hours", 48),
        )
        all_news[s["id"]] = items
        logging.info(f"  ✓ {len(items)} articles")

    total = sum(len(v) for v in all_news.values())
    logging.info(f"\nTotal articles: {total}")

    logging.info("\nGenerating HTML dashboard …")
    html = generate_html(all_news)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    logging.info("=" * 60)
    logging.info(f"✅  Dashboard → {OUTPUT_FILE}")
    logging.info("   Open in your browser to view.")
    logging.info("   Re-run the script anytime to refresh the news.")
    logging.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
