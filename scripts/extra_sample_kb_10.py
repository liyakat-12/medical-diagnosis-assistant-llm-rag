"""Phase 1 knowledge-base gap notes (8 new topics).

Plain-language teaching summaries informed by the cited public pages.
Not a verbatim copy of any leaflet. Eligibility for screening and vaccines
differs by country; each note records that limitation.
"""

# Each tuple: (id, title, source, url, condition, triage_level, body)
PHASE1_DOCUMENTS = [
    (
        "food_safety_at_home",
        "Food Safety at Home",
        "CDC - Preventing Food Poisoning",
        "https://www.cdc.gov/food-safety/prevention/index.html",
        "Food Safety",
        "self_care",
        """Food poisoning is often prevented with four steps: clean, separate, cook, and chill.
Wash hands and surfaces with soap, keep raw meat and seafood away from ready-to-eat
food, cook food until it is steaming hot throughout, and refrigerate leftovers promptly.
Risky foods include raw or undercooked meat, poultry, eggs, sprouts, unpasteurized milk
or juice, and raw dough.

Do not wash raw chicken, because splashes can spread germs. Perishable food should not
sit out for more than about two hours, or one hour in hot weather. Safe cooking
temperatures are published by local food-safety agencies and can differ by country.

See a doctor for bloody diarrhoea, high fever, or signs of dehydration after suspect food.
Seek urgent care if you cannot keep fluids down. Pregnant people, older adults, and
people with a weak immune system should be especially careful with high-risk foods.""",
    ),
    (
        "norovirus",
        "Norovirus (Winter Vomiting Bug)",
        "NHS - Norovirus",
        "https://www.nhs.uk/conditions/norovirus/",
        "Norovirus",
        "self_care",
        """Norovirus is a very contagious stomach bug, also called the winter vomiting bug.
It is not influenza. Symptoms often start suddenly 12 to 48 hours after exposure and
include vomiting, diarrhoea, nausea, tummy pain, and sometimes fever, headache, or
aches. Most people improve in about one to three days.

Drink small sips of water or an oral rehydration drink. Rest, and eat when you can.
Wash hands with soap and water; alcohol gel does not reliably kill norovirus. Stay
home until 48 hours after the last vomit or diarrhoea.

See a doctor or pharmacist if you cannot keep fluids down, you are dehydrated, or
symptoms last longer than expected. Seek emergency care for blood in vomit, severe
tummy pain, confusion, or trouble breathing. Young children, older adults, and
pregnant people need earlier review if they cannot drink.""",
    ),
    (
        "adult_vaccination_overview",
        "Adult Vaccination Overview",
        "NHS - NHS vaccinations and when to have them",
        "https://www.nhs.uk/vaccinations/nhs-vaccinations-and-when-to-have-them/",
        "Adult Vaccination",
        "consult_doctor",
        """Vaccines reduce the chance of serious infection. Which ones you are offered depends
on age, pregnancy, long-term illness, and the country you live in. In the UK NHS
programme, adults may be offered flu, pneumococcal, shingles, RSV, or COVID-19
vaccines according to age and risk, and catch-up is often possible if a dose was missed.

Pregnancy programmes may include flu, whooping cough, and RSV vaccines at set times.
People with no spleen, diabetes, kidney, liver, heart, or lung disease, or a weakened
immune system may be offered extra vaccines. Other countries use different adult
schedules.

This is general education, not a personal immunisation plan. Ask a GP or clinic which
vaccines you are due. Seek emergency care for trouble breathing, facial swelling, or
collapse after a vaccine.""",
    ),
    (
        "cervical_screening",
        "Cervical Screening (Smear Test)",
        "NHS - What is cervical screening?",
        "https://www.nhs.uk/conditions/cervical-screening/what-is-cervical-screening/",
        "Cervical Screening",
        "consult_doctor",
        """Cervical screening, once called a smear test, checks the health of the cervix and
helps prevent cervical cancer. It is not a test for cancer already present. A sample
is checked first for high-risk human papillomavirus (HPV). If HPV is not found, further
cell tests are not needed at that visit.

In the NHS programme in England, people with a cervix aged 25 to 64 are usually invited
every five years. Ages, intervals, and HPV-first testing differ by country. The HPV
vaccine lowers risk but does not replace screening.

Attend when invited, or ask a GP if you missed an invitation. Do not wait for screening
if you have bleeding after sex, bleeding after menopause, unusual discharge, or pelvic
pain — see a doctor for those symptoms.""",
    ),
    (
        "breast_screening",
        "Breast Screening (Mammogram)",
        "NHS - Who breast screening is for",
        "https://www.nhs.uk/conditions/breast-screening-mammogram/when-youll-be-invited-and-who-should-go/",
        "Breast Screening",
        "consult_doctor",
        """A mammogram is an X-ray used to look for breast cancers that are too small to see or
feel. Screening is for people without symptoms. It does not replace reporting a new
lump, nipple change, or dimpling of the skin.

NHS breast screening is offered to women aged 50 up to the 71st birthday, usually every
three years. Other countries start at different ages. Trans and non-binary people may
need to ask a GP how invitations are arranged.

Go to screening appointments if you are invited, and still see a doctor promptly for
any new breast change, even soon after a normal mammogram.""",
    ),
    (
        "bowel_cancer_screening",
        "Bowel Cancer Screening",
        "NHS - Bowel cancer screening",
        "https://www.nhs.uk/conditions/bowel-cancer-screening/",
        "Bowel Cancer Screening",
        "consult_doctor",
        """Bowel cancer screening looks for hidden blood in a stool sample, often with a home
FIT kit. Finding blood does not mean you have cancer; piles and other conditions can
also bleed. A positive result is usually followed by a camera test of the bowel
(colonoscopy).

The NHS programme currently offers screening every two years to people aged 50 to 74.
In the United States, many adults are advised to start colorectal screening at age 45.
Starting ages, tests, and intervals differ by country and personal risk.

Complete the kit if you are invited. See a doctor without waiting for screening if you
have lasting blood in the stool, a change in bowel habit, or unexplained weight loss.
Seek emergency care for heavy rectal bleeding.""",
    ),
    (
        "dementia",
        "Dementia",
        "NHS - What is dementia",
        "https://www.nhs.uk/conditions/dementia/about-dementia/what-is-dementia/",
        "Dementia",
        "consult_doctor",
        """Dementia is a group of symptoms from an ongoing decline in brain function. It is not
a normal part of ageing. Memory loss is common, but dementia can also affect language,
judgement, mood, movement, and daily tasks. Alzheimer's disease is one type; vascular
dementia is another.

Occasional forgetfulness with stress or tiredness is different from memory loss that
disrupts work, safety, or independence. There is no simple home test. A GP can look
for treatable causes and arrange further assessment.

See a doctor if forgetfulness is getting worse or worrying you or someone close to you.
Sudden confusion over hours is not typical dementia and needs urgent review.""",
    ),
    (
        "listeriosis",
        "Listeriosis (Listeria Infection)",
        "NHS - Listeriosis",
        "https://www.nhs.uk/conditions/listeriosis/",
        "Listeriosis",
        "consult_doctor",
        """Listeriosis is a rare foodborne infection from listeria bacteria. Many healthy people
have no symptoms or a short flu-like illness with fever, aches, nausea, or diarrhoea.
It can be serious in pregnancy, newborns, people aged 65 or over, and anyone with a
weak immune system. In pregnancy it can lead to miscarriage or stillbirth.

Higher-risk chilled ready-to-eat foods include some soft mould-ripened or blue cheeses,
pâté, smoked or cured fish, cold cooked meats, and unpasteurised milk. Keep the fridge
cold, eat ready-to-eat food promptly, and follow use-by dates.

Most mild cases settle with rest and fluids. See a doctor urgently if you are pregnant
or at higher risk and think you have listeriosis. Call emergency services for a severe
headache with a stiff neck, confusion, a seizure, or a rash that does not fade when a
glass is pressed on it.""",
    ),
]

PHASE1_NEW_IDS = tuple(row[0] for row in PHASE1_DOCUMENTS)
