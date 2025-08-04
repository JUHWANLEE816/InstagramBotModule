#!/usr/bin/env python3
"""
PopMart 자동 주문 봇
- 다중 계정 지원
- 프록시 지원
- Discord 웹훅 알림
- KB카드 자동 결제
"""

import json
import requests
import re
import concurrent.futures
import time
import random
from bs4 import BeautifulSoup
from requests_toolbelt.multipart.encoder import MultipartEncoder
from urllib.parse import quote_plus, unquote_plus, urlencode

from config import (
    COOKIE_FILE, PROXY_FILE, MAX_WORKERS, DISCORD_WEBHOOK_URL,
    REQUIRED_COOKIES, ITEMS_TO_ADD
)
from utils import load_proxies, load_cookies, send_discord_message
from cart_manager import CartManager
from order_manager import OrderManager
from payment_manager import PaymentManager


def process_account(account_id, cookies, proxy_info):
    """단일 계정 처리"""
    session = requests.Session()
    
    # 쿠키 설정
    for name, value in cookies.items():
        if name in REQUIRED_COOKIES:
            session.cookies.set(name, value, domain=".popmart.co.kr")
    
    # 프록시 설정
    try:
        ip, port, user, pwd = proxy_info.split(":")
        proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
        session.proxies = {"http": proxy_url, "https": proxy_url}
    except Exception as e:
        print(f"[❌ Proxy Failed] {account_id} | {e}")
        return

    # 로그인 확인
    if not check_login(session, account_id):
        return

    # 장바구니 및 주문 처리
    cart_manager = CartManager(session, account_id)
    cart_manager.clear_cart()
    cart_manager.add_all_items_parallel()

    # 주문서 처리
    order_manager = OrderManager(session, account_id)
    html = order_manager.fetch_order_form()
    order_manager.submit_order(html)

    # 결제 처리
    payment_manager = PaymentManager(session, account_id)
    payment_manager.process_payment()


def check_login(session, account_id):
    """로그인 상태 확인"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Referer": "https://popmart.co.kr/"
        }
        check_url = "https://popmart.co.kr/myshop/order/list.html"
        resp = session.get(check_url, headers=headers, allow_redirects=False, timeout=10)
        
        if resp.status_code in (301, 302) and "/member/login.html" in resp.headers.get("Location", ""):
            print(f"[❌ {account_id}] login Failed")
            return False
        elif resp.status_code == 200:
            print(f"[✅ {account_id}] login Success")
            send_discord_message(f"✅ [{account_id}] login Success")
            return True
        else:
            print(f"[❌ {account_id}] login Failed: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[❌ {account_id}] login Failed | {e}")
        return False


def main():
    """메인 실행 함수"""
    print("🚀 PopMart 자동 주문 봇 시작")
    
    cookies = load_cookies()
    proxies = load_proxies()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for i, (account_id, cookie) in enumerate(cookies.items()):
            proxy_info = proxies[i % len(proxies)]
            executor.submit(process_account, account_id, cookie, proxy_info)


if __name__ == "__main__":
    main()