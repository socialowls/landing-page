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
PATH = {}  # key -> public path
for k, v in assets.items():
    mime = v[5:v.index(';')]
    root, _ = os.path.splitext(k)
    p = root + EXT.get(mime, '.bin')
    os.makedirs(os.path.dirname(REPO + '/' + p), exist_ok=True)
    open(REPO + '/' + p, 'wb').write(base64.b64decode(v.split(',', 1)[1]))
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
def room_brands(r):
    if r == 9: return BRANDING
    if r == 10: return PHOTO
    return [B[s] for s in ROOMS[r - 1]['brands']]
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

SERVICES_TEXT = {k: v for k, v in S['serv']}
SITE_DESC = ("Social Owls is a strategy-first social media and branding agency with offices in Cairo and Dubai, "
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
  <nav class="main" aria-label="Main"><a class="hm" href="/">Home</a><a href="/#rooms">Work</a><a href="/branding/">Branding</a><a class="hm" href="/#services">Services</a><a href="/#contact">Contact</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap"><span>Social Owls · Cairo &amp; Dubai · UAE &amp; Egypt · <a href="mailto:letstalk@socialowls.agency">letstalk@socialowls.agency</a></span><span class="serif">Don’t do social. Be social.</span></div></footer>
<div class="lb" id="lb" hidden><button type="button" id="lbx">Close</button><img id="lbi" alt=""></div>
<script src="/site.js" defer></script>
</body>
</html>
'''

def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(items)]}

def logo_tile(b_or_o, cls=''):
    return f'<i><img src="{src(b_or_o["logo"])}" alt="{e(b_or_o["name"])} logo" loading="lazy"></i>'

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
def floor_plan():
    out = []
    for r in ROOMS:
        bs = room_brands(r['r']); seen = set(); lg = []
        for x in bs + (r.get('others') or []):
            if x.get('logo') and x['logo'] not in seen: seen.add(x['logo']); lg.append(x)
        out.append(f'''<a class="room {ACC[r["r"]]}" href="{room_url(r["r"])}"><span class="no">R{r["r"]:02d}</span><h3>{e(r["name"])}</h3><span class="ind">{e(r["ind"])}</span>
<div class="lg">{''.join(logo_tile(x) for x in lg)}</div></a>''')
    return '<div class="plan">' + ''.join(out) + '</div>'

CASES = [("Engagement beat awareness.", "M Group Holding on LinkedIn: organic posts and paid campaigns compared side by side, so the budget went where it worked."),
         ("Built from day one.", "Project Pavilion, from blank page to brand: identity, guidelines and the content that launched it."),
         ("The grammar of a brand.", "her’, premium sportswear for women: the thinking behind the identity, turned into a carousel and a reel.")]
FAQ = [
 ("What does Social Owls do?", "Social Owls is a strategy-first social media and branding agency. We build brand positioning, visual identities and social media content systems that connect content to business results, from strategy and design to community management, paid media and reporting."),
 ("Where is Social Owls based?", "We have two offices, in Cairo, Egypt and Dubai, UAE, and we work with brands across the UAE & Egypt."),
 ("Which industries do you work with?", "We have worked with 66 brand partners across travel & tourism, food & beverage, retail, fashion & beauty, tech, medical & aesthetics, engineering & building materials, and events & entertainment."),
 ("What makes your approach different?", "Most brands don’t have a content problem, they have a strategy problem. We start with positioning and audience behaviour in each market, then build content that supports awareness, intent and conversion, rather than chasing vanity metrics."),
 ("Do you create brand identities as well as social media?", "Yes. Our branding work covers brand strategy, logo and visual systems, brand guidelines and marketing templates. You can see identities we built on our branding page."),
 ("How do I start a project with Social Owls?", "Email letstalk@socialowls.agency or call +971 50 508 9055 (UAE) or +20 155 633 1102 (Egypt)."),
]

def home_page():
    nb = len(B)
    branding_cards = ''.join(f'''<a class="bcard" href="{id_url(b)}"><div class="lgo"><img src="{src(b["logo"])}" alt="{e(b["name"])} logo" loading="lazy"></div><div class="bt"><strong>{e(b["name"])}</strong><span class="bdesc">{e(b.get("tagline") or "")}</span></div></a>''' for b in BRANDING if b.get('logo'))
    body = f'''
<section class="hero">
  <div>
    <h1>Welcome to <span class="serif">the Nest.</span></h1>
    <p class="lead">Social Owls is a strategy-first social media and branding agency in the UAE &amp; Egypt. We’ve built, grown and given a voice to 66 brands. Ten rooms, one per industry: pick a room, meet the brand, see the work.</p>
    <div class="how"><span><b>1</b>Pick a room</span><span><b>2</b>Meet the brand</span><span><b>3</b>See the posts, reels and identities</span></div>
  </div>
  <div class="stats">
    <div class="stat s1"><b>66</b><span>Brand partners</span></div>
    <div class="stat s2"><b>10</b><span>Rooms of work</span></div>
    <div class="stat s3"><b>CAI · DXB</b><span>Two offices</span></div>
    <div class="stat s4"><b>2021</b><span>The nest was built</span></div>
  </div>
</section>
<section id="about" class="about">
  <div class="sec-head"><div><div class="eyebrow">Who we are</div><h2>Strategy first. <span class="serif">Content second.</span></h2></div></div>
  <div class="about-grid">
    <p>Most brands don’t have a content problem. They have a strategy problem. Social Owls builds positioning, identity and social media systems that connect content to business growth, not vanity metrics.</p>
    <p>What works in Egypt doesn’t automatically work in the UAE. We plan market-specific content around how audiences in each market actually behave, then structure it around awareness, intent and conversion.</p>
    <p>From brand strategy and visual identity to content creation, community management, media buying and reporting, we run it as one system, so every post has a job to do.</p>
  </div>
</section>
<section id="rooms">
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
  <div class="cases">{''.join(f'<figure class="case"><button class="shot" data-z="{src(c)}" type="button"><img src="{src(c)}" alt="Case study: {e(t)} {e(d)}" loading="lazy"></button><figcaption><strong>{e(t)}</strong> {e(d)}</figcaption></figure>' for c, (t, d) in zip(S["cases"], CASES))}</div>
</section>
<section id="services">
  <div class="sec-head"><div><div class="eyebrow">How the house runs</div><h2>Seven <span class="serif">services.</span></h2></div></div>
  <div class="serv">{''.join(f'<div><h3>{e(n)}</h3><ul>{"".join(f"<li>{e(x)}</li>" for x in it)}</ul></div>' for n, it in S["serv"])}</div>
</section>
<section>
  <div class="host"><div class="badge"><img src="{src('logos/so-icon-lp.png')}" alt="" loading="lazy"></div><div>
    <div class="eyebrow">Your host</div><h2>Mary Gaied</h2><div class="serif">The founding owl.</div>
    <p>13+ years in digital marketing, on both the agency and the client side. Lead instructor and course developer of the certified Social Media Management course for the Middle East by Skillful Academy. Specialised in brand and digital strategy, content creation, media planning and buying, and reporting.</p></div></div>
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
                'Strategy-first social media and branding agency with offices in Cairo and Dubai. 66 brand partners across the UAE & Egypt. See our work by industry.',
                body, [org, site, faq])

