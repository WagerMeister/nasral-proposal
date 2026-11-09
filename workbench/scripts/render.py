"""Render the presentation states and verify their browser behavior."""
from pathlib import Path
from importlib.metadata import version
import json, os, sys
from presentation import SCREENS, source_digest
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'workbench'
(WORK/'verification').mkdir(parents=True,exist_ok=True)
STATES=[(key,route) for key,title,route in SCREENS]
results={'playwright':version('playwright'),'viewport':[1920,1080],'source_digest':source_digest(ROOT),'states':[],'interactions':[]}
errors=[]
with sync_playwright() as pw:
    configured=os.environ.get('NASRAL_CHROMIUM_PATH')
    executable=Path(configured) if configured else Path(pw.chromium.executable_path)
    if not executable.is_file():
        candidates=sorted((Path.home()/'Library/Caches/ms-playwright').glob('chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'))
        if not candidates:
            sys.exit('Chromium not found. Run: uv run --with playwright playwright install chromium')
        executable=candidates[-1]
    browser=pw.chromium.launch(executable_path=str(executable),headless=True)
    context=browser.new_context(viewport={'width':1920,'height':1080},device_scale_factor=1,locale='ru-RU',reduced_motion='reduce')
    tab=context.new_page()
    tab.on('pageerror',lambda e:errors.append(str(e)))
    base=(WORK/'src/index.html').as_uri()
    for name,route in STATES:
        tab.goto(base+'?page='+route,wait_until='load')
        tab.evaluate('document.fonts.ready')
        tab.evaluate('''async () => { await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));
          await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))); }''')
        tab.locator('#screen h1').wait_for()
        layout=tab.evaluate('''() => ({title:document.querySelector('h1').textContent,
          height:document.querySelector('.app').getBoundingClientRect().height,
          footerBottom:document.querySelector('.footer').getBoundingClientRect().bottom,
          brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).map(i=>i.getAttribute('src')),
          horizontalOverflow:document.documentElement.scrollWidth>1920,
          processCopy:['макет','рендер','после ревью','архивном наборе','прогресс не изображается'].filter(t=>document.querySelector('main').innerText.toLowerCase().includes(t)),
          editorialInTournament:[...document.querySelectorAll('[data-award]')].filter(e=>/редактор|прогноз|выбор организаторов/i.test(e.dataset.award)).length})''')
        if layout['brokenImages']:errors.append(name+': broken images '+str(layout['brokenImages']))
        if layout['footerBottom']>1080.5:errors.append(name+': cropped footer at '+str(layout['footerBottom']))
        if layout['horizontalOverflow']:errors.append(name+': horizontal overflow')
        if layout['processCopy']:errors.append(name+': development copy in product '+str(layout['processCopy']))
        if route.split('&')[0] not in {'candidates','voting','selection'} and layout['editorialInTournament']:
            errors.append(name+': editorial badges outside voting')
        tab.screenshot(path=str(ROOT/'renders'/f'{name}.png'),full_page=False,animations='disabled')
        results['states'].append({'file':f'renders/{name}.png','route':route,**layout})

    def check(label,fn):
        try: fn(); results['interactions'].append({'check':label,'passed':True})
        except Exception as e: errors.append(label+': '+str(e));results['interactions'].append({'check':label,'passed':False,'error':str(e)})
    def reset(route):
        tab.evaluate("history.replaceState(null,'',location.href)")
        tab.goto(base+'?page='+route,wait_until='load')
    def search():
        reset('candidates');tab.locator('#candidate-search').fill('Melharucos')
        assert tab.locator('.candidate').count()==1
        assert tab.locator('.candidate-name').inner_text()=='Melharucos'
    def badges():
        reset('candidates');tab.locator('[data-achievement]').first.click();assert tab.locator('.modal').count()==1
        assert 'Победы в двух сезонах' in tab.locator('.modal').inner_text()
        tab.keyboard.press('Escape');assert tab.locator('.modal').count()==0
    def sorting():
        reset('statistics');tab.locator('[data-sort="finished"]').click()
        assert tab.locator('.statistics-table tbody tr').first.locator('.player strong').inner_text()=='Dunduk'
        tab.locator('[data-sort="finished"]').click()
        assert tab.locator('.statistics-table tbody tr').first.locator('.player strong').inner_text()=='nenormova'
    def gamefilter():
        reset('games');tab.locator('#game-player').select_option('mel');tab.locator('#game-status').select_option('dropped')
        assert tab.locator('.games-table tbody tr').count()==3
        assert all('Melharucos' in x for x in tab.locator('.games-table tbody tr').all_inner_texts())
    def auctionfilter():
        reset('auctions');tab.locator('#donut-mode').select_option('outcome');tab.locator('#donut-unit').select_option('lots')
        tab.locator('[data-auction-filter="Дроп игры"]').click()
        assert 'Дроп игры' in tab.locator('.auction-table').inner_text()
        assert 'Сбросить' in tab.locator('.tabs').inner_text()
    def compare():
        reset('comparison');tab.locator('#compare-right').select_option('dunduk')
        assert tab.locator('.comparison-person').nth(1).locator('h2').inner_text()=='Dunduk'
    def flow():
        reset('auctions');tab.locator('.auction-table tbody tr').first.locator('.game-title').click()
        assert 'Inscryption' in tab.locator('.lot-hero h2').inner_text()
        tab.locator('a[href="?page=profile&player=mel"]').first.click()
        assert 'Melharucos' in tab.locator('.profile-identity h2').inner_text()
        tab.go_back();assert 'Inscryption' in tab.locator('.lot-hero h2').inner_text()
    def archive():
        reset('season');tab.locator('#archive-season').select_option('2025')
        assert tab.locator('.archive-intro h2').inner_text()=='NASRAL 2025'
        assert tab.locator('.archive-table tbody tr').count()==8
    def draft():
        reset('selection&example=full');assert tab.locator('.selection-person').count()==9
        tab.locator('[data-favorite="flash"]').click();assert 'Фаворит' in tab.locator('[data-favorite="flash"]').inner_text()
        tab.locator('.selection-person').last.locator('[data-select]').click();assert tab.locator('.selection-person').count()==8
        assert tab.locator('a[href="https://nasral.pro/vote2026/vote"]').count()==1
    def chart_links():
        reset('standings')
        assert tab.locator('svg.chart a').nth(6).get_attribute('href')=='?page=lot&lot=LOT-006'
        assert tab.locator('svg.chart a').nth(17).get_attribute('href')=='?page=lot&lot=LOT-020'
    def unavailable_comparison():
        reset('profile&player=arrow')
        assert tab.locator('a[href="?page=comparison&left=arrow"]').count()==0
        reset('comparison&left=arrow')
        assert tab.locator('.comparison-person').count()==0
        assert 'Arrowwoods' in tab.locator('.empty-state').inner_text()
    def no_editorial_layer():
        for route in ['candidates','voting','selection&example=full']:
            reset(route)
            text=tab.locator('#screen').inner_text().lower()
            assert not any(term in text for term in ['выбор организаторов','высокий риск','прогноз','уверенность'])
        reset('candidates')
        assert tab.locator('.candidate-picture img').count()==10
        assert tab.locator('.candidate-picture .portrait-monogram').count()==0
    def filtered_aggregation():
        reset('auctions&player=mel');tab.locator('[data-auction-tab="players"]').click()
        assert tab.locator('.auction-table tbody tr').count()==1
        assert 'Melharucos' in tab.locator('.auction-table tbody tr').inner_text()
        tab.locator('[data-auction-filter="Хорроры"]').click()
        row=tab.locator('.auction-table tbody tr').inner_text()
        expected=tab.evaluate("NASRAL_DATA.auctions.filter(l=>l.player==='mel'&&l.genre==='Хорроры').reduce((s,l)=>s+l.winning,0)")
        actual=tab.locator('.auction-table tbody tr td').nth(2).inner_text()
        assert ''.join(c for c in actual if c.isdigit())==str(expected)
    def search_back():
        reset('candidates');tab.locator('#candidate-search').fill('Melharucos')
        tab.locator('.candidate-name').click();tab.go_back()
        assert tab.locator('#candidate-search').input_value()=='Melharucos'
        assert tab.locator('.candidate').count()==1
    def empty_draft():
        reset('candidates');tab.evaluate('sessionStorage.clear()');tab.reload()
        tab.locator('a[href="?page=selection"]').click()
        assert tab.locator('.selection-person').count()==0
    def persisted_favorite():
        reset('selection&example=full');tab.locator('[data-favorite="flash"]').click();tab.reload()
        assert tab.locator('[data-favorite="flash"]').evaluate("e=>e.classList.contains('active')")
    def historical_participation():
        reset('standings');row=tab.locator('.standings-table tbody tr').filter(has_text='AlinaRinRin')
        assert 'NASRAL 2025 · #8' in row.inner_text()
        assert 'Первый сезон' not in row.inner_text()
    def complete_award_collections():
        data=json.loads((WORK/'src/data.json').read_text())
        # Every archived podium place has an earned award; it must render in the owner's collection.
        for pid in {a['player'] for a in data['achievements']}:
            reset('profile&player='+pid+'&tab=awards')
            expected=[a['id'] for a in data['achievements'] if a['player']==pid]
            actual=tab.locator('.award-card').evaluate_all("els=>els.map(e=>e.dataset.achievement)")
            if len(expected)>6:
                tab.locator('[data-award-page="6"]').click()
                actual+=tab.locator('.award-card').evaluate_all("els=>els.map(e=>e.dataset.achievement)")
            assert sorted(actual)==sorted(expected),pid+': incomplete award collection'
        for person in [p for p in data['players'] if p.get('points') is not None]:
            assert any(a['id']=='nasral-2026-'+person['id']+'-season' for a in data['achievements']),person['id']+': missing current season emblem'
        reset('profile&player=dunduk&tab=awards')
        text=tab.locator('.collection-grid').inner_text()
        assert 'Бронза · NASRAL 2025' in text and 'Серебро · NASSAL 2026' in text
    def award_category_and_context():
        reset('profile&player=mel&tab=awards')
        tab.locator('[data-award-category="Роли"]').click()
        assert tab.locator('.award-card').count()==1
        tab.locator('.award-card').click()
        assert 'Судейство на MGE' in tab.locator('.modal').inner_text()
        assert 'спортивным местом' in tab.locator('.modal').inner_text()
        tab.keyboard.press('Escape')
        reset('hall');tab.locator('[data-achievement="series-double-flash"]').click()
        text=tab.locator('.modal').inner_text()
        assert 'особая регалия' in text.lower() and 'NASRAL 2025' in text and 'NASSAL 2026' in text
        tab.locator('.modal a[href="?page=season&season=2025"]').click()
        assert tab.locator('.archive-intro h2').inner_text()=='NASRAL 2025'
    def phase_safe_badges():
        for route in ['candidates','voting','selection&example=full']:
            reset(route)
            ids=tab.locator('[data-achievement]').evaluate_all("els=>els.map(e=>e.dataset.achievement)")
            current=tab.evaluate("NASRAL_DATA.achievements.filter(a=>a.events.includes('nasral-2026')).map(a=>a.id)")
            assert not set(ids).intersection(current),route+': future record shown during voting'
    def memorable_events():
        reset('profile&player=mel&tab=events')
        first=tab.locator('.moment-card').first.inner_text()
        assert '342' in first and 'Inscryption' in first
        tab.locator('#event-kind').select_option('record')
        assert tab.locator('.moment-card').count()==1
        tab.locator('.moment-card a').first.click()
        assert 'Inscryption' in tab.locator('.lot-hero h2').inner_text()
        reset('profile&player=mel&tab=events')
        tab.locator('#event-media').select_option('clip')
        assert tab.locator('.moment-card').count()==0
        assert 'По этим фильтрам событий нет' in tab.locator('.memory-layout').inner_text()
        tab.locator('[data-reset-events]').click()
        initial=tab.locator('.moment-card').first.get_attribute('data-moment')
        tab.locator('[data-event-page="3"]').click()
        assert tab.locator('.moment-card').first.get_attribute('data-moment')!=initial
    def unselected_variants():
        reset('auctions&auctionTab=unselected')
        assert tab.locator('.unselected-table tbody tr').count()==5
        tab.locator('.unselected-table tbody tr').first.locator('.game-title').click()
        values=tab.locator('.option-row').all_inner_texts()
        assert any('Не выбран' in v for v in values)
        data=json.loads((WORK/'src/data.json').read_text())
        non_max=next(l for l in data['auctions'] if l['winning']<max(o['amount'] for o in l['options']))
        reset('lot&lot='+non_max['id'])
        assert tab.locator('.lot-hero h2').inner_text()==data['games'][non_max['game']]['title']
    def consistent_roster():
        data=json.loads((WORK/'src/data.json').read_text())
        expected={p['id'] for p in data['players'] if p['voteRank']<=9}
        actual={p['id'] for p in data['players'] if p.get('points') is not None}
        assert actual==expected and len(actual)==9
        reset('standings');assert tab.locator('.standings-table tbody tr').count()==9
        assert '9 участников' in tab.locator('.kpis').inner_text()
        assert 'OZON671GAMES3' in tab.locator('.standings-table').inner_text()
        reset('statistics');assert tab.locator('.statistics-table tbody tr').count()==9
    def complete_paginated_lists():
        data=json.loads((WORK/'src/data.json').read_text())
        reset('games');seen=[]
        while True:
            seen+=tab.locator('.games-table tbody a.game-title').evaluate_all("els=>els.map(e=>e.getAttribute('href'))")
            next=tab.locator('[data-list="games"]').last
            if next.is_disabled():break
            next.click()
        assert len(seen)==len(data['attempts']) and len(set(seen))==len(seen)
        for mode in ['top','unselected']:
            reset('auctions&auctionTab='+mode);seen=[]
            while True:
                seen+=tab.locator('.auction-table tbody a.game-title').evaluate_all("els=>els.map(e=>e.getAttribute('href')+'|'+e.innerText)")
                next=tab.locator('[data-list="auctions"]').last
                if next.is_disabled():break
                next.click()
            expected=len(data['auctions']) if mode=='top' else sum(not o['winner'] for l in data['auctions'] for o in l['options'])
            assert len(seen)==expected and len(set(seen))==len(seen),mode+': truncated or repeated rows'
    def scoped_auction_kpis():
        reset('auctions');tab.locator('[data-auction-filter="Хорроры"]').click()
        expected=tab.evaluate("(()=>{let lots=NASRAL_DATA.auctions.filter(l=>l.genre==='Хорроры');return {total:lots.reduce((s,l)=>s+l.total,0),count:lots.length,mean:Math.round(lots.reduce((s,l)=>s+l.winning,0)/lots.length),max:Math.max(...lots.map(l=>l.winning))}})()")
        values=tab.locator('.kpis .big-number').all_inner_texts()
        actual=[int(''.join(c for c in v if c.isdigit())) for v in values]
        assert actual==[expected['total'],expected['count'],expected['mean'],expected['max']],str(actual)
        assert tab.locator('.donut-item').count()==1
        assert '100,0%' in tab.locator('.donut-item').inner_text()
        tab.locator('[data-auction-filter="all"]').click()
        assert tab.locator('.donut-item').count()>1
    def comparison_links():
        reset('comparison&left=flash');tab.locator('#compare-right').select_option('dunduk')
        assert 'right=dunduk' in tab.url
        tab.reload()
        assert tab.locator('.comparison-person h2').all_inner_texts()==['F1ashko','Dunduk']
    def distinct_profile_views():
        reset('profile&player=mel&tab=history')
        assert tab.locator('.career-row').count()>0
        tab.locator('[data-profile-tab="statistics"]').click()
        assert tab.locator('.career-row').count()==0 and tab.locator('.profile-kpis').count()==1
        reset('statistics');tab.locator('[data-stats-tab="finishes"]').click()
        assert tab.locator('.games-table').count()==1 and tab.locator('.statistics-table').count()==0
        tab.locator('a[href="?page=games&status=finished"]').click()
        assert all('Пройдено' in s for s in tab.locator('.games-table tbody tr').all_inner_texts())
    def latest_completions():
        reset('profile&player=mel&tab=history')
        assert tab.locator('.profile-game b').first.inner_text()=='Katana ZERO'
        assert 'Inscryption' not in tab.locator('.profile-columns > section').last.inner_text()
    def back_restores_list_context():
        reset('games');tab.locator('#game-player').select_option('dunduk');tab.locator('#game-status').select_option('finished')
        tab.locator('[data-list="games"]').last.click()
        before=tab.locator('.games-table tbody a.game-title').first.get_attribute('href')
        tab.locator('.games-table tbody a.game-title').first.click();tab.go_back()
        assert tab.locator('#game-player').input_value()=='dunduk'
        assert tab.locator('#game-status').input_value()=='finished'
        assert tab.locator('.games-table tbody a.game-title').first.get_attribute('href')==before
        reset('profile&player=mel&tab=events');tab.locator('#event-kind').select_option('record')
        tab.locator('.moment-card a').first.click();tab.go_back()
        assert tab.locator('#event-kind').input_value()=='record' and tab.locator('.moment-card').count()==1
    def supplied_media_paths():
        # Synthetic browser-only data verifies links without adding fake videos to the public fixture.
        for kind in ['clip','vod','timestamp']:
            reset('profile&player=mel&tab=events')
            expected='https://example.invalid/nasral/'+kind+'?t=12'
            tab.evaluate("({kind,url})=>{let m=NASRAL_DATA.moments.find(m=>m.id==='moment-mel-01');m.media={type:kind,url};NASRAL_DATA.attempts.find(a=>a.id==='mel-01').clip=m.media;NASRAL_APP.render()}",{'kind':kind,'url':expected})
            tab.locator('#event-media').select_option(kind)
            assert tab.locator('.moment-card').count()==1
            tab.locator('.moment-card a').first.click()
            assert tab.locator('.recording-link').get_attribute('href')==expected
    for label,fn in [('candidate search',search),('badge disclosure and Escape',badges),('numeric sorting',sorting),('player + outcome filters',gamefilter),('auction unit and outcome filter',auctionfilter),('participant comparison',compare),('auction → result → profile → back',flow),('archive season switching',archive),('local selection and favorite',draft),('chart links to nearest prior result',chart_links),('no silent participant substitution',unavailable_comparison),('portraits present and editorial layer removed',no_editorial_layer),('filtered auction aggregation',filtered_aggregation),('search context after browser Back',search_back),('empty draft is not auto-filled',empty_draft),('favorite persists after reload',persisted_favorite),('season history consistent across views',historical_participation),('all earned awards survive profile navigation',complete_award_collections),('award category, criteria and specific result links',award_category_and_context),('no current records during pre-season voting',phase_safe_badges),('memorable events, filters, pagination and result links',memorable_events),('unselected alternatives and non-maximal chosen variant',unselected_variants),('same nine qualifiers across tournament phases',consistent_roster),('complete pagination of games, lots and unselected options',complete_paginated_lists),('auction KPI and chart respect the same filter',scoped_auction_kpis),('comparison link keeps both people after reload',comparison_links),('profile and statistics tabs have distinct content',distinct_profile_views),('latest completions are actually newest',latest_completions),('Back preserves list and event filters',back_restores_list_context),('positive clip, VOD and timestamp links using browser-only fixtures',supplied_media_paths)]:check(label,fn)
    browser.close()
results['errors']=errors
(WORK/'verification/browser.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'renders':len(results['states']),'interactions':results['interactions'],'errors':errors},ensure_ascii=False,indent=2))
sys.exit(bool(errors))
