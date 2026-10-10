import pytest

from tracker.filters import classify_title, clean_location, is_australia

BIG = "Big Tech / Global Software"
BANK = "Banking / Finance / Insurance"


@pytest.mark.parametrize(
    "title,sector,expected",
    [
        ("Software Engineer Intern", BIG, ("Intern", "Software")),
        ("2027 Software Engineering Internship - Sydney", BIG, ("Intern", "Software")),
        ("Graduate Software Engineer", BIG, ("Graduate", "Software")),
        ("Graduate Data Analyst", BANK, ("Graduate", "Data & Analytics")),
        ("Data Engineer - Graduate Program 2027", BANK, ("Graduate", "Data & Analytics")),
        ("Junior Data Engineer", BANK, ("Early career", "Data & Analytics")),
        ("Machine Learning Engineer Intern", BIG, ("Intern", "ML/AI")),
        ("AI Research Intern", BIG, ("Intern", "ML/AI")),
        ("Summer Intern - Data Science", BIG, ("Intern", "Data & Analytics")),
        ("Cyber Security Graduate", BANK, ("Graduate", "Infra/Cloud/Security")),
        ("Cloud Engineer - Early Careers", BANK, ("Early career", "Infra/Cloud/Security")),
        ("Technology Graduate Program 2027", BANK, ("Graduate", "Other tech")),
        ("2027 Technology Summer Internship Program", BANK, ("Intern", "Other tech")),
        ("2027 Graduate Program", BANK, ("Graduate", "General program")),
        ("Summer Vacation Program", BANK, ("Intern", "General program")),
        ("Software Engineer I", BIG, ("Early career", "Software")),
        ("Entry Level Database Administrator", BANK, ("Early career", "Data & Analytics")),
        ("Engineering Intern", BIG, ("Intern", "Software")),
        ("Quantitative Developer Intern", "Trading / Quant", ("Intern", "Software")),
        ("Associate Software Engineer", BIG, ("Early career", "Software")),
        ("Junior Full Stack Developer", BIG, ("Early career", "Software")),
        ("QA Test Engineer - Graduate", BIG, ("Graduate", "Infra/Cloud/Security")),
        ("Business Intelligence Analyst Intern", BANK, ("Intern", "Data & Analytics")),
        ("IT Support Cadet", "Government / Research", ("Intern", "Infra/Cloud/Security")),
        ("Digital Cadetship", "Government / Research", ("Intern", "Other tech")),
        ("Front End Developer (Junior)", BIG, ("Early career", "Software")),
        # negatives
        ("Senior Software Engineer", BIG, None),
        ("Staff Data Engineer", BIG, None),
        ("Engineering Manager", BIG, None),
        ("Lead Graduate Recruiter", BANK, None),
        ("Campus Recruiter", BIG, None),
        ("Software Engineer", BIG, None),
        ("Data Scientist", BIG, None),
        ("Marketing Intern", BIG, None),
        ("Graduate Accountant", BANK, None),
        ("Sales Development Representative - Graduate", BIG, None),
        ("Mining Engineering Graduate", "Energy / Resources / Infrastructure", None),
        ("Mechanical Engineering Intern", "Defence / Aerospace", None),
        ("Engineering Intern", "Energy / Resources / Infrastructure", None),
        ("Graduate Lawyer", BANK, None),
        ("Internal Audit Analyst", BANK, None),
        ("International Payments Specialist", BANK, None),
        ("Principal Architect", BIG, None),
        ("Senior Data Analyst - Graduate Programs", BANK, None),
        ("PhD Research Scientist", BIG, None),
        ("Registered Nurse - Graduate", "Health / Biotech / Medtech", None),
        ("Graduate Finance Analyst", BANK, None),
        ("Customer Service Trainee", "Telco / Infrastructure", None),
        ("2027 Payments Settlements Graduate Program - Risk Management Stream", BANK, None),
        ("Cyber Risk Graduate", BANK, ("Graduate", "Infra/Cloud/Security")),
    ],
)
def test_classify_title(title, sector, expected):
    assert classify_title(title, sector) == expected


@pytest.mark.parametrize(
    "loc,expected",
    [
        ("Sydney, Australia", True),
        ("Sydney CBD Area", True),
        ("Melbourne", True),
        ("AU, Sydney", True),
        ("Remote - Australia", True),
        ("Canberra, ACT", True),
        ("Brisbane, QLD", True),
        ("Sydney or Melbourne", True),
        ("Barangaroo", True),
        ("Perth, Western Australia", True),
        ("Seattle, WA", False),
        ("Victoria, British Columbia, Canada", False),
        ("Newcastle upon Tyne, UK", False),
        ("San Francisco, CA", False),
        ("Remote", False),
        ("Singapore", False),
        ("", False),
        ("Auckland, New Zealand", False),
        ("Perth, Scotland", False),
        ("US-FL-MELBOURNE-312 ~ 795 W Nasa Blvd", False),
        ("Melbourne, FL, US", False),
    ],
)
def test_is_australia(loc, expected):
    assert is_australia(loc) is expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Sydney, NSW, Australia, Australia", "Sydney, NSW, Australia"),
        ("Cremorne, Victoria, AU, Australia", "Cremorne, Victoria, Australia"),
        ("AU - Sydney; AU - Melbourne; Australia", "AU - Sydney, AU - Melbourne, Australia"),
        ("2 Locations, Australia", "Australia"),
        ("", "Australia"),
    ],
)
def test_clean_location(raw, expected):
    assert clean_location(raw) == expected
