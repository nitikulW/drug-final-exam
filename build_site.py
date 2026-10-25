"""Build the offline study & mock-exam web app for 553103-168 Basic Knowledge of Medications."""
from pathlib import Path
import re, json, html, hashlib, shutil

ROOT = Path(__file__).resolve().parent

META = {
    '01': {
        'shortTitle': 'อาการไม่พึงประสงค์จากการใช้ยา (ADR)',
        'instructor': 'อ.ภญ.ปัทมวรรณ',
        'partLabel': 'ตอนที่ 1 (อ.ปัทมวรรณ · 24 คะแนน)'
    },
    '02': {
        'shortTitle': 'อันตรกิริยาระหว่างยา (Drug Interactions)',
        'instructor': 'รศ.ดร.ภญ.ศรีสมบัติ',
        'partLabel': 'ตอนที่ 2 (รศ.ดร.ภญ.ศรีสมบัติ · 12 คะแนน)'
    },
    '03': {
        'shortTitle': 'ทางเลือกในการรักษาโรค (CAM & สมุนไพร)',
        'instructor': 'อ.ภญ.ปัทมวรรณ',
        'partLabel': 'ตอนที่ 1 (อ.ปัทมวรรณ · 24 คะแนน)'
    },
    '04': {
        'shortTitle': 'ยาแก้ปวดและยาลดไข้ในชีวิตประจำวัน',
        'instructor': 'อ.ภญ.ปัทมวรรณ',
        'partLabel': 'ตอนที่ 1 (อ.ปัทมวรรณ · 24 คะแนน)'
    },
    '05': {
        'shortTitle': 'การแพทย์แม่นยำ (Precision Medicine)',
        'instructor': 'รศ.ดร.ภญ.ศรีสมบัติ',
        'partLabel': 'ตอนที่ 2 (รศ.ดร.ภญ.ศรีสมบัติ · 12 คะแนน)'
    },
    '06': {
        'shortTitle': 'ยาหวัด ท้องเสีย ท้องผูก และโรคกระเพาะอาหาร',
        'instructor': 'อ.ภญ.ปัทมวรรณ',
        'partLabel': 'ตอนที่ 1 (อ.ปัทมวรรณ · 24 คะแนน)'
    },
}

def format_math(s: str) -> str:
    # Convert simple LaTeX-like notations used in markdown into clean HTML
    s = re.sub(r'\$\$(.+?)\$\$', lambda m: f'<strong>{m.group(1)}</strong>', s)
    s = re.sub(r'\\text\{([^}]*)\}', r'\1', s)
    s = s.replace(r'\ge', '≥').replace(r'\le', '≤').replace(r'\supset', '⊃').replace(r'\cup', '∪')
    s = s.replace(r'\uparrow', '↑').replace(r'\downarrow', '↓').replace(r'\xrightarrow', '→')
    s = s.replace(r'^\circ', '°')
    s = re.sub(r'_\{([^}]+)\}', r'<sub>\1</sub>', s)
    s = re.sub(r'_([0-9a-zA-Z]+)', r'<sub>\1</sub>', s)
    s = re.sub(r'\^\{([^}]+)\}', r'<sup>\1</sup>', s)
    s = re.sub(r'\^([0-9+\-]+)', r'<sup>\1</sup>', s)
    s = s.replace('$', '')
    return s

