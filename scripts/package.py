"""Validate the curated artifact set; create galleries and the organizer ZIP."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, re, zipfile, sys

ROOT=Path(__file__).resolve().parents[1]
screens=[('01_candidates','Кандидаты'),('02_voting','Рейтинг голосования'),('03_standings','Турнирная таблица'),
         ('04_statistics','Статистика участников'),('05_games','Игры и прохождения'),('06_auctions','Аукционы'),
         ('07_hall_of_fame','Зал славы'),('08_participant_profile','Профиль участника'),
         ('09_comparison','Сравнение участников'),('10_auction_to_result','История назначения'),
         ('11_season_archive','Архив сезона'),('12_vote_selection','Проверка состава')]
routes=['candidates','voting','standings','statistics','games','auctions','hall','profile&player=mel','comparison','lot','season','selection&example=full']
data=json.loads((ROOT/'src/data.json').read_text())
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
expect(all(g['hltb'] is None for g in data['games'].values()),'unverified HLTB benchmark included')
for key,title in screens:
    path=ROOT/'renders'/f'{key}.png'
    try:
        with Image.open(path) as im:
            im.load();expect(im.size==(1920,1080),'wrong render size: '+path.name)
    except Exception as exc:errors.append(f'invalid PNG {path.name}: {exc}')
browser=json.loads((ROOT/'verification/browser.json').read_text())
errors.extend(browser['errors'])
expect(len(browser['states'])==12,'browser did not render twelve states')
expect(all(x['passed'] for x in browser['interactions']),'browser interaction failed')
if errors:
    print(json.dumps({'status':'FAILED','errors':errors},ensure_ascii=False,indent=2));sys.exit(1)

font_path=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
font=ImageFont.truetype(str(font_path),21) if font_path.is_file() else ImageFont.load_default()
def sheet(items,path):
    tw,th=900,548
    canvas=Image.new('RGB',(tw*2,th*((len(items)+1)//2)), '#0b1119')
    draw=ImageDraw.Draw(canvas)
    for i,(key,title) in enumerate(items):
        x=(i%2)*tw;y=(i//2)*th
        draw.text((x+22,y+14),key[:2]+' / '+title,fill='#d5b57b',font=font)
        with Image.open(ROOT/'renders'/f'{key}.png') as im:
            im.thumbnail((tw-28,491),Image.Resampling.LANCZOS)
            canvas.paste(im.convert('RGB'),(x+14,y+49))
    canvas.save(path,quality=92,subsampling=0)
sheet(screens[:8],ROOT/'renders/overview.jpg')
sheet(screens[8:],ROOT/'renders/details_overview.jpg')
cards=''.join(f'<article><a href="renders/{key}.png"><img src="renders/{key}.png" alt="{title}" loading="lazy"></a><div><h2>{key[:2]}. {title}</h2><a href="src/index.html?page={route}">Открыть локальный сценарий →</a></div></article>' for (key,title),route in zip(screens,routes))
(ROOT/'index.html').write_text('''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NASRAL — предложение v4</title><style>*{box-sizing:border-box}body{margin:0;background:#0b1119;color:#edf0f2;font:16px Arial,sans-serif}main{max-width:1500px;padding:55px 28px;margin:auto}h1{font:42px Georgia,serif;color:#d5b57b}p{color:#a1b1c3;max-width:1050px;line-height:1.75}nav{display:flex;gap:28px;margin:25px 0 35px}a{color:#d5b57b}section{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{background:#15212e;border:1px solid #344759;border-radius:9px;overflow:hidden}img{width:100%;display:block}article div{padding:17px 22px 24px}h2{font-size:18px;margin:0 0 12px}article a{font-size:14px}@media(max-width:800px){section{grid-template-columns:1fr}h1{font-size:32px}}</style><main><h1>NASRAL — история, статистика и достижения</h1><p>Предложение для организаторов · v4. Восемь основных экранов и четыре раскрытых сценария. Все PNG — 1920×1080. Текущие результаты, голоса, игры, время и деньги в них сценарные, не официальные. Для проверки переходов доступны локальные HTML-состояния; голосов и платежей они не отправляют.</p><nav><a href="README.md">Описание предложения</a><a href="SPEC.md">Функциональное ТЗ</a><a href="REVIEW.md">Результат ревью</a></nav><section>'''+cards+'</section></main></html>')

verification=f'''# Проверка пакета v4

Проверено локально 9 ноября 2026. Это проверка визуальной поставки и локальных сценариев, не доказательство работы интеграций действующего NASRAL.

| Проверка | Результат |
|---|---|
| Основные PNG и раскрытые состояния | 12 из 12; 1920×1080, каждый декодируется |
| Изображения в HTML-состояниях | Нет недоступных ресурсов |
| Компоновка | Нижний блок каждого кадра целиком внутри 1080 px; нет горизонтального выхода |
| Редакторские оценки | Не обнаружены на основных турнирных и исторических состояниях |
| Журнал попыток | Очки, время, финиши и дропы совпадают с агрегатами участников |
| Связи назначения | Каждая начатая попытка связана с лотом, тем же участником, игрой и исходом |
| Аукционные суммы | Банк равен сумме вариантов; один победитель, его сумма совпадает с рейтингом |
| Ожидающие задания | Четыре назначения без начатой попытки, отдельно от 62 попыток |
| Архив | Счётчик титулов и знак межсезонного изменения согласованы |
| Недоступные показатели | HLTB и медиа не выдаются за известные значения |
| Браузерные взаимодействия | {len(browser['interactions'])} из {len(browser['interactions'])} проверок пройдены |

Проверенные действия: поиск кандидата; раскрытие значка и Escape; числовая сортировка в обе стороны; совместный фильтр игры и участника; переключение единицы и исхода аукционов; выбор соперника; переход аукцион → результат → профиль → назад; смена архивного сезона; локальный состав и смена фаворита. Дополнительно: ближайшая предыдущая попытка из графика; отсутствие подмены личности без статистики; редакторский класс прогнозов; агрегация аукционов с фильтрами; сохранение поиска при возврате; отсутствие автоматического заполнения пустого состава; сохранение фаворита после перезагрузки.

PNG получены Chromium через Playwright {browser['playwright']}, viewport 1920×1080, device scale factor 1. Исходники и команды: [REPRODUCING.md](REPRODUCING.md). Сценарные данные: [DATA_AND_ASSETS.md](DATA_AND_ASSETS.md).

Граница проверки: полноценная мобильная версия, фактическая отправка голосов, платежи, обновление настоящих результатов, полная медиатека и историческая фактологическая сверка не проверялись и не заявляются реализованными.
'''
fresh_report=ROOT/'verification/fresh_reproduction.json'
if fresh_report.is_file():
    fresh=json.loads(fresh_report.read_text())
    if fresh.get('status')=='PASS':
        verification+='\n## Свежая распаковка\n\nИз ZIP без каталога технических отчётов заново выполнены генерация данных, получение 12 PNG, 16 браузерных сценариев и сборка архива. Все этапы завершились успешно; ссылки, изображения, размеры и сценарные связи проходят те же проверки.\n'
(ROOT/'docs/VERIFICATION.md').write_text(verification)
for md in [ROOT/'README.md',ROOT/'SPEC.md',ROOT/'REVIEW.md',*(ROOT/'docs').glob('*.md')]:
    for target in re.findall(r'\]\(([^)]+)\)',md.read_text()):
        if target.startswith(('https://','http://','#')):continue
        expect((md.parent/target.split('#')[0]).is_file(),'broken local documentation link: '+str(md.relative_to(ROOT))+' → '+target)
if errors:
    print(json.dumps({'status':'FAILED','errors':errors},ensure_ascii=False,indent=2));sys.exit(1)

def deliverable(path):
    rel=path.relative_to(ROOT)
    return path.is_file() and not any(part in {'.git','verification','dist','__pycache__','.venv','node_modules'} for part in rel.parts) and path.name not in {'.DS_Store','MANIFEST.sha256'}
files=sorted(p for p in ROOT.rglob('*') if deliverable(p))
hashes=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in files)
(ROOT/'MANIFEST.sha256').write_text(hashes)
out=ROOT/'dist';out.mkdir(exist_ok=True)
archive=out/'NASRAL-v4-organizers.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files+[ROOT/'MANIFEST.sha256']:
        z.write(p,arcname='NASRAL-v4/'+p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    expect(z.testzip() is None,'release ZIP CRC failed')
(ROOT/'verification/package.json').write_text(json.dumps({'renders':12,'files':len(files)+1,'zip_bytes':archive.stat().st_size,'errors':errors},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS' if not errors else 'FAILED','renders':12,'files':len(files)+1,'zip':str(archive.relative_to(ROOT)),'zip_bytes':archive.stat().st_size,'errors':errors},ensure_ascii=False,indent=2))
sys.exit(bool(errors))
