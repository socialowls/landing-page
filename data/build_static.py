"""Build socialowls.agency as a real multi-page static site (crawlable by search engines and AI assistants).
Input: data/site.json (site data), data/site.base.css, data/*.json image bundles (data URIs) -> real image files.
Run: python3 data/build_static.py
"""
import json, os, re, base64, glob, html, shutil, datetime
REPO = '/home/claude/landing-page'
S = json.load(open(REPO + '/data/site.json'))
CSS = open(REPO + '/data/site.base.css').read()
BASE = 'https://socialowls.agency'
TODAY = datetime.date.today().isoformat()
e = lambda x: html.escape(str(x), quote=True)

# ---------- 1. images: data URIs -> files ----------
assets = {}
for f in glob.glob(REPO + '/data/*.json'):
    try: d = json.load(open(f))
    except Exception: continue
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, str) and v.startswith('data:image'): assets[k] = v
EXT = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/svg+xml': '.svg', 'image/gif': '.gif'}
from PIL import Image as _Im
import io as _io
LOGO_R = {}  # public path -> aspect ratio after trim
def trim_logo(raw, p):
    """Crop empty margins (transparent or near-white) so every logo's ink fills its box the same way."""
    try:
        im = _Im.open(_io.BytesIO(raw)); im.load()
        rgba = im.convert('RGBA')
        a = rgba.getchannel('A').point(lambda x: 255 if x > 16 else 0)
        rgb = rgba.convert('RGB')
        from PIL import ImageChops
        bgc = rgb.getpixel((0, 0))
        diff = ImageChops.difference(rgb, _Im.new('RGB', rgb.size, bgc)).convert('L').point(lambda x: 255 if x > 28 else 0)
        corners_opaque = all(rgba.getpixel(c)[3] > 200 for c in [(0, 0), (rgba.width-1, 0), (0, rgba.height-1), (rgba.width-1, rgba.height-1)])
        same_corners = len({rgb.getpixel(c) for c in [(0, 0), (rgb.width-1, 0), (0, rgb.height-1), (rgb.width-1, rgb.height-1)]}) == 1
        light_bg = sum(bgc) > 660
        if corners_opaque and same_corners and light_bg: mask = ImageChops.multiply(diff, a)
        elif not corners_opaque: mask = a
        else: mask = None   # logo sits on its own coloured block: keep it whole
        bb = mask.getbbox() if mask is not None else None
        if bb:
            pad = round(max(bb[2]-bb[0], bb[3]-bb[1]) * 0.03)
            bb = (max(0, bb[0]-pad), max(0, bb[1]-pad), min(im.width, bb[2]+pad), min(im.height, bb[3]+pad))
            im = im.crop(bb)
        LOGO_R['/' + p] = im.width / max(1, im.height)
        if bb:
            out = _io.BytesIO(); fmt = {'.png': 'PNG', '.webp': 'WEBP', '.jpg': 'JPEG'}[os.path.splitext(p)[1]]
            (im.convert('RGB') if fmt == 'JPEG' else im).save(out, fmt, **({'quality': 92} if fmt != 'PNG' else {}))
            return out.getvalue()
    except Exception as ex:
        print('trim skip', p, ex)
    return raw
PATH = {}  # key -> public path
for k, v in assets.items():
    mime = v[5:v.index(';')]
    root, _ = os.path.splitext(k)
    p = root + EXT.get(mime, '.bin')
    os.makedirs(os.path.dirname(REPO + '/' + p), exist_ok=True)
    raw = base64.b64decode(v.split(',', 1)[1])
    if p.startswith('logos/') and not p.startswith('logos/so-') and not p.endswith('.svg'):
        raw = trim_logo(raw, p)
    open(REPO + '/' + p, 'wb').write(raw)
    PATH[k] = '/' + p
def src(k): return PATH.get(k, '/' + k)

# ---------- 2. model ----------
B = S['brands']; ROOMS = S['rooms']
def slugify(t): return re.sub(r'[^a-z0-9]+', '-', t.lower().replace('’', '').replace("'", '')).strip('-')
ROOMSLUG = {r['r']: slugify(r['name'].replace('The ', '')) for r in ROOMS}
ACC = {1: 'c-mint', 2: 'c-lime', 3: 'c-mid', 4: 'c-dark', 5: 'c-mint', 6: 'c-mid', 7: 'c-lime', 8: 'c-lav', 9: 'c-dark', 10: 'c-mint'}
BRANDING = [b for b in B.values() if 'Branding' in b['kind']]
PHOTO = [b for b in B.values() if 'Photography' in b['kind']]
PH = {'img/slide-103.jpg', 'img/slide-104.jpg'}
CCLS = {'UAE': 'k-uae', 'Saudi Arabia': 'k-ksa', 'Oman': 'k-om', 'Kuwait': 'k-kw', 'Middle East': 'k-me', 'Europe': 'k-eu', 'Egypt, UAE & Oman': 'k-multi', 'Egypt': 'k-eg'}
CSHORT = {'Saudi Arabia': 'KSA', 'Egypt, UAE & Oman': 'EG · UAE · OM', 'Middle East': 'ME'}
CORDER = ['UAE', 'Saudi Arabia', 'Oman', 'Kuwait', 'Middle East', 'Europe', 'Egypt, UAE & Oman', 'Egypt']
BYNAME = {b['name']: b for b in B.values()}
def room_items(r):
    """Ordered items (brand dicts or logo-only 'others') for a room, biggest names first, grouped by country order."""
    if r in (9, 10):
        lst = BRANDING if r == 9 else PHOTO
        items = sorted(lst, key=lambda b: CORDER.index(b.get('country', 'Egypt')))
        return [dict(kind='brand', b=b, name=b['name'], logo=b.get('logo'), country=b.get('country', 'Egypt')) for b in items]
    R = ROOMS[r - 1]; oth = {o['name']: o for o in R.get('others', [])}; out = []
    for k in R.get('order') or (R['brands'] + list(oth)):
        if k in B: out.append(dict(kind='brand', b=B[k], name=B[k]['name'], logo=B[k].get('logo'), country=B[k].get('country', 'Egypt')))
        else:
            o = oth[k]; out.append(dict(kind='other', b=BYNAME.get(o['name']), name=o['name'], logo=o.get('logo'), country=o.get('country', 'Egypt')))
    return sorted(out, key=lambda x: CORDER.index(x['country']))
def by_country(items):
    groups = []
    for it in items:
        if not groups or groups[-1][0] != it['country']: groups.append((it['country'], []))
        groups[-1][1].append(it)
    return groups
def room_brands(r):
    return [it['b'] for it in room_items(r) if it['kind'] == 'brand']
def room_url(r):
    return '/branding/' if r == 9 else f'/rooms/{ROOMSLUG[r]}/'