def inline(s: str) -> str:
    s = html.escape(s)
    s = format_math(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', s)
    return s

def markdown(s: str) -> str:
    out, lines, i = [], s.splitlines(), 0
    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()
        if not line:
            i += 1
            continue
        if line.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(html.escape(lines[i]))
                i += 1
            i += 1
            out.append('<pre class="codeblock">' + '\n'.join(code_lines) + '</pre>')
            continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = lines[i].strip().strip('|').split('|')
                if not all(re.fullmatch(r'\s*:?-+:?\s*', c) for c in cells):
                    tag = 'th' if not rows else 'td'
                    rows.append('<tr>' + ''.join(f'<{tag}>{inline(c.strip())}</{tag}>' for c in cells) + '</tr>')
                i += 1
            out.append('<div class="table-wrap"><table>' + ''.join(rows) + '</table></div>')
            continue
        if line.startswith('>'):
            bq_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                bq_lines.append(inline(lines[i].strip().lstrip('>').strip()))
                i += 1
            out.append('<blockquote>' + '<br>'.join(bq_lines) + '</blockquote>')
            continue
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            out.append(f'<h{len(m[1])}>{inline(m[2])}</h{len(m[1])}>')
        elif re.fullmatch(r'[-*_]{3,}', line):
            out.append('<hr>')
        elif re.match(r'^[-*]\s+', line):
            out.append('<p class="bullet">• ' + inline(line[2:]) + '</p>')
        elif re.match(r'^\d+[.)]\s+', line):
            out.append('<p class="bullet">' + inline(line) + '</p>')
        else:
            out.append('<p>' + inline(line) + '</p>')
        i += 1
    return '\n'.join(out)

chapters = []
manifest = []

for f in sorted(ROOT.glob('คาบ*.md')):
    text = f.read_text(encoding='utf-8-sig')
    chap_id = re.search(r'คาบ(\d+)', f.name)[1]
    meta = META[chap_id]

    summary_part, exam_part = re.split(r'^## ส่วนที่ 2 แนวข้อสอบ.*$', text, maxsplit=1, flags=re.M)
    questions_part, key_part = re.split(r'^### เฉลยและคำอธิบาย\s*$', exam_part, maxsplit=1, flags=re.M)

    # Split summary into header+checklist vs detailed body for embedding inside mock exam
    if '## ส่วนที่ 1 ' in summary_part:
        before_sec1, sec1_body = summary_part.split('## ส่วนที่ 1 ', 1)
        sec1_body = '## ส่วนที่ 1 ' + sec1_body
        if '## สรุปจุดเน้นออกสอบประจำบท' in before_sec1:
            _, checklist_md = before_sec1.split('## สรุปจุดเน้นออกสอบประจำบท', 1)
            checklist_md = '### สรุปจุดเน้นออกสอบประจำบท' + checklist_md
        else:
            checklist_md = before_sec1
    else:
        checklist_md = summary_part
        sec1_body = summary_part

    answers = {}
    for n, a, e in re.findall(r'^\|\s*(\d+)\s*\|\s*([กขคง])\s*\|\s*(.*?)\s*\|\s*$', key_part, re.M):
        clean_e = re.sub(r'\*\*(.+?)\*\*', r'\1', e.strip())
        clean_e = format_math(clean_e).replace('<sub>', '').replace('</sub>', '').replace('<sup>', '').replace('</sup>', '')
        src_match = re.search(r'\(([^)]+)\)', clean_e)
        source_ref = src_match.group(1) if src_match else f'เอกสารและคลิปการสอน คาบที่ {int(chap_id)}'
        answers[int(n)] = ('กขคง'.index(a), clean_e, source_ref)

    qs = []
    matches = list(re.finditer(r'^\*\*(\d+)\.\*\*\s*', questions_part, re.M))
    for ix, m in enumerate(matches):
        qnum = int(m[1])
        block = questions_part[m.end():matches[ix + 1].start() if ix + 1 < len(matches) else len(questions_part)].strip()
        parts = re.split(r'(?:^|\n)\s*([กขคง])\.\s*', block)
        assert len(parts) == 9, (f.name, qnum, len(parts), parts)
        assert parts[1::2] == list('กขคง'), (f.name, qnum)

        raw_q = parts[0].strip()
        star_match = re.match(r'^(⭐+)\s*(.*)', raw_q, re.S)
        if star_match:
            stars = len(star_match.group(1))
            q_text = star_match.group(2).strip()
        else:
            stars = 2
            q_text = raw_q

        q_text = re.sub(r'\*\*(.+?)\*\*', r'\1', q_text)
        q_text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', q_text)
        q_text = format_math(q_text).replace('<sub>', '').replace('</sub>', '').replace('<sup>', '').replace('</sup>', '')

        choices = []
        for c_item in parts[2::2]:
            c_clean = re.sub(r'\*\*(.+?)\*\*', r'\1', c_item.strip())
            c_clean = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', c_clean)
            c_clean = format_math(c_clean).replace('<sub>', '').replace('</sub>', '').replace('<sup>', '').replace('</sup>', '')
            choices.append(c_clean)

        a_idx, exp_text, source_ref = answers[qnum]
        qs.append(dict(
            q=q_text,
            c=choices,
            a=a_idx,
            e=exp_text,
            stars=stars,
            source=source_ref,
            topicId=chap_id,
            topicTitle=f'คาบที่ {int(chap_id)}: {meta["shortTitle"]}',
            partLabel=meta['partLabel']
        ))

    assert len(qs) == 30 and len(answers) == 30, (f.name, len(qs), len(answers))
    title = summary_part.splitlines()[0].lstrip('# ').strip()
    chapters.append(dict(
        id=chap_id,
        title=title,
        shortTitle=meta['shortTitle'],
        instructor=meta['instructor'],
        partLabel=meta['partLabel'],
        summary=markdown(summary_part),
        checklistHtml=markdown(checklist_md),
        bodyHtml=markdown(sec1_body),
        questions=qs,
        filename=f.name
    ))
    manifest.append(dict(
        file=f.name,
        sha256=hashlib.sha256(f.read_bytes()).hexdigest(),
        total=len(qs),
        stars_3=sum(1 for q in qs if q['stars'] == 3),
        stars_2=sum(1 for q in qs if q['stars'] == 2),
        stars_1=sum(1 for q in qs if q['stars'] == 1),
    ))

# Build the 36-question Full Final Exam Simulation matching ใบปะหน้า.jpg
# Part 1 (24 pts): อ.ปัทมวรรณ -> คาบ 1, 3, 4, 6 (6 questions each = 24 questions)
# Part 2 (12 pts): รศ.ดร.ภญ.ศรีสมบัติ -> คาบ 2, 5 (6 questions each = 12 questions)
CURATED_EXAM_INDICES = {
    '01': [0, 2, 4, 5, 7, 15],   # AE/ADE/ADR, Type A Side/Secondary, Type B Malignant Hyperthermia, AID Digital Health
    '03': [0, 1, 6, 10, 12, 18], # Complementary vs Alternative, นวดแผนไทยข้อห้าม, ฟ้าทะลายโจร, ขมิ้นชัน, ว่านหางจระเข้
    '04': [0, 8, 9, 10, 17, 18], # กลไกไข้, พิษพารา NAPQI, Antidote NAC, ไทลินอล 8 ชม., Selective COX-2, ไข้เลือดออกห้าม NSAIDs
    '06': [4, 7, 9, 14, 24, 26], # ยาแก้แพ้รุ่น 1 vs 2, ยาพ่นจมูก 3-5 วัน, ยากดศูนย์ไอห้ามไอมีเสมหะ, Loperamide ข้อห้าม, PPI ระยะยาว, Domperidone
    '02': [2, 5, 8, 10, 11, 22], # Chelation นม+Cipro, Warfarin+Phenylbutazone 5 เท่า, Prodrug+Inducer, ยาคุม+ยาฆ่าเชื้อ, Amphetamine+Vit C, MAOI+Tyramine Cheese effect
    '05': [2, 3, 5, 9, 12, 18],  # HLA-B*15:02 Carbamazepine, Chemo 40% vs Targeted 70%, Small molecule vs mAb, CAR-T 4 ขั้นตอน, Asthma Endotype T2 High, Procalcitonin
}

exam36_questions = []
for cid in ['01', '03', '04', '06', '02', '05']:
    ch = next(c for c in chapters if c['id'] == cid)
    for idx in CURATED_EXAM_INDICES[cid]:
        exam36_questions.append(dict(ch['questions'][idx]))

exam36_summary_md = """# จำลองสอบปลายภาคจริง 36 ข้อ (ตามโครงสร้างใบปะหน้าข้อสอบ)

**รหัสวิชา:** 553103-168 ความรู้พื้นฐานเรื่องยา (Basic Knowledge of Medications)  
**วัน-เวลาสอบตามใบปะหน้า:** วันที่ 26 ตุลาคม 2569 เวลา 09.00–10.00 น. (60 นาที) · คะแนนเต็ม **36 คะแนน (ปรนัย 36 ข้อ)**

> **[⭐⭐⭐ โครงสร้างข้อสอบจริงจากใบปะหน้า (`ใบปะหน้า.jpg`) และสรุปแยกแต่ละเรื่องในข้อสอบ]**
> - **ตอนที่ 1 (ข้อที่ 1–24 · 24 คะแนน) — อ.ภญ.ปัทมวรรณ เผือกผ่อง (4 เรื่อง · เรื่องละ 6 ข้อ):**
>   1. **คาบที่ 1:** อาการไม่พึงประสงค์จากการใช้ยา (ADR) — ข้อ 1–6
>   2. **คาบที่ 3:** ทางเลือกในการรักษาโรค (CAM, นวดแผนไทย, สมุนไพร 8 ชนิด) — ข้อ 7–12
>   3. **คาบที่ 4:** ยาแก้ปวดและยาลดไข้ในชีวิตประจำวัน (กลไกไข้, Paracetamol, NSAIDs, Opioids) — ข้อ 13–18
>   4. **คาบที่ 6:** ยารักษาอาการหวัด ท้องเสีย ท้องผูก และโรคกระเพาะอาหารในชีวิตประจำวัน — ข้อ 19–24
> - **ตอนที่ 2 (ข้อที่ 25–36 · 12 คะแนน) — รศ.ดร.ภญ.ศรีสมบัติ นวนพรัตน์สกุล (2 เรื่อง · เรื่องละ 6 ข้อ):**
>   5. **คาบที่ 2:** อันตรกิริยาระหว่างยา (Drug Interactions: PK ADME, P-gp, PD, Drug-Food CDSS) — ข้อ 25–30
>   6. **คาบที่ 5:** การแพทย์แม่นยำ (Precision Medicine: Pharmacogenomics, Targeted/mAb/ADC/CAR-T, Asthma Endotypes, Genomics Thailand, Biomarkers) — ข้อ 31–36
> - **พิเศษ:** ในแบบจำลองข้อสอบด้านล่างนี้ **ได้นำสรุปจุดเน้นและสรุปฉบับเต็มของแต่ละเรื่องใส่ไว้ในหัวข้อข้อสอบแต่ละเรื่องโดยตรง** เพื่อให้ทบทวนเนื้อหาควบคู่กับการทำข้อสอบแต่ละเรื่องได้ทันที และสามารถกดปุ่ม **"สุ่มชุดข้อสอบปลายภาค 36 ข้อใหม่"** เพื่อฝึกทำข้อสอบชุดใหม่จากคลัง 180 ข้อได้ไม่จำกัดครั้ง
"""

chapters.append(dict(
    id='exam36',
    title='จำลองสอบปลายภาคจริง 36 ข้อ (ตามใบปะหน้า)',
    shortTitle='ตอนที่ 1 (24 ข้อ) + ตอนที่ 2 (12 ข้อ)',
    instructor='อ.ปัทมวรรณ + รศ.ดร.ภญ.ศรีสมบัติ',
    partLabel='ครบทั้ง 2 ตอนตามใบปะหน้า',
    summary=markdown(exam36_summary_md),
    checklistHtml=markdown(exam36_summary_md),
    bodyHtml='',
    questions=exam36_questions,
    filename='ใบปะหน้า.jpg'
))

template = (ROOT / 'template.html').read_text(encoding='utf-8')
payload = json.dumps(chapters, ensure_ascii=False).replace('</', '<\\/')
html_out = template.replace('/*__DATA__*/', payload)

(ROOT / 'index.html').write_text(html_out, encoding='utf-8')
(ROOT / 'build_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

how_to_open = """วิธีเปิดใช้งานเว็บสรุปเนื้อหาและจำลองข้อสอบปลายภาค (553103-168 ความรู้พื้นฐานเรื่องยา)
================================================================================

1. ดับเบิลคลิกเปิดไฟล์ "index.html" ในโฟลเดอร์นี้ด้วยเว็บเบราว์เซอร์ใดก็ได้ (เช่น Google Chrome, Microsoft Edge, Safari)
   - สามารถเปิดใช้งานแบบออฟไลน์ได้ทันที ไม่ต้องเชื่อมต่ออินเทอร์เน็ต
2. ฟีเจอร์หลักภายในเว็บ:
   - แถบเมนูด้านซ้ายแยกตามบทเรียนครบทั้ง 6 คาบ (คาบที่ 1 ถึง คาบที่ 6) และ "โหมดจำลองสอบปลายภาคจริง 36 ข้อ (ตามใบปะหน้า)"
   - เนื้อหาในสรุปและข้อสอบมีป้ายดาว (⭐⭐⭐ ออกสอบเน้นย้ำ, ⭐⭐ มีโอกาสออกสูง, ⭐ เก็บตกครบเนื้อหา) บอกจุดที่น่าจะออกสอบชัดเจน
   - ในแบบจำลองข้อสอบของแต่ละเรื่อง มี "สรุปเนื้อหาประจำเรื่อง" แนบไว้ด้านในข้อสอบของเรื่องนั้นโดยตรง สามารถคลิกย่อ/ขยายดูสรุปขณะทำข้อสอบได้ทันที
   - มีปุ่มกรองเฉพาะข้อสอบติดดาว (⭐⭐⭐) ปุ่มสลับโหมดมืด/สว่าง และบันทึกคำตอบอัตโนมัติในเบราว์เซอร์
"""
(ROOT / 'วิธีเปิดเว็บ.txt').write_text(how_to_open, encoding='utf-8')

# Also mirror into subfolder สรุปและแนวข้อสอบ for consistency with the sibling course folder
SUB = ROOT / 'สรุปและแนวข้อสอบ'
SUB.mkdir(exist_ok=True)
for fname in ['index.html', 'template.html', 'build_site.py', 'build_manifest.json', 'PRODUCT.md', 'DESIGN.md', 'วิธีเปิดเว็บ.txt']:
    shutil.copy2(ROOT / fname, SUB / fname)
for md_file in ROOT.glob('คาบ*.md'):
    shutil.copy2(md_file, SUB / md_file.name)

print(f'Successfully built {len(chapters)-1} chapters ({sum(len(c["questions"]) for c in chapters if c["id"]!="exam36")} questions) + 36-question Full Exam Blueprint mode!')
