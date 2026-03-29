from __future__ import annotations

from urllib.parse import urlparse

try:
    import tldextract
except ImportError:  # pragma: no cover
    tldextract = None

TLD_EXTRACTOR = (
    tldextract.TLDExtract(suffix_list_urls=None, cache_dir=None) if tldextract is not None else None
)

INFRASTRUCTURE_DOMAINS = {
    "amazonses.com",
    "amazonaws.com",
    "mailgun.org",
    "mailgun.net",
    "sendgrid.net",
    "sendgrid.com",
    "postmarkapp.com",
    "sparkpostmail.com",
    "mandrillapp.com",
}

PUBLIC_SUFFIX_ONLY = {
    "com.br",
    "com",
    "net",
    "org",
    "co",
}

TRACKING_HINTS = {
    "click",
    "trk",
    "track",
    "email",
    "links",
    "lnk",
}

DOMAIN_ALIASES = {
    "gmail.com": "Google",
    "googlemail.com": "Google",
    "google.com": "Google",
    "youtube.com": "Google",
    "github.com": "GitHub",
    "discord.com": "Discord",
    "whatsapp.com": "WhatsApp",
    "apple.com": "Apple",
    "icloud.com": "Apple",
    "paypal.com": "PayPal",
    "steamcommunity.com": "Steam",
    "steampowered.com": "Steam",
    "microsoft.com": "Microsoft",
    "office.com": "Microsoft",
    "live.com": "Microsoft",
    "outlook.com": "Microsoft",
    "notion.so": "Notion",
    "amazon.com": "Amazon",
    "primevideo.com": "Amazon",
    "aws.amazon.com": "Amazon Web Services",
    "netflix.com": "Netflix",
    "dropbox.com": "Dropbox",
    "openai.com": "OpenAI",
    "chatgpt.com": "OpenAI",
    "supercell.com": "Supercell",
    "facebookmail.com": "Facebook",
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "pokemongolive.com": "Pokemon GO",
    "nianticlabs.com": "Niantic",
    "deviantart.com": "DeviantArt",
    "sheinemail.com": "SHEIN",
    "shein.com": "SHEIN",
    "twitch.tv": "Twitch",
    "pinterest.com": "Pinterest",
    "gog.com": "GOG",
    "ebay.com": "eBay",
    "spotify.com": "Spotify",
    "rockstargames.com": "Rockstar Games",
    "duolingo.com": "Duolingo",
    "hotmart.com": "Hotmart",
    "scribd.com": "Scribd",
    "quillbot.com": "QuillBot",
    "krisp.ai": "Krisp",
    "manus.im": "Manus",
    "napkin.ai": "Napkin",
    "meister.co": "Meister",
    "wbgames.com": "WB Games",
    "runwayml.com": "Runway",
    "nvcam.net": "NVCAM",
    "pixlr.com": "Pixlr",
    "ubisoft.com": "Ubisoft",
    "temuemail.com": "Temu",
    "temuofficial.com": "Temu",
    "sheinnotice.com": "SHEIN",
    "shopifyemail.com": "Shopify",
    "mozmail.com": "Mozilla",
    "familysearch.org": "FamilySearch",
    "fatsecret.com": "FatSecret",
    "pipastudios.com": "Pipa Studios",
    "aiqfome.com": "Aiqfome",
    "trueskate.com": "True Skate",
    "signalrgb.com": "SignalRGB",
    "vsco.co": "VSCO",
    "joysticket.com": "Joysticket",
    "terabox.com": "TeraBox",
    "capcut.com": "CapCut",
    "blockerxmails.com": "BlockerX",
    "virtuagym.com": "Virtuagym",
    "mapify.so": "Mapify",
    "kwai.com": "Kwai",
    "picpay.com": "PicPay",
    "mega.nz": "MEGA",
    "soundcloud.com": "SoundCloud",
    "mindmeister.com": "MindMeister",
    "meistertask.com": "MindMeister",
    "riotgames.com": "Riot Games",
    "redditmail.com": "Reddit",
    "reddit.com": "Reddit",
    "chess.com": "Chess.com",
    "olx.com.br": "OLX",
    "grow.games": "Grow Games",
    "tiktok.com": "TikTok",
    "aliexpress.com": "AliExpress",
    "x.com": "X",
    "twitter.com": "X",
    "slack.com": "Slack",
}

