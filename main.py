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

def format_title(raw_text):
    text = clean_text(raw_text)
    
    # Loại bỏ ngày giờ (Ví dụ: 23:00 | 28-09 hoặc 28-09-2026)
    text = re.sub(r'\d{1,2}:\d{2}\s*\|\s*\d{1,2}-\d{1,2}(-\d{2,4})?', '', text)
    text = re.sub(r'\d{1,2}:\d{2}', '', text)
    text = clean_text(text)

    # Tìm phút thi đấu
    minute_match = re.search(r"(\d+['′]|Hiệp \d|H\d|HT)", text, re.IGNORECASE)
    minute_str = ""
    if minute_match:
        minute_str = minute_match.group(1)
        text = text.replace(minute_str, '').strip()

    if not minute_str:
        return None

    # Dọn dẹp từ thừa
    text = re.sub(r'^(Trực tiếp|Live|Xem|TRỰC TIẾP)\s+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+(blv|BLV).*$', '', text, flags=re.IGNORECASE)

    return f"{text} | {minute_str}"

async def capture_m3u8(page, match_url):
    """
    Mở trang trận đấu bằng Chromium ảo, lắng nghe request mạng 
    để chộp lấy link .m3u8 thật do trình duyệt giải mã
    """
    found_m3u8 = None

    def handle_request(request):
        nonlocal found_m3u8
        url = request.url
        # Bắt request chứa m3u8 và loại bỏ quảng cáo
        if '.m3u8' in url and not any(x in url.lower() for x in ['ad', 'promo', 'banner', 'analytics']):
            found_m3u8 = url

    page.on("request", handle_request)

    try:
        print(f"Đang mở trình duyệt ảo vào: {match_url}")
        await page.goto(match_url, timeout=15000, wait_until="domcontentloaded")
        
        # Thử bấm vào vùng phát video nếu cần để trigger phát stream
        try:
            await page.click("video, iframe, .player-wrapper", timeout=3000)
        except:
            pass

        # Chờ tối đa 6 giây để trình duyệt giải mã JavaScript và tạo request stream
        for _ in range(12):
            if found_m3u8:
                break
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"Lỗi khi bắt stream từ {match_url}: {e}")

    return found_m3u8 or match_url

async def main():
    matches = []
    
    async with async_playwright() as p:
        # Khởi chạy trình duyệt Chromium ẩn (Headless)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"Đang quét danh sách trận đấu từ {BASE_DOMAIN}...")
        try:
            await page.goto(BASE_DOMAIN, timeout=20000, wait_until="networkidle")
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            links = soup.find_all('a', href=True)
            seen_urls = set()

            raw_matches = []
            for a in links:
                href = a['href']
                if '/truc-tiep/' in href:
                    full_url = href if href.startswith("http") else f"{BASE_DOMAIN.rstrip('/')}/{href.lstrip('/')}"
                    base_url = re.sub(r'\?blv=.*$', '', full_url)

                    if base_url in seen_urls:
                        continue
                    
                    raw_text = a.get_text(separator=" ")
                    title = format_title(raw_text)

                    if title:
                        seen_urls.add(base_url)
                        raw_matches.append((title, base_url))

            print(f"==> Tìm thấy {len(raw_matches)} trận đang LIVE. Bắt đầu giải mã .m3u8...")

            # Truy cập từng trận để bắt link .m3u8 thật
            for title, url in raw_matches:
                m3u8_url = await capture_m3u8(page, url)
                print(f" -> Trận: {title}")
                print(f"    Stream: {m3u8_url}")
                matches.append((title, m3u8_url))

        except Exception as e:
            print(f"Lỗi truy cập trang chủ: {e}")
        
        await browser.close()

    # Ghi ra file M3U
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
