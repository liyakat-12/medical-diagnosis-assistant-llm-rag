"""Phase 2 follow-on notes for remaining evaluation gaps."""

PHASE2B_DOCUMENTS = [
    (
        "sun_safety_prevention",
        "Sun Safety to Lower Skin Cancer Risk",
        "CDC - Reducing Risk for Skin Cancer",
        "https://www.cdc.gov/skin-cancer/prevention/index.html",
        "Sun Safety",
        "self_care",
        """Most skin cancers are linked to too much ultraviolet (UV) light from the sun or
tanning beds. Protecting skin every day, including on cloudy days, lowers that risk.
A tan is a sign of skin injury, not of health, and a "base tan" does not prevent burn.

Stay in the shade, cover arms and legs, wear a wide-brim hat, and use sunglasses that
block UVA and UVB. CDC advice is to use a broad-spectrum sunscreen of SPF 15 or higher
on exposed skin when the UV index is 3 or above. Peak sun in much of the United States
is about 10 a.m. to 4 p.m. in daylight-saving months; local UV forecasts differ.

See a doctor for a mole that is changing, a sore that will not heal, or repeated severe
sunburn. Seek urgent care if someone becomes confused or very drowsy after heavy sun.""",
    ),
    (
        "gaucher_disease",
        "Gaucher Disease",
        "MedlinePlus Genetics - Gaucher disease",
        "https://medlineplus.gov/genetics/condition/gaucher-disease/",
        "Gaucher Disease",
        "consult_doctor",
        """Gaucher disease is a rare inherited condition. Both copies of the GBA1 gene are
changed, so an enzyme that breaks down a fatty substance is too low and that fat
builds up in cells. Parents usually have no symptoms. This note is general information,
not a diagnosis.

Type 1, the most common form, can cause an enlarged liver or spleen, anaemia, easy
bruising, bone pain, and fractures. Types 2 and 3 also affect the brain and can cause
abnormal eye movements, seizures, or developmental problems. Only a clinician can
confirm Gaucher disease with tests.

See a doctor if these features run in the family or a child has unexplained spleen
enlargement or bone crises. Seek emergency care for a seizure, sudden severe bone
pain, or unusual bleeding.""",
    ),
]

PHASE2B_NEW_IDS = tuple(row[0] for row in PHASE2B_DOCUMENTS)
