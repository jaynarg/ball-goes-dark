"""
Rebuild index.html from live openfootball data.

    python refresh.py

Pulls the 104-match dataset, recomputes every team's record, scorers and stage,
injects it into template.html alongside the pre-baked flags, and writes index.html.
Commit index.html and Vercel redeploys. No Node, no npm, no build step.

Only the standard library is used.
"""
import json, urllib.request, pathlib, sys

HERE = pathlib.Path(__file__).parent
SRC  = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

print(f"fetching {SRC}")
with urllib.request.urlopen(SRC, timeout=30) as r:
    WC = json.loads(r.read().decode("utf-8"))
M = WC["matches"]
print(f"  {len(M)} matches, {sum(1 for m in M if 'score' in m)} played")

CODE = {
 'Algeria':'ALG','Argentina':'ARG','Australia':'AUS','Austria':'AUT','Belgium':'BEL',
 'Bosnia & Herzegovina':'BIH','Brazil':'BRA','Canada':'CAN','Cape Verde':'CPV','Colombia':'COL',
 'Croatia':'CRO','Curaçao':'CUW','Czech Republic':'CZE','DR Congo':'COD','Ecuador':'ECU',
 'Egypt':'EGY','England':'ENG','France':'FRA','Germany':'GER','Ghana':'GHA','Haiti':'HAI',
 'Iran':'IRN','Iraq':'IRQ','Ivory Coast':'CIV','Japan':'JPN','Jordan':'JOR','Mexico':'MEX',
 'Morocco':'MAR','Netherlands':'NED','New Zealand':'NZL','Norway':'NOR','Panama':'PAN',
 'Paraguay':'PAR','Portugal':'POR','Qatar':'QAT','Saudi Arabia':'KSA','Scotland':'SCO',
 'Senegal':'SEN','South Africa':'RSA','South Korea':'KOR','Spain':'ESP','Sweden':'SWE',
 'Switzerland':'SUI','Tunisia':'TUN','Turkey':'TUR','USA':'USA','Uruguay':'URU','Uzbekistan':'UZB'}

# FIFA/Coca-Cola Men's World Ranking, official release of 11 June 2026 (published hours before kickoff)
RANK = {'Argentina':1,'Spain':2,'France':3,'England':4,'Portugal':5,'Brazil':6,'Morocco':7,
 'Netherlands':8,'Belgium':9,'Germany':10,'Croatia':11,'Colombia':13,'Mexico':14,'Senegal':15,
 'Uruguay':16,'USA':17,'Japan':18,'Switzerland':19,'Iran':20,'Turkey':22,'Ecuador':23,'Austria':24,
 'South Korea':25,'Australia':27,'Algeria':28,'Egypt':29,'Canada':30,'Norway':31,'Ivory Coast':33,
 'Panama':34,'Sweden':38,'Czech Republic':40,'Paraguay':41,'Scotland':42,'Tunisia':45,'DR Congo':46,
 'Uzbekistan':50,'Qatar':56,'Iraq':57,'South Africa':60,'Saudi Arabia':61,'Jordan':63,
 'Bosnia & Herzegovina':64,'Cape Verde':67,'Ghana':73,'Curaçao':82,'Haiti':83,'New Zealand':85}

CONF = {'Argentina':'CONMEBOL','Brazil':'CONMEBOL','Colombia':'CONMEBOL','Ecuador':'CONMEBOL',
 'Paraguay':'CONMEBOL','Uruguay':'CONMEBOL','Canada':'CONCACAF','Curaçao':'CONCACAF',
 'Haiti':'CONCACAF','Mexico':'CONCACAF','Panama':'CONCACAF','USA':'CONCACAF','Algeria':'CAF',
 'Cape Verde':'CAF','DR Congo':'CAF','Egypt':'CAF','Ghana':'CAF','Ivory Coast':'CAF',
 'Morocco':'CAF','Senegal':'CAF','South Africa':'CAF','Tunisia':'CAF','Australia':'AFC',
 'Iran':'AFC','Iraq':'AFC','Japan':'AFC','Jordan':'AFC','Qatar':'AFC','Saudi Arabia':'AFC',
 'South Korea':'AFC','Uzbekistan':'AFC','New Zealand':'OFC','Austria':'UEFA','Belgium':'UEFA',
 'Bosnia & Herzegovina':'UEFA','Croatia':'UEFA','Czech Republic':'UEFA','England':'UEFA',
 'France':'UEFA','Germany':'UEFA','Netherlands':'UEFA','Norway':'UEFA','Portugal':'UEFA',
 'Scotland':'UEFA','Spain':'UEFA','Sweden':'UEFA','Switzerland':'UEFA','Turkey':'UEFA'}

