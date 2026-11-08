# Материалы для сборки

`src/` — HTML, стили и данные экранов. `assets/` — изображения. `scripts/` — получение PNG и сборка архива. Итоговые изображения находятся в `../renders/`, описание продукта — в корневых README и ТЗ.

Открыть экраны локально: `src/index.html`.

Из корня репозитория:

```sh
python3 workbench/scripts/build_data.py
uv run --no-project --with playwright python workbench/scripts/render.py
uv run --no-project --with pillow python workbench/scripts/package.py
```

Для рендеринга нужен Chromium Playwright. При отдельной установке его путь можно передать через `NASRAL_CHROMIUM_PATH`. Служебные отчёты и готовый ZIP сохраняются в `verification/` и `dist/`; в Git они не входят. В презентационный ZIP попадают только README, ТЗ и изображения.
