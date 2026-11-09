"""Build a deterministic presentation fixture. No live event data is fetched."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
games = json.loads((ROOT / 'src/games.json').read_text())
portraits = json.loads((ROOT / 'src/portraits.json').read_text())
archive = json.loads((ROOT / 'src/history.json').read_text())
history = archive['standings']
historical = {p['id']: p for p in history}
events = archive['events']
genres = {'witcher3':'RPG','disco':'RPG','bg3':'RPG','gothic2':'RPG','kingdom':'RPG','ds3':'RPG','pathologic2':'Хорроры','cyberpunk':'RPG','portal2':'Приключения','inside':'Платформеры','celeste':'Платформеры','firewatch':'Приключения','limbo':'Платформеры','inscryption':'Хорроры','katana':'Платформеры','hades':'Экшен'}
for key, game in games.items():
    game['genre'] = genres[key]
    game['hltb'] = None  # Unverified benchmarks must not become apparent facts.

definitions = [
    ('flash','F1ashko','F1ashko',1240,6,1,62,'witcher3',1392),
    ('dunduk','Dunduk','Dunduk',1128,7,1,65,'disco',1126),
    ('mel','Melharucos','Melharucos',1094,5,3,68,'bg3',1562),
    ('karmik','KarmikKoala','KarmikKoala',1020,5,1,58,'gothic2',1038),
    ('lasqa','Lasqa','Lasqa',990,5,2,60,'kingdom',1140),
    ('praden','Praden','Praden',910,4,2,55,'ds3',1266),
    ('alina','AlinaRinRin','AlinaRinRin',847,4,3,61,'pathologic2',725),
    ('nenormova','nenormova','nenormova',799,3,2,57,'cyberpunk',1242),
    ('ozon','OZON671GAMES3','OZON671GAMES3',741,3,2,54,'hades',1120),
]
players = []
attempts = []
short_games = ['portal2','inside','celeste','firewatch','limbo','inscryption','katana','hades']
for pi, (pid,name,asset,points,finished,drops,hours,current,elapsed) in enumerate(definitions):
    player = dict(id=pid,name=name,asset=asset,platform='Kick' if pid=='ozon' else 'Twitch',rank25=historical.get(pid,{}).get('rank25'),rank26=historical.get(pid,{}).get('rank26'),
                  current=current)
    players.append(player)
    entries = []
    remaining_minutes = hours * 60 - elapsed
    weights = [5 + ((j + pi) % 4) for j in range(finished)] + [2] * drops
    minutes = [remaining_minutes * w // sum(weights) for w in weights]
    minutes[-1] += remaining_minutes - sum(minutes)
    # Completed games supply all points. Dropped/active attempts supply no points here.
    point_parts = [points // finished] * finished
    for j in range(points % finished):
        point_parts[j] += 1
    player_games=short_games[pi%8:]+short_games[:pi%8]
    if pid=='mel': player_games=['inscryption']+[g for g in player_games if g!='inscryption']
    for j in range(finished + drops):
        game = player_games[j % len(player_games)]
        status = 'finished' if j < finished else 'dropped'
        entries.append(dict(id=f'{pid}-{j+1:02}',player=pid,game=game,status=status,minutes=minutes[j],
                            points=point_parts[j] if j < finished else 0,day=1+(j*7//finished) if j<finished else 6,clip=None))
    entries.append(dict(id=f'{pid}-live',player=pid,game=current,status='playing',minutes=elapsed,points=None,day=max(1,7-elapsed//600),clip=None))
    attempts.extend(entries)
    player['points'] = sum(a['points'] or 0 for a in entries)
    player['minutes'] = sum(a['minutes'] for a in entries)
    player['finished'] = sum(a['status']=='finished' for a in entries)
    player['dropped'] = sum(a['status']=='dropped' for a in entries)
    player['playing'] = sum(a['status']=='playing' for a in entries)
    player['attempts'] = len(entries)

# Position movement uses the same ledger as the chart, measured at start of day 6.
previous = sorted(players, key=lambda p: sum(a['points'] or 0 for a in attempts if a['player']==p['id'] and a['day']<=5), reverse=True)
for rank, player in enumerate(players, 1):
    player['delta'] = next(i+1 for i,p in enumerate(previous) if p['id']==player['id'])-rank

extras = [('dawg','Dawgonosik','Dawgonosik','Twitch'),
          ('arrow','Arrowwoods','Arrowwoods','Twitch'),('vj','VJLinktopgamer','VJLinktopgamer','Twitch')]
for pid,name,asset,platform in extras:
    old = historical.get(pid, {})
    players.append(dict(id=pid,name=name,asset=asset,platform=platform,
                        rank25=old.get('rank25'),rank26=old.get('rank26')))

votes = [14200,13600,12900,12000,11400,10800,9900,9200,8600,8200,7600,7000]
ratings = [5.8,5.0,4.5,4.1,4.0,3.9,3.6,3.6,3.6,3.5,3.4,3.2]
for i,p in enumerate(players):
    p['votes'] = votes[i]
    p['favorites'] = round(votes[i] * (0.07 + (i % 4)*0.023))
    p['rating'] = ratings[i]
    p['voteRank'] = i + 1
    # Actual ordering is explicit, not inferred from rounded percentage labels.

auctions = []
for i,a in enumerate(attempts):
    winning = (25 + (i * 43 + 17) % 240) * 1000
    if a['id']=='mel-01':
        winning=342000
    alternatives = [g for g in short_games[i%8:]+short_games[:i%8] if g!=a['game']][:2]
    options = [dict(game=a['game'],amount=winning,winner=True),
               dict(game=alternatives[0],amount=winning*(125 if i%5==0 else 60)//100,winner=False),
               dict(game=alternatives[1],amount=winning*22//100,winner=False)]
    lot=dict(id=f'LOT-{i+1:03}',player=a['player'],game=a['game'],attempt=a['id'],status=a['status'],
             day=a['day'],winning=winning,total=sum(o['amount'] for o in options),options=options,
             condition='Без подсказок' if a['id']=='mel-01' else 'Обычное прохождение',genre=games[a['game']]['genre'])
    # All three alternatives are separate title/condition choices, even when a title repeats.
    a['lot'] = lot['id']
    auctions.append(lot)
for i,game in enumerate(['hades','inside','portal2','katana']):
    amount=48000+i*13000
    auctions.append(dict(id=f'LOT-{len(auctions)+1:03}',player=players[i]['id'],game=game,attempt=None,status='waiting',
                         day=7,winning=amount,total=amount+amount//2,options=[dict(game=game,amount=amount,winner=True),
                         dict(game='firewatch',amount=amount//2,winner=False)],condition='Обычное прохождение',genre=games[game]['genre']))

for person in players+history:
    if person['id'] in portraits: person['portraitFile']=portraits[person['id']]['file']

# Careers and awards are derived from the same archive and presentation ledger.
careers = {p['id']: [] for p in players+history}
for row in archive['legacy']:
    careers[row['player']].append(dict(row))
for person in history:
    for field, event in [('rank25','nasral-2025'), ('rank26','nassal-2026')]:
        if person[field] is not None:
            careers[person['id']].append(dict(player=person['id'],event=event,role='Участник',place=person[field]))

for person in players:
    if person.get('points') is not None:
        careers[person['id']].append(dict(player=person['id'],event='nasral-2026',role='Участник',place=None))

achievements = []
def award(key, player, category, rarity, title, criterion, event_ids, symbol, color='', links=None):
    achievements.append(dict(id=key,player=player,category=category,rarity=rarity,title=title,
                             criterion=criterion,events=event_ids,symbol=symbol,color=color,links=links or []))
for pid, rows in careers.items():
    for row in rows:
        eid=row['event']; event=events[eid]
        links=[dict(label='Архив '+event['name'],route=event['route'])] if event.get('route') else []
        if row['place'] and row['place']<=3:
            place=row['place']; label={1:'Чемпион',2:'Серебро',3:'Бронза'}[place]
            award(eid+'-'+pid+'-place',pid,'Титулы' if place==1 else 'Призовые места',
                  'rare' if place==1 else 'standard',label+' · '+event['name'],
                  f"{place}-е место в итоговом зачёте {event['name']}.",[eid],
                  'trophy' if place==1 else 'medal','' if place==1 else 'silver' if place==2 else 'bronze',links)
        if row['role']=='Судья':
            award(eid+'-'+pid+'-judge',pid,'Роли','standard','Судья · '+event['name'],
                  'Судейство на '+event['name']+'. Роль не считается спортивным местом.',[eid],'scales','violet',links)
        if event['series']:
            award(eid+'-'+pid+'-season',pid,'Сезоны','standard',event['name'],
                  'Участие в '+event['name']+' после утверждения состава.',[eid],event['symbol'],eid,links)
    titles=[r['event'] for r in rows if r['place']==1 and events[r['event']]['series']]
    if len(titles)>=2:
        award('series-double-'+pid,pid,'Титулы','signature','Дважды чемпион серии',
              'Победы в двух сезонах NASRAL / NASSAL: '+', '.join(events[e]['name'] for e in titles)+'.',
              titles,'double','', [dict(label=events[e]['name'],route=events[e]['route']) for e in titles])
    if len(rows)>=3:
        award('veteran-'+pid,pid,'Карьера','standard','Ветеран игровых ивентов',
              'Участие или судейство минимум в трёх разных ивентах. В карьере — '+str(len(rows))+'.',
              [r['event'] for r in rows],'laurel','violet')

record_lot=max(auctions,key=lambda l:l['winning'])
longest=max((a for a in attempts if a['status']=='finished'),key=lambda a:a['minutes'])
record_specs=[('auction-record',record_lot['player'],'Самый дорогой выбор',
              f"Наибольшая сумма выбранного варианта: {record_lot['winning']:,} ₽.".replace(',',' '),
              record_lot['id'],'coins'),
             ('endurance-record',longest['player'],'Длинная дистанция',
              f"Самое долгое завершённое прохождение: {longest['minutes']//60} ч {longest['minutes']%60:02} мин — {games[longest['game']]['title']}.",
              longest['lot'],'hourglass')]
for key,pid,title,criterion,lid,symbol in record_specs:
    award(key,pid,'Рекорды','rare',title,criterion+' NASRAL 2026, срез 7-го дня.',
          ['nasral-2026'],symbol,'',[dict(label='Игра и аукцион',route='lot&lot='+lid)])

moments=[]
for a in attempts:
    if a['status']=='playing':continue
    l=next(l for l in auctions if l['id']==a['lot'])
    record=next((r for r in record_specs if r[4]==l['id']),None)
    focus=a['id']=='mel-01'
    title=record[2] if record else ('Выбор зрителей → '+games[a['game']]['title'] if focus else games[a['game']]['title'])
    if record and record[0]=='auction-record': title=f"{l['winning']:,} ₽ на {games[a['game']]['title']}".replace(',',' ')
    moments.append(dict(id='moment-'+a['id'],player=a['player'],event='nasral-2026',game=a['game'],lot=l['id'],
                        day=a['day'],kind='record' if record else 'game',title=title,
                        description=('Игра пройдена' if a['status']=='finished' else 'Игра дропнута')+
                        f" за {a['minutes']//60} ч {a['minutes']%60:02} мин. "+
                        (f"Начислено {a['points']} GGP." if a['status']=='finished' else 'Начислено 0 GGP.'),
                        media=a['clip'],featured=bool(record or focus)))
for l in auctions:
    if l['status']=='waiting':
        moments.append(dict(id='moment-'+l['id'],player=l['player'],event='nasral-2026',game=l['game'],lot=l['id'],
                            day=l['day'],kind='auction',title='Назначена '+games[l['game']]['title'],
                            description='Зрительский выбор завершён. Прохождение ещё не началось.',media=None,featured=False))

data = dict(version='5.0',snapshot=dict(day=7,totalDays=14,time='21:45',season='NASRAL 2026',phase='tournament'),
            players=players,attempts=attempts,auctions=auctions,games=games,history=history,events=events,
            careers=careers,achievements=achievements,moments=moments,
            focusAttempt='mel-01',selection=['flash','dunduk','mel','karmik','lasqa','praden','alina','nenormova','arrow'])
(ROOT/'src/data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(ROOT/'src/data.js').write_text('window.NASRAL_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
print(json.dumps({'candidates':len(players),'attempts':len(attempts),'lots':len(auctions),
                  'achievements':len(achievements),'moments':len(moments)},ensure_ascii=False))
