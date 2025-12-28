#!/bin/bash

# election_results.py в КОРНЕ проекта
cat > election_results.py << 'EOF'
"""
Скрипт подсчёта результатов выборов и формирования парламента
"""
import logging
from database import db
from config import PARLIAMENT_SEATS, ELECTION_THRESHOLD_PERCENT

logger = logging.getLogger(__name__)


def calculate_election_results(election_id: int):
    """
    Подсчёт результатов выборов и формирование парламента
    
    Логика:
    1. Подсчитать голоса за каждую партию
    2. Применить 5% барьер
    3. Распределить места пропорционально
    4. Заполнить парламент по спискам партий
    """
    
    # Получаем результаты
    results = db.get_election_results(election_id)
    total_votes = db.get_election_total_votes(election_id)
    
    if total_votes == 0:
        logger.warning("❌ Нет голосов на выборах")
        return None
    
    # Применяем барьер
    threshold = (total_votes * ELECTION_THRESHOLD_PERCENT) / 100
    passed_parties = []
    
    for result in results:
        if result['votes'] >= threshold:
            passed_parties.append({
                'party_id': result['id'],
                'party_name': result['name'],
                'votes': result['votes'],
                'percentage': (result['votes'] / total_votes) * 100
            })
    
    if not passed_parties:
        logger.warning("❌ Ни одна партия не прошла барьер")
        return None
    
    # Подсчитываем общее количество голосов прошедших партий
    passed_votes = sum(p['votes'] for p in passed_parties)
    
    # Распределяем места пропорционально
    for party in passed_parties:
        seats = int((party['votes'] / passed_votes) * PARLIAMENT_SEATS)
        party['seats'] = seats
    
    # Корректируем если сумма не равна PARLIAMENT_SEATS
    total_seats = sum(p['seats'] for p in passed_parties)
    diff = PARLIAMENT_SEATS - total_seats
    
    if diff > 0:
        # Раздаём оставшиеся места партиям с наибольшим остатком
        for i in range(diff):
            # Считаем остатки
            for party in passed_parties:
                exact_seats = (party['votes'] / passed_votes) * PARLIAMENT_SEATS
                party['remainder'] = exact_seats - party['seats']
            
            # Даём место партии с максимальным остатком
            max_party = max(passed_parties, key=lambda p: p.get('remainder', 0))
            max_party['seats'] += 1
    
    # Очищаем старый парламент
    db.clear_parliament()
    
    # Заполняем парламент по спискам
    for party in passed_parties:
        members = db.get_party_members(party['party_id'])
        
        # Берём первых N членов по списку
        for i in range(min(party['seats'], len(members))):
            member = members[i]
            db.add_to_parliament(member['telegram_id'], party['party_id'])
    
    # Закрываем выборы
    results_text = "\n".join([
        f"{p['party_name']}: {p['votes']} голосов ({p['percentage']:.1f}%) - {p['seats']} мест"
        for p in passed_parties
    ])
    
    db.close_election(election_id, results_text)
    
    logger.info(f"✅ Выборы завершены. Парламент сформирован.")
    logger.info(f"Результаты:\n{results_text}")
    
    return {
        'total_votes': total_votes,
        'passed_parties': passed_parties,
        'results_text': results_text
    }
EOF

echo "✅ election_results.py created (ROOT)"