CATEGORY_HINTS = {
    "Google": "productivity",
    "GitHub": "developer",
    "Discord": "communication",
    "WhatsApp": "communication",
    "Apple": "productivity",
    "PayPal": "finance",
    "Steam": "gaming",
    "Microsoft": "productivity",
    "Notion": "productivity",
    "Amazon": "shopping",
    "Amazon Web Services": "cloud",
    "Netflix": "entertainment",
    "Dropbox": "productivity",
    "OpenAI": "productivity",
    "Supercell": "gaming",
    "Facebook": "social",
    "Instagram": "social",
    "Pokemon GO": "gaming",
    "Niantic": "gaming",
    "DeviantArt": "social",
    "SHEIN": "shopping",
    "Twitch": "entertainment",
    "Pinterest": "social",
    "GOG": "gaming",
    "eBay": "shopping",
    "Spotify": "entertainment",
    "Rockstar Games": "gaming",
    "Duolingo": "education",
    "Hotmart": "productivity",
    "Scribd": "productivity",
    "QuillBot": "productivity",
    "Krisp": "productivity",
    "Manus": "productivity",
    "Napkin": "productivity",
    "Meister": "productivity",
    "WB Games": "gaming",
    "Runway": "productivity",
    "NVCAM": "productivity",
    "Pixlr": "productivity",
    "Ubisoft": "gaming",
    "Temu": "shopping",
    "Shopify": "shopping",
    "Mozilla": "productivity",
    "FamilySearch": "productivity",
    "FatSecret": "productivity",
    "Pipa Studios": "gaming",
    "Aiqfome": "shopping",
    "True Skate": "gaming",
    "SignalRGB": "productivity",
    "VSCO": "social",
    "Joysticket": "gaming",
    "TeraBox": "productivity",
    "CapCut": "productivity",
    "BlockerX": "productivity",
    "Virtuagym": "productivity",
    "Mapify": "travel",
    "Kwai": "social",
    "PicPay": "finance",
    "MEGA": "productivity",
    "SoundCloud": "entertainment",
    "MindMeister": "productivity",
    "Riot Games": "gaming",
    "Reddit": "social",
    "Chess.com": "gaming",
    "OLX": "shopping",
    "Grow Games": "gaming",
    "TikTok": "social",
    "AliExpress": "shopping",
    "X": "social",
    "Slack": "communication",
}


def normalize_host(value: str | None) -> str | None:
    if not value:
        return None
    host = value.strip().lower().strip(".")
    if "@" in host and "/" not in host:
        host = host.split("@", 1)[1]
    if "://" in host:
        host = urlparse(host).hostname or ""
    if ":" in host:
        host = host.split(":", 1)[0]
    return host or None


def registrable_domain(value: str | None) -> str | None:
    host = normalize_host(value)
    if not host:
        return None
    if TLD_EXTRACTOR is not None:
        extracted = TLD_EXTRACTOR(host)
        if not extracted.domain or not extracted.suffix:
            return host
        return f"{extracted.domain}.{extracted.suffix}"
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def meaningful_domain(value: str | None) -> str | None:
    host = normalize_host(value)
    if not host:
        return None
    if host in DOMAIN_ALIASES:
        return host
    base = registrable_domain(host)
    return base or host


def domain_from_url(url: str) -> str | None:
    return meaningful_domain(urlparse(url).hostname)


def is_infrastructure_domain(domain: str | None) -> bool:
    if not domain:
        return False
    base = registrable_domain(domain) or domain
    return base in INFRASTRUCTURE_DOMAINS


def looks_like_tracking_domain(domain: str | None) -> bool:
    if not domain:
        return False
    host = normalize_host(domain) or ""
    labels = host.split(".")
    return any(label in TRACKING_HINTS for label in labels[:-2])


def canonical_service_for_domain(domain: str | None) -> str | None:
    if not domain:
        return None
    host = normalize_host(domain)
    if not host:
        return None
    if host in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[host]
    base = registrable_domain(host)
    if base in PUBLIC_SUFFIX_ONLY:
        return None
    if base in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[base]
    if not base:
        return None
    label = base.split(".")[0].replace("-", " ").replace("_", " ").strip()
    return label.title() if label else None


def category_for_service(name: str) -> str:
    return CATEGORY_HINTS.get(name, "unknown")