def has_social(b): return bool(b['posts'] or b['reels'] or (b['slides'] and not ({'Branding', 'Photography'} & set(b['kind']))))
def social_url(b): return f'/work/{b["slug"]}/'
def id_url(b): return f'/branding/{b["slug"]}/'
def ph_url(b): return f'/photography/{b["slug"]}/'
def main_url(b):
    if has_social(b): return social_url(b)
    if 'Branding' in b['kind']: return id_url(b)
    return ph_url(b)
IND = {r['r']: r['ind'] for r in ROOMS}
LABEL = {r['r']: {8: 'More industries'}.get(r['r'], r['ind'].replace('Ai', 'AI')) for r in ROOMS}

SERVICES_TEXT = {k: v for k, v in S['serv']}
SITE_DESC = ("Social Owls is a strategy-first social media and branding agency with offices in Egypt and the UAE, "
             "working with brands across the UAE & Egypt. 66 brand partners in travel, food & beverage, fashion, tech, "
             "healthcare, industry and more.")

# ---------- 3. layout ----------
def page(path, title, desc, body, jsonld=None, extra_head=''):
    url = BASE + path
    ld = ''
    if jsonld:
        ld = '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False) + '</script>'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{e(title)}</title>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="apple-touch-icon" href="/favicon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Social Owls">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/thumbnail.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Google+Sans+Flex:opsz,wght@6..144,400..900&family=Playfair+Display:ital,wght@1,600;1,700&display=swap">
<link rel="stylesheet" href="/site.css">
{extra_head}{ld}
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="/" aria-label="Social Owls home"><img src="{src('logos/so-wordmark.png')}" alt="Social Owls" width="120" height="40"></a>
  <nav class="main" aria-label="Main"><a href="/#about">About</a><a href="/#services">Services</a><a href="/#work">Work</a><a href="/#branding">Branding</a><a href="/#cases">Case studies</a><a href="/#faq">FAQ</a><a class="cta" href="/#contact">Contact</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap"><span>Social Owls · UAE &amp; Egypt · <a href="mailto:letstalk@socialowls.agency">letstalk@socialowls.agency</a></span><span class="serif">Don’t do social. Be social.</span></div></footer>
<div class="lb" id="lb" hidden><button type="button" id="lbx">Close</button><img id="lbi" alt=""></div>
<script src="/site.js" defer></script>
</body>
</html>
'''

def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(items)]}

def logo_tile(b_or_o, cls=''):
    return f'<i{f" class={cls}" if cls else ""}><img src="{src(b_or_o["logo"])}" alt="{e(b_or_o["name"])} logo" loading="lazy"></i>'

def services_of(b, mode):
    if mode == 'id': return ['Branding']
    if mode == 'ph': return ['Photography']
    return [k for k in b['kind'] if k not in ('Branding', 'Photography')]

def kind_sentence(b):
    k = set(b['kind']); parts = []
    if 'Account management' in k: parts.append('full account management')
    if 'Social media' in k: parts.append('social media management and content design')
    if 'Reels' in k: parts.append('reels and short-form video')
    if 'Branding' in k: parts.append('brand identity')
    if 'Photography' in k: parts.append('photography')
    if not parts: return ''
    return ', '.join(parts[:-1]) + (' and ' if len(parts) > 1 else '') + parts[-1]

# ---------- 4. home ----------
CKEYS = {'UAE': 'uae', 'Saudi Arabia': 'ksa', 'Oman': 'om', 'Kuwait': 'kw', 'Middle East': 'me', 'Europe': 'eu', 'Egypt, UAE & Oman': 'uae eg om', 'Egypt': 'eg'}
FILTERS = [('uae', 'UAE'), ('ksa', 'KSA'), ('om', 'Oman'), ('kw', 'Kuwait'), ('me', 'Middle East'), ('eu', 'Europe'), ('eg', 'Egypt')]
def country_counts():
    seen = {}
    for r in ROOMS:
        for c, its in by_country(room_items(r['r'])):
            for it in its:
                if it['name'].strip().lower() != 'social owls': seen.setdefault(it['name'].strip().lower(), CKEYS[c])
    cnt = {k: 0 for k, _ in FILTERS}
    for v in seen.values():
        for k in v.split(): cnt[k] += 1
    return cnt
def logo_fit(path):
    r = LOGO_R.get(path)
    if not r: return ''
    W, H, A = 44, 28, 0.5          # tile content box and share of it each logo's ink should cover
    w = (A * W * H * r) ** .5; h = w / r
    if w > W: w = W; h = w / r
    if h > H: h = H; w = h * r
    return f' style="width:{w / W * 100:.0f}%;max-width:none;max-height:none;height:auto"'
def floor_plan():
    cnt = country_counts()
    order = sorted(FILTERS, key=lambda kn: -cnt[kn[0]])
    chips = '<button class="fchip on" data-f="">All</button>' + ''.join(
        f'<button class="fchip" data-f="{k}"><b class="dot k-{k if k!="om" else "om"}"></b>{e(n)} <small>{cnt[k]}</small></button>' for k, n in order if cnt[k])
    out = []
    for r in ROOMS:
        groups = []
        for c, its in by_country(room_items(r['r'])):
            seen = set(); items = []
            for it in its:
                if it['logo'] and it['logo'] not in seen: seen.add(it['logo']); items.append(it)
            if items: groups.append((c, items))
        total = sum(len(i) for _, i in groups); n = 0; flow = []
        for c, items in groups:
            tiles = []
            for it in items:
                tiles.append(f'<i data-c="{CKEYS[c]}"><span class="li"><img src="{src(it["logo"])}" alt="{e(it["name"])} logo" loading="lazy"{logo_fit(src(it["logo"]))}></span><s class="ct {CCLS[c]}">{e(CSHORT.get(c, c))}</s></i>')
            tag = f'<em class="ctag {CCLS[c]}" data-c="{CKEYS[c]}">{e(CSHORT.get(c, c))}</em>'
            flow.append(f'<span class="cl{" eg" if c == "Egypt" else ""}">{tag}<span class="lt">' + ''.join(tiles) + '</span></span>')
        more = ''
        rsum = ''
        out.append(f'''<a class="room {ACC[r["r"]]}" href="{room_url(r["r"])}"><span class="no">{e(LABEL[r["r"]])}</span><h3>{e(r["name"])}</h3>{rsum}
