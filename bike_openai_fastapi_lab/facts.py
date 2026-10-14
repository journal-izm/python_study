"""CSV 계산은 Python, 문장 작성은 모델. 데이터 검증에 실패하면 멈춘다."""
import csv
from datetime import datetime
from pathlib import Path

DATA_PATH = Path(__file__).parent / 'data' / 'SeoulBikeData.csv'
SOURCE = 'https://doi.org/10.24432/C5F62R'


def build_facts(path: Path = DATA_PATH) -> dict:
    with path.open(encoding='latin1', newline='') as handle:
        reader = csv.DictReader(handle)
        required = {'Date', 'Hour', 'Rented Bike Count', 'Functioning Day'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('필수 열이 없습니다.')
        rows = list(reader)
    if not rows:
        raise ValueError('CSV가 비어 있습니다.')
    totals, counts, dates, seen = [0]*24, [0]*24, [], set()
    excluded = 0
    for row in rows:
        date = datetime.strptime(row['Date'], '%d/%m/%Y').date()
        hour, count = int(row['Hour']), int(row['Rented Bike Count'])
        operating = row['Functioning Day']
        if not 0 <= hour <= 23 or count < 0 or operating not in {'Yes', 'No'}:
            raise ValueError('시간·대여 건수·운영 여부를 확인하세요.')
        if (date, hour) in seen:
            raise ValueError('날짜와 시간의 중복 행입니다.')
        seen.add((date, hour))
        dates.append(date)
        if operating == 'No':
            excluded += 1
            continue
        totals[hour] += count
        counts[hour] += 1
    if any(n == 0 for n in counts):
        raise ValueError('운영 시간대의 자료가 없습니다.')
    hourly = [{'hour': h, 'rental_total': totals[h], 'observations': counts[h],
               'mean_rentals': round(totals[h] / counts[h], 2)} for h in range(24)]
    best = max(totals[h] / counts[h] for h in range(24))
    peaks = [h for h in range(24) if totals[h] / counts[h] == best]
    return {
        'source': SOURCE,
        'period_start': min(dates).isoformat(), 'period_end': max(dates).isoformat(),
        'raw_rows': len(rows), 'excluded_non_operating_rows': excluded,
        'included_rows': sum(counts), 'filter': 'Functioning Day == Yes',
        'metric': '시간대별 평균 대여 건수', 'unit': '건/관측 시간',
        'peak_hours': peaks, 'hourly': hourly,
        'caution': '대여 건수는 고유 이용자 수가 아니다. 관찰 자료로 원인이나 현재 현황을 단정할 수 없다.'
    }


if __name__ == '__main__':
    import json
    print(json.dumps(build_facts(), ensure_ascii=False, indent=2))