# Appearances (incl. 2026), debut year, best result prior to 2026.
# Source: Wikipedia, "National team appearances in the FIFA World Cup" (as of 18 Nov 2025).
HIST = {
 'Brazil':(23,1930,'Champions (1958, 1962, 1970, 1994, 2002)'),
 'Germany':(21,1934,'Champions (1954, 1974, 1990, 2014)'),
 'Argentina':(19,1930,'Champions (1978, 1986, 2022)'),
 'Mexico':(18,1930,'Quarter-finals (1970, 1986)'),
 'Spain':(17,1934,'Champions (2010)'),
 'England':(17,1950,'Champions (1966)'),
 'France':(17,1930,'Champions (1998, 2018)'),
 'Belgium':(15,1930,'Third place (2018)'),
 'Uruguay':(15,1930,'Champions (1930, 1950)'),
 'Switzerland':(13,1934,'Quarter-finals (1934, 1938, 1954)'),
 'South Korea':(12,1954,'Fourth place (2002)'),
 'USA':(12,1930,'Third place (1930)'),
 'Netherlands':(12,1934,'Runners-up (1974, 1978, 2010)'),
 'Sweden':(12,1934,'Runners-up (1958)'),
 'Portugal':(9,1966,'Third place (1966)'),
 'Scotland':(9,1954,'Group stage'),
 'Paraguay':(9,1930,'Quarter-finals (2010)'),
 'Czech Republic':(9,1934,'Runners-up (1934, 1962)'),
 'Japan':(8,1998,'Round of 16 (2002, 2010, 2018, 2022)'),
 'Austria':(8,1934,'Third place (1954)'),
 'Australia':(7,1974,'Round of 16 (2006, 2022)'),
 'Croatia':(7,1998,'Runners-up (2018)'),
 'Iran':(7,1978,'Group stage'),
 'Saudi Arabia':(7,1994,'Round of 16 (1994)'),
 'Morocco':(7,1970,'Fourth place (2022)'),
 'Tunisia':(7,1978,'Group stage'),
 'Colombia':(7,1962,'Quarter-finals (2014)'),
 'Ghana':(5,2006,'Quarter-finals (2010)'),
 'Ecuador':(5,2002,'Round of 16 (2006)'),
 'Algeria':(5,1982,'Round of 16 (2014)'),
 'Senegal':(4,2002,'Quarter-finals (2002)'),
 'Ivory Coast':(4,2006,'Group stage'),
 'Norway':(4,1938,'Round of 16 (1938, 1998)'),
 'South Africa':(4,1998,'Group stage'),
 'Egypt':(4,1934,'Round of 16 (1934)'),
 'Canada':(3,1986,'Group stage'),
 'New Zealand':(3,1982,'Group stage'),
 'Qatar':(2,2022,'Group stage'),
 'Haiti':(2,1974,'Group stage'),
 'Panama':(2,2018,'Group stage'),
 'Turkey':(2,1954,'Third place (2002)'),
 'DR Congo':(1,1974,'Group stage'),
 'Iraq':(1,1986,'Group stage'),
 'Bosnia & Herzegovina':(1,2014,'Group stage'),
 'Cape Verde':(1,2026,None),
 'Curaçao':(1,2026,None),
 'Jordan':(1,2026,None),
 'Uzbekistan':(1,2026,None)}

# The third-place match is played by the teams that LOST the semi-finals, so it
# must not promote them to the same stage as the finalists.
KO_ORDER = {'Round of 32':1,'Round of 16':2,'Quarter-final':3,'Semi-final':4,
            'Match for third place':4,'Final':5}
STAGE_LABEL = {0:'Group stage',1:'Round of 32',2:'Round of 16',3:'Quarter-finals',
               4:'Semi-finals',5:'Final',6:'Champions'}

teams = {t: {'name':t,'code':CODE[t],'group':None,'rank':RANK[t],'conf':CONF[t],
             'matches':[],'gf':0,'ga':0,'w':0,'d':0,'l':0,'scorers':{},'og_for':0,'og_against':0}
         for t in CODE}

for m in M:
    if m.get('group'):
        for side in ('team1','team2'):
            teams[m[side]]['group'] = m['group'].replace('Group ','')

def minute(g):
    return g['minute']

for m in M:
    t1, t2 = m['team1'], m['team2']
    if t1 not in teams or t2 not in teams:
        continue  # unresolved knockout placeholder (W99, L101, ...)
    sc = m.get('score')
    rec = {'round': m['round'], 'date': m['date'], 'ground': m['ground'],
           'ko': KO_ORDER.get(m['round'], 0)}
    if not sc:
        for a, b in ((t1, t2), (t2, t1)):
            teams[a]['matches'].append({**rec,'opp':b,'opp_code':CODE[b],'played':False})
        continue

    ft = sc['ft']; et = sc.get('et'); p = sc.get('p')
    fin = et or ft

    for a, b, i, j in ((t1,t2,0,1), (t2,t1,1,0)):
        gfa, gaa = fin[i], fin[j]
        teams[a]['gf'] += gfa; teams[a]['ga'] += gaa
        if gfa > gaa: res='W'; teams[a]['w']+=1
        elif gfa < gaa: res='L'; teams[a]['l']+=1
        else: res='D'; teams[a]['d']+=1
        # a shoot-out stays a draw in the record; the advance is noted separately
        if p:   detail = 'won %d-%d on pens' % (p[i],p[j]) if p[i]>p[j] else 'lost %d-%d on pens' % (p[i],p[j])
        elif et: detail = 'after extra time'
        else:   detail = ''
        teams[a]['matches'].append({**rec,'opp':b,'opp_code':CODE[b],'played':True,
                                    'gf':gfa,'ga':gaa,'res':res,'detail':detail,
                                    'adv': bool(p) and p[i]>p[j]})

    # goals1 belongs to team1's scoreline; owngoal entries name an opposition player
    for side, scoring, conceding in (('goals1', t1, t2), ('goals2', t2, t1)):
        for g in m.get(side, []):
            if g.get('owngoal'):
                teams[scoring]['og_for'] += 1        # gifted into this team's scoreline
                teams[conceding]['og_against'] += 1  # this team's player put it in
                continue
            s = teams[scoring]['scorers'].setdefault(g['name'], {'g':0,'pens':0,'mins':[]})
            s['g'] += 1
            if g.get('penalty'): s['pens'] += 1
            s['mins'].append(minute(g))

