"""
Functions to get the ids of all the cs2 items in the buff market
"""

import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Carpeta donde se guarda la sesión (cookies + localStorage)
SESSION_DIR = "buff_session"

# Lista de categorías a scrapear (añade las que quieras)
CATEGORIES = [
    "weapon_knife_butterfly",
    "weapon_knife_karambit",
    "weapon_knife_m9_bayonet"
]

# URL base con paginación dinámica
BASE_URL = (
    "https://buff.163.com/market/csgo"
    "?game=csgo&category={cat}&tab=selling&page_num={page}&sort_by=price.asc"
)


async def scrape_items_on_page(page, category_name):
    # 1) El <ul> que contiene las cartas
    ul = page.locator("ul.card_csgo").first

    # 2) Solo hijos directos <li> de ese ul
    cards = ul.locator("> li")
    total_slots = await cards.count()
    print(f"Slots en el grid: {total_slots}")

    results = []
    valid_count = 0

    for i in range(total_slots):
        card = cards.nth(i)

        # 3) Tiene link /goods/? si no, es basura/placeholder
        link_locator = card.locator("a[href*='/goods/']")
        if await link_locator.count() == 0:
            # Debug opcional:
            # print(f"   [slot {i}] sin <a href='/goods/'>, se ignora")
            continue

        # 4) Tiene nombre en <h3>? si no, también se ignora
        h3 = card.locator("h3")
        if await h3.count() == 0:
            # print(f"   [slot {i}] sin <h3>, se ignora")
            continue

        name = (await h3.first.text_content() or "").strip()
        if not name:
            # print(f"   [slot {i}] h3 vacío, se ignora")
            continue

        valid_count += 1

        # ID: primero intentamos data-goods_id, si no lo hay, lo sacamos del href
        item_id = await card.get_attribute("data-goods_id")
        href = await link_locator.first.get_attribute("href")

        if not item_id and href and "/goods/" in href:
            item_id = href.split("/goods/")[1].split("?")[0]

        # wear
        wear_el = card.locator("span[class*='tag_csgo_wear']")
        wear = (await wear_el.first.text_content() or "").strip() if await wear_el.count() > 0 else ""

        # StatTrak
        is_stattrak = "StatTrak" in name or "StatTrak™" in name

        # imagen
        img_el = card.locator("img")
        img_url = await img_el.first.get_attribute("src") if await img_el.count() > 0 else None

        # url absoluta
        if href and href.startswith("/"):
            href = "https://buff.163.com" + href

        results.append({
            "id": item_id,
            "name": name,
            "wear": wear,
            "is_stattrak": is_stattrak,
            "image": img_url,
            "url": href,
            "category": category_name,
        })

    return results


async def scrape_category(page, category):
    all_items = []
    page_num = 1

    while True:
        url = BASE_URL.format(cat=category, page=page_num)
        print(f"Cargando {url}")
        await page.goto(url, wait_until="networkidle")

        # sacar items de esta página
        page_items = await scrape_items_on_page(page, category)

        if not page_items:
            print("Página sin items válidos, fin.")
            break

        all_items.extend(page_items)

        # fin si el botón siguiente está desactivado
        next_disabled = page.locator("li.disabled span.current.next")
        if await next_disabled.count() > 0:
            print("Botón 'Siguiente' desactivado → última página.")
            break

        page_num += 1
        await asyncio.sleep(5)

    return all_items


async def main():
    Path(SESSION_DIR).mkdir(exist_ok=True)

    async with async_playwright() as p:

        # Abrimos Chromium con perfil persistente → mantiene cookies
        browser = await p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False,
        )

        page = await browser.new_page()

        # Detecta si estás logueado
        await page.goto("https://buff.163.com/account/settings", wait_until="networkidle")

        if "login" in page.url:
            print("No estás logueado. Inicia sesión manualmente en Buff.")
            print("Cuando hayas iniciado sesión correctamente, pulsa ENTER aquí.")
            input(">>> ")
            # Tras login, Playwright guarda automáticamente las cookies

        print("Sesión cargada, empezando scraping…")

        global_results = {}

        for cat in CATEGORIES:
            print(f"\n==============================")
            print(f"  Scrapeando categoría: {cat}")
            print(f"==============================")

            items = await scrape_category(page, cat)
            global_results[cat] = items
            print(items)

            # Guardado por categoría
            with open(f"{cat}.json", "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)

        # Guardado general
        with open("buff_items_all.json", "w", encoding="utf-8") as f:
            json.dump(global_results, f, indent=2, ensure_ascii=False)

        await browser.close()


asyncio.run(main())
