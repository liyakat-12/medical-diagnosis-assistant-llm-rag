"""
One-time generator for the STARTER sample knowledge base.

IMPORTANT: The text in DOCUMENTS below is written in plain language for
demonstration purposes only. It is general medical knowledge (the kind
found in any patient-education leaflet) written by the project author,
NOT a verbatim copy of any single source. The "source" field names the
organization whose public guidance informed the summary, so every chunk
retrieved at query time can show a real, checkable citation.

For a real submission, replace/extend these files with verified excerpts
from actual guideline documents (WHO, CDC, NICE, Mayo Clinic, MedlinePlus,
PubMed review articles, etc.) using the same front-matter format, or use
scripts/ingest_pdf.py to pull in full PDF guideline documents.
"""
from __future__ import annotations

from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "sample_documents"

# Each tuple: (id, title, source, url, condition, triage_level, body)
# triage_level in {"self_care", "consult_doctor", "emergency"}
DOCUMENTS = [
    (
        "common_cold",
        "Common Cold",
        "CDC - Common Colds: Protect Yourself and Others",
        "https://www.cdc.gov/antibiotic-use/colds.html",
        "Common Cold",
        "self_care",
        """The common cold is a mild viral infection of the nose and throat caused mainly by
rhinoviruses. Typical symptoms include a runny or stuffy nose, sneezing, sore throat,
mild cough, low energy, and occasionally a mild fever. Symptoms usually build up over
one to three days and resolve on their own within seven to ten days.

Self-care measures include rest, drinking plenty of fluids, using saline nasal sprays,
and taking over-the-counter pain relievers such as paracetamol or ibuprofen for
discomfort. Antibiotics do not work against colds because they are caused by viruses,
not bacteria.

See a doctor if symptoms last longer than ten days, if fever is high (above 39C/102F),
or if symptoms are unusually severe, since this may indicate a secondary infection such
as sinusitis or bronchitis rather than a simple cold.""",
    ),
    (
        "seasonal_allergies",
        "Seasonal Allergies (Allergic Rhinitis)",
        "Mayo Clinic - Hay fever (allergic rhinitis)",
        "https://www.mayoclinic.org/diseases-conditions/hay-fever/symptoms-causes/syc-20373039",
        "Allergic Rhinitis",
        "self_care",
        """Allergic rhinitis, commonly called hay fever, is triggered by airborne allergens such
as pollen, dust mites, or pet dander. Symptoms include sneezing, itchy or watery eyes,
nasal congestion, and an itchy throat. Unlike a cold, allergic rhinitis does not cause
fever and often follows a predictable seasonal pattern.

Self-care includes avoiding known triggers, using over-the-counter antihistamines, and
nasal saline rinses. Symptoms typically improve quickly once the allergen exposure
stops or with antihistamine use.

Consult a doctor if over-the-counter antihistamines do not control symptoms, if
symptoms significantly affect sleep or daily activities, or if you develop wheezing or
shortness of breath, which may indicate allergic asthma.""",
    ),
    (
        "tension_headache",
        "Mild Tension Headache",
        "MedlinePlus - Tension Headache",
        "https://medlineplus.gov/ency/article/000797.htm",
        "Tension Headache",
        "self_care",
        """Tension headaches are the most common type of headache, often described as a dull,
band-like pressure around the head. They are usually triggered by stress, poor
posture, eye strain, or dehydration and are not associated with vomiting, visual
disturbances, or neurological symptoms.

Self-care includes rest, hydration, over-the-counter pain relievers such as
paracetamol or ibuprofen, and stress reduction techniques. Most tension headaches
resolve within a few hours to a day.

Consult a doctor if headaches become frequent (more than twice a week), progressively
worsen, or are accompanied by neck stiffness, visual changes, or fever, as these can
signal a different underlying cause.""",
    ),
    (
        "muscle_strain",
        "Minor Muscle Strain",
        "NHS - Muscle strains",
        "https://www.nhs.uk/conditions/sprains-and-strains/",
        "Muscle Strain",
        "self_care",
        """A minor muscle strain occurs when muscle fibers are overstretched or slightly torn,
commonly from exercise, lifting, or sudden movement. Symptoms include localized pain,
mild swelling, and stiffness that worsens with movement of the affected area.

Self-care follows the R.I.C.E. approach: rest, ice, compression, and elevation, along
with over-the-counter anti-inflammatory medication. Most minor strains improve within
a few days to two weeks.

Consult a doctor if you cannot bear weight or move the limb at all, if swelling and
bruising are severe, or if pain does not improve after a week of self-care, as this may
indicate a more serious tear or fracture.""",
    ),
    (
        "mild_gastroenteritis",
        "Mild Gastroenteritis (Upset Stomach)",
        "CDC - Norovirus: Symptoms and Care",
        "https://www.cdc.gov/norovirus/about/symptoms.html",
        "Gastroenteritis",
        "self_care",
        """Mild gastroenteritis, often called stomach flu, causes nausea, vomiting, watery
diarrhea, and mild abdominal cramping, usually from a viral infection or food-related
irritation. Symptoms typically last one to three days.

Self-care includes staying hydrated with water or oral rehydration solutions, eating
bland foods as tolerated, and resting. Avoid dairy and greasy foods until symptoms
settle.

Consult a doctor if you notice blood in vomit or stool, signs of dehydration (very dark
urine, dizziness, dry mouth), high fever, or if symptoms last more than three days,
especially in young children or older adults.""",
    ),
    (
        "migraine",
        "Migraine",
        "Mayo Clinic - Migraine",
        "https://www.mayoclinic.org/diseases-conditions/migraine-headache/symptoms-causes/syc-20360201",
        "Migraine",
        "consult_doctor",
        """Migraine is a neurological condition causing recurring, often one-sided, throbbing
headaches that can last from hours to several days. It is frequently accompanied by
nausea, vomiting, and heightened sensitivity to light and sound. Some people experience
an "aura" of visual disturbances before the headache begins.

Migraines are usually managed with rest in a dark quiet room, prescribed or
over-the-counter migraine-specific medication, and identifying/avoiding personal
triggers such as certain foods, stress, or sleep disruption.

Consult a doctor to confirm the diagnosis and discuss preventive treatment if migraines
occur frequently (more than four times a month) or significantly disrupt daily life. A
first-ever severe headache, or one with fever, neck stiffness, confusion, or weakness,
needs urgent evaluation rather than routine migraine care.""",
    ),
    (
        "urinary_tract_infection",
        "Urinary Tract Infection (UTI)",
        "CDC - Urinary Tract Infection",
        "https://www.cdc.gov/antibiotic-use/uti.html",
        "Urinary Tract Infection",
        "consult_doctor",
        """A urinary tract infection is a bacterial infection anywhere along the urinary
system, most often the bladder. Typical symptoms include a burning sensation during
urination, frequent and urgent need to urinate, cloudy or strong-smelling urine, and
mild lower abdominal discomfort.

UTIs generally require a course of antibiotics prescribed by a clinician after
confirming the diagnosis, typically with a urine test. Drinking extra water can help
but does not replace antibiotic treatment for a confirmed infection.

Consult a doctor promptly for antibiotic treatment. Seek urgent care if you develop
fever, chills, nausea, or back/flank pain, which may indicate the infection has spread
to the kidneys (pyelonephritis) and needs prompt treatment.""",
    ),
    (
        "type2_diabetes",
        "Type 2 Diabetes (Early Symptoms)",
        "CDC - Diabetes Symptoms",
        "https://www.cdc.gov/diabetes/basics/symptoms.html",
        "Type 2 Diabetes",
        "consult_doctor",
        """Type 2 diabetes develops when the body becomes resistant to insulin or does not
produce enough of it, leading to elevated blood sugar. Early symptoms are often subtle
and include increased thirst, frequent urination, unexplained fatigue, blurred vision,
slow-healing sores, and unintended weight loss.

Because these symptoms can develop gradually, many people are diagnosed through
routine blood tests before symptoms become severe. Diagnosis requires blood glucose or
HbA1c testing performed by a healthcare provider; it cannot be confirmed from symptoms
alone.

Consult a doctor for blood sugar testing if you notice these symptoms, particularly if
you have risk factors such as obesity, family history, or age over 45. Seek urgent care
for very high thirst/urination with confusion, rapid breathing, or fruity-smelling
breath, which can indicate a diabetic emergency.""",
    ),
    (
        "hypertension",
        "Hypertension (High Blood Pressure)",
        "WHO - Hypertension Fact Sheet",
        "https://www.who.int/news-room/fact-sheets/detail/hypertension",
        "Hypertension",
        "consult_doctor",
        """Hypertension, or high blood pressure, is often called a "silent" condition because
it usually causes no obvious symptoms until it is severe or has caused organ damage.
Occasionally people report headaches, shortness of breath, or nosebleeds, but these are
not reliable indicators on their own.

Hypertension is diagnosed through repeated blood pressure measurements, not symptoms.
Management includes lifestyle changes (reduced salt intake, regular exercise, limiting
alcohol) and, frequently, prescribed medication.

Consult a doctor for a formal diagnosis and treatment plan if home blood pressure
readings are consistently at or above 140/90 mmHg. Seek emergency care immediately if
blood pressure exceeds 180/120 mmHg together with symptoms like chest pain, severe
headache, shortness of breath, or vision changes (a hypertensive crisis).""",
    ),
    (
        "asthma_mild",
        "Asthma (Mild-to-Moderate)",
        "NHLBI - Asthma Symptoms",
        "https://www.nhlbi.nih.gov/health/asthma/symptoms",
        "Asthma",
        "consult_doctor",
        """Asthma is a chronic condition in which the airways narrow and swell, causing
wheezing, shortness of breath, chest tightness, and coughing, especially at night or
during exercise. Symptoms can range from mild and intermittent to severe.

Mild, well-controlled asthma is typically managed with a prescribed reliever inhaler
(such as albuterol) used as needed, along with avoiding known triggers like smoke,
allergens, or cold air.

Consult a doctor to obtain a proper diagnosis and inhaler prescription if you have
recurring wheeze, cough, or breathlessness. Seek emergency care immediately if the
reliever inhaler does not ease symptoms, if you are too breathless to speak or walk, or
if lips/fingertips turn bluish, as this indicates a severe asthma attack.""",
    ),
    (
        "gerd",
        "Gastroesophageal Reflux Disease (GERD)",
        "Mayo Clinic - GERD",
        "https://www.mayoclinic.org/diseases-conditions/gerd/symptoms-causes/syc-20361940",
        "GERD",
        "consult_doctor",
        """GERD occurs when stomach acid frequently flows back into the esophagus, causing a
burning sensation in the chest (heartburn), regurgitation of food or sour liquid, and
sometimes difficulty swallowing. Symptoms often worsen after eating or when lying down.

Occasional heartburn can be managed with over-the-counter antacids and lifestyle
changes such as smaller meals, avoiding trigger foods, and not lying down right after
eating.

Consult a doctor if heartburn occurs more than twice a week, disrupts sleep, or does not
respond to over-the-counter antacids, since long-term GERD can damage the esophagus.
Seek urgent care if chest pain is severe, crushing, or accompanied by shortness of
breath or arm/jaw pain, since this can mimic a heart attack and must be ruled out.""",
    ),
    (
        "depression",
        "Depression (Major Depressive Disorder)",
        "WHO - Depression Fact Sheet",
        "https://www.who.int/news-room/fact-sheets/detail/depression",
        "Depression",
        "consult_doctor",
        """Depression is a common mental health condition marked by persistent low mood, loss
of interest in previously enjoyable activities, changes in sleep or appetite, low
energy, difficulty concentrating, and feelings of worthlessness, lasting most of the
day for two weeks or more.

Depression is treatable with psychotherapy, medication, or a combination, tailored by
a mental health professional. It is not something that resolves through willpower
alone, and self-care alone is usually not sufficient.

Consult a doctor or mental health professional for an evaluation if these symptoms
persist for two weeks or more. Seek emergency care immediately, or contact a crisis
line, if there are thoughts of self-harm or suicide.""",
    ),
    (
        "anemia",
        "Iron Deficiency Anemia",
        "Mayo Clinic - Iron deficiency anemia",
        "https://www.mayoclinic.org/diseases-conditions/iron-deficiency-anemia/symptoms-causes/syc-20355034",
        "Anemia",
        "consult_doctor",
        """Iron deficiency anemia occurs when the body lacks enough iron to produce healthy red
blood cells. Common symptoms include persistent fatigue, pale skin, shortness of
breath on exertion, dizziness, brittle nails, and unusual cravings for non-food items
such as ice (pica).

Diagnosis requires a blood test, and treatment usually involves iron supplements and
addressing the underlying cause (such as diet or blood loss), guided by a doctor.

Consult a doctor if you experience persistent fatigue and pallor, especially alongside
heavy menstrual periods or a diet low in iron-rich foods. Seek urgent care for chest
pain, fainting, or a very fast heartbeat alongside these symptoms.""",
    ),
    (
        "cellulitis_mild",
        "Mild Skin Infection (Cellulitis)",
        "CDC - Cellulitis: All You Need to Know",
        "https://www.cdc.gov/groupastrep/diseases-hcp/cellulitis.html",
        "Cellulitis",
        "consult_doctor",
        """Cellulitis is a bacterial skin infection that causes redness, warmth, swelling, and
tenderness, usually on the legs or arms, often starting from a small cut or insect
bite. The affected skin may look stretched or glossy.

Cellulitis needs a course of prescribed antibiotics to prevent it from spreading; it
does not typically resolve with self-care alone.

Consult a doctor promptly for antibiotic treatment when you notice spreading redness
and warmth. Seek emergency care if the redness spreads rapidly, if you develop high
fever, chills, or confusion, or if the area becomes intensely painful, as this may
indicate a deeper, more dangerous infection.""",
    ),
    (
        "heart_attack",
        "Heart Attack (Myocardial Infarction)",
        "American Heart Association - Warning Signs of a Heart Attack",
        "https://www.heart.org/en/health-topics/heart-attack/warning-signs-of-a-heart-attack",
        "Heart Attack",
        "emergency",
        """A heart attack occurs when blood flow to part of the heart is blocked, damaging
heart muscle. Warning signs include chest pain or pressure (often described as
squeezing or fullness), pain spreading to the arm, jaw, neck, or back, shortness of
breath, cold sweat, nausea, and lightheadedness. Symptoms can be less typical in women,
presenting as fatigue or nausea without prominent chest pain.

This is a medical emergency. Call emergency services immediately; do not attempt to
drive yourself. Chew an aspirin if available and not allergic, and remain calm and
seated while waiting for help. Every minute of delay increases the risk of permanent
heart damage.""",
    ),
    (
        "stroke",
        "Stroke",
        "CDC - Stroke Signs and Symptoms (F.A.S.T.)",
        "https://www.cdc.gov/stroke/signs_symptoms.htm",
        "Stroke",
        "emergency",
        """A stroke occurs when blood supply to part of the brain is interrupted. Use the
F.A.S.T. test: Face drooping on one side, Arm weakness or drift when raised, Speech
that is slurred or hard to understand, and Time to call emergency services
immediately if any of these signs appear. Other symptoms include sudden confusion,
trouble seeing in one or both eyes, sudden severe headache, or loss of balance.

This is a medical emergency. Call emergency services immediately and note the time
symptoms started, as clot-dissolving treatment is most effective within a few hours of
onset. Do not give the person food, drink, or medication while waiting for help.""",
    ),
    (
        "appendicitis",
        "Appendicitis",
        "Mayo Clinic - Appendicitis",
        "https://www.mayoclinic.org/diseases-conditions/appendicitis/symptoms-causes/syc-20369543",
        "Appendicitis",
        "emergency",
        """Appendicitis is inflammation of the appendix that typically starts as dull pain
near the navel and migrates to sharp pain in the lower right abdomen over several
hours. It is often accompanied by nausea, vomiting, low-grade fever, loss of appetite,
and pain that worsens with movement, coughing, or pressing on the abdomen.

This condition can progress to a ruptured appendix within 24 to 72 hours if untreated,
which is life-threatening. Seek emergency care immediately for evaluation; treatment
usually requires surgical removal of the appendix. Do not eat, drink, or take
laxatives/pain medication that could mask symptoms before being seen.""",
    ),
    (
        "anaphylaxis",
        "Anaphylaxis (Severe Allergic Reaction)",
        "American College of Allergy, Asthma & Immunology - Anaphylaxis",
        "https://acaai.org/allergies/allergic-conditions/anaphylaxis/",
        "Anaphylaxis",
        "emergency",
        """Anaphylaxis is a severe, rapid-onset allergic reaction that can be triggered by
foods, insect stings, medications, or latex. Symptoms include sudden difficulty
breathing or wheezing, swelling of the lips/tongue/throat, widespread hives or itching,
a drop in blood pressure causing dizziness or fainting, and a feeling of impending
doom.

This is a medical emergency that can be fatal within minutes. If an epinephrine
auto-injector (EpiPen) is available, use it immediately and call emergency services
right away, even if symptoms initially improve, since a second wave of symptoms can
occur. Lay the person flat and elevate their legs unless breathing is difficult.""",
    ),
    (
        "sepsis",
        "Sepsis",
        "CDC - What is Sepsis?",
        "https://www.cdc.gov/sepsis/what-is-sepsis.html",
        "Sepsis",
        "emergency",
        """Sepsis is the body's extreme, life-threatening response to an infection, which can
lead to tissue damage, organ failure, and death if not treated immediately. Warning
signs include high fever or feeling very cold with shivering, fast heart rate, fast
breathing, confusion or disorientation, extreme pain or discomfort, clammy or sweaty
skin, and low urine output.

This is a medical emergency, especially in people who are already unwell, elderly,
very young, or immunocompromised. Seek emergency care immediately. Sepsis requires
urgent hospital treatment with antibiotics and fluids; it cannot be safely managed at
home.""",
    ),
    (
        "mental_health_crisis",
        "Suicidal Ideation / Mental Health Crisis",
        "988 Suicide & Crisis Lifeline - Help Someone Else",
        "https://988lifeline.org/help-someone-else/",
        "Mental Health Crisis",
        "emergency",
        """A mental health crisis involving thoughts of suicide or self-harm, or a plan or
intent to act on such thoughts, is a medical emergency. Warning signs include talking
about wanting to die, feeling hopeless or trapped, withdrawing from others, giving away
possessions, or a sudden sense of calm after a period of depression.

This requires immediate action. Call a crisis line (such as 988 in the United States,
or your local emergency number) or go to the nearest emergency department right away.
Do not leave the person alone, and remove access to means of self-harm if it is safe to
do so while waiting for professional help.""",
    ),
    (
        "tuberculosis",
        "Tuberculosis (TB)",
        "CDC - Tuberculosis Symptoms",
        "https://www.cdc.gov/tb/signs-symptoms/index.html",
        "Tuberculosis",
        "consult_doctor",
        """Tuberculosis is a bacterial infection that most often affects the lungs. Typical
symptoms include a cough lasting three weeks or more, coughing up blood or sputum,
chest pain, night sweats, unexplained weight loss, fever, and tiredness. It spreads
through the air when a person with active lung TB coughs or speaks.

TB is not a simple cold. A clinician needs to confirm it with tests such as a chest
X-ray and sputum samples, then prescribe a full course of combination antibiotics.
Stopping treatment early can make the infection harder to treat.

See a doctor promptly if a cough lasts more than three weeks, especially with night
sweats or weight loss. Seek emergency care for severe breathing difficulty or coughing
up large amounts of blood.""",
    ),
    (
        "dengue_fever",
        "Dengue Fever",
        "CDC - Dengue Symptoms",
        "https://www.cdc.gov/dengue/symptoms/index.html",
        "Dengue Fever",
        "consult_doctor",
        """Dengue is a mosquito-borne viral illness. Common symptoms start suddenly and include
high fever, severe headache, pain behind the eyes, muscle and joint pain, nausea, and
sometimes a rash. Most people recover with rest and fluids, but a smaller group can
progress to severe dengue with bleeding, persistent vomiting, or shock.

There is no specific antiviral for dengue. Avoid aspirin and ibuprofen because they
can increase bleeding risk; paracetamol is usually preferred for fever after a
clinician advises it. Prevention focuses on mosquito bites.

Consult a doctor if you have high fever after travel to, or living in, a dengue area.
Seek emergency care for severe abdominal pain, persistent vomiting, bleeding gums,
or feeling faint.""",
    ),
    (
        "malaria",
        "Malaria",
        "WHO - Malaria Fact Sheet",
        "https://www.who.int/news-room/fact-sheets/detail/malaria",
        "Malaria",
        "consult_doctor",
        """Malaria is a parasite infection spread by Anopheles mosquitoes. Symptoms often include
fever that comes in waves, chills, sweating, headache, muscle aches, and tiredness.
They usually start 10 to 15 days after a bite, but can appear later.

Malaria can become life-threatening, especially falciparum malaria, if treatment is
delayed. Diagnosis needs a blood test. Treatment is prescription antimalarial medicine
chosen by a clinician based on the parasite type and local resistance.

See a doctor urgently for fever after travel to a malaria region, even if you took
prevention tablets. Seek emergency care for confusion, seizures, difficulty breathing,
or jaundice.""",
    ),
    (
        "covid_19",
        "COVID-19",
        "CDC - COVID-19 Symptoms",
        "https://www.cdc.gov/covid/signs-symptoms/index.html",
        "COVID-19",
        "consult_doctor",
        """COVID-19 is a viral respiratory illness. Symptoms range from a mild cold-like illness
to severe pneumonia. Common features include fever, cough, sore throat, runny nose,
fatigue, body aches, loss of smell or taste, and shortness of breath.

Many otherwise healthy people recover with rest, fluids, and isolation to protect
others. People at higher risk, including older adults and those with heart, lung, or
immune conditions, may need antiviral treatment started early.

Consult a doctor if you are at higher risk or symptoms are not improving. Seek
emergency care for trouble breathing, persistent chest pain, new confusion, or lips
or face turning blue.""",
    ),
    (
        "pneumonia",
        "Pneumonia",
        "CDC - Pneumonia Symptoms",
        "https://www.cdc.gov/pneumonia/signs-symptoms.html",
        "Pneumonia",
        "consult_doctor",
        """Pneumonia is an infection of the lung tissue, often causing cough with mucus, fever,
chills, shortness of breath, and chest pain that worsens when you breathe in. It can
follow a cold or flu, especially in older adults, young children, or people with
chronic illness.

A clinician may use a chest exam, oxygen check, and sometimes a chest X-ray.
Antibiotics help if bacteria are the cause; viral pneumonia is managed supportively.

See a doctor promptly for suspected pneumonia. Seek emergency care if you struggle to
breathe, have blue lips, a very high fever, or become confused.""",
    ),
    (
        "acute_bronchitis",
        "Acute Bronchitis",
        "Mayo Clinic - Bronchitis",
        "https://www.mayoclinic.org/diseases-conditions/bronchitis/symptoms-causes/syc-20355566",
        "Acute Bronchitis",
        "consult_doctor",
        """Acute bronchitis is inflammation of the large airways, usually after a viral cold.
The main symptom is a cough that can last two to three weeks, sometimes with mucus,
wheezing, and mild chest discomfort. Fever is usually low or absent.

Most cases improve with rest, fluids, and steam or a humidifier. Antibiotics are
rarely needed because viruses cause most acute bronchitis.

Consult a doctor if the cough lasts more than three weeks, you cough up blood, you
have a high fever, or you have known asthma or COPD and symptoms worsen.""",
    ),
    (
        "chickenpox",
        "Chickenpox (Varicella)",
        "CDC - Chickenpox Symptoms",
        "https://www.cdc.gov/chickenpox/signs-symptoms/index.html",
        "Chickenpox",
        "self_care",
        """Chickenpox causes an itchy blister-like rash that appears in waves, often with fever
and tiredness. Spots start on the chest, back, and face, then spread. It is very
contagious until all blisters have crusted.

In healthy children, care is usually rest, fluids, and itch relief. Do not give
aspirin to children because of Reye syndrome risk. Adults, pregnant people, and those
with weak immune systems are more likely to have complications.

Stay home until lesions crust. See a doctor if you are pregnant, immunocompromised,
or develop breathing trouble, a stiff neck, or a rash that looks infected.""",
    ),
    (
        "measles",
        "Measles",
        "CDC - Measles Symptoms",
        "https://www.cdc.gov/measles/symptoms/index.html",
        "Measles",
        "consult_doctor",
        """Measles is a highly contagious viral illness. It usually starts with high fever,
cough, runny nose, and red eyes, followed by a blotchy rash that starts on the face
and spreads down the body. Tiny white spots may appear inside the mouth.

There is no specific antiviral for most people; care is supportive. Measles can cause
pneumonia, ear infections, and brain inflammation. Vaccination is the main protection.

Call a doctor before visiting a clinic if you suspect measles, so they can prevent
spread. Seek urgent care for trouble breathing, dehydration, or unusual sleepiness.""",
    ),
    (
        "kidney_stones",
        "Kidney Stones",
        "NIDDK - Kidney Stones",
        "https://www.niddk.nih.gov/health-information/urologic-diseases/kidney-stones",
        "Kidney Stones",
        "consult_doctor",
        """Kidney stones are hard mineral deposits that can cause sudden, severe pain in the
side or back, often radiating to the lower abdomen or groin. Other signs include
blood in the urine, nausea, and a need to urinate often. Pain may come in waves.

Small stones may pass with extra fluids and pain control advised by a clinician.
Larger stones may need medication or a procedure. Do not ignore fever with stone
pain, which can mean an infected blocked kidney.

See a doctor for suspected kidney stone pain. Seek emergency care for fever and
chills with flank pain, inability to urinate, or vomiting that prevents fluids.""",
    ),
    (
        "conjunctivitis",
        "Conjunctivitis (Pink Eye)",
        "CDC - Conjunctivitis (Pink Eye)",
        "https://www.cdc.gov/conjunctivitis/about/index.html",
        "Conjunctivitis",
        "self_care",
        """Pink eye is inflammation of the thin lining of the eye. It can be viral, bacterial,
or allergic. Symptoms include redness, itching or grittiness, watering, and sometimes
sticky discharge that crusts overnight. Vision is usually not badly reduced.

Viral and allergic cases often settle with hygiene and cool compresses. Bacterial
cases may need antibiotic drops from a clinician. Wash hands often and avoid sharing
towels.

See a doctor if pain is severe, light hurts the eye, vision drops, or symptoms do not
improve after a few days, especially in contact-lens wearers.""",
    ),
    (
        "sinusitis",
        "Sinusitis (Sinus Infection)",
        "CDC - Sinus Infection (Sinusitis)",
        "https://www.cdc.gov/sinus-infection/about/index.html",
        "Sinusitis",
        "self_care",
        """Sinusitis is swelling of the sinus lining. It often follows a cold and causes facial
pressure, blocked nose, thick nasal mucus, reduced smell, and pain in the forehead
or cheeks that may worsen when you bend forward.

Most sinus infections are viral and improve in 7 to 10 days with rest, fluids, saline
rinses, and steam. Antibiotics help only when a bacterial infection is likely, such as
symptoms lasting more than 10 days or a fever that returns after briefly improving.

See a doctor if symptoms last more than 10 days, you have a high fever, swelling
around the eyes, or a severe headache.""",
    ),
    (
        "ear_infection",
        "Middle Ear Infection (Otitis Media)",
        "NIDCD - Ear Infections in Children",
        "https://www.nidcd.nih.gov/health/ear-infections-children",
        "Otitis Media",
        "consult_doctor",
        """A middle ear infection causes ear pain, fever, fussiness in children, and sometimes
temporary hearing reduction. It often follows a cold. The eardrum may look red and
bulging if a clinician examines it.

Many mild cases improve on their own. Pain relief with age-appropriate paracetamol or
ibuprofen helps. Some children need antibiotics, especially if they are very young or
symptoms are severe.

See a doctor for ear pain with high fever, discharge from the ear, or symptoms lasting
more than two to three days. Seek urgent care for a stiff neck, severe swelling behind
the ear, or a child who is unusually drowsy.""",
    ),
    (
        "eczema",
        "Atopic Dermatitis (Eczema)",
        "NIAMS - Atopic Dermatitis",
        "https://www.niams.nih.gov/health-topics/atopic-dermatitis",
        "Eczema",
        "self_care",
        """Eczema is a long-term itchy skin condition. Patches are often dry, red, and very
itchy, commonly in the bends of elbows and knees, on the neck, or on the face in
infants. Scratching can break the skin and lead to infection.

Daily moisturiser, short lukewarm baths, and avoiding known irritants such as harsh
soaps help most people. A clinician may add steroid creams for flares.

See a doctor if itching disrupts sleep, the rash is spreading, or you see yellow crust,
pus, or fever, which can mean a skin infection.""",
    ),
    (
        "constipation",
        "Constipation",
        "NIDDK - Constipation",
        "https://www.niddk.nih.gov/health-information/digestive-diseases/constipation",
        "Constipation",
        "self_care",
        """Constipation means bowel movements that are infrequent, hard, or difficult to pass.
People may feel bloated or that they have not fully emptied. Common triggers include
low fibre, low fluids, inactivity, some medicines, and ignoring the urge to go.

Self-care includes drinking more water, eating fruit, vegetables, and whole grains,
and staying active. Over-the-counter fibre or stool softeners can help for a short
time if a pharmacist or clinician agrees they are suitable.

See a doctor for constipation lasting more than two weeks, blood in the stool,
unexplained weight loss, or severe abdominal pain.""",
    ),
    (
        "hypothyroidism",
        "Hypothyroidism (Underactive Thyroid)",
        "Mayo Clinic - Hypothyroidism",
        "https://www.mayoclinic.org/diseases-conditions/hypothyroidism/symptoms-causes/syc-20350284",
        "Hypothyroidism",
        "consult_doctor",
        """An underactive thyroid slows many body processes. Symptoms build gradually and may
include tiredness, feeling cold, weight gain, dry skin, constipation, low mood, and
a puffy face. In women, periods may become heavier.

Diagnosis needs a blood test for thyroid hormones. Treatment is usually a daily
thyroid hormone tablet prescribed and adjusted by a clinician. It is not something
to self-dose.

See a doctor if you have several of these symptoms lasting weeks. Seek urgent care
for severe drowsiness, very low temperature, or confusion, which are rare but serious.""",
    ),
    (
        "gallstones",
        "Gallstones",
        "NIDDK - Gallstones",
        "https://www.niddk.nih.gov/health-information/digestive-diseases/gallstones",
        "Gallstones",
        "consult_doctor",
        """Gallstones are hard deposits in the gallbladder. Many cause no symptoms. When a stone
blocks a duct, people get sudden pain in the upper right or middle abdomen, often after
a fatty meal, sometimes with nausea. Pain may last 30 minutes to several hours.

A clinician confirms gallstones with ultrasound. Recurring attacks may need surgery
to remove the gallbladder. Do not ignore fever or yellowing of the skin with this pain.

See a doctor for repeated upper abdominal attacks. Seek emergency care for pain with
fever, yellow skin or eyes, or vomiting that will not stop.""",
    ),
    (
        "heat_stroke",
        "Heat Stroke",
        "CDC - Heat Stress - Heat Stroke",
        "https://www.cdc.gov/niosh/heat-stress/about/heat-stroke.html",
        "Heat Stroke",
        "emergency",
        """Heat stroke is a medical emergency. Body temperature rises quickly, often above 40C
(104F). Warning signs include confusion, slurred speech, loss of consciousness, hot
skin that may be dry or wet, and seizures after heavy heat exposure or exertion.

This is not ordinary heat exhaustion. Call emergency services immediately. Move the
person to shade, cool them with water and fanning, and do not give fluids if they are
unconscious.

Never leave someone with suspected heat stroke to 'sleep it off'. Delay can cause
permanent organ damage or death.""",
    ),
    (
        "meningitis",
        "Meningitis",
        "CDC - Meningitis Signs and Symptoms",
        "https://www.cdc.gov/meningitis/about/symptoms.html",
        "Meningitis",
        "emergency",
        """Meningitis is inflammation of the membranes around the brain and spinal cord. Classic
features include sudden fever, severe headache, stiff neck, dislike of bright light,
vomiting, and confusion. A rash that does not fade when pressed can appear in some
bacterial cases.

Bacterial meningitis can become life-threatening within hours. Do not wait to see if
it settles. Viral meningitis is usually less severe but still needs a clinical
assessment.

Seek emergency care immediately for fever with stiff neck, severe headache, a
non-blanching rash, or rapidly worsening confusion.""",
    ),
    (
        "bone_fracture",
        "Broken Bone (Fracture)",
        "NHS - Broken Arm or Wrist",
        "https://www.nhs.uk/conditions/broken-arm-or-wrist/",
        "Bone Fracture",
        "emergency",
        """A fracture is a break in a bone. Signs include sudden pain after a fall or blow,
swelling, bruising, deformity, and inability to use the limb. The area may look out
of place or the person may have heard a snap.

Do not try to straighten a deformed limb. Support it, apply ice wrapped in cloth, and
get urgent in-person care. An X-ray is needed to confirm the break.

Go to emergency care for an open wound over the bone, numbness, a cold or pale limb,
or any suspected break in the hip, pelvis, spine, or skull.""",
    ),
    (
        "pulmonary_embolism",
        "Pulmonary Embolism (Blood Clot in the Lung)",
        "CDC - Venous Thromboembolism",
        "https://www.cdc.gov/blood-clots/about/index.html",
        "Pulmonary Embolism",
        "emergency",
        """A pulmonary embolism is a blood clot that travels to the lungs. Warning signs include
sudden shortness of breath, sharp chest pain that worsens with a deep breath, coughing
(sometimes with blood), a fast heart rate, and feeling faint. Risk is higher after
surgery, long flights, or with a swollen painful calf (possible DVT).

This is a medical emergency. Clot-dissolving or blood-thinning treatment in hospital
can be life-saving. Do not wait to see if breathing 'settles'.

Call emergency services for sudden unexplained breathlessness or chest pain, especially
with a swollen leg.""",
    ),
]


FRONT_MATTER_TEMPLATE = """---
id: {id}
title: {title}
source: {source}
url: {url}
condition: {condition}
triage_level: {triage_level}
---

# {title}

{body}
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for doc_id, title, source, url, condition, triage_level, body in DOCUMENTS:
        text = FRONT_MATTER_TEMPLATE.format(
            id=doc_id,
            title=title,
            source=source,
            url=url,
            condition=condition,
            triage_level=triage_level,
            body=body.strip(),
        )
        path = OUT_DIR / f"{doc_id}.md"
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")

    print(f"\nGenerated {len(DOCUMENTS)} sample knowledge base documents in {OUT_DIR}")


if __name__ == "__main__":
    main()
