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
    #"weapon_knife_butterfly",
    #"weapon_knife_karambit",
    #"weapon_knife_m9_bayonet",
    #"weapon_knife_kke",
    #"weapon_knife_skeleton",
    #"weapon_bayonet",
    #"weapon_knife_widowmaker",
    #"weapon_knife_outdoor",
    #"weapon_knife_flip",
    #"weapon_knife_stiletto",
    #"weapon_knife_css",
    #"weapon_knife_ursus",
    #"weapon_knife_tactical",
    #"weapon_knife_cord",
    #"weapon_knife_canis",
    #"weapon_knife_falchion",
    #"weapon_knife_push",
    #"weapon_knife_survival_bowie",
    #"weapon_knife_gut",
    #"weapon_knife_gypsy_jackknife",
    #"weapon_sport_gloves",
    #"weapon_specialist_gloves",
    #"weapon_moto_gloves",
    #"weapon_driver_gloves",
    #"weapon_hand_wraps",
    # "weapon_brokenfang_gloves",
    # "weapon_hydra_gloves",
    # "weapon_bloodhound_gloves",
    # "weapon_ak47",
    # "weapon_awp",
    # "weapon_m4a1_silencer",
    # "weapon_m4a1",
    # "weapon_aug",
    # "weapon_sg556",
    # "weapon_famas",
    # "weapon_galilar",
    # "weapon_ssg08",
    # "weapon_scar20",
    # "weapon_g3sg1",
    # "weapon_deagle",
    # "weapon_usp_silencer",
    # "weapon_glock",
    # "weapon_hkp2000",
    # "weapon_p250",
    # "weapon_fiveseven",
    # "weapon_revolver",
    # "weapon_tec9",
    # "weapon_elite",
    # "weapon_cz75a",
    # "weapon_zeus",
    # "weapon_mp9",
    # "weapon_mac10",
    # "weapon_ump45",
    # "weapon_p90",
    # "weapon_mp7",
    # "weapon_bizon",
    "weapon_mp5sd",
    "weapon_xm1014",
    "weapon_mag7",
    "weapon_sawedoff",
    "weapon_nova",
    "weapon_m249",
    "weapon_negev",
    "csgo_tool_keychain_missing_link_community",
    "csgo_tool_keychain_dr_boom",
    "csgo_tool_keychain_austin_2025",
    "csgo_tool_keychain_small_arms",
    "csgo_tool_keychain_missing_link",
    "agent_team_ct",
    "agent_team_t",
    "csgo_type_weaponcase",
    "csgo_type_musickit",
    "csgo_type_tool",
    "csgo_type_spray",
    "csgo_type_ticket",
    "csgo_type_collectible",
    "csgo_tool_patch",
    "csgo_tool_gifttag",
    "sticker_tournament25"
    "set_stkr_craft_03",
    "set_stkr_craft_04",
    "sticker_tournament24",
    "crate_sticker_pack_warhammer_capsule",
    "sticker_tournament23",
    "set_stkr_craft_01",
    "set_stkr_craft_02",
    "sticker_tournament22",
    "crate_sticker_pack_community_2024_capsule",
    "sticker_tournament21",
    "crate_sticker_pack_community2022_capsule",
    "sticker_tournament20",
    "crate_sticker_pack_csgo10_capsule",
    "sticker_tournament19",
    "crate_sticker_pack_spring2022_capsule",
    "crate_sticker_pack_bf2042_capsule_lootlist",
    "sticker_tournament18",
    "crate_sticker_pack_riptide_surfshop_lootlist",
    "crate_sticker_pack_op_riptide_capsule_lootlist",
    "sticker_community2021"
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
        only_one_page = page.locator("a.page-link.next")
        print(f"only one page is {only_one_page}")
        if await next_disabled.count() > 0 or await only_one_page.count() <= 0:
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
