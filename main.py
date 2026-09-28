import os
import re
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

M3U_FILE = "xoilac_live.m3u"
BASE_DOMAIN = "https://xoiche1.live"

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()

def clean_title(raw_text):
    text = clean_text(raw_text)
    if not text or len(text) < 4:
        return None

    # Loại bỏ ngày giờ trùng lặp (VD: 23:00 | 28-09-2026)
    text = re.sub(r'\d{1,2}:\d{2}\s*\|\s*\d{1,2}-\d{1,2}(-\d{2,4})?', '', text)
    text = re.sub(r'\d{1,2}:\d{2}', '', text)
    
    # Loại bỏ từ khóa thừa
    text = re.sub(r'^(Trực tiếp|Live|Xem|TRỰC TIẾP)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+(blv|BLV).*$', '', text, flags=re.IGNORECASE)
    text = clean_text(text)

    return text if text else "Trận đấu Trực tiếp"

async def capture_m3u8(context, match_url):
    page = await context.new_page()
    found_m3u8 = None

    def handle_request(request):
        nonlocal found_m3u8
        url = request.url
        # Bắt request m3u8 thật, bỏ qua quảng cáo
        if '.m3u8' in url and not any(x in url.lower() for x in ['ad', 'promo', 'banner', 'analytics']):
            if not found_m3u8:
                found_m3u8 = url

    page.on("request", handle_request)

    try:
        print(f"Đang mở trang trận đấu: {match_url}")
        await page.goto(match_url, timeout=25000, wait_until="domcontentloaded")
        
        # Click giả lập vào khung phát để kích hoạt stream
        try:
            await page.click("video, iframe, .player-wrapper", timeout=3000)
        except:
            pass

        # Chờ tối đa 10 giây để nhận request .m3u8
        for _ in range(20):
            if found_m3u8:
                break
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"Lỗi khi bắt stream từ {match_url}: {e}")

    await page.close()
    return found_m3u8 or match_url

async def main():
    matches = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"Đang truy cập trang chủ: {BASE_DOMAIN}...")
        try:
            await page.goto(BASE_DOMAIN, timeout=25000, wait_until="networkidle")
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            links = soup.find_all('a', href=True)
            seen_urls = set()
            raw_matches = []

            for a in links:
                href = a['href']
                # Lấy tất cả các đường dẫn chứa trận đấu trực tiếp
                if '/truc-tiep/' in href:
                    full_url = href if href.startswith("http") else f"{BASE_DOMAIN.rstrip('/')}/{href.lstrip('/')}"
                    base_url = re.sub(r'\?blv=.*$', '', full_url)

                    if base_url in seen_urls:
                        continue
                    
                    raw_text = a.get_text(separator=" ")
                    title = clean_title(raw_text)

                    if title:
                        seen_urls.add(base_url)
                        raw_matches.append((title, base_url))

            print(f"==> Quét được {len(raw_matches)} link trận đấu. Bắt đầu giải mã .m3u8...")

            for title, url in raw_matches:
                m3u8_url = await capture_m3u8(context, url)
                print(f" -> Trận: {title}")
                print(f"    Link stream: {m3u8_url}")
                matches.append((title, m3u8_url))

        except Exception as e:
            print(f"Lỗi khi quét trang chủ: {e}")
        
        await browser.close()

    # Xuất file M3U
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        if not matches:
            f.write('#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", [LIVE] Hiện không có trận đấu nào đang đá\n')
            f.write("https://example.com/live.m3u8\n")
        else:
            for title, stream_url in matches:
                f.write(f'#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", {title}\n')
                f.write(f'{stream_url}\n')

if __name__ == "__main__":
    asyncio.run(main())