# ---------- 5. room pages ----------
def bcard(b, url, chips):
    lgo = f'<img src="{src(b["logo"])}" alt="{e(b["name"])} logo" loading="lazy">' if b.get('logo') else f'<b>{e(b["name"])}</b>'
    return f'<a class="bcard" href="{url}"><div class="lgo">{lgo}</div><div class="bt"><strong>{e(b["name"])}</strong><div class="chips">{"".join(f"<span class=chip>{e(k)}</span>" for k in chips)}</div></div></a>'

def room_page(r):
    R = ROOMS[r - 1]; bs = room_brands(r)
    mode = 'id' if r == 9 else 'ph' if r == 10 else 'b'
    def url(b): return id_url(b) if mode == 'id' else ph_url(b) if mode == 'ph' else main_url(b)
    cards = ''.join(bcard(b, url(b), services_of(b, mode) + ([f'▶ {len(b["reels"])} reels'] if mode == 'b' and b['reels'] else [])) for b in bs)
    others = ''
    if R.get('others'):
        others = '<div class="others"><h2 class="sub">Also in this room</h2><div class="row">' + ''.join(f'<div title="{e(o["name"])}"><img src="{src(o["logo"])}" alt="{e(o["name"])} logo" loading="lazy"></div>' for o in R['others']) + '</div></div>'
    names = ', '.join(b['name'] for b in bs) + (', ' + ', '.join(o['name'] for o in R.get('others', [])) if R.get('others') else '')
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
    body = f'''<a class="back" href="/#rooms">← Floor plan</a>
<div class="roomhead {ACC[r]}"><div class="eyebrow">Room {r:02d} · {e(R["ind"].replace("Ai", "AI"))}</div><h1>{e(R["name"])}</h1><p>{e(R["line"])}</p></div>
<p class="sec-lead">{e(intro)}</p>
<div class="bgrid">{cards}</div>
{others}
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
        parts.append('<h2 class="sub">Reels · tap to watch</h2><div class="reels">' + ''.join(f'<a class="reel" href="{e(x["url"])}" target="_blank" rel="noopener"><div class="th"><img src="{src(x["thumb"])}" alt="{e(b["name"])} reel: {e(x["title"])}" loading="lazy"><div class="pl"><i></i></div></div><span>{e(x["title"])}</span></a>' for x in b['reels']) + '</div>')
    if mode == 'b' and b['posts']:
        parts.append('<h2 class="sub">Social media posts</h2><div class="posts">' + ''.join(f'<button class="shot" type="button" data-z="{src(p)}"><img src="{src(p)}" alt="{e(b["name"])} social media post {n + 1} designed by Social Owls" loading="lazy"></button>' for n, p in enumerate(b['posts'])) + '</div>')
    if show_slides and slides:
        h = 'Identity &amp; applications' if mode == 'id' else 'Photography' if mode == 'ph' else 'Behind the work'
        parts.append(f'<h2 class="sub">{h}</h2><div class="slides">' + ''.join(f'<figure><button class="shot" type="button" data-z="{src(s["img"])}"><img src="{src(s["img"])}" alt="{e(b["name"])} {e(s.get("cap") or what)}" loading="lazy"></button>{f"<figcaption>{e(s["cap"])}</figcaption>" if s.get("cap") else ""}</figure>' for s in slides) + '</div>')
    prev = lst[i - 1] if i > 0 else None; nxt = lst[i + 1] if i + 1 < len(lst) else None
    pager = (f'<a href="{urlf(prev)}"><small>Previous</small>{e(prev["name"])}</a>' if prev else '<span></span>') + (f'<a href="{urlf(nxt)}"><small>Next</small>{e(nxt["name"])}</a>' if nxt else f'<a href="{room_url(r)}"><small>Done here?</small>Back to {e(R["name"])}</a>')
    lgo = f'<img src="{src(b["logo"])}" alt="{e(b["name"])} logo">' if b.get('logo') else f'<b style="color:var(--mid);font-size:24px">{e(b["name"])}</b>'
    body = f'''<a class="back" href="{room_url(r)}">← {e(R["name"] if r != 9 else "Branding")}</a>