alive = set()
for t, d in teams.items():
    d['matches'].sort(key=lambda x: x['date'])
    if any(not x['played'] for x in d['matches']):
        alive.add(t)

# Once the final is played the champion is promoted to stage 6, so exactly one
# panel stays lit on a dark ball. Until then, the eight survivors are lit.
champion = None
for m in M:
    if m['round'] == 'Final' and m.get('score') and m['team1'] in teams:
        ft, et, p = m['score']['ft'], m['score'].get('et'), m['score'].get('p')
        fin = p or et or ft
        champion = m['team1'] if fin[0] > fin[1] else m['team2']

for t, d in teams.items():
    played = [x for x in d['matches'] if x['played']]
    d['stage'] = max([x['ko'] for x in d['matches']], default=0)
    if t == champion: d['stage'] = 6
    d['alive'] = t in alive
    d['lit'] = d['alive'] or d['stage'] == 6
    d['stage_label'] = STAGE_LABEL[d['stage']]
    d['pld'] = len(played)
    d['cs'] = sum(1 for x in played if x['ga'] == 0)
    d['gd'] = d['gf'] - d['ga']
    sc = sorted(d['scorers'].items(), key=lambda kv: (-kv[1]['g'], kv[0]))
    d['top'] = [{'name':n,'g':v['g'],'pens':v['pens'],'mins':v['mins']} for n,v in sc]
    d['n_scorers'] = len(sc)
    ap, debut, best = HIST[t]
    d['apps'] = ap; d['debut'] = debut; d['best'] = best
    d['debutant'] = debut == 2026
    del d['scorers']

# ---- tournament-wide scorer table (own goals already excluded upstream) ----
SUFFIX = {'Júnior','Junior','Filho','Neto','Jr','Jr.'}
def short(full):
    parts = full.split()
    if len(parts) >= 2 and parts[-1] in SUFFIX:
        return ' '.join(parts[:-1]) if len(parts) == 2 else parts[-2]
    return parts[-1]

boot = []
for t in sorted(teams):
    for sc in teams[t]['top']:
        boot.append({'n':sc['name'],'s':short(sc['name']),'c':CODE[t],'t':t,
                     'g':sc['g'],'pens':sc['pens']})
boot.sort(key=lambda r: (-r['g'], r['n']))
boot = [r for r in boot if r['g'] >= 3]      # client cuts at 10 and extends through ties

out = {'generated':'2026-07-08','rank_release':'2026-06-11',
       'boot':boot,
       'teams':[teams[t] for t in sorted(teams)]}

# ---------------------------------------------------------------- inject
tpl   = (HERE / "template.html").read_text(encoding="utf-8")
flags = (HERE / "data" / "flags_b64.json").read_text(encoding="utf-8")
data  = json.dumps(out, ensure_ascii=False, separators=(",", ":"))

if "/*__DATA__*/" not in tpl or "/*__FLAGS__*/" not in tpl:
    sys.exit("template.html is missing a placeholder")

html = tpl.replace("/*__DATA__*/", data).replace("/*__FLAGS__*/", flags)
(HERE / "index.html").write_text(html, encoding="utf-8")

# ---------------------------------------------------------------- checks
named = sum(s["g"] for t in out["teams"] for s in t["top"])
og    = sum(t["og_for"] for t in out["teams"])
goals = sum(t["gf"] for t in out["teams"])
assert named + og == goals, f"goal accounting off: {named} + {og} != {goals}"
for t in out["teams"]:
    assert sum(s["g"] for s in t["top"]) + t["og_for"] == t["gf"], t["name"]

lit = [t["name"] for t in out["teams"] if t["lit"]]
print(f"  {goals} goals = {named} named + {og} own goals  [ok]")
print(f"  golden boot: {out['boot'][0]['n']} ({out['boot'][0]['g']})")
print(f"  lit panels: {len(lit)} -> {', '.join(lit)}")
print(f"wrote index.html ({(HERE / 'index.html').stat().st_size:,} bytes)")