<div class="lg">{''.join(flow)}{more}</div></a>''')
    return (f'<div class="cfilter" role="group" aria-label="Filter work by country">{chips}</div>'
            '<div class="plan">' + ''.join(out) + '</div>')

CASES = [
 dict(slug='m-group-natur-sutures', label='M Group', eyebrow='Case study · The Clinic', title='Engagement beat awareness.', sub='On LinkedIn, for M Group Holding.',
      intro='A medical manufacturer with operations in Egypt, Sudan and Ghana. The question: which LinkedIn spend was actually working?',
      cols=[('The brief','Make sense of M Group’s LinkedIn: organic posts and paid campaigns, side by side, with one clear answer on where the budget should go.'),
            ('What we did','Built an interactive performance dashboard covering organic and paid metrics, then compared campaign objectives head to head.'),
            ('What we found','The engagement-focused campaign delivered strong CTR and follower growth against a brand-awareness boost. Video beat text posts on engagement.')]),
 dict(slug='project-pavilion', eyebrow='Case study · Branding', title='Built from day one.', sub='Project Pavilion, from blank page to brand.',
      intro='A project-management software brand we have worked with from the very beginning, before it had a logo, a look or a voice.',
      cols=[('The brief','Give a new software system a brand people trust with their work: clear, organised and confident from the first screen.'),
            ('What we did','Logo, brand guidelines and the line “Plan. Track. Deliver.” Then the ongoing content and design that put the brand to work.'),
            ('What it means','One partner from first sketch to everyday posts, so the brand that launched is the brand people still see today.')]),
 dict(slug='her', eyebrow='Case study · Branding', title='The grammar of a brand.', sub='her’, premium sportswear for women.',
      intro='Branding and brand guidelines for a premium women’s sportswear label, built around one small, possessive mark.',
      cols=[('The brief','A sportswear brand for women that feels personal, premium and theirs, not another logo on a waistband.'),
            ('What we did','The her’ identity and guidelines: the possessive apostrophe, a nude, sage, khaki and gold palette, and type with character.'),
            ('How we told it','“The Grammar of a Brand”: the thinking behind the identity, turned into a 7-slide carousel and a reel.')]),
]
FAQ = [
 ("What does Social Owls do?", "Social Owls is a strategy-first social media and branding agency. We build brand positioning, visual identities and social media content systems that connect content to business results, from strategy and design to community management, paid media and reporting."),
 ("Where is Social Owls based?", "We have two offices, in Egypt and the UAE, and we work with brands across the UAE & Egypt."),
 ("Which industries do you work with?", "We have worked with 66 brand partners across travel & tourism, food & beverage, retail, fashion & beauty, tech, medical & aesthetics, engineering & building materials, and events & entertainment."),
 ("What makes your approach different?", "Most brands don’t have a content problem, they have a strategy problem. We start with positioning and audience behaviour in each market, then build content that supports awareness, intent and conversion, rather than chasing vanity metrics."),
 ("Do you create brand identities as well as social media?", "Yes. Our branding work covers brand strategy, logo and visual systems, brand guidelines and marketing templates. You can see identities we built on our branding page."),
 ("How do I start a project with Social Owls?", "Email letstalk@socialowls.agency or call +971 50 508 9055 (UAE) or +20 155 633 1102 (Egypt)."),
]

def case_card(c):
    b = B[c['slug']]
    cols = ''.join(f'<div class="cc"><h4>{e(h)}</h4><p>{e(t)}</p></div>' for h, t in c['cols'])
    return f'''<article class="case"><div class="case-top"><a class="case-logo" href="{main_url(b)}"><img src="{src(b["logo"])}" alt="{e(b["name"])} logo" loading="lazy"></a><div><div class="eyebrow">{e(c["eyebrow"])}</div><h3>{e(c["title"])}</h3><p class="case-sub">{e(c["sub"])}</p><p class="case-intro">{e(c["intro"])}</p></div></div>
<div class="case-cols">{cols}</div><span class="swipe-hint">Swipe for more →</span><a class="case-link" href="{main_url(b)}">See the {e(c.get("label") or b["name"])} work →</a></article>'''

def home_page():
    nb = len(B)
    branding_cards = ''.join(f'''<a class="bcard" href="{id_url(b)}"><div class="lgo"><img src="{src(b["logo"])}" alt="{e(b["name"])} logo" loading="lazy"></div><div class="bt"><strong>{e(b["name"])}</strong><span class="bdesc">{e(b.get("tagline") or "")}</span></div></a>''' for b in BRANDING if b.get('logo'))
    body = f'''
<section class="hero">
  <div>
    <h1>Welcome to <span class="serif">the Nest.</span></h1>
    <p class="lead">Social Owls is a strategy-first social media and branding agency in the UAE &amp; Egypt. We’ve built, grown and given a voice to 66 brands. Ten rooms, one per industry: pick a room, meet the brand, see the work.</p>
    <p class="how">Pick a room <span>→</span> meet the brand <span>→</span> see the posts, reels and identities.</p>
  </div>
  <div class="stats">
    <div class="stat s1"><b>66</b><span>Brand partners</span></div>
    <div class="stat s2"><b>10</b><span>Rooms of work</span></div>
    <div class="stat s3"><b>EG · UAE</b><span>Two offices</span></div>
    <div class="stat s4"><b>2021</b><span>The nest was built</span></div>
  </div>
</section>
<section id="about" class="about">
  <div class="sec-head"><div><div class="eyebrow">Who we are</div><h2>Strategy first. <span class="serif">Content second.</span></h2></div></div>
  <p class="sec-lead">We build positioning, identity and social media systems that connect content to business growth, not vanity metrics.</p>
  <ol class="pillars">
    <li><b>Strategy before content.</b> Most brands don’t have a content problem. They have a strategy problem.</li>
    <li><b>Built for each market.</b> What works in Egypt doesn’t automatically work in the UAE, so we plan around how each audience behaves.</li>
    <li><b>One system.</b> Identity, content, community, media and reporting run together, so every post has a job to do.</li>
  </ol>
</section>
<section id="founder">
  <div class="host"><div class="badge"><img src="{src('logos/so-icon-lp.png')}" alt="" loading="lazy"></div><div>
    <div class="eyebrow">Your host</div><h2>Mary Gaied</h2><div class="serif">The founding owl.</div>
    <p>13+ years in digital marketing, on both the agency and the client side. Lead instructor and course developer of the certified Social Media Management course for the Middle East by Skillful Academy. Specialised in brand and digital strategy, content creation, media planning and buying, and reporting.</p></div></div>
</section>
<section id="services">
  <div class="sec-head"><div><div class="eyebrow">How the house runs</div><h2>Seven <span class="serif">services.</span></h2></div></div>
  <div class="serv">{''.join(f'<div><h3>{e(n)}</h3><ul>{"".join(f"<li>{e(x)}</li>" for x in it)}</ul></div>' for n, it in S["serv"])}</div>
</section>
<section id="work"><span id="rooms"></span>
  <div class="sec-head"><div><div class="eyebrow">Our work, by industry</div><h2>Pick a <span class="serif">room.</span></h2></div></div>
  {floor_plan()}
</section>
<section id="branding">
  <div class="sec-head"><div><div class="eyebrow">Branding</div><h2>Brands we <span class="serif">built.</span></h2></div><a class="more" href="/branding/">All branding projects →</a></div>
  <p class="sec-lead">Identities, guidelines and packaging, from the first sketch to the shelf.</p>
  <div class="bgrid">{branding_cards}</div>
</section>
<section id="cases">
  <div class="sec-head"><div><div class="eyebrow">Case studies</div><h2>Results, <span class="serif">not noise.</span></h2></div></div>
  <div class="cases">{''.join(case_card(c) for c in CASES)}</div>