<div class="bhead"><div class="lgo">{lgo}</div>
<div><div class="eyebrow">{e(R["name"])} · {e(ind if r < 9 else R["ind"])}</div><h1>{e(b["name"])}</h1>{f'<p class="tag">{e(b["tagline"])}</p>' if b.get("tagline") else ''}
<div class="chips" style="margin-top:14px">{"".join(f"<span class=chip>{e(k)}</span>" for k in services_of(b, mode))}</div>
{('<div class="xlinks">' + ''.join(f'<a href="{u}">{t} →</a>' for u, t in other) + '</div>') if other else ''}</div></div>
<p class="sec-lead">{e(about)}</p>
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
.about-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.about-grid p{margin:0;font-size:17px;color:var(--fg-dim);background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:20px}
.sec-lead{color:var(--fg-dim);font-size:17px;max-width:70ch;margin:14px 0 6px}
.sec-head .more{font-weight:700;color:var(--mid);text-decoration:none}
.bcard .bdesc{font-size:14px;color:var(--fg-dim);line-height:1.35}
.case{margin:0}.case figcaption{margin-top:10px;color:var(--fg-dim);font-size:15px}.case figcaption strong{color:var(--ink)}
.faq{display:grid;gap:10px;max-width:860px}
.faq details{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.faq summary{font-weight:800;cursor:pointer;color:var(--ink)}
.faq p{margin:10px 0 0;color:var(--fg-dim)}
.copy a{text-decoration:none;overflow-wrap:anywhere}
.tag{margin:8px 0 0}
footer a{color:inherit}
@media (max-width:900px){.about-grid{grid-template-columns:1fr}}
@media (max-width:600px){.about-grid p{font-size:15px;padding:16px}.sec-lead{font-size:15px}.bcard .bdesc{font-size:13px}}
'''
open(REPO + '/site.css', 'w').write(CSS + EXTRA_CSS)
open(REPO + '/site.js', 'w').write('''const lb=document.getElementById('lb'),lbi=document.getElementById('lbi');
document.addEventListener('click',e=>{const z=e.target.closest('[data-z]');if(z){lbi.src=z.dataset.z;lb.hidden=false;return}
const c=e.target.closest('[data-copy]');if(c){navigator.clipboard&&navigator.clipboard.writeText(c.dataset.copy).then(()=>{c.textContent='Copied';setTimeout(()=>c.textContent='Copy',1500)});return}
if(e.target===lb||e.target.id==='lbx'){lb.hidden=true;lbi.src=''}});
addEventListener('keydown',e=>{if(e.key==='Escape'&&!lb.hidden){lb.hidden=true;lbi.src=''}});
''')
# sitemap / robots / llms.txt
urls = ''.join(f'<url><loc>{BASE}{p}</loc><lastmod>{TODAY}</lastmod></url>' for p in written)
open(REPO + '/sitemap.xml', 'w').write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
open(REPO + '/robots.txt', 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')
L = ['# Social Owls', '', f'> {SITE_DESC}', '',
     'Social Owls (socialowls.agency) is a strategy-first social media and branding agency founded in 2021 by Mary Gaied, with offices in Cairo, Egypt and Dubai, UAE. We build positioning, brand identities and social media content systems that connect content to business growth.', '',
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
