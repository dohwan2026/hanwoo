"""한우 도체 경락가격을 받아 prices.json으로 저장한다 (GitHub Actions에서 매일 실행).

출처: 축산물품질평가원 '축산물 도매시장 소도체 등급별 경락가격정보' (공공데이터포털 15058822)
인증키는 환경변수 DATA_GO_KR_KEY (공공데이터포털 '일반 인증키(Decoding)')로 받는다.
키가 로그에 찍히지 않도록, 요청 주소는 절대 출력하지 않는다.

사용: python scripts/fetch_prices.py            # 최근 며칠치를 받아 prices.json 갱신
      python scripts/fetch_prices.py --probe    # 응답 구조만 살펴보기 (파일 안 바꿈)
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

URL = 'http://data.ekape.or.kr/openapi-data/service/user/grade/auct/cattle'
BREED_HANWOO = '024001'
SEXES = {'거세': '025003', '암': '025001'}
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'prices.json')
KST = timezone(timedelta(hours=9))
KEEP_DAYS = 400


def call(key, start, end, sex_cd, defect='Y'):
    q = urllib.parse.urlencode({
        'startYmd': start, 'endYmd': end, 'breedCd': BREED_HANWOO, 'sexCd': sex_cd,
        'qgradeYn': 'Y', 'defectIncludeYn': defect,
    })
    url = f'{URL}?serviceKey={urllib.parse.quote(key, safe="")}&{q}'
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                body = r.read()
            break
        except Exception as e:  # 네트워크 오류 메시지에도 주소가 섞일 수 있어 종류만 남긴다
            last = type(e).__name__
            time.sleep(3 * (attempt + 1))
    else:
        raise RuntimeError(f'요청 실패 ({last})')
    root = ET.fromstring(body)
    code = (root.findtext('.//resultCode') or root.findtext('.//returnReasonCode') or '').strip()
    msg = (root.findtext('.//resultMsg') or root.findtext('.//returnAuthMsg') or root.findtext('.//errMsg') or '').strip()
    items = [{c.tag: (c.text or '').strip() for c in it} for it in root.iter('item')]
    return code, msg, items


def num(v):
    try:
        return float(str(v).replace(',', ''))
    except ValueError:
        return 0.0


def summarize(items):
    """등급명 -> {amt: 전국 평균 kg당 경락가(원), cnt: 경락두수}"""
    out = {}
    for it in items:
        g = it.get('gradeNm') or it.get('gradeCd')
        amt, cnt = num(it.get('CTotAmt', 0)), num(it.get('CTotCnt', 0))
        if g and cnt > 0:
            out[g] = {'amt': round(amt), 'cnt': int(cnt)}
    return out


def main():
    key = os.environ.get('DATA_GO_KR_KEY', '').strip()
    if not key:
        sys.exit('DATA_GO_KR_KEY 환경변수가 없습니다.')
    today = datetime.now(KST).date()

    if '--probe' in sys.argv:
        for back in range(1, 8):
            d = (today - timedelta(days=back)).strftime('%Y%m%d')
            for defect in ('Y', 'N'):
                code, msg, items = call(key, d, d, SEXES['거세'], defect)
                print(f'{d} 결함포함={defect} result={code} {msg} items={len(items)}')
                if items:
                    print('  필드:', sorted(items[0].keys()))
                    for it in items:
                        print('  ', {k: it.get(k) for k in ('gradeCd', 'gradeNm', 'judgeSexNm', 'CTotAmt', 'CTotCnt')})
            if items:
                break
        return

    data = {'days': []}
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as f:
            data = json.load(f)
    byday = {d['date']: d for d in data.get('days', [])}
    # 처음엔 60일, 그 뒤로는 늦게 올라오는 자료까지 잡도록 최근 10일을 다시 받는다
    span = 10 if byday else 60
    got = 0
    for back in range(span, -1, -1):
        d = today - timedelta(days=back)
        if d.weekday() == 6:  # 일요일엔 경매가 없다
            continue
        ymd = d.strftime('%Y%m%d')
        day = {'date': d.isoformat()}
        for name, cd in SEXES.items():
            code, msg, items = call(key, ymd, ymd, cd)
            if code not in ('', '00'):
                sys.exit(f'API 오류: {code} {msg}')
            g = summarize(items)
            if g:
                day[name] = g
        if any(k in day for k in SEXES):
            byday[day['date']] = day
            got += 1
        time.sleep(0.2)
    cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
    days = sorted((v for k, v in byday.items() if k >= cutoff), key=lambda x: x['date'])
    out = {
        'source': '축산물품질평가원 소도체 등급별 경락가격정보 (공공데이터포털)',
        'unit': '원/kg (도체, 전국 평균, 결함 포함)',
        'updated': datetime.now(KST).isoformat(timespec='minutes'),
        'days': days,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'{got}일치 갱신, 보관 {len(days)}일, 최근 {days[-1]["date"] if days else "-"}')


if __name__ == '__main__':
    main()
