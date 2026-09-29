"""
Additional starter knowledge-base notes used to bring the sample corpus to 100.

Text is original plain-language teaching summary, not a copy of any one leaflet.
The source field names a public organisation whose guidance informed the note.
"""

# Each tuple: (id, title, source, url, condition, triage_level, body)
EXTRA_DOCUMENTS = [
    (
        "insomnia",
        "Insomnia (Trouble Sleeping)",
        "NHLBI - Insomnia",
        "https://www.nhlbi.nih.gov/health/insomnia",
        "Insomnia",
        "self_care",
        """Insomnia means trouble falling asleep, staying asleep, or waking too early and
feeling unrefreshed. Short spells are common during stress, jet lag, caffeine use,
or irregular sleep times. Daytime tiredness, irritability, and poor concentration
often follow.

Self-care includes a regular sleep schedule, limiting caffeine after midday, keeping
the bedroom dark and cool, and putting screens away before bed. Short-term use of
sleep aids should only follow advice from a pharmacist or clinician.

See a doctor if poor sleep lasts more than a few weeks, if you snore loudly and stop
breathing at night, or if low mood and daytime sleepiness affect work or safety.""",
    ),
    (
        "acne",
        "Acne",
        "NHS - Acne",
        "https://www.nhs.uk/conditions/acne/",
        "Acne",
        "self_care",
        """Acne is a common skin condition with whiteheads, blackheads, and inflamed pimples,
usually on the face, chest, or back. Hormones, oil, and blocked pores play a role.
It is not caused by poor hygiene.

Mild acne often improves with gentle cleansing twice a day and over-the-counter
benzoyl peroxide or salicylic acid products. Avoid picking, which can scar.

See a doctor or dermatologist if acne is painful, scarring, or not improving after
several weeks of careful self-care, or if it appears with sudden extra facial hair
or irregular periods.""",
    ),
    (
        "athletes_foot",
        "Athlete's Foot",
        "CDC - Athlete's Foot",
        "https://www.cdc.gov/fungal/athletes-foot/index.html",
        "Athlete's Foot",
        "self_care",
        """Athlete's foot is a fungal infection of the skin between the toes or on the soles.
It causes itching, burning, peeling, and sometimes small cracks. Warm, damp shoes
make it more likely.

Self-care includes keeping feet dry, changing socks, and using an over-the-counter
antifungal cream for the full recommended course, even after itching eases.

See a doctor if the rash spreads, you have diabetes, the skin looks infected with
pus, or over-the-counter treatment does not help after two to four weeks.""",
    ),
    (
        "canker_sore",
        "Canker Sore (Mouth Ulcer)",
        "MedlinePlus - Canker Sore",
        "https://medlineplus.gov/ency/article/000998.htm",
        "Canker Sore",
        "self_care",
        """A canker sore is a small, painful white or yellow ulcer inside the mouth, often on
the inner lip or cheek. It is not the same as a cold sore and is not caused by the
herpes virus. Stress, minor injury, or acidic foods can trigger one.

Most sores heal in one to two weeks. Salt-water rinses, avoiding spicy food, and
simple pain gels can reduce discomfort. They are not usually contagious.

See a doctor or dentist if ulcers last more than three weeks, keep returning, or you
also have fever, a rash, or trouble swallowing.""",
    ),
    (
        "motion_sickness",
        "Motion Sickness",
        "CDC - Motion Sickness",
        "https://wwwnc.cdc.gov/travel/page/motion-sickness",
        "Motion Sickness",
        "self_care",
        """Motion sickness happens when the brain gets mixed signals from the eyes and inner
ear during travel. People feel queasy, sweaty, and dizzy, and may vomit. Cars,
boats, and planes are common triggers.

Looking at the horizon, sitting where motion is least, fresh air, and small plain
snacks can help. Over-the-counter travel tablets may be useful if a pharmacist
agrees they are suitable.

See a doctor if dizziness happens when you are not travelling, lasts for days, or
comes with hearing loss, severe headache, or fainting.""",
    ),
    (
        "sunburn",
        "Sunburn",
        "CDC - Sun Safety",
        "https://www.cdc.gov/sun-safety/about/index.html",
        "Sunburn",
        "self_care",
        """Sunburn is skin damage from ultraviolet light. The skin becomes red, hot, and
painful, sometimes with blistering later. Fever and chills can occur with a large
burn. Fair skin burns faster, but any skin can burn.

Cool compresses, moisturiser, extra fluids, and staying out of the sun help mild
burns. Do not pop blisters. Pain relief such as paracetamol or ibuprofen may be
used if suitable for you.

See a doctor for large blistering, fever, confusion, or a burn in a baby. Seek
urgent care if someone becomes very drowsy after severe sun exposure.""",
    ),
    (
        "insect_bite",
        "Insect Bite or Sting",
        "CDC - Mosquito Bites",
        "https://www.cdc.gov/mosquitoes/mosquito-bites/prevent-mosquito-bites.html",
        "Insect Bite",
        "self_care",
        """Most mosquito, ant, or mild bee stings cause a small itchy or painful lump that
settles in a day or two. A local welt is common. Wash the area, use a cold pack,
and avoid scratching.

Antihistamine tablets or cream can ease itch. Remove a visible stinger by scraping,
not squeezing.

Seek emergency care for trouble breathing, swelling of the lips or tongue, dizziness,
or widespread hives after a sting, which can be anaphylaxis. See a doctor if redness
spreads quickly or pus appears.""",
    ),
    (
        "nosebleed",
        "Nosebleed (Epistaxis)",
        "NHS - Nosebleed",
        "https://www.nhs.uk/conditions/nosebleed/",
        "Nosebleed",
        "self_care",
        """A nosebleed is bleeding from the lining of the nose, often after dry air, picking,
or a mild knock. Most stop with simple first aid.

Sit up, lean slightly forward, and pinch the soft part of the nose for 10 to 15
minutes without checking early. Spit blood out rather than swallowing it. Avoid
blowing the nose for a few hours after it stops.

Seek urgent care if bleeding will not stop after 20 minutes, follows a head injury,
or you are on blood thinners and losing a lot of blood. See a doctor for frequent
unexplained nosebleeds.""",
    ),
    (
        "dry_eye",
        "Dry Eye",
        "NEI - Dry Eye",
        "https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/dry-eye",
        "Dry Eye",
        "self_care",
        """Dry eye happens when tears are too few or evaporate too fast. The eyes feel gritty,
burn, or water paradoxically. Screen use, air conditioning, contact lenses, and
some medicines make it worse.

Self-care includes blinking more during screen work, using a humidifier, and
preservative-free lubricating drops from a pharmacy.

See a doctor or optometrist if pain is severe, vision drops, the eye is very red,
or drops do not help, especially if you wear contact lenses.""",
    ),
    (
        "sprained_ankle",
        "Sprained Ankle",
        "NHS - Sprains and Strains",
        "https://www.nhs.uk/conditions/sprains-and-strains/",
        "Sprained Ankle",
        "self_care",
        """A sprained ankle is a stretch or tear of the ligaments after the foot turns in or
out. Pain, swelling, and bruising around the ankle are typical. Walking may be
possible but uncomfortable.

Rest, ice wrapped in cloth, compression, and elevation help in the first two days.
Gentle movement can start as pain allows. Most mild sprains improve over one to
three weeks.

See a doctor or urgent care if you cannot take four steps, the ankle looks deformed,
numbness develops, or swelling is extreme, because a fracture needs to be ruled out.""",
    ),
    (
        "dandruff",
        "Dandruff",
        "AAD - Dandruff",
        "https://www.aad.org/public/diseases/a-z/dandruff-overview",
        "Dandruff",
        "self_care",
        """Dandruff causes white or yellow flakes on the scalp and shoulders, often with mild
itch. It is related to oil, yeast on the skin, and sensitive scalp, not poor
cleanliness.

Medicated shampoos with zinc pyrithione, selenium sulfide, or ketoconazole used
a few times a week usually control flakes.

See a doctor if the scalp is very red, painful, or swollen, or if flakes appear
with a widespread rash, which can mean psoriasis or infection rather than simple
dandruff.""",
    ),
    (
        "hemorrhoids",
        "Hemorrhoids (Piles)",
        "NIDDK - Hemorrhoids",
        "https://www.niddk.nih.gov/health-information/digestive-diseases/hemorrhoids",
        "Hemorrhoids",
        "self_care",
        """Hemorrhoids are swollen veins in the anus or lower rectum. They can cause itching,
a lump, and bright red blood on the toilet paper. Straining, constipation, and
pregnancy make them more likely.

Self-care includes more fibre and water, not sitting too long on the toilet, warm
sitz baths, and pharmacy creams for a short time.

See a doctor if bleeding is heavy, you feel dizzy, or symptoms last more than a
week. Any new rectal bleeding should be checked so other causes are not missed.""",
    ),
    (
        "menstrual_cramps",
        "Menstrual Cramps (Dysmenorrhea)",
        "OASH - Period Problems",
        "https://womenshealth.gov/menstrual-cycle/period-problems",
        "Menstrual Cramps",
        "self_care",
        """Period cramps are aching or cramping pain in the lower abdomen before or during
a period. They can spread to the back or thighs and come with loose stools or
headache. Prostaglandins that help the uterus shed lining also cause the pain.

Heat, rest, and over-the-counter anti-inflammatory pain relief (if suitable) help
many people. Regular exercise and not missing meals can also reduce severity.

See a doctor if pain is sudden and severe, starts after years of easy periods, or
stops you from school or work, because endometriosis or other causes may need
treatment.""",
    ),
    (
        "cold_sore",
        "Cold Sore (Oral Herpes)",
        "CDC - About Genital Herpes (HSV)",
        "https://www.cdc.gov/herpes/about/index.html",
        "Cold Sore",
        "self_care",
        """A cold sore is a cluster of fluid-filled blisters on the lip caused by herpes
simplex virus. Tingling often comes first. The sores crust and heal in about
one to two weeks. Stress, sunlight, and illness can trigger recurrences.

Start an over-the-counter antiviral cream at the first tingle if you use one.
Avoid kissing or sharing cups while sores are open. Do not touch your eyes after
touching a sore.

See a doctor if sores are very frequent, appear near the eye, or you have a weak
immune system. Seek urgent care for eye pain or a new sore on the cornea.""",
    ),
    (
        "contact_dermatitis",
        "Contact Dermatitis",
        "NIAMS - Contact Dermatitis",
        "https://www.niams.nih.gov/health-topics/atopic-dermatitis",
        "Contact Dermatitis",
        "self_care",
        """Contact dermatitis is an itchy rash where the skin touched an irritant or allergen,
such as nickel, perfume, detergent, or plants like poison ivy. The area is red,
itchy, and sometimes blistered, often in the shape of the exposure.

Wash the area, avoid the trigger, and use a bland moisturiser. A short course of
mild hydrocortisone cream from a pharmacy can help if the skin is not broken.

See a doctor if the rash is on the face or genitals, covers a large area, weeps
pus, or does not improve after a week.""",
    ),
    (
        "low_back_strain",
        "Low Back Strain",
        "NINDS - Low Back Pain",
        "https://www.ninds.nih.gov/health-information/disorders/back-pain",
        "Low Back Strain",
        "self_care",
        """A low back strain is a pulled muscle or ligament after lifting, twisting, or
sitting too long. Pain is usually one-sided or across the lower back and worsens
with movement. The legs are not usually numb.

Keep gently mobile, use heat or ice, and take suitable over-the-counter pain
relief. Bed rest for many days often makes stiffness worse.

See a doctor if pain lasts more than a few weeks. Seek urgent care for back pain
with fever, loss of bladder or bowel control, saddle numbness, or weak legs.""",
    ),
    (
        "hives",
        "Hives (Urticaria)",
        "AAAAI - Hives (Urticaria)",
        "https://www.aaaai.org/conditions-treatments/allergies/hives",
        "Hives",
        "self_care",
        """Hives are raised, itchy weals that come and go on the skin, often within hours.
They can be triggered by infection, foods, medicines, or unknown causes. The
surface looks pale in the centre with a red edge.

A non-drowsy antihistamine from a pharmacy often calms ordinary hives. Avoid
known triggers. Do not scratch hard, which can worsen swelling.

Seek emergency care if hives come with swelling of the tongue or lips, wheeze,
or faintness. See a doctor if weals keep returning for more than six weeks.""",
    ),
    (
        "food_poisoning_mild",
        "Mild Food Poisoning",
        "CDC - Food Poisoning Symptoms",
        "https://www.cdc.gov/food-safety/signs-symptoms/index.html",
        "Food Poisoning",
        "self_care",
        """Mild food poisoning causes sudden nausea, vomiting, cramps, and diarrhoea a few
hours to a day after contaminated food. Fever is usually low. Most otherwise
healthy adults recover in one to three days.

Sip water or oral rehydration drinks, rest, and restart bland food when you can
keep it down. Handwashing protects others in the home.

See a doctor for blood in stool, high fever, signs of dehydration, or symptoms
lasting more than three days. Seek urgent care if vomiting is relentless or you
cannot keep any fluids down.""",
    ),
    (
        "influenza",
        "Influenza (The Flu)",
        "CDC - Flu Symptoms and Complications",
        "https://www.cdc.gov/flu/symptoms/symptoms.html",
        "Influenza",
        "consult_doctor",
        """Influenza is a viral illness that starts suddenly with fever, chills, body aches,
dry cough, sore throat, and marked tiredness. It is usually heavier than a common
cold. Headache and sometimes vomiting can occur.

Rest, fluids, and fever control help most healthy people. Antiviral medicine may
be offered early to people at higher risk, such as older adults or those with
lung or heart disease.

Consult a doctor if you are high risk or not improving after a few days. Seek
emergency care for trouble breathing, chest pain, confusion, or blue lips.""",
    ),
    (
        "strep_throat",
        "Strep Throat",
        "CDC - Strep Throat",
        "https://www.cdc.gov/group-a-strep/about/strep-throat.html",
        "Strep Throat",
        "consult_doctor",
        """Strep throat is a bacterial infection of the throat. It often causes sudden sore
throat, pain on swallowing, fever, and swollen neck glands, sometimes with white
patches on the tonsils. A cough and runny nose are less typical than with a virus.

A clinician can confirm it with a rapid test or throat swab. Antibiotics shorten
illness and reduce rare complications such as rheumatic fever.

See a doctor for a severe sore throat with fever and no cough. Seek urgent care
if you cannot swallow saliva, have a stiff neck, or breathing feels tight.""",
    ),
    (
        "tonsillitis",
        "Tonsillitis",
        "NHS - Tonsillitis",
        "https://www.nhs.uk/conditions/tonsillitis/",
        "Tonsillitis",
        "consult_doctor",
        """Tonsillitis is inflammation of the tonsils, usually from a virus and sometimes
from bacteria. The throat is sore, swallowing hurts, and the tonsils look red
and swollen. Fever and bad breath are common.

Rest, fluids, and pain relief help viral cases. Bacterial cases may need
antibiotics after a clinical review.

See a doctor if symptoms last more than four days, you cannot eat or drink, or
infections keep returning. Seek urgent care if the voice becomes muffled, the
jaw will not open, or breathing is hard.""",
    ),
    (
        "shingles",
        "Shingles (Herpes Zoster)",
        "CDC - Shingles Symptoms",
        "https://www.cdc.gov/shingles/signs-symptoms/index.html",
        "Shingles",
        "consult_doctor",
        """Shingles is a painful blistering rash on one side of the body or face, caused by
reactivation of the chickenpox virus. Burning or tingling often starts a few days
before the rash. The blisters crust over in about a week.

Early antiviral tablets from a clinician can shorten the attack and reduce later
nerve pain, especially if started within 72 hours.

See a doctor promptly when a one-sided blistering rash appears. Seek urgent care
if the rash is near the eye, you have a weak immune system, or a severe headache
and confusion develop.""",
    ),
    (
        "mononucleosis",
        "Infectious Mononucleosis (Glandular Fever)",
        "CDC - About Epstein-Barr Virus",
        "https://www.cdc.gov/epstein-barr/about/index.html",
        "Mononucleosis",
        "consult_doctor",
        """Glandular fever is often caused by Epstein-Barr virus. It brings marked tiredness,
sore throat, fever, and swollen neck glands. The spleen can enlarge, so contact
sport is unsafe until a clinician advises it is safe.

There is no specific antiviral for most people. Rest, fluids, and time are the
main treatment. Recovery can take weeks.

See a doctor to confirm the diagnosis and rule out strep throat. Seek urgent care
for difficulty breathing, severe abdominal pain (possible spleen injury), or
jaundice.""",
    ),
    (
        "gout",
        "Gout",
        "NIAMS - Gout",
        "https://www.niams.nih.gov/health-topics/gout",
        "Gout",
        "consult_doctor",
        """Gout is a sudden, very painful joint attack caused by uric acid crystals, most
often in the big toe. The joint becomes hot, red, and so tender that a bedsheet
hurts. Attacks can last days.

A clinician confirms gout and may prescribe anti-inflammatory medicine. Drinking
water and resting the joint help. Long-term uric-acid lowering tablets are used
if attacks keep returning.

See a doctor for a first hot swollen joint. Seek urgent care if you also have
high fever, which can mean septic arthritis instead of gout.""",
    ),
    (
        "osteoarthritis",
        "Osteoarthritis",
        "CDC - Osteoarthritis",
        "https://www.cdc.gov/arthritis/osteoarthritis/index.html",
        "Osteoarthritis",
        "consult_doctor",
        """Osteoarthritis is wear-and-repair change in a joint, common in knees, hips, hands,
and the spine. Pain is worse with use, stiffness eases after a few minutes of
movement, and the joint may creak or swell mildly.

Activity you can tolerate, weight management if needed, and pain relief advised
by a clinician are the main treatments. Joint replacement is only for severe
cases after other options.

See a doctor if joint pain limits walking or sleep, or a joint suddenly becomes
hot and very swollen.""",
    ),
    (
        "rheumatoid_arthritis",
        "Rheumatoid Arthritis",
        "NIAMS - Rheumatoid Arthritis",
        "https://www.niams.nih.gov/health-topics/rheumatoid-arthritis",
        "Rheumatoid Arthritis",
        "consult_doctor",
        """Rheumatoid arthritis is an autoimmune disease that inflames joints, often the
small joints of both hands and feet. Morning stiffness lasts longer than 30
minutes. Fatigue and low-grade fever can occur.

Early specialist treatment with disease-modifying medicine can protect joints.
This is not ordinary wear-and-tear arthritis.

See a doctor promptly for persistent symmetric joint swelling. Seek urgent care
for chest pain, sudden shortness of breath, or a very hot single joint with
fever.""",
    ),
    (
        "psoriasis",
        "Psoriasis",
        "NIAMS - Psoriasis",
        "https://www.niams.nih.gov/health-topics/psoriasis",
        "Psoriasis",
        "consult_doctor",
        """Psoriasis causes thick, scaly, well-defined plaques, often on the elbows, knees,
scalp, or lower back. The skin can itch or crack. Joint pain can occur in
psoriatic arthritis.

Moisturisers and prescribed topical treatments help many people. Phototherapy or
systemic medicine may be needed for wider disease.

See a doctor or dermatologist for a new scaly rash that does not clear. Seek
urgent care if most of the skin becomes red and painful (possible erythrodermic
psoriasis).""",
    ),
    (
        "ibs",
        "Irritable Bowel Syndrome (IBS)",
        "NIDDK - Irritable Bowel Syndrome",
        "https://www.niddk.nih.gov/health-information/digestive-diseases/irritable-bowel-syndrome",
        "Irritable Bowel Syndrome",
        "consult_doctor",
        """IBS causes recurrent abdominal pain with a change in bowel habit, such as
diarrhoea, constipation, or both. Bloating is common. It does not cause bleeding,
unexplained weight loss, or waking every night with pain.

A clinician diagnoses IBS after checking for other causes. Diet changes, stress
management, and medicines for the main symptom can help.

See a doctor for new bowel change lasting more than a few weeks. Seek prompt
review for blood in stool, weight loss, or a family history of bowel cancer.""",
    ),
    (
        "celiac_disease",
        "Celiac Disease",
        "NIDDK - Celiac Disease",
        "https://www.niddk.nih.gov/health-information/digestive-diseases/celiac-disease",
        "Celiac Disease",
        "consult_doctor",
        """Celiac disease is an immune reaction to gluten that damages the small bowel.
Symptoms include bloating, diarrhoea, tiredness, anaemia, and sometimes an itchy
rash. Some people have few gut symptoms.

Diagnosis needs blood tests and often a biopsy while still eating gluten. A
strict gluten-free diet, guided by a clinician and dietitian, is the treatment.

Do not start a gluten-free diet before testing if you can avoid it, because tests
can become negative. See a doctor if symptoms suggest celiac disease.""",
    ),
    (
        "peptic_ulcer",
        "Peptic Ulcer",
        "NIDDK - Peptic Ulcers",
        "https://www.niddk.nih.gov/health-information/digestive-diseases/peptic-ulcers-stomach-ulcers",
        "Peptic Ulcer",
        "consult_doctor",
        """A peptic ulcer is a sore in the stomach or first part of the small bowel, often
linked to H. pylori infection or regular anti-inflammatory tablets. Burning upper
abdominal pain may ease or worsen with food.

A clinician may test for H. pylori and prescribe acid-lowering medicine plus
antibiotics if needed. Alcohol and smoking slow healing.

See a doctor for ongoing upper abdominal burning. Seek emergency care for
vomiting blood, black stools, sudden severe abdominal pain, or fainting.""",
    ),
    (
        "hyperthyroidism",
        "Hyperthyroidism (Overactive Thyroid)",
        "Mayo Clinic - Hyperthyroidism",
        "https://www.mayoclinic.org/diseases-conditions/hyperthyroidism/symptoms-causes/syc-20373659",
        "Hyperthyroidism",
        "consult_doctor",
        """An overactive thyroid speeds body processes. People may notice weight loss despite
a good appetite, heat intolerance, tremor, palpitations, anxiety, and more
frequent bowel movements. The neck may look swollen.

Blood tests confirm the diagnosis. Treatment may include tablets, radioactive
iodine, or surgery, chosen by a specialist.

See a doctor if you have several of these symptoms. Seek urgent care for a very
fast heartbeat, high fever, and confusion, which can be a thyroid storm.""",
    ),
    (
        "copd",
        "COPD (Chronic Bronchitis or Emphysema)",
        "NHLBI - COPD",
        "https://www.nhlbi.nih.gov/health/copd",
        "COPD",
        "consult_doctor",
        """COPD is a long-term lung disease, usually after years of smoking or fume exposure.
People have a daily cough, sputum, and breathlessness that slowly worsens. Colds
can trigger dangerous flare-ups.

Inhalers, stopping smoking, vaccinations, and pulmonary rehabilitation help.
Oxygen is only used when a clinician finds low oxygen levels.

See a doctor for a long-term smoker’s cough or breathlessness. Seek emergency
care if you cannot speak in sentences, lips turn blue, or confusion appears.""",
    ),
    (
        "sleep_apnea",
        "Obstructive Sleep Apnea",
        "NHLBI - Sleep Apnea",
        "https://www.nhlbi.nih.gov/health/sleep-apnea",
        "Sleep Apnea",
        "consult_doctor",
        """Obstructive sleep apnea causes repeated pauses in breathing during sleep. Loud
snoring, witnessed gasping, morning headaches, and strong daytime sleepiness are
typical. Weight, a crowded airway, and alcohol in the evening increase risk.

A sleep study confirms it. Treatment may include a CPAP machine, positional
advice, or dental devices. Untreated apnea raises blood pressure and accident
risk.

See a doctor if you snore loudly and feel sleepy by day, especially before
driving. Seek urgent care for chest pain or fainting on waking.""",
    ),
    (
        "anxiety_disorder",
        "Generalised Anxiety",
        "NIMH - Generalized Anxiety Disorder",
        "https://www.nimh.nih.gov/health/topics/anxiety-disorders",
        "Anxiety Disorder",
        "consult_doctor",
        """Generalised anxiety is ongoing, hard-to-control worry that lasts most days for
months. People feel on edge, tire easily, have tense muscles, and sleep poorly.
Panic attacks are sudden waves of fear with a racing heart and shortness of breath.

Talking therapies and, when needed, prescribed medicine help. Breathing exercises
and reduced caffeine can support care but do not replace assessment if life is
disrupted.

See a doctor or mental health professional if worry controls your days. Seek
emergency care or a crisis line for thoughts of self-harm, or if chest pain could
be a heart problem.""",
    ),
    (
        "epilepsy",
        "Epilepsy (Seizures)",
        "CDC - Epilepsy",
        "https://www.cdc.gov/epilepsy/about/index.html",
        "Epilepsy",
        "consult_doctor",
        """Epilepsy is a tendency to have unprovoked seizures. A seizure may be a full-body
convulsion or a brief stare, lip-smacking, or odd smell. Afterward people are
often confused or sleepy.

A neurologist diagnoses epilepsy with the history, and sometimes EEG or scans.
Daily anti-seizure medicine is common. Never put something in a seizing person's
mouth.

See a doctor after any first seizure. Call emergency services if a seizure lasts
more than five minutes, repeats, or the person is injured or pregnant.""",
    ),
    (
        "vertigo",
        "Vertigo (Spinning Dizziness)",
        "NHS - Vertigo",
        "https://www.nhs.uk/conditions/vertigo/",
        "Vertigo",
        "consult_doctor",
        """Vertigo is a false sense that you or the room is spinning. Inner-ear problems such
as BPPV or vestibular neuritis are common causes. Nausea and unsteadiness come
with it. Simple light-headedness on standing is not the same.

A clinician can often diagnose BPPV and show repositioning manoeuvres. Rest and
anti-nausea medicine may be used short term.

See a doctor for a first spinning attack. Seek emergency care if vertigo comes
with sudden double vision, facial droop, slurred speech, or one-sided weakness,
which can be a stroke.""",
    ),
    (
        "sciatica",
        "Sciatica",
        "NINDS - Sciatica",
        "https://www.ninds.nih.gov/health-information/disorders/sciatica",
        "Sciatica",
        "consult_doctor",
        """Sciatica is nerve pain that shoots from the lower back into the buttock and down
one leg, often from a disc pressing the sciatic nerve. Sitting, coughing, or
bending can worsen it. Pins and needles in the foot may occur.

Most episodes improve over weeks with gentle activity, pain relief, and avoiding
heavy lifting. Bed rest for long periods is not advised.

See a doctor if pain is severe or lasts more than a few weeks. Seek urgent care
for weak legs, numbness in the saddle area, or loss of bladder or bowel control.""",
    ),
    (
        "carpal_tunnel",
        "Carpal Tunnel Syndrome",
        "NINDS - Carpal Tunnel Syndrome",
        "https://www.ninds.nih.gov/health-information/disorders/carpal-tunnel-syndrome",
        "Carpal Tunnel Syndrome",
        "consult_doctor",
        """Carpal tunnel syndrome is pressure on the median nerve at the wrist. People wake
with numb, tingling fingers, especially the thumb, index, and middle finger. The
hand may feel weak or drop objects.

Night splints, work-station changes, and short rest from repetitive strain help
mild cases. A clinician may offer a steroid injection or surgery if nerve tests
show ongoing compression.

See a doctor if night tingling persists or the thumb muscle looks wasted.""",
    ),
    (
        "osteoporosis",
        "Osteoporosis",
        "NIAMS - Osteoporosis",
        "https://www.niams.nih.gov/health-topics/osteoporosis",
        "Osteoporosis",
        "consult_doctor",
        """Osteoporosis is thinning of bone that raises fracture risk. It often has no
symptoms until a wrist, spine, or hip breaks after a minor fall. Height loss or
a stooped back can appear later.

A DEXA bone-density scan diagnoses it. Treatment includes falls prevention,
vitamin D and calcium if needed, and prescription bone-strengthening medicine
chosen by a clinician.

See a doctor after a low-impact fracture, or if you have long-term steroid use
or early menopause.""",
    ),
    (
        "hyperlipidemia",
        "High Cholesterol",
        "CDC - About High Cholesterol",
        "https://www.cdc.gov/cholesterol/about/index.html",
        "High Cholesterol",
        "consult_doctor",
        """High cholesterol usually causes no symptoms. It is found on a blood test. Over
years it contributes to heart attack and stroke risk, especially with smoking,
diabetes, or high blood pressure.

Lifestyle changes include a diet lower in saturated fat, activity, and not
smoking. Many people also need a statin prescribed by a clinician.

See a doctor for a cholesterol check from mid-adulthood, or earlier with a strong
family history of early heart disease. This cannot be judged from symptoms alone.""",
    ),
    (
        "fibromyalgia",
        "Fibromyalgia",
        "NIAMS - Fibromyalgia",
        "https://www.niams.nih.gov/health-topics/fibromyalgia",
        "Fibromyalgia",
        "consult_doctor",
        """Fibromyalgia causes widespread muscle pain, tender points, poor sleep, and
cognitive fog for months. Blood tests are often normal. It is a real pain
processing condition, not 'in the mind', though mood can worsen with it.

A clinician diagnoses it after ruling out other causes. Graded activity, sleep
routines, and some prescribed medicines can help. There is no single cure.

See a doctor for widespread pain lasting more than three months. New fever, weight
loss, or a single hot swollen joint needs a different work-up.""",
    ),
    (
        "lyme_disease",
        "Lyme Disease",
        "CDC - Lyme Disease",
        "https://www.cdc.gov/lyme/signs-symptoms/index.html",
        "Lyme Disease",
        "consult_doctor",
        """Lyme disease is a tick-borne bacterial infection. Early on, some people get a
slowly expanding circular rash (erythema migrans), fever, and aches days to weeks
after a bite in a risk area. Not every patient remembers a tick.

A clinician may treat based on the rash and later use blood tests if needed.
Antibiotics work best when started early.

See a doctor after a tick bite if a spreading rash or flu-like illness appears.
Seek urgent care for facial droop, severe headache with stiff neck, or chest
palpitations.""",
    ),
    (
        "pyelonephritis",
        "Kidney Infection (Pyelonephritis)",
        "NIDDK - Kidney Infection",
        "https://www.niddk.nih.gov/health-information/urologic-diseases/kidney-infection-pyelonephritis",
        "Kidney Infection",
        "consult_doctor",
        """A kidney infection often starts as a bladder infection then spreads. People have
fever, shaking chills, pain in the side or back, nausea, and burning or frequent
urination.

This needs prompt prescribed antibiotics and sometimes hospital fluids. Home
fluids alone are not enough once fever and flank pain are present.

See a doctor the same day for suspected kidney infection. Seek emergency care if
you are pregnant, vomiting everything, confused, or in severe pain.""",
    ),
    (
        "diverticulitis",
        "Diverticulitis",
        "NIDDK - Diverticulosis and Diverticulitis",
        "https://www.niddk.nih.gov/health-information/digestive-diseases/diverticulosis-diverticulitis",
        "Diverticulitis",
        "consult_doctor",
        """Diverticulitis is inflammation of small pouches in the colon, usually on the left
lower abdomen. Pain, fever, and a change in bowel habit are typical. It is more
common after middle age.

A clinician may use blood tests and a scan. Mild cases are treated with rest,
fluids, and sometimes antibiotics. Severe cases need hospital care.

See a doctor for new left-sided abdominal pain with fever. Seek emergency care
for rigid abdomen, vomiting, or fainting, which can mean a perforation.""",
    ),
    (
        "pcos",
        "Polycystic Ovary Syndrome (PCOS)",
        "OASH - Polycystic Ovary Syndrome",
        "https://womenshealth.gov/a-z-topics/polycystic-ovary-syndrome",
        "PCOS",
        "consult_doctor",
        """PCOS is a hormone condition that can cause irregular periods, extra facial or
body hair, acne, and weight gain around the middle. Some people have cysts on
the ovaries on ultrasound, but cysts alone do not make the diagnosis.

A clinician uses history, blood tests, and sometimes ultrasound. Treatment
targets periods, fertility, and metabolic health.

See a doctor for very irregular periods or difficulty conceiving. Seek urgent
care for sudden severe one-sided pelvic pain, which is not typical PCOS and may
be a cyst accident or torsion.""",
    ),
    (
        "endometriosis",
        "Endometriosis",
        "OASH - Endometriosis",
        "https://womenshealth.gov/a-z-topics/endometriosis",
        "Endometriosis",
        "consult_doctor",
        """Endometriosis is tissue like the womb lining growing outside the uterus. It can
cause very painful periods, pain during sex, pain with bowel movements, and
trouble conceiving. Pain may start before bleeding.

Pain relief and hormonal treatments from a clinician help many people. Surgery
is sometimes used. It cannot be confirmed from symptoms alone.

See a doctor if period pain is not controlled by simple pain relief. Seek urgent
care for sudden severe pelvic pain with fainting.""",
    ),
    (
        "bph",
        "Enlarged Prostate (BPH)",
        "NIDDK - Prostate Enlargement (BPH)",
        "https://www.niddk.nih.gov/health-information/urologic-diseases/prostate-problems/prostate-enlargement-benign-prostatic-hyperplasia",
        "Benign Prostatic Hyperplasia",
        "consult_doctor",
        """An enlarged prostate is common with ageing. It can slow the urine stream, cause
hesitancy, dribbling, and night-time trips to the toilet. It is not cancer, but
cancer can coexist, so checks matter.

A clinician may examine the prostate and do a urine and blood test. Tablets or
procedures can improve flow.

See a doctor for ongoing urinary obstruction. Seek emergency care if you suddenly
cannot pass urine, which is acute retention.""",
    ),
    (
        "glaucoma",
        "Glaucoma",
        "NEI - Glaucoma",
        "https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/glaucoma",
        "Glaucoma",
        "consult_doctor",
        """Open-angle glaucoma slowly damages the optic nerve, often with no early pain.
Side vision is lost first. People may not notice until a lot of vision is gone.
Raised eye pressure is a major risk.

Regular eye tests detect it. Daily pressure-lowering drops prescribed by an eye
specialist can protect remaining vision.

Book an eye exam, especially after age 40 or with a family history. Sudden severe
eye pain, headache, and a steamy cornea is acute angle-closure and needs emergency
care the same hour.""",
    ),
    (
        "dental_abscess",
        "Dental Abscess",
        "NHS - Dental Abscess",
        "https://www.nhs.uk/conditions/dental-abscess/",
        "Dental Abscess",
        "consult_doctor",
        """A dental abscess is a pocket of pus from a tooth or gum infection. The tooth
throbs, chewing hurts, and the face or gum may swell. A bad taste and fever can
occur.

This needs a dentist. Antibiotics alone do not fix the source. Pain relief and
avoiding very hot or cold food can help until you are seen.

See a dentist the same day. Seek emergency care if swelling spreads to the eye
or neck, you cannot swallow, or breathing feels tight.""",
    ),
    (
        "hepatitis_a",
        "Hepatitis A",
        "CDC - Hepatitis A",
        "https://www.cdc.gov/hepatitis-a/about/index.html",
        "Hepatitis A",
        "consult_doctor",
        """Hepatitis A is a viral liver infection spread by contaminated food or close
contact. It causes tiredness, nausea, fever, dark urine, pale stools, and yellow
skin or eyes after a few weeks.

Most people recover fully with rest and fluids. There is no specific everyday
antiviral. Vaccination prevents it. Alcohol should be avoided until a clinician
says the liver has recovered.

See a doctor for jaundice after travel or known exposure. Seek urgent care for
confusion, severe vomiting, or bleeding, which can mean acute liver failure.""",
    ),
    (
        "deep_vein_thrombosis",
        "Deep Vein Thrombosis (DVT)",
        "CDC - About Venous Thromboembolism",
        "https://www.cdc.gov/blood-clots/about/index.html",
        "Deep Vein Thrombosis",
        "emergency",
        """A DVT is a blood clot in a deep vein, usually the calf or thigh. The leg becomes
swollen, warm, and painful, often after surgery, a long flight, or when mobility
is low. The skin may look red or bluish.

A clot can break off and travel to the lung as a pulmonary embolism. Do not
massage the leg or wait to see if swelling 'settles' overnight.

Seek urgent in-person care the same day for a suddenly swollen painful leg.
Call emergency services if you also become short of breath or have chest pain.""",
    ),
    (
        "diabetic_ketoacidosis",
        "Diabetic Ketoacidosis (DKA)",
        "CDC - Diabetic Ketoacidosis",
        "https://www.cdc.gov/diabetes/about/diabetic-ketoacidosis.html",
        "Diabetic Ketoacidosis",
        "emergency",
        """DKA is a life-threatening diabetes emergency, more common in type 1 diabetes.
Warning signs include very high thirst and urination, vomiting, abdominal pain,
deep rapid breathing, fruity-smelling breath, and confusion.

It needs hospital fluids and insulin. Home sugar drinks or extra tablets are not
enough. People with diabetes should follow their sick-day plan and seek help
early.

Call emergency services for suspected DKA. Do not drive yourself if you feel
drowsy or are vomiting.""",
    ),
    (
        "hypoglycemia",
        "Severe Low Blood Sugar (Hypoglycemia)",
        "CDC - Low Blood Sugar (Hypoglycemia)",
        "https://www.cdc.gov/diabetes/treatment-insulin/low-blood-sugar.html",
        "Hypoglycemia",
        "emergency",
        """Low blood sugar can happen in people treated with insulin or some diabetes
tablets. Early signs are shakiness, sweating, hunger, and a fast heartbeat.
Severe lows cause confusion, seizures, or unconsciousness.

If the person is awake, fast-acting carbohydrate such as glucose tablets or juice
is used, then a snack. Never force drinks into an unconscious person.

Call emergency services if the person cannot swallow, has a seizure, or does not
improve after treatment. Glucagon may be used if prescribed and available.""",
    ),
    (
        "ectopic_pregnancy",
        "Ectopic Pregnancy",
        "ACOG - Ectopic Pregnancy",
        "https://www.acog.org/womens-health/faqs/ectopic-pregnancy",
        "Ectopic Pregnancy",
        "emergency",
        """An ectopic pregnancy grows outside the womb, often in a fallopian tube. It can
cause one-sided pelvic pain, spotting, shoulder-tip pain, and dizziness in early
pregnancy, including before a person is sure they are pregnant.

A ruptured ectopic pregnancy is life-threatening internal bleeding. A scan and
blood tests in hospital are needed. It cannot be managed safely at home.

Seek emergency care for pregnancy (or a missed period) with severe pelvic pain,
fainting, or heavy bleeding.""",
    ),
    (
        "testicular_torsion",
        "Testicular Torsion",
        "NHS - Testicular Torsion",
        "https://www.nhs.uk/conditions/testicular-lumps-and-swellings/",
        "Testicular Torsion",
        "emergency",
        """Testicular torsion is twisting of the spermatic cord that cuts off blood flow to
a testis. It causes sudden, severe one-sided scrotal pain, often with nausea, in
teenagers and young men. The testis may sit higher than usual.

This is a surgical emergency. Hours matter for saving the testis. Pain that
started suddenly should not be treated as a simple infection overnight.

Go to an emergency department immediately for sudden testicular pain. Do not wait
for a routine clinic appointment.""",
    ),
    (
        "pneumothorax",
        "Collapsed Lung (Pneumothorax)",
        "NHS - Pneumothorax",
        "https://www.nhs.uk/conditions/pneumothorax/",
        "Pneumothorax",
        "emergency",
        """A pneumothorax is air leaking into the space around a lung so it cannot expand.
People feel sudden one-sided chest pain and shortness of breath, sometimes after
a tall thin young person coughs, or after chest injury.

A large or tension pneumothorax can be rapidly fatal. Hospital X-ray and, if
needed, a chest drain are the treatments.

Call emergency services for sudden chest pain with breathlessness. Do not fly or
ignore worsening pain.""",
    ),
    (
        "carbon_monoxide_poisoning",
        "Carbon Monoxide Poisoning",
        "CDC - Carbon Monoxide Poisoning",
        "https://www.cdc.gov/carbon-monoxide/about/index.html",
        "Carbon Monoxide Poisoning",
        "emergency",
        """Carbon monoxide is a colourless gas from faulty heaters, engines, or blocked
flues. Several people in the same building may get headache, nausea, dizziness,
and confusion at the same time. Cherry-red skin is not reliable.

Get into fresh air at once and call emergency services. Do not re-enter the
building. Hospital oxygen is the treatment.

Treat any suspected CO exposure as an emergency, especially if someone is drowsy
or has lost consciousness.""",
    ),
    (
        "severe_burn",
        "Severe Burn",
        "CDC - Burn Prevention",
        "https://www.cdc.gov/burn-prevention/about/index.html",
        "Severe Burn",
        "emergency",
        """A severe burn is deep, large, on the face, hands, feet, or genitals, or caused by
chemicals or electricity. The skin may be white, charred, or painless if nerves
are destroyed. Blisters over a wide area also need urgent care.

Cool the burn with running cool (not ice-cold) water for 20 minutes, cover with
cling film or a clean cloth, and do not apply butter or toothpaste.

Call emergency services for large, deep, or airway burns, or burns with smoke
inhalation. Watch for shock.""",
    ),
    (
        "concussion",
        "Concussion (Mild Traumatic Brain Injury)",
        "CDC - About Concussion",
        "https://www.cdc.gov/heads-up/about/index.html",
        "Concussion",
        "emergency",
        """A concussion is a brain injury from a blow or jolt to the head. People may feel
dazed, have headache, nausea, dizziness, or memory of the event that is patchy.
Loss of consciousness is not required.

Rest from sport the same day. A clinician should assess any suspected concussion.
Worsening symptoms after a head injury are a red flag.

Seek emergency care for a head injury with repeated vomiting, worsening headache,
unequal pupils, seizures, clear fluid from the ear or nose, or increasing
confusion.""",
    ),
    (
        "acute_pancreatitis",
        "Acute Pancreatitis",
        "NIDDK - Pancreatitis",
        "https://www.niddk.nih.gov/health-information/digestive-diseases/pancreatitis",
        "Acute Pancreatitis",
        "emergency",
        """Acute pancreatitis is sudden inflammation of the pancreas, often linked to
gallstones or heavy alcohol use. Pain is severe in the upper abdomen and may go
through to the back. Vomiting and a tender abdomen are common.

This needs hospital fluids and monitoring. Eating and drinking are often paused
at first. It can become life-threatening.

Go to emergency care for sudden severe upper abdominal pain with vomiting,
especially after a fatty meal or heavy drinking.""",
    ),
]
