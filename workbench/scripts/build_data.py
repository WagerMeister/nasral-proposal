"""Build a deterministic presentation fixture. No live event data is fetched."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
games = json.loads((ROOT / 'src/games.json').read_text())
portraits = json.loads((ROOT / 'src/portraits.json').read_text())
genres = {'witcher3':'RPG','disco':'RPG','bg3':'RPG','gothic2':'RPG','kingdom':'RPG','ds3':'RPG','pathologic2':'Хорроры','cyberpunk':'RPG','portal2':'Приключения','inside':'Платформеры','celeste':'Платформеры','firewatch':'Приключения','limbo':'Платформеры','inscryption':'Хорроры','katana':'Платформеры','hades':'Экшен'}
for key, game in games.items():
    game['genre'] = genres[key]
    game['hltb'] = None  # Unverified benchmarks must not become apparent facts.

definitions = [
    ('flash','F1ashko','F1ashko',1240,6,1,62,'witcher3',1392,0,1,1),
    ('dunduk','Dunduk','Dunduk',1128,7,1,65,'disco',1126,1,3,2),
    ('mel','Melharucos','Melharucos',1094,5,3,68,'bg3',1562,-1,None,3),
    ('karmik','KarmikKoala','KarmikKoala',1020,5,1,58,'gothic2',1038,0,4,4),
    ('lasqa','Lasqa','Lasqa',990,5,2,60,'kingdom',1140,2,None,5),
    ('praden','Praden','Praden',910,4,2,55,'ds3',1266,0,None,6),
    ('alina','AlinaRinRin','AlinaRinRin',847,4,3,61,'pathologic2',725,1,8,None),
    ('nenormova','nenormova','nenormova',799,3,2,57,'cyberpunk',1242,-1,None,12),
]
players = []
attempts = []
short_games = ['portal2','inside','celeste','firewatch','limbo','inscryption','katana','hades']
for pi, (pid,name,asset,points,finished,drops,hours,current,elapsed,delta,rank25,rank26) in enumerate(definitions):
    player = dict(id=pid,name=name,asset=asset,platform='Twitch',delta=delta,rank25=rank25,rank26=rank26,
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

extras = [('ozon','OZON671GAMES3','OZON671GAMES3','Kick','red'),('dawg','Dawgonosik','Dawgonosik','Twitch','red'),
          ('arrow','Arrowwoods','Arrowwoods','Twitch','green'),('vj','VJLinktopgamer','VJLinktopgamer','Twitch','orange')]
for pid,name,asset,platform,risk in extras:
    players.append(dict(id=pid,name=name,asset=asset,platform=platform,
                        rank25=5 if pid=='arrow' else None,rank26=11 if pid=='arrow' else None))

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
               dict(game=alternatives[0],amount=winning*60//100,winner=False),
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

history = [
    dict(id='flash',name='F1ashko',rank25=1,rank26=1,points26=1624),
    dict(id='dunduk',name='Dunduk',rank25=3,rank26=2,points26=1479),
    dict(id='mel',name='Melharucos',rank25=None,rank26=3,points26=1462),
    dict(id='karmik',name='KarmikKoala',rank25=4,rank26=4,points26=None),
    dict(id='lasqa',name='Lasqa',rank25=None,rank26=5,points26=None),
    dict(id='praden',name='Praden',rank25=None,rank26=6,points26=None),
    dict(id='maddyson',name='Maddyson',rank25=7,rank26=7,points26=None),
    dict(id='cake',name='C_a_k_e',rank25=2,rank26=8,points26=None),
    dict(id='viktor',name='ViktorZu',rank25=None,rank26=9,points26=None),
    dict(id='valakas',name='GladValakas',rank25=6,rank26=10,points26=None),
    dict(id='arrow',name='Arrowwoods',rank25=5,rank26=11,points26=None),
    dict(id='nenormova',name='nenormova',rank25=None,rank26=12,points26=None),
    dict(id='alina',name='AlinaRinRin',rank25=8,rank26=None,points26=None),
]

for person in players+history:
    if person['id'] in portraits: person['portraitFile']=portraits[person['id']]['file']

data = dict(version='4.0',snapshot=dict(day=7,totalDays=14,time='21:45',season='NASRAL 2026',phase='tournament'),
            players=players,attempts=attempts,auctions=auctions,games=games,history=history,
            focusAttempt='mel-01',selection=['flash','dunduk','mel','karmik','lasqa','praden','alina','nenormova','arrow'])
(ROOT/'src/data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(ROOT/'src/data.js').write_text('window.NASRAL_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
print(json.dumps({'players':8,'candidates':len(players),'attempts':len(attempts),'finished':sum(p['finished'] for p in players[:8]),
                  'dropped':sum(p['dropped'] for p in players[:8]),'lots':len(auctions),'points':sum(p['points'] for p in players[:8]),
                  'minutes':sum(p['minutes'] for p in players[:8])},ensure_ascii=False))
