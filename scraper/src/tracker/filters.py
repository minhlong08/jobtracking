"""Classify postings: Australian location, early-career level, tech category."""
import re

# --- Location -----------------------------------------------------------------

_AU_STRONG = re.compile(r"australia|\bAUS\b|\bAU\b", re.I)
_AU_PLACES = re.compile(
    r"\b(sydney|melbourne|brisbane|perth|adelaide|canberra|hobart|darwin|gold coast|sunshine coast|"
    r"newcastle|wollongong|geelong|parramatta|north sydney|barangaroo|docklands|macquarie park|"
    r"chatswood|cremorne|townsville|cairns|toowoomba|ballarat|launceston|"
    r"new south wales|victoria|queensland|western australia|south australia|tasmania|"
    r"northern territory|australian capital territory|NSW|QLD)\b",
    re.I,
)
_NON_AU = re.compile(
    r"canada|british columbia|united kingdom|\buk\b|england|scotland|united states|\busa\b|south africa|"
    r"upon tyne|\b(AL|AK|AZ|CA|CO|CT|FL|GA|IL|MA|MD|MI|MN|NC|NJ|NY|OH|OR|PA|TX|VA|WA)\b,?\s*(\d{5}|$|united)",
    re.I,
)


# Case-sensitive US markers, e.g. Workday's "US-FL-MELBOURNE" (Melbourne, Florida).
_US_CODE = re.compile(r"\b(US|USA)\b")


def is_australia(location: str) -> bool:
    if not location:
        return False
    if _AU_STRONG.search(location):
        return True
    return bool(_AU_PLACES.search(location)) and not _NON_AU.search(location) and not _US_CODE.search(location)


# --- Level --------------------------------------------------------------------

_EXCLUDE_LEVEL = re.compile(
    r"\b(senior|snr|sr\.?|lead|principal|staff|manager|director|head of|architect|vp|vice president|chief|"
    r"recruit\w*|talent acquisition|campus recruiter|phd|postdoc\w*|professor|lecturer)\b",
    re.I,
)
_INTERN = re.compile(
    r"\b(intern|interns|internship|internships|co-?op|vacation(er)?|summer (student|program|associate|analyst|clerk)|"
    r"winter (program|student)|industrial placement|placement student|cadet|cadetship|student|undergraduate|"
    r"apprentice|apprenticeship|traineeship|work experience)\b",
    re.I,
)
_GRAD = re.compile(
    r"\b(graduate|graduates|grad|new grad|campus|university hire|class of 20\d\d|graduate program|"
    r"graduate programme|analyst program|technology program)\b",
    re.I,
)
_EARLY = re.compile(
    r"\b(early career|early careers|early-career|entry[- ]level|junior|jnr|jr\.?|new college grad|"
    r"associate (software|data|cloud|security|devops|platform|machine learning|ml) (engineer|developer|analyst|scientist))\b"
    r"|\b(engineer|developer|analyst|scientist),?\s+(i|1)\b(?!\w)",
    re.I,
)


def classify_level(title: str) -> str | None:
    if _EXCLUDE_LEVEL.search(title):
        return None
    if _INTERN.search(title):
        return "Intern"
    if _GRAD.search(title):
        return "Graduate"
    if _EARLY.search(title):
        return "Early career"
    return None


# --- Category -----------------------------------------------------------------

_NON_TECH = re.compile(
    r"\b(marketing|sales|account executive|accounting|accountant|audit|tax|legal|lawyer|law|paralegal|"
    r"human resources|\bhr\b|people & culture|nurs\w*|medical|clinical|pharmac\w*|mining|geolog\w*|"
    r"geotech\w*|mechanical|civil|chemical|electrical|metallurg\w*|process engineer|structural|"
    r"supply chain|procurement|logistics|customer service|call centre|retail|hospitality|"
    r"communications|journalis\w*|design(er)? \(product\)|graphic|actuar\w*|economist|policy|"
    r"investment banking|wealth|risk|compliance|insurance|underwrit\w*|claims|operations analyst|finance)\b",
    re.I,
)
_ML = re.compile(
    r"\b(machine learning|ml|ai|artificial intelligence|deep learning|computer vision|nlp|"
    r"research (scientist|engineer)|applied scientist|llm|genai)\b",
    re.I,
)
_DATA = re.compile(
    r"\b(data|analytics|business intelligence|bi|insights?|statistic\w*|database|dba|sql|"
    r"quant(itative)? (analyst|researcher)|decision science)\b",
    re.I,
)
_INFRA = re.compile(
    r"\b(cloud|devops|dev ops|sre|site reliability|infrastructure|platform|network\w* engineer|cyber\w*|"
    r"information security|security (engineer|analyst|consultant)|penetration|soc analyst|"
    r"systems? engineer|it support|service desk|sysadmin|system administrator|"
    r"quality assurance|qa|test(ing)? (automation|engineer|analyst)|automation engineer)\b",
    re.I,
)
_SOFTWARE = re.compile(
    r"\b(software|swe|developer|programmer|full[- ]?stack|front[- ]?end|back[- ]?end|mobile|ios|android|"
    r"web|embedded|firmware|quant(itative)? developer|technologist|computer science|coding)\b",
    re.I,
)
_OTHER_TECH = re.compile(
    r"\b(technology|tech|it|ict|digital|technical|information systems|solutions? engineer|stem)\b",
    re.I,
)
_BARE_ENGINEER = re.compile(r"\bengineer(ing)?\b", re.I)
_GENERIC_PROGRAM = re.compile(
    r"\b(graduate|internship|vacation|summer|intern|cadetship|early careers?)\s+(program|programme|intake)\b"
    r"|^(20\d\d\s+)?(graduate|summer intern|intern|vacation)\w*(\s+program\w*)?(\s*[-–|]\s*20\d\d)?$",
    re.I,
)

# Sectors where a bare "Engineer/Engineering" title almost always means software.
TECH_NATIVE_SECTORS = {"Big Tech / Global Software", "Australian Software / Scale-ups", "Trading / Quant"}


def classify_category(title: str, sector: str = "") -> str | None:
    if _ML.search(title):
        return "ML/AI"
    if _DATA.search(title):
        return "Data & Analytics"
    if _SOFTWARE.search(title):
        return "Software"
    if _INFRA.search(title):
        return "Infra/Cloud/Security"
    if _NON_TECH.search(title):
        return None
    if _OTHER_TECH.search(title):
        return "Other tech"
    if _BARE_ENGINEER.search(title) and sector in TECH_NATIVE_SECTORS:
        return "Software"
    if _GENERIC_PROGRAM.search(title.strip()):
        return "General program"
    return None


def classify(title: str, location: str, sector: str = "") -> tuple[str, str] | None:
    """Return (level, category) if the posting is an AU early-career tech role, else None."""
    if not is_australia(location):
        return None
    return classify_title(title, sector)


def classify_title(title: str, sector: str = "") -> tuple[str, str] | None:
    title = re.sub(r"\s+", " ", title).strip()
    level = classify_level(title)
    if not level:
        return None
    category = classify_category(title, sector)
    if not category:
        return None
    return level, category


def clean_location(location: str) -> str:
    """Tidy ATS location strings: drop country codes and repeated parts."""
    parts = []
    for chunk in re.split(r"[;,]", location):
        part = re.sub(r"\s+", " ", chunk).strip(" -~")
        if not part or part.upper() in {"AU", "AUS"} or re.fullmatch(r"\d+ Locations", part):
            continue
        if part.lower() not in (p.lower() for p in parts):
            parts.append(part)
    return ", ".join(parts) or "Australia"
