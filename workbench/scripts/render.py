"""Render the twelve presentation states and verify their browser behavior."""
from pathlib import Path
from importlib.metadata import version
import json, os, sys
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'workbench'
(WORK/'verification').mkdir(parents=True,exist_ok=True)
STATES=[('01_candidates','candidates'),('02_voting','voting'),('03_standings','standings'),
        ('04_statistics','statistics'),('05_games','games'),('06_auctions','auctions'),
        ('07_hall_of_fame','hall'),('08_participant_profile','profile&player=mel'),
        ('09_comparison','comparison'),('10_auction_to_result','lot'),
        ('11_season_archive','season'),('12_vote_selection','selection&example=full')]
results={'playwright':version('playwright'),'viewport':[1920,1080],'states':[],'interactions':[]}
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
          editorialInTournament:[...document.querySelectorAll('[data-award]')].filter(e=>/редактор|прогноз|выбор организаторов/i.test(e.dataset.award)).length})''')
        if layout['brokenImages']:errors.append(name+': broken images '+str(layout['brokenImages']))
        if layout['footerBottom']>1080.5:errors.append(name+': cropped footer at '+str(layout['footerBottom']))
        if layout['horizontalOverflow']:errors.append(name+': horizontal overflow')
        if route.split('&')[0] not in {'candidates','voting','selection'} and layout['editorialInTournament']:
            errors.append(name+': editorial badges outside voting')
        tab.screenshot(path=str(ROOT/'renders'/f'{name}.png'),full_page=False,animations='disabled')
        results['states'].append({'file':f'renders/{name}.png','route':route,**layout})

    def check(label,fn):
        try: fn(); results['interactions'].append({'check':label,'passed':True})
        except Exception as e: errors.append(label+': '+str(e));results['interactions'].append({'check':label,'passed':False,'error':str(e)})
    def reset(route):tab.goto(base+'?page='+route,wait_until='load')
    def search():
        reset('candidates');tab.locator('#candidate-search').fill('Melharucos')
        assert tab.locator('.candidate').count()==1
        assert tab.locator('.candidate-name').inner_text()=='Melharucos'
    def badges():
        reset('candidates');tab.locator('[data-award]').first.click();assert tab.locator('.modal').count()==1
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
    for label,fn in [('candidate search',search),('badge disclosure and Escape',badges),('numeric sorting',sorting),('player + outcome filters',gamefilter),('auction unit and outcome filter',auctionfilter),('participant comparison',compare),('auction → result → profile → back',flow),('archive season switching',archive),('local selection and favorite',draft),('chart links to nearest prior result',chart_links),('no silent participant substitution',unavailable_comparison),('portraits present and editorial layer removed',no_editorial_layer),('filtered auction aggregation',filtered_aggregation),('search context after browser Back',search_back),('empty draft is not auto-filled',empty_draft),('favorite persists after reload',persisted_favorite),('season history consistent across views',historical_participation)]:check(label,fn)
    browser.close()
results['errors']=errors
(WORK/'verification/browser.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'renders':len(results['states']),'interactions':results['interactions'],'errors':errors},ensure_ascii=False,indent=2))
sys.exit(bool(errors))
