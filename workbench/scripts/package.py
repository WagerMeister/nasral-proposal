"""Build the presentation: README, specification and images only."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, re, zipfile, sys
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'workbench'
screens=[('01_candidates','Кандидаты'),('02_voting','Рейтинг голосования'),('03_standings','Турнирная таблица'),('04_statistics','Статистика участников'),('05_games','Игры и прохождения'),('06_auctions','Аукционы'),('07_hall_of_fame','Зал славы'),('08_participant_profile','Профиль участника'),('09_comparison','Сравнение участников'),('10_auction_to_result','История назначения'),('11_season_archive','Архив сезона'),('12_vote_selection','Выбранный состав')]
routes=['candidates','voting','standings','statistics','games','auctions','hall','profile&player=mel','comparison','lot','season','selection&example=full']
data=json.loads((WORK/'src/data.json').read_text())
errors=[]
def expect(condition,message):
    if not condition:errors.append(message)
players={p['id']:p for p in data['players']}
attempts={a['id']:a for a in data['attempts']}
lots={l['id']:l for l in data['auctions']}
for p in data['players'][:8]:
    own=[a for a in data['attempts'] if a['player']==p['id']]
    expect(p['points']==sum(a['points'] or 0 for a in own),'GGP ledger mismatch: '+p['id'])
    expect(p['minutes']==sum(a['minutes'] for a in own),'time ledger mismatch: '+p['id'])
    expect(p['attempts']==len(own),'attempt count mismatch: '+p['id'])
    expect(p['finished']==sum(a['status']=='finished' for a in own),'finish count mismatch: '+p['id'])
    expect(p['dropped']==sum(a['status']=='dropped' for a in own),'drop count mismatch: '+p['id'])
    expect(sum(a['status']=='playing' for a in own)==1,'current attempt mismatch: '+p['id'])
    expect(p['minutes']<=7*10*60,'hours exceed scenario day 7 allowance: '+p['id'])
for a in data['attempts']:
    expect(a['player'] in players,'unknown participant: '+a['id'])
    expect(a['lot'] in lots,'missing lot: '+a['id'])
    l=lots[a['lot']]
    expect(l['attempt']==a['id'] and l['game']==a['game'] and l['player']==a['player'] and l['status']==a['status'],'broken assignment relation: '+a['id'])
    expect((a['points'] is None)==(a['status']=='playing'),'pending result represented as awarded: '+a['id'])
for l in data['auctions']:
    expect(l['total']==sum(o['amount'] for o in l['options']),'option bank mismatch: '+l['id'])
    winners=[o for o in l['options'] if o['winner']]
    expect(len(winners)==1,'winner cardinality: '+l['id'])
    expect(winners[0]['amount']==l['winning'] and winners[0]['game']==l['game'],'wrong winning variant: '+l['id'])
    expect(l['winning']==max(o['amount'] for o in l['options']),'winning scenario choice not top: '+l['id'])
    expect((l['attempt'] is None)==(l['status']=='waiting'),'waiting assignment mismatch: '+l['id'])
expect(data['history'][0]['rank25']==1 and data['history'][0]['rank26']==1,'archived champion mismatch')
expect(next(p for p in data['history'] if p['id']=='dunduk')['rank25']-next(p for p in data['history'] if p['id']=='dunduk')['rank26']==1,'season delta sign mismatch')
expect(len(set(data['selection']))==9,'selection fixture must have nine distinct candidates')
expect(len({a['game'] for a in data['attempts'] if a['player']=='mel' and a['status']=='finished'})==5,'duplicate completed titles in Melharucos library')
expect(all(g['hltb'] is None for g in data['games'].values()),'unverified HLTB benchmark included')
for key,title in screens:
    path=ROOT/'renders'/f'{key}.png'
    try:
        with Image.open(path) as im:
            im.load();expect(im.size==(1920,1080),'wrong render size: '+path.name)
    except Exception as exc:errors.append(f'invalid PNG {path.name}: {exc}')
browser=json.loads((WORK/'verification/browser.json').read_text())
errors.extend(browser['errors'])
expect(len(browser['states'])==12,'browser did not render twelve states')
expect(all(x['passed'] for x in browser['interactions']),'browser interaction failed')
for person in data['players']:
    expect(bool(person.get('portraitFile')),'candidate portrait missing: '+person['id'])
    expect((WORK/'assets/portraits'/person['portraitFile']).is_file(),'portrait asset unavailable: '+person['id'])
    expect('risk' not in person and 'editorial' not in person,'editorial data remains: '+person['id'])
for file in ['README.md','SPEC.md']:
    text=(ROOT/file).read_text()
    expect(not re.search(r'(?i)\bv4\b|сценарн|выбор организаторов|высокий риск|что исправлено|после ревью|визуальное и функциональное предложение',text),'process copy remains in '+file)
allowed={'.git','.gitignore','README.md','SPEC.md','renders','workbench'}
expect(not [p.name for p in ROOT.iterdir() if p.name not in allowed and p.name!='.DS_Store'],'unexpected root entries')
font_paths=[Path('/System/Library/Fonts/Supplemental/Arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
font_path=next((p for p in font_paths if p.is_file()),None)
font=ImageFont.truetype(str(font_path),32) if font_path else ImageFont.load_default()
def sheet(items,path):
    # Keep every screenshot at its original size. No downsampling of UI text.
    width,height,gap,label=1920,1080,32,50
    rows=(len(items)+1)//2
    canvas=Image.new('RGB',(width*2+gap*3,rows*(height+label)+gap*(rows+1)),'#0b1119')
    draw=ImageDraw.Draw(canvas)
    for i,(key,title) in enumerate(items):
        x=gap+(i%2)*(width+gap);y=gap+(i//2)*(height+label+gap)
        draw.text((x,y+3),title,fill='#d5b57b',font=font)
        with Image.open(ROOT/'renders'/f'{key}.png') as im:
            expect(im.size==(width,height),'source was not native-sized')
            canvas.paste(im.convert('RGB'),(x,y+label))
    canvas.save(path,quality=97,subsampling=0)
sheet(screens[:8],ROOT/'renders/overview.jpg')
sheet(screens[8:],ROOT/'renders/details_overview.jpg')
with Image.open(ROOT/'renders/overview.jpg') as im:expect(im.size==(3936,4680),'overview does not preserve native screenshot size')
for md in [ROOT/'README.md',ROOT/'SPEC.md']:
    for target in re.findall(r'\]\(([^)]+)\)',md.read_text()):
        if target.startswith(('http://','https://','#')):continue
        expect((md.parent/target.split('#')[0]).is_file(),'broken link: '+str(md.name)+' → '+target)
if errors:
    print(json.dumps({'status':'FAILED','errors':errors},ensure_ascii=False,indent=2));sys.exit(1)
public=[ROOT/'README.md',ROOT/'SPEC.md']+sorted(p for p in (ROOT/'renders').iterdir() if p.suffix in {'.png','.jpg'})
manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in public)
(WORK/'MANIFEST.sha256').write_text(manifest)
out=WORK/'dist';out.mkdir(exist_ok=True)
archive=out/'NASRAL-presentation.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in public:z.write(p,arcname='NASRAL/'+p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    expect(z.testzip() is None,'archive CRC failed')
    expect({n.split('/')[1] for n in z.namelist()}=={'README.md','SPEC.md','renders'},'internal materials leaked into presentation ZIP')
cards=''.join(f'<article><a href="../renders/{key}.png"><img src="../renders/{key}.png" alt="{title}"></a><h2>{title}</h2><a href="src/index.html?page={route}">Открыть экран</a></article>' for (key,title),route in zip(screens,routes))
(WORK/'index.html').write_text('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NASRAL — экраны</title><style>body{background:#0b1119;color:#eee;font:16px Arial;margin:40px}main{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{border:1px solid #345;padding:18px}img{width:100%}a{color:#d5b57b}h2{font-size:20px}</style><h1>NASRAL</h1><main>'+cards+'</main></html>')
report={'status':'PASS' if not errors else 'FAILED','renders':12,'checks':len(browser['interactions']),'overview_size':[3936,4680],'native_screenshot_scale':True,'presentation_files':len(public),'zip_bytes':archive.stat().st_size,'zip':str(archive.relative_to(ROOT)),'errors':errors}
(WORK/'verification/package.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
sys.exit(bool(errors))
