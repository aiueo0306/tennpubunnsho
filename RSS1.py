import os
import sys
import subprocess
import tempfile
import re
import time
import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ===== GitHub 上の共通関数を一時ディレクトリにクローン =====
REPO_URL = "https://github.com/aiueo0306/shared-python-env.git"
SHARED_DIR = os.path.join(tempfile.gettempdir(), "shared-python-env")

if not os.path.exists(SHARED_DIR):
    print("🔄 共通関数を初回クローン中...")
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, SHARED_DIR], check=True)
else:
    print("🔁 共通関数を更新中...")
    subprocess.run(["git", "-C", SHARED_DIR, "pull"], check=True)

sys.path.append(SHARED_DIR)

# ===== 共通関数のインポート =====
from rss_utils import generate_rss
from scraper_utils import extract_items
from browser_utils import click_button_in_order

# ===== 固定情報（学会サイト） =====
BASE_URL = "https://www.info.pmda.go.jp/psearch/tenpulist.jsp"
GAKKAI = "添付文書改訂"

# ===== 抽出設定 =====
# /html/body/table[5]/tbody の2個目のtr内にあるaタグをすべて対象
SELECTOR_TITLE = "xpath=/html/body/table[5]/tbody/tr[2] a"

# SELECTOR_TITLE自体がaタグなので、
# タイトルはそのaタグ自身のテキストを取得
title_selector = ""
title_index = 0

# hrefもそのaタグ自身から取得
href_selector = ""
href_index = 0

# ===== 日付なし =====
SELECTOR_DATE = ""
date_selector = ""
date_index = 0

year_unit = ""
month_unit = ""
day_unit = ""

date_format = ""
date_regex = ""

# ===== ポップアップ順序クリック設定 =====
POPUP_MODE = 0  # 1: 実行 / 0: スキップ
POPUP_BUTTONS = [""]  # 正確なボタン表記だけを指定
WAIT_BETWEEN_POPUPS_MS = 500
BUTTON_TIMEOUT_MS = 12000

# ===== Playwright 実行ブロック =====
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")

    # 無人実行：headless=True のまま
    browser = p.chromium.launch(headless=True)

    context = browser.new_context(
        locale="ja-JP",
        viewport={"width": 1366, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        extra_http_headers={"Accept-Language": "ja,en;q=0.8"},
    )

    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")

        page.goto(
            BASE_URL,
            timeout=30000
        )

        try:
            page.wait_for_load_state(
                "networkidle",
                timeout=30000
            )
        except Exception:
            page.wait_for_load_state(
                "domcontentloaded"
            )

        print("🌐 到達URL:", page.url)

        # ---- ポップアップ順に処理 ----
        if POPUP_MODE == 1 and POPUP_BUTTONS:

            for i, label in enumerate(
                POPUP_BUTTONS,
                start=1
            ):

                handled = click_button_in_order(
                    page,
                    label,
                    step_idx=i,
                    timeout_ms=BUTTON_TIMEOUT_MS
                )

                if handled:
                    page.wait_for_timeout(
                        WAIT_BETWEEN_POPUPS_MS
                    )
                else:
                    break

        else:
            print(
                "ℹ ポップアップ処理をスキップ（POPUP_MODE=0）"
            )

        # 本文読み込み
        page.wait_for_load_state(
            "load",
            timeout=30000
        )

    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")

        browser.close()

        raise

    print("▶ 記事を抽出しています...")

    items = extract_items(
        page,
        SELECTOR_DATE,
        SELECTOR_TITLE,
        title_selector,
        title_index,
        href_selector,
        href_index,
        BASE_URL,
        date_selector,
        date_index,
        date_format,
        date_regex,
    )

    if not items:
        print(
            "⚠ 抽出できた記事がありません。"
            "HTML構造が変わっている可能性があります。"
        )

    os.makedirs(
        "rss_output",
        exist_ok=True
    )

    rss_path = "rss_output/Feed1.xml"

    generate_rss(
        items,
        rss_path,
        BASE_URL,
        GAKKAI
    )

    browser.close()
