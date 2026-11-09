"""Shared presentation inventory: no separate screen lists in render/package steps."""
from pathlib import Path
import hashlib
SCREENS = [
 ('01_candidates','Кандидаты','candidates'),
 ('02_voting','Рейтинг голосования','voting'),
 ('03_standings','Турнирная таблица','standings'),
 ('04_statistics','Статистика участников','statistics'),
 ('05_games','Игры и прохождения','games'),
 ('06_auctions','Аукционы','auctions'),
 ('07_hall_of_fame','Зал славы','hall'),
 ('08_participant_profile','Коллекция достижений','profile&player=mel&tab=awards'),
 ('09_comparison','Сравнение участников','comparison'),
 ('10_auction_to_result','История назначения','lot'),
 ('11_season_archive','Архив сезона','season'),
 ('12_vote_selection','Выбранный состав','selection&example=full'),
 ('13_participant_career','Карьера участника','profile&player=mel&tab=history'),
 ('14_memorable_events','Памятные события','profile&player=mel&tab=events'),
 ('15_unselected_options','Не выпавшие варианты','auctions&auctionTab=unselected'),
]
def source_digest(root):
    digest=hashlib.sha256()
    for p in sorted((Path(root)/'workbench/src').iterdir()):
        if p.is_file():
            digest.update(p.name.encode());digest.update(p.read_bytes())
    return digest.hexdigest()