</section>
<section id="faq">
  <div class="sec-head"><div><div class="eyebrow">Good to know</div><h2>Questions, <span class="serif">answered.</span></h2></div></div>
  <div class="faq">{''.join(f'<details><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in FAQ)}</div>
</section>
<section id="contact">
  <div class="contact"><div><div class="eyebrow">Every room here started as a blank one</div><h2>Yours is <span class="serif">next.</span></h2></div>
  <div class="rows">
    <div class="copy"><a href="mailto:letstalk@socialowls.agency">letstalk@socialowls.agency</a><button type="button" data-copy="letstalk@socialowls.agency">Copy</button></div>
    <div class="copy"><a href="tel:+971505089055">UAE +971 50 508 9055</a><button type="button" data-copy="+971505089055">Copy</button></div>
    <div class="copy"><a href="tel:+201556331102">Egypt +20 155 633 1102</a><button type="button" data-copy="+201556331102">Copy</button></div>
    <div class="soc">{''.join(f'<a href="{u}" target="_blank" rel="noopener">{n} ↗</a>' for n, u in [("Instagram", "https://instagram.com/social.owls"), ("LinkedIn", "https://linkedin.com/company/socialowls"), ("Facebook", "https://facebook.com/socialowls"), ("TikTok", "https://tiktok.com/@socialowls")])}</div>
  </div></div>
</section>
<script>(function(){{var h=location.hash.slice(1),m;var R={json.dumps({str(k): room_url(k) for k in ROOMSLUG})};var W={json.dumps({b["slug"]: [social_url(b) if has_social(b) else main_url(b), id_url(b) if "Branding" in b["kind"] else main_url(b), ph_url(b) if "Photography" in b["kind"] else main_url(b)] for b in B.values()})};
if((m=h.match(/^room-(\\d+)$/))&&R[m[1]])location.replace(R[m[1]]);else if((m=h.match(/^(b|id|ph)-(.+)$/))&&W[m[2]])location.replace(W[m[2]][{{b:0,id:1,ph:2}}[m[1]]]);}})();</script>'''
    org = {"@context": "https://schema.org", "@type": "ProfessionalService", "@id": BASE + "/#org",
           "name": "Social Owls", "url": BASE + "/", "logo": BASE + src('logos/so-wordmark.png'), "image": BASE + "/thumbnail.png",
           "description": SITE_DESC, "slogan": "Don’t do social. Be social.", "foundingDate": "2021",
           "email": "letstalk@socialowls.agency", "telephone": ["+971505089055", "+201556331102"],
           "areaServed": [{"@type": "Country", "name": "United Arab Emirates"}, {"@type": "Country", "name": "Egypt"}],
           "address": [{"@type": "PostalAddress", "addressLocality": "Cairo", "addressCountry": "EG"}, {"@type": "PostalAddress", "addressLocality": "Dubai", "addressCountry": "AE"}],
           "founder": {"@type": "Person", "name": "Mary Gaied", "jobTitle": "Founder"},
           "knowsAbout": ["Social media strategy", "Social media management", "Brand identity", "Brand strategy", "Content creation", "Digital PR", "Media planning and buying", "Influencer management", "Community management"],
           "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Services", "itemListElement": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": n, "description": ", ".join(it)}} for n, it in S["serv"]]},
           "sameAs": ["https://instagram.com/social.owls", "https://linkedin.com/company/socialowls", "https://facebook.com/socialowls", "https://tiktok.com/@socialowls"]}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}
    site = {"@context": "https://schema.org", "@type": "WebSite", "name": "Social Owls", "url": BASE + "/", "publisher": {"@id": BASE + "/#org"}}
    return page('/', 'Social Owls | Social Media & Branding Agency in the UAE & Egypt',
                'Strategy-first social media and branding agency with offices in Egypt and the UAE. 66 brand partners across the UAE & Egypt. See our work by industry.',
                body, [org, site, faq])

# ---------- 5. room pages ----------
def bcard(b, url, chips):
    lgo = f'<img src="{src(b["logo"])}" alt="{e(b["name"])} logo" loading="lazy">' if b.get('logo') else f'<b>{e(b["name"])}</b>'
    return f'<a class="bcard" href="{url}"><div class="lgo">{lgo}</div><div class="bt"><strong>{e(b["name"])}</strong><div class="chips">{"".join(f"<span class=chip>{e(k)}</span>" for k in chips)}</div></div></a>'

def room_page(r):
    R = ROOMS[r - 1]; bs = room_brands(r)
    mode = 'id' if r == 9 else 'ph' if r == 10 else 'b'
    def url(b): return id_url(b) if mode == 'id' else ph_url(b) if mode == 'ph' else main_url(b)
    def card(it):
        b = it['b']
        if it['kind'] == 'brand':
            return bcard(b, url(b), services_of(b, mode) + ([f'▶ {len(b["reels"])} reels'] if mode == 'b' and b['reels'] else []))
        if b:  # logo-only entry that has its own branding/photo page
            return bcard(dict(b, name=it['name'], logo=it['logo'] or b.get('logo')), main_url(b), [k for k in b['kind'] if k != 'Reels'][:2])
        lg = f'<img src="{src(it["logo"])}" alt="{e(it["name"])} logo" loading="lazy">' if it['logo'] else f'<b>{e(it["name"])}</b>'
        return f'<div class="bcard plain"><div class="lgo">{lg}</div><div class="bt"><strong>{e(it["name"])}</strong></div></div>'
    def tagged(it):
        h = card(it)
        return h.replace('<div class="lgo">', f'<div class="lgo"><em class="ctag {CCLS[it["country"]]}">{e(it["country"])}</em>', 1)
    cards = '<div class="bgrid">' + ''.join(tagged(it) for it in room_items(r)) + '</div>'
    others = ''
    names = ', '.join(it['name'] for it in room_items(r))
    if r == 9:
        intro = f'Brand identities built by Social Owls: strategy, logo and visual systems, guidelines, packaging and applications. Projects include {names}.'
        title = 'Branding & Brand Identity Projects | Social Owls'
    elif r == 10:
        intro = f'Product, food and lifestyle photography by Social Owls for {names}.'
        title = 'Photography | Social Owls'
    else:
        intro = f'Social Owls’ work in {R["ind"].lower().replace("ai", "AI")}: social media management, content, reels and branding for {names}.'
        title = f'{R["ind"].replace("Ai", "AI")} Social Media & Branding Work | Social Owls'
    nav = ''.join(f'<a href="{room_url(x)}"><small>{"Previous" if x < r else "Next"} room</small>{e(ROOMS[x - 1]["name"])}</a>' if 1 <= x <= 10 else '<span></span>' for x in (r - 1, r + 1))
    body = f'''<a class="back" href="/#work">← All industries</a>
<div class="roomhead {ACC[r]}"><div class="eyebrow">{e(LABEL[r])}</div><h1>{e(R["name"])}</h1><p>{e(R["line"])}</p></div>
<p class="sec-lead">{e(intro)}</p>
{cards}
<div class="pager">{nav}</div>'''
    path = room_url(r)
    ld = [crumbs([('Home', '/'), (R['name'] if r != 9 else 'Branding', path)]),
          {"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "url": BASE + path, "about": R['ind'],
           "hasPart": [{"@type": "CreativeWork", "name": b['name'], "url": BASE + url(b)} for b in bs]}]
    return path, page(path, title, intro[:300], body, ld)

# ---------- 6. brand pages ----------
def brand_page(b, mode):
    r = 9 if mode == 'id' else 10 if mode == 'ph' else b['room']
    R = ROOMS[r - 1]; lst = room_brands(r); i = [x['slug'] for x in lst].index(b['slug'])
    urlf = {'b': lambda x: main_url(x), 'id': id_url, 'ph': ph_url}[mode]
    path = {'b': social_url, 'id': id_url, 'ph': ph_url}[mode](b)
    other = []
    if mode != 'b' and has_social(b): other.append((social_url(b), 'See the social media'))
    if mode != 'id' and 'Branding' in b['kind']: other.append((id_url(b), 'See the branding'))
    if mode != 'ph' and 'Photography' in b['kind']: other.append((ph_url(b), 'See the photography'))
    both = 'Branding' in b['kind'] and 'Photography' in b['kind']
    slides = [s for s in b['slides'] if not both or ((s['img'] in PH) if mode == 'ph' else (s['img'] not in PH))]
    show_slides = mode != 'b' or not ({'Branding', 'Photography'} & set(b['kind']))
    ind = IND[b['room']].replace('Ai', 'AI')
    what = {'b': kind_sentence(b) or 'social media', 'id': 'brand identity', 'ph': 'photography'}[mode]
    desc = f'{b["name"]}: {what} by Social Owls, a strategy-first social media and branding agency in the UAE & Egypt.'
    if b.get('tagline'): desc = f'{b["name"]}, {b["tagline"].rstrip(".")}. {what[0].upper() + what[1:]} by Social Owls, UAE & Egypt.'
    counts = []
    if mode == 'b' and b['posts']: counts.append(f'{len(b["posts"])} social media posts')
    if mode == 'b' and b['reels']: counts.append(f'{len(b["reels"])} reels')
    if show_slides and slides: counts.append(f'{len(slides)} {"identity and application boards" if mode == "id" else "photographs" if mode == "ph" else "project boards"}')
    about = f'{b["name"]} is a {ind.lower().replace("ai","AI")} client of Social Owls. Our work for {b["name"]} on this page: {what}.' + (f' This page shows {", ".join(counts)}.' if counts else '')
    parts = []
    if mode == 'b' and b['reels']:
        parts.append('<h2 class="sub">Reels · tap to watch</h2><div class="rail"><div class="track reels">' + ''.join(f'<a class="reel" href="{e(x["url"])}" target="_blank" rel="noopener"><div class="th"><img src="{src(x["thumb"])}" alt="{e(b["name"])} reel: {e(x["title"])}" loading="lazy"><div class="pl"><i></i></div></div><span>{e(x["title"])}</span></a>' for x in b['reels']) + '</div><button class="rail-btn prev" type="button" aria-label="Scroll left">‹</button><button class="rail-btn next" type="button" aria-label="Scroll right">›</button></div>')
    if mode == 'b' and b.get('markets'):
        for m in b['markets']:
            parts.append(f'<h2 class="sub">{e(m["name"])} · posts <a class="handle" href="https://www.instagram.com/{e(m["handle"])}/" target="_blank" rel="noopener">@{e(m["handle"])}</a></h2><div class="rail"><div class="track posts">' + ''.join(f'<button class="shot" type="button" data-z="{src(p)}"><img src="{src(p)}" alt="{e(m["name"])} social media post {n + 1} designed by Social Owls" loading="lazy"></button>' for n, p in enumerate(m['posts'])) + '</div><button class="rail-btn prev" type="button" aria-label="Scroll left">‹</button><button class="rail-btn next" type="button" aria-label="Scroll right">›</button></div>')
    elif mode == 'b' and b['posts']:
        parts.append('<h2 class="sub">Social media posts</h2><div class="rail"><div class="track posts">' + ''.join(f'<button class="shot" type="button" data-z="{src(p)}"><img src="{src(p)}" alt="{e(b["name"])} social media post {n + 1} designed by Social Owls" loading="lazy"></button>' for n, p in enumerate(b['posts'])) + '</div><button class="rail-btn prev" type="button" aria-label="Scroll left">‹</button><button class="rail-btn next" type="button" aria-label="Scroll right">›</button></div>')
    if show_slides and slides:
        h = 'Identity &amp; applications' if mode == 'id' else 'Photography' if mode == 'ph' else 'Behind the work'
        parts.append(f'<h2 class="sub">{h}</h2><div class="slides">' + ''.join(f'<figure><button class="shot" type="button" data-z="{src(s["img"])}"><img src="{src(s["img"])}" alt="{e(b["name"])} {e(s.get("cap") or what)}" loading="lazy"></button>{f"<figcaption>{e(s["cap"])}</figcaption>" if s.get("cap") else ""}</figure>' for s in slides) + '</div>')
    prev = lst[i - 1] if i > 0 else None; nxt = lst[i + 1] if i + 1 < len(lst) else None
    pager = (f'<a href="{urlf(prev)}"><small>Previous</small>{e(prev["name"])}</a>' if prev else '<span></span>') + (f'<a href="{urlf(nxt)}"><small>Next</small>{e(nxt["name"])}</a>' if nxt else f'<a href="{room_url(r)}"><small>Done here?</small>Back to {e(R["name"])}</a>')
    lgo = f'<img src="{src(b["logo"])}" alt="{e(b["name"])} logo">' if b.get('logo') else f'<b style="color:var(--mid);font-size:24px">{e(b["name"])}</b>'
    body = f'''<a class="back" href="{room_url(r)}">← {e(R["name"] if r != 9 else "Branding")}</a>
<div class="bhead"><div class="lgo">{lgo}</div>
<div><div class="eyebrow">{e(R["name"])} · {e(ind if r < 9 else R["ind"])} · {e(b.get("country", "Egypt"))}</div><h1>{e(b["name"])}</h1>{f'<p class="tag">{e(b["tagline"])}</p>' if b.get("tagline") else ''}
<div class="chips" style="margin-top:14px">{"".join(f"<span class=chip>{e(k)}</span>" for k in services_of(b, mode))}</div>
{('<div class="xlinks">' + ''.join(f'<a href="{u}">{t} →</a>' for u, t in other) + '</div>') if other else ''}</div></div>
<p class="sec-lead">{e(about)}</p>
{(f'<div class="mnote"><b>{len(b["markets"])} markets</b><span>{e(b["note"])}</span><div class="mk">' + ''.join(f'<a href="https://www.instagram.com/{e(m["handle"])}/" target="_blank" rel="noopener">{e(m["name"])}</a>' for m in b['markets']) + '</div></div>') if mode == 'b' and b.get('note') and b.get('markets') else ''}
{''.join(parts)}
<div class="pager">{pager}</div>'''
    title = f'{b["name"]} · {"Brand Identity" if mode == "id" else "Photography" if mode == "ph" else "Social Media"} | Social Owls'
    ld = [crumbs([('Home', '/'), (R['name'] if r != 9 else 'Branding', room_url(r)), (b['name'], path)]),
          {"@context": "https://schema.org", "@type": "CreativeWork", "name": f'{b["name"]}: {what}', "url": BASE + path, "description": about,
           "creator": {"@id": BASE + "/#org", "@type": "Organization", "name": "Social Owls"}, "about": {"@type": "Organization", "name": b['name']},
           "genre": what, "image": [BASE + src(p) for p in (b['posts'] if mode == 'b' else [s['img'] for s in slides])[:6]]}]
    return path, page(path, title, desc[:300], body, ld)

# ---------- 7. write ----------
written = []
def write(path, content):
    fp = REPO + path + ('index.html' if path.endswith('/') else '')
    os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, 'w').write(content); written.append(path)

for d in ('rooms', 'work', 'branding', 'photography'):
    shutil.rmtree(REPO + '/' + d, ignore_errors=True)
write('/', home_page())
for r in range(1, 11):
    p, c = room_page(r); write(p, c)
for b in B.values():
    if has_social(b): p, c = brand_page(b, 'b'); write(p, c)
    if 'Branding' in b['kind']: p, c = brand_page(b, 'id'); write(p, c)
    if 'Photography' in b['kind']: p, c = brand_page(b, 'ph'); write(p, c)

EXTRA_CSS = '''
/* static site additions */
.pillars{list-style:none;counter-reset:p;margin:22px 0 0;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:28px}
.pillars li{counter-increment:p;position:relative;padding-top:44px;color:var(--fg-dim);font-size:16px;line-height:1.55}
.pillars li::before{content:"0" counter(p);position:absolute;top:0;left:0;font-family:var(--serif);font-style:italic;font-weight:700;font-size:28px;color:var(--mid)}
.pillars b{display:block;color:var(--ink);font-size:18px;margin-bottom:4px}
.room .no{font-size:11px;letter-spacing:.16em;text-transform:uppercase;font-weight:800}
nav.main a.cta{background:var(--ink);color:#fff}nav.main a.cta:hover{background:var(--mid);color:#fff}
section[id]{scroll-margin-top:84px}
@media (max-width:760px){
 header.top .wrap{flex-wrap:wrap;gap:6px;padding-block:10px 6px}
 nav.main{margin-left:0;width:100%;flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;margin-inline:-16px;padding-inline:16px;width:calc(100% + 32px)}
 nav.main::-webkit-scrollbar{display:none}
 nav.main a{flex:none;font-size:12px;padding:7px 11px}
 nav.main a.hm{display:inline-block}
 .pillars{grid-template-columns:1fr;gap:18px;margin-top:16px}
 .pillars li{padding:0 0 0 44px;font-size:15px}
 .pillars li::before{font-size:22px;top:-2px}
 .pillars b{font-size:16px}
 section[id]{scroll-margin-top:112px}
 .serv{gap:10px}.serv div{padding:16px 18px}.serv h3{font-size:17px;margin-bottom:6px}
 .serv ul{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:0;font-size:14px;line-height:1.6}
 .serv li:not(:last-child)::after{content:"·";margin:0 7px;color:var(--lav)}
 .s3 b{font-size:26px}
}
.about-grid p{margin:0;font-size:17px;color:var(--fg-dim);background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:20px}
.sec-lead{color:var(--fg-dim);font-size:17px;max-width:70ch;margin:14px 0 6px}
.sec-head .more{font-weight:700;color:var(--mid);text-decoration:none}
.bcard .bdesc{font-size:14px;color:var(--fg-dim);line-height:1.35}
.how{display:block;margin:22px 0 0;font-size:15px;font-weight:600;color:var(--fg-dim)}.how span{color:var(--mid);margin:0 4px;background:none;border:0;padding:0}
.cases{grid-template-columns:1fr;gap:18px}
.swipe-hint{display:none}
.case{background:var(--ink);color:#fff;border-radius:24px;padding:36px 40px;position:relative;overflow:hidden}
.case .eyebrow{color:var(--lime)}
.case-top{display:grid;grid-template-columns:1fr 240px;gap:28px;align-items:start}
.case h3{font-size:clamp(28px,4vw,52px);font-weight:900;margin-top:10px;color:#fff;letter-spacing:-.01em}
.case-sub{font-family:var(--serif);font-style:italic;font-weight:700;color:var(--lime);font-size:clamp(20px,2.6vw,32px);margin:8px 0 0}
.case-intro{color:#e8e0f4;margin:14px 0 0;max-width:60ch;font-size:17px}
.case-logo{order:2;display:grid;place-items:center;height:150px;background:#fff;border-radius:18px;padding:20px}
.case-logo img{max-width:100%;max-height:100px;object-fit:contain}
.case-cols{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;margin-top:28px}
.cc{border-radius:16px;padding:20px 22px;color:var(--ink);position:relative;min-height:150px}
.cc:nth-child(1){background:var(--lime)}.cc:nth-child(2){background:var(--mint)}.cc:nth-child(3){background:var(--lav)}
.cc:not(:last-child)::after{content:"";position:absolute;right:-16px;top:50%;margin-top:-7px;border-left:9px solid var(--lime);border-top:7px solid transparent;border-bottom:7px solid transparent}
.cc h4{margin:0 0 8px;font-size:12px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--mid)}
.cc p{margin:0;font-size:16px;font-weight:600;line-height:1.45}
.case-link{display:inline-block;margin-top:22px;font-weight:700;color:var(--lime);text-decoration:none}
.case-link:hover{text-decoration:underline}
@media (max-width:760px){
.cases{gap:24px}
.case{padding:26px 22px 24px;border-radius:22px}
.case-top{display:block}.case-top::after{content:'';display:block;clear:both}
.case-logo{order:0;float:right;width:76px;height:56px;padding:8px;border-radius:12px;margin:0 0 10px 16px}.case-logo img{max-height:38px}
.case .eyebrow{font-size:11px;letter-spacing:.18em;line-height:1.5}
.case h3{font-size:25px;line-height:1.15;margin-top:10px}
.case-sub{font-size:17px;line-height:1.3;margin-top:8px}
.case-intro{display:none}
.case-cols{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;scroll-padding-left:22px;margin:22px -22px 0;padding:0 22px 4px;scrollbar-width:none}
.case-cols::-webkit-scrollbar{display:none}
.cc{flex:0 0 80%;scroll-snap-align:start;min-height:0;padding:20px 20px 22px}
.cc h4{margin-bottom:10px}
.cc p{font-size:15px;font-weight:500;line-height:1.6}
.cc:not(:last-child)::after{display:none}

.case-link{margin-top:18px}}
'''

COLOR_CSS = """
/* spacing + colour pass */
body{line-height:1.6;overflow-x:hidden}
p,li{font-weight:400}
.lead,.sec-lead,.case-intro,.host p,.faq p,.pillars li{line-height:1.65}
.eyebrow{display:inline-flex;align-items:center;gap:8px}
.eyebrow::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--acc-lime);flex:none}
.case .eyebrow::before{background:var(--lime)}
.pillars li:nth-child(1)::before{color:var(--acc-lime)}.pillars li:nth-child(2)::before{color:var(--acc-mint)}.pillars li:nth-child(3)::before{color:var(--acc-lav)}
.s2 b{color:var(--acc-mint)}.s4 b{color:var(--acc-lime)}
.serv div{border-top:3px solid var(--acc-lav)}
.serv div:nth-child(3n+1){border-top-color:var(--acc-lime)}.serv div:nth-child(3n+2){border-top-color:var(--acc-mint)}
#services,#faq{position:relative;isolation:isolate}
#services::before,#faq::before{content:"";position:absolute;top:0;bottom:0;left:calc(50% - 50vw);right:calc(50% - 50vw);z-index:-1}
#services::before{background:#f3f8ec}#faq::before{background:#eef7f6}
.faq summary::marker{color:var(--acc-mint)}
.host{border-left:5px solid var(--acc-lime)}
.contact{background:linear-gradient(135deg,#efe7f8,#e7f3f2)}
@media (max-width:760px){
 section{padding-block:44px}
 .sec-head{margin-bottom:16px}
 .sec-head h2{font-size:32px;line-height:1.1}
 .hero{padding-block:32px 12px;gap:28px}
 .hero h1{font-size:46px;line-height:1.02}
 .lead{font-size:16px;margin-top:18px}
 .how{font-size:14px;margin-top:16px}
 .stats{gap:10px}
 .sec-lead{font-size:15px;margin-top:6px}
 .pillars{gap:22px}
 .host{padding:22px 20px;gap:14px;border-left-width:4px}.host h2{font-size:30px}.host .serif{font-size:22px}.host p{font-size:15px}
 .serv{gap:12px}
 .plan{gap:14px}.room{padding:18px 18px 16px}
 .bgrid{gap:12px}
 .faq details{padding:14px 16px}.faq summary{font-size:15px;line-height:1.4}
 .contact{padding:24px 20px;gap:18px}.contact h2{font-size:36px}
 footer .wrap{font-size:13px}
 #branding .bdesc{display:none}
}
"""
open(REPO + '/site.css', 'w').write(CSS + EXTRA_CSS + COLOR_CSS + '''
/* country tags */
.room .ctag{font-style:normal;align-self:center;font-size:9px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--mid);background:var(--fog);border-radius:999px;padding:4px 7px;white-space:nowrap}
.bcard .lgo{position:relative}
.bcard .ctag{position:absolute;top:10px;left:10px;font-style:normal;font-size:10px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:var(--mid);background:var(--fog);border-radius:999px;padding:3px 8px}
.ctag.k-uae{background:#bcda7b;color:#2a1645}.ctag.k-ksa{background:#bce4e3;color:#2a1645}.ctag.k-om{background:#c9bbdc;color:#2a1645}
.ctag.k-kw{background:#765da8;color:#fff}.ctag.k-eg{background:#2a1645;color:#fff}.ctag.k-me{background:#f6d9b8;color:#2a1645}
.ctag.k-eu{background:#fff;color:#2a1645;box-shadow:inset 0 0 0 1.5px #2a1645}.ctag.k-multi{background:linear-gradient(90deg,#2a1645 0,#2a1645 33%,#bcda7b 33%,#bcda7b 66%,#c9bbdc 66%);color:#fff;text-shadow:0 0 3px #2a1645}
.room .lg i.k-uae{border-color:#bcda7b}.room .lg i.k-ksa{border-color:#8fcfcd}.room .lg i.k-om{border-color:#c9bbdc}.room .lg i.k-kw{border-color:#765da8}
.room .lg i.k-eg{border-color:rgba(42,22,69,.35)}.room .lg i.k-me{border-color:#f0c38f}.room .lg i.k-eu{border-color:#2a1645}.room .lg i.k-multi{border-color:#a7b9e0}
.room .lg i{border-width:1.5px}
.room .lg{gap:8px}
.room .cl{display:inline-flex;flex-wrap:wrap;align-items:center;gap:5px;padding:5px;border-radius:12px;max-width:100%}
.room .cl .ctag{margin:0 2px}
.room .cl{background:#f4f1f8}.room .cl.eg{background:none;padding:5px 0}
.room .lg i{border-color:#e6e0ef!important;transition:opacity .25s,transform .25s}
.cfilter{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px}
.fchip{font-family:var(--sans);font-size:11px;line-height:1;font-weight:800;letter-spacing:.14em;text-transform:uppercase;color:#2a1645;background:#fff;border:1.5px solid #e2dcec;border-radius:999px;padding:10px 15px;display:inline-flex;align-items:center;gap:8px;cursor:pointer;transition:border-color .2s,background .2s}
.fchip:hover{border-color:#765da8}
.fchip small{font-size:11px;letter-spacing:0;color:#765da8;font-weight:800}
.room .ctag[data-c]{cursor:pointer;transition:transform .15s}.room .ctag[data-c]:hover{transform:scale(1.08)}
.stat.s3{container-type:inline-size}.stat.s3 b{white-space:nowrap;font-size:min(44px,20cqw)}
.fchip .dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.dot.k-uae{background:#bcda7b}.dot.k-ksa{background:#7fcfcb}.dot.k-om{background:#c9bbdc}.dot.k-kw{background:#765da8}.dot.k-me{background:#f0c48f}.dot.k-eu{background:#fff;box-shadow:inset 0 0 0 1.5px #2a1645}.dot.k-eg{background:#2a1645}
.fchip.on{background:#2a1645;color:#fff;border-color:#2a1645}.fchip.on small{color:#c9bbdc}
.cfilter{margin-bottom:22px}
.plan.filtering .lg i:not(.hit),.plan.filtering .ctag:not(.hit){opacity:.14}
.plan.filtering .cl:not(.hit){background:transparent}
.plan.filtering .lg i.hit{transform:scale(1.04)}
.plan.filtering .room:not(.hit){opacity:.45}
.room .lt{display:contents}
.mnote{display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;background:#2a1645;color:#fff;border-radius:18px;padding:18px 22px;margin:0 0 28px}
.mnote b{font-family:var(--serif);font-style:italic;font-size:26px;color:#bcda7b;font-weight:700}
.mnote span{flex:1;min-width:220px;font-size:15px;line-height:1.5}
.mnote .mk{display:flex;gap:8px;flex-wrap:wrap}
.mnote .mk a{font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:#2a1645;background:#bce4e3;padding:8px 12px;border-radius:999px;text-decoration:none}
.mnote .mk a:nth-child(2){background:#bcda7b}.mnote .mk a:nth-child(3){background:#c9bbdc}
h2.sub .handle{font-family:var(--sans);font-style:normal;font-size:13px;font-weight:700;color:#765da8;margin-left:8px;text-decoration:none}
.room .rsum,.room .more,.room .ct{display:none}
.room .li{display:contents}
.dot.k-multi{background:linear-gradient(90deg,#2a1645 33%,#bcda7b 33% 66%,#c9bbdc 66%)}
@media(max-width:700px){
.cfilter{gap:6px;margin-bottom:18px}
.fchip{font-size:10px;letter-spacing:.1em;padding:8px 11px;gap:6px}
.fchip small{font-size:10px}
.room{padding:18px 16px 16px}
.room .lg{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:4px!important}
.room .cl,.room .cl.eg,.room .lt{display:contents}
.room .cl .ctag{display:none}
.room .lg i{width:auto!important;height:auto!important;display:flex!important;flex-direction:column-reverse;justify-content:flex-end;padding:0!important;overflow:hidden;border-radius:9px}
.room .li{display:grid!important;place-items:center;aspect-ratio:3/2;padding:4px}
.room .ct{display:block;font-style:normal;align-self:center;margin-top:5px;border-radius:4px;text-decoration:none;font-size:7.5px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;text-align:center;line-height:1;padding:4px 2px;background:#f4f1f8;color:#2a1645;white-space:nowrap;overflow:hidden}
.ct.k-uae{background:#bcda7b}.ct.k-ksa{background:#bce4e3}.ct.k-om{background:#c9bbdc}.ct.k-kw{background:#765da8;color:#fff}.ct.k-me{background:#f6d9b8}.ct.k-eu{background:#fff;box-shadow:inset 0 1px #2a1645}.ct.k-eg{background:#2a1645;color:#fff}.ct.k-multi{background:#2a1645;color:#fff;letter-spacing:.02em}
.plan.filtering .room:not(.hit){display:none}
.plan.filtering .lg i:not(.hit){display:none!important}
.plan.filtering .room{opacity:1}
}
.bcard.plain{cursor:default}.bcard.plain:hover{transform:none;box-shadow:none}

/* horizontal rails for posts and reels */
.rail{position:relative}
.track{display:flex!important;gap:14px;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;padding:4px 2px 14px;scrollbar-width:thin;columns:auto!important}
.track>*{flex:none;scroll-snap-align:start;margin:0!important}
.track.posts .shot{height:380px;width:auto;background:var(--card)}
.track.posts .shot img{height:100%;width:auto;max-width:none;object-fit:contain}
.track.reels .reel{width:220px}
.rail-btn{position:absolute;top:calc(50% - 30px);width:44px;height:44px;border-radius:50%;border:1px solid var(--line);background:rgba(255,255,255,.95);color:var(--ink);font-size:26px;line-height:1;cursor:pointer;box-shadow:0 6px 18px rgba(42,22,69,.15);display:grid;place-items:center;z-index:2}
.rail-btn.prev{left:-12px}.rail-btn.next{right:-12px}
.rail-btn[hidden]{display:none}
@media (max-width:760px){.track{gap:10px;margin-inline:-16px;padding-inline:16px;scroll-padding-left:16px}.track.posts .shot{height:300px}.track.reels .reel{width:170px}.rail-btn{display:none}}
''')
open(REPO + '/site.js', 'w').write('''const pl=document.querySelector('.plan');document.querySelectorAll('.fchip').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.fchip').forEach(x=>x.classList.toggle('on',x===b));const f=b.dataset.f;pl.classList.toggle('filtering',!!f);pl.querySelectorAll('.hit').forEach(x=>x.classList.remove('hit'));if(!f)return;pl.querySelectorAll('[data-c]').forEach(x=>{if(x.dataset.c.split(' ').includes(f)){x.classList.add('hit');const cl=x.closest('.cl');cl&&cl.classList.add('hit');x.closest('.room').classList.add('hit')}})}));
pl&&pl.addEventListener('click',ev=>{const t=ev.target.closest('.ctag[data-c]');if(!t)return;ev.preventDefault();ev.stopPropagation();const k=t.dataset.c.split(' ');const cur=(document.querySelector('.fchip.on')||{}).dataset;const f=k.length>1?'':(cur&&cur.f===k[0]?'':k[0]);const b=document.querySelector('.fchip[data-f="'+f+'"]');b&&b.click()},true);
const lb=document.getElementById('lb'),lbi=document.getElementById('lbi');
document.addEventListener('click',e=>{const z=e.target.closest('[data-z]');if(z){lbi.src=z.dataset.z;lb.hidden=false;return}
const c=e.target.closest('[data-copy]');if(c){navigator.clipboard&&navigator.clipboard.writeText(c.dataset.copy).then(()=>{c.textContent='Copied';setTimeout(()=>c.textContent='Copy',1500)});return}
if(e.target===lb||e.target.id==='lbx'){lb.hidden=true;lbi.src=''}});
addEventListener('keydown',e=>{if(e.key==='Escape'&&!lb.hidden){lb.hidden=true;lbi.src=''}});
document.querySelectorAll('.rail').forEach(r=>{const t=r.querySelector('.track'),p=r.querySelector('.prev'),n=r.querySelector('.next');
const u=()=>{p.hidden=t.scrollLeft<8;n.hidden=t.scrollLeft+t.clientWidth>=t.scrollWidth-8};
p.onclick=()=>t.scrollBy({left:-t.clientWidth*.8});n.onclick=()=>t.scrollBy({left:t.clientWidth*.8});
t.addEventListener('scroll',u,{passive:true});addEventListener('resize',u);t.querySelectorAll('img').forEach(i=>i.addEventListener('load',u));u()});
''')
# sitemap / robots / llms.txt
urls = ''.join(f'<url><loc>{BASE}{p}</loc><lastmod>{TODAY}</lastmod></url>' for p in written)
open(REPO + '/sitemap.xml', 'w').write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
open(REPO + '/robots.txt', 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')
L = ['# Social Owls', '', f'> {SITE_DESC}', '',
     'Social Owls (socialowls.agency) is a strategy-first social media and branding agency founded in 2021 by Mary Gaied, with offices in Egypt and the UAE. We build positioning, brand identities and social media content systems that connect content to business growth.', '',
     'Contact: letstalk@socialowls.agency · UAE +971 50 508 9055 · Egypt +20 155 633 1102', '',
     '## Services', *[f'- {n}: {", ".join(it)}' for n, it in S['serv']], '',
     '## Work by industry']
for r in range(1, 11):
    R = ROOMS[r - 1]; L.append(f'- [{R["name"]} ({R["ind"].replace("Ai","AI")})]({BASE}{room_url(r)}): ' + ', '.join(b['name'] for b in room_brands(r)))
L += ['', '## Brand pages']
for b in B.values():
    L.append(f'- [{b["name"]}]({BASE}{main_url(b)}): {b.get("tagline") or kind_sentence(b)}')
open(REPO + '/llms.txt', 'w').write('\n'.join(L) + '\n')
print(len(written), 'pages,', len(PATH), 'images')
