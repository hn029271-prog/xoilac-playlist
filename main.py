import re
from bs4 import BeautifulSoup
import requests

TARGET_URL = "https://xoiche.tv"
OUTPUT_FILE = "xoilac_live.m3u"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": TARGET_URL,
}


def cao_link_bong_da():
  print("Đang tiến hành truy cập và cào dữ liệu từ Xôi Lạc...")
  try:
    response = requests.get(TARGET_URL, headers=HEADERS, timeout=10)
    if response.status_code != 200:
      return

    soup = BeautifulSoup(response.text, "html.parser")
    m3u_content = "#EXTM3U\n"
    so_luong_tran = 0

    matches = soup.find_all(
        "div", class_=re.compile(r"(match-item|live|playing)")
    )

    for match in matches:
      try:
        team_home = match.find("span", class_="home-team").text.strip()
        team_away = match.find("span", class_="away-team").text.strip()
        match_name = f"{team_home} vs {team_away}"

        match_link = match.find("a")["href"]
        if not match_link.startswith("http"):
          match_link = TARGET_URL + match_link

        match_page = requests.get(match_link, headers=HEADERS, timeout=5)
        stream_urls = re.findall(
            r"(https?://[^\s\"']+\.m3u8[^\s\"']*)", match_page.text
        )

        if stream_urls:
          final_stream_url = stream_urls[0]
          m3u_content += (
              f'#EXTINF:-1 group-title="Xôi Lạc Live", [LIVE] {match_name}\n'
          )
          m3u_content += f"{final_stream_url}\n"
          so_luong_tran += 1
      except Exception:
        continue

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
      f.write(m3u_content)
    print(f"Hoàn tất! Đã tìm thấy {so_luong_tran} trận.")

  except Exception as e:
    print(f"Lỗi: {e}")


if __name__ == "__main__":
  cao_link_bong_da()
