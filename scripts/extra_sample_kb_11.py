"""Phase 2 knowledge-base gap notes.

Plain-language teaching summaries informed by the cited public pages.
These notes do not give a personal dose. Follow the packet and a pharmacist.
"""

PHASE2_DOCUMENTS = [
    (
        "paracetamol_safety",
        "Paracetamol Safety",
        "NHS - Paracetamol for adults",
        "https://www.nhs.uk/medicines/paracetamol-for-adults/",
        "Paracetamol Safety",
        "consult_doctor",
        """Paracetamol (also called acetaminophen) is a common pain and fever medicine.
Taking more than the packet allows, or taking two products that both contain
paracetamol such as a cold-and-flu remedy plus tablets, can damage the liver.
Always read the label and ask a pharmacist which products already contain it.

NHS advice is that paracetamol is usually the first pain option for many adults,
including in pregnancy and while breastfeeding, but it is not suitable for everyone,
especially some people with liver problems or heavy alcohol use. This note does not
give a personal dose.

See a pharmacist or doctor if you are unsure which product is safe. Get urgent help
if you have taken more than the packet allows, even if you feel well. Seek emergency
care for swelling of the tongue, trouble breathing, or yellowing of the skin or eyes.""",
    ),
    (
        "ibuprofen_nsaid_safety",
        "Ibuprofen and NSAID Safety",
        "NHS - Ibuprofen for adults",
        "https://www.nhs.uk/medicines/ibuprofen-for-adults/",
        "Ibuprofen Safety",
        "consult_doctor",
        """Ibuprofen is a non-steroidal anti-inflammatory drug (NSAID) used for pain, swelling,
and fever. It can irritate the stomach. It is often a poorer choice than paracetamol
if you have a stomach ulcer, have had stomach bleeding, have asthma that is set off
by NSAIDs, kidney or heart disease, or you are pregnant.

Do not take ibuprofen together with other NSAIDs such as naproxen or aspirin for pain.
Take the smallest amount that helps, for the shortest time, and ideally with or after
food. Follow the packet; this note does not give a personal dose.

See a pharmacist or doctor before using ibuprofen if you have an ulcer, asthma, or
you are pregnant. Seek emergency care for vomiting blood, black tar-like stool,
swelling of the tongue, or sudden breathlessness.""",
    ),
    (
        "aspirin_and_children",
        "Aspirin and Children",
        "NHS - Aspirin",
        "https://www.nhs.uk/medicines/aspirin-for-pain-relief/",
        "Aspirin Safety",
        "consult_doctor",
        """Do not give aspirin for pain or fever to children aged 15 or under, unless a doctor
has specifically prescribed it. In rare cases aspirin in children can be linked with
Reye's syndrome, a serious illness. Use a child pain or fever medicine that a
pharmacist says is suitable for that age.

In adults, aspirin is an NSAID. Low-dose aspirin used to lower clot risk is not the
same as a pain dose. Pain-dose aspirin can irritate the stomach and is not the usual
pain option in pregnancy. Follow the packet and a clinician; this note does not give
a personal dose.

See a doctor or pharmacist before giving any aspirin product to a young person.
Seek emergency care for vomiting blood, black stool, wheeze, or swelling of the
tongue after aspirin.""",
    ),
    (
        "medicines_in_pregnancy",
        "Medicines in Pregnancy",
        "NHS - Medicines in pregnancy",
        "https://www.nhs.uk/pregnancy/keeping-well/medicines/",
        "Medicines in Pregnancy",
        "consult_doctor",
        """Most medicines taken in pregnancy can reach the baby. Check with a pharmacist,
midwife, or GP before taking painkillers, cold remedies, herbal products, or any
new tablet, even ones you can buy in a shop. Do not stop a prescribed medicine
that keeps you well without asking the prescriber first.

NHS pages list paracetamol as the usual first pain option in pregnancy. Ibuprofen
and other NSAIDs are generally avoided unless a doctor or pharmacist advises them.
Herbal and homeopathic products are not automatically safe because they are natural.

See a midwife, pharmacist, or doctor before starting or stopping a medicine in
pregnancy. Seek urgent maternity advice for a severe headache, visual change, or
sudden facial swelling.""",
    ),
    (
        "smoking_cessation",
        "Help to Stop Smoking",
        "NHS - NHS stop smoking services help you quit",
        "https://www.nhs.uk/live-well/quit-smoking/nhs-stop-smoking-services-help-you-quit/",
        "Stop Smoking",
        "self_care",
        """Stopping smoking is one of the most useful health changes a person can make.
Free stop-smoking services can raise the chance of quitting. They may offer advice,
nicotine replacement such as patches or gum, and prescribed stop-smoking medicines
when suitable. Programmes and helplines differ by country.

You can ask a GP, pharmacist, or local stop-smoking service for support. Some people
also use an e-cigarette to replace cigarettes; a stop-smoking adviser can discuss
what is available where you live. This is not a personal quit plan.

See a clinician if you want help to quit, especially in pregnancy. Seek emergency
care for sudden chest pain or severe breathlessness.""",
    ),
    (
        "delirium",
        "Delirium (Sudden Confusion)",
        "MedlinePlus - Delirium",
        "https://medlineplus.gov/ency/article/000740.htm",
        "Delirium",
        "consult_doctor",
        """Delirium is a sudden change in attention and thinking. A person may become confused
over hours or a few days, mix up day and night, or swing between drowsiness and
agitation. It is not the same as dementia, which usually develops slowly. Delirium
is common in older adults who are unwell, after surgery, or in hospital.

Triggers include infections such as a urine or chest infection, medicines, withdrawal
from alcohol, severe lack of sleep, and chemical imbalances. It often improves when
the cause is treated, but it needs prompt medical assessment.

See a doctor urgently for a rapid change in mental state. Seek emergency care if the
person cannot be woken, has a seizure, or has a fever with a stiff neck.""",
    ),
    (
        "fabry_disease",
        "Fabry Disease",
        "MedlinePlus Genetics - Fabry disease",
        "https://medlineplus.gov/genetics/condition/fabry-disease/",
        "Fabry Disease",
        "consult_doctor",
        """Fabry disease is a rare inherited condition. A change in the GLA gene reduces an
enzyme that helps break down a fatty substance, which then builds up in cells. It is
passed in an X-linked pattern, so males are often more severely affected, but many
females also have symptoms. This note is general information, not a diagnosis.

Features can include burning pain in the hands and feet, small dark-red skin spots,
reduced sweating, gut symptoms, hearing change, and later kidney, heart, or stroke
problems. Milder later-onset forms mainly affect the heart, kidneys, or brain vessels.
Only a clinician can confirm it with tests.

See a doctor if these features run in the family or start in childhood. Seek emergency
care for sudden face droop, speech change, or one-sided weakness.""",
    ),
]

PHASE2_NEW_IDS = tuple(row[0] for row in PHASE2_DOCUMENTS)
