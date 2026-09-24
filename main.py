import requests
from bs4 import BeautifulSoup
import re

URL = "https://xoiche.tv/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_match_name(raw_title):
    if not raw_title:
        return None
    lower_title = raw_title.lower()
    # Lọc bỏ các mục không phải tên cặp đấu trực tiếp
    if any(keyword in lower_title for keyword in ["nhà đài", "blv", "kênh", "soi kèo", "lịch thi đấu"]):
        return None
    
    # Xóa các hậu tố mã số rác phía sau tên trận
    title = re.sub(r'\s+(?:kg|id)?\s*\d+', '', raw_title, flags=re.IGNORECASE)
    title = re.sub(r'[\?#].*', '', title)
    title = title.strip().upper()
    
    # Đảm bảo tên trận đấu phải có độ dài hợp lý
    if len(title) < 4:
        return None
        
    return title

def get_realtime_matches():
    playlist = ["#EXTM3U\n"]
    try:
        response = requests.get(URL, headers=headers, timeout=10)
        if response.status_code != 200:
            return playlist

        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        match_dict = {}
        
        for l in links:
            href = l['href']
            if '/tran-dau/' in href or '/match/' in href:
                if not href.startswith('http'):
                    match_url = "https://xoiche.tv" + href
                else:
                    match_url = href
                
                title = l.get_text(strip=True)
                if not title or len(title) < 3:
                    title = href.split('/')[-1].replace('-', ' ')
                
                cleaned = clean_match_name(title)
                if cleaned:
                    match_dict[match_url] = cleaned

        count = 0
        for match_url, title in match_dict.items():
            if count >= 8:  # Lấy tối đa 8 trận đang đá
                break
            try:
                detail_resp = requests.get(match_url, headers=headers, timeout=5)
                if detail_resp.status_code == 200:
                    # Kiểm tra xem trận này có luồng stream .m3u8 thực tế đang phát không
                    m3u8_matches = re.findall(r'https?://[^\s<>"]+?\.m3u8[^\s<>"]*', detail_resp.text)
                    if m3u8_matches:
                        stream_url = m3u8_matches[0]
                        # Xử lý chuẩn hóa URL nếu có ký tự thoát
                        stream_url = stream_url.encode().decode('unicode-escape') if '\\u' in stream_url else stream_url
                        
                        playlist.append(f'#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [LIVE] {title}\n')
                        playlist.append(f'{stream_url}\n')
                        count += 1
            except Exception:
                continue

    except Exception as e:
        print(f"Lỗi: {e}")

    return playlist

def save_playlist():
    playlist = get_realtime_matches()
    if len(playlist) <= 1:
        playlist.append('#EXTINF:-1 group-title="Bóng Đá Trực Tiếp", [THÔNG BÁO] Chưa có trận đang phát trực tiếp\n')
        playlist.append('https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8\n')
        
    with open("xoilac_live.m3u", "w", encoding="utf-8") as f:
        f.writelines(playlist)
    print("Đã cập nhật file m3u thành công!")

if __name__ == "__main__":
    save_playlist()
