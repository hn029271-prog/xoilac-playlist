import os
import re
import requests
from bs4 import BeautifulSoup

DOMAINS = [
    "https://xoiche1.live",
    "https://xoilac.live",
    "https://xoilac.tv",
    "https://xoilac.net"
]

M3U_FILE = "xoilac_live.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://xoiche1.live/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_match_title(raw_text):
    """
    Phân tích văn bản thô của trận đấu và chuẩn hóa về form:
    'Đội A [Tỉ số] Đội B | Phút' (VD: Arsenal 1-0 Chelsea | 45')
    Trả về (formatted_title, is_live)
    """
    text = clean_text(raw_text)
    
    # Bỏ qua các mục không phải trận đấu
    if any(k in text.lower() for k in ['highlight', 'tin tức', 'lịch thi đấu', 'bảng xếp hạng']):
        return None, False

    # 1. Tìm phút trận đấu (VD: 45', 86', Hiệp 1, Hiệp 2, H1, H2, HT, FT)
    minute_match = re.search(r"(\d+['′]|Hiệp \d|H\d|HT)", text, re.IGNORECASE)
    
    # Kiểm tra xem trận đấu có dấu hiệu ĐANG LIVE hay không
    is_live = False
    minute_str = ""
    
    if minute_match:
        is_live = True
        minute_str = minute_match.group(1)
    elif "live" in text.lower() or "đang đá" in text.lower() or "trực tiếp" in text.lower():
        is_live = True
        minute_str = "LIVE"

    # Nếu KHÔNG CÓ dấu hiệu đang đá / đang live (ví dụ chỉ có giờ đá 22:00, 02:00, chưa bắt đầu) -> Bỏ qua
    if not is_live:
        return None, False

    # 2. Bóc tách Tên 2 Đội và Tỉ số (dạng X-Y hoặc X - Y)
    score_match = re.search(r"([A-Za-z0-9\sÀ-ỹ]+?)\s+(\d+\s*[-–]\s*\d+)\s+([A-Za-z0-9\sÀ-ỹ]+)", text)
    
    if score_match:
        team_a = clean_text(score_match.group(1))
        score = clean_text(score_match.group(2)).replace(" ", "")
        team_b = clean_text(score_match.group(3))
        
        # Lọc bỏ các từ thừa như 'Truc tiep', 'Live' dính vào tên đội
        team_a = re.sub(r'^(Trực tiếp|Live|Xem|TRỰC TIẾP)\s+', '', team_a, flags=re.IGNORECASE)
        team_b = re.sub(r'\s+(Trực tiếp|Live|Xem|TRỰC TIẾP)$', '', team_b, flags=re.IGNORECASE)
        
        formatted = f"{team_a} {score} {team_b} | {minute_str}"
        return formatted, True
    else:
        # Nếu đang LIVE nhưng chưa bóc tách được tỉ số chuẩn (VD: vừa vào trận 0-0)
        # Rút gọn tên trận sạch sẽ
        clean_title = re.sub(r'^(Trực tiếp|Live|Xem)\s+', '', text, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s+(xem trực tiếp|link xem)$', '', clean_title, flags=re.IGNORECASE)
        
        if minute_str and minute_str not in clean_title:
            clean_title = f"{clean_title} | {minute_str}"
            
        return clean_title, True

def get_live_matches_from_domain(domain):
    matches = []
    seen_urls = set()
    
    print(f"Đang quét dữ liệu từ: {domain}...")
    try:
        res = requests.get(domain, headers=HEADERS, timeout=12)
        res.encoding = 'utf-8'
        
        if res.status_code != 200:
            return matches

        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        for a in links:
            href = a['href']
            if any(path in href for path in ['/truc-tiep/', '/match/', '/xem-truc-tiep/', '/room/']):
                full_url = href if href.startswith("http") else f"{domain.rstrip('/')}/{href.lstrip('/')}"
                
                if full_url in seen_urls:
                    continue
                    
                raw_text = a.get_text(separator=" ") or a.get('title', '')
                title, is_live = parse_match_title(raw_text)
                
                # CHỈ LẤY TRẬN ĐANG LIVE / ĐANG ĐÁ
                if is_live and title:
                    seen_urls.add(full_url)
                    matches.append((title, full_url))
                    
    except Exception as e:
        print(f"Lỗi khi xử lý {domain}: {e}")

    return matches

def main():
    live_matches = []
    
    for domain in DOMAINS:
        live_matches = get_live_matches_from_domain(domain)
        if live_matches:
            print(f"==> Quét thành công {len(live_matches)} trận ĐANG ĐÁ từ {domain}.")
            break

    # Ghi dữ liệu ra tệp M3U
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        if not live_matches:
            print("Không có trận đấu nào đang phát sóng live lúc này.")
            f.write('#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", [LIVE] Hiện không có trận đấu nào đang đá\n')
            f.write("https://example.com/live.m3u8\n")
        else:
            for title, url in live_matches:
                f.write(f'#EXTINF:-1 tvg-logo="" group-title="Bóng Đá", {title}\n')
                f.write(f'{url}\n')

if __name__ == "__main__":
    main()
