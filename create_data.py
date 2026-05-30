from app import app, db
from models import User, Doctor, Service, Promotion
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, date

with app.app_context():
    db.drop_all()
    db.create_all()
    
    print("🔄 Заполнение базы данных...")
    
    # ========== АДМИНИСТРАТОР ==========
    admin = User(
        username='admin',
        email='admin@smileclinic.ru',
        password_hash=generate_password_hash('admin'),
        role='admin'
    )
    db.session.add(admin)
    
    # ========== ВРАЧИ ==========
    doctors_data = [
        {
            'username': 'petrov.ivan',
            'password': 'password',
            'email': 'petrov.ivan@smileclinic.ru',
            'first_name': 'Иван',
            'last_name': 'Петров',
            'specialty': 'Терапевт',
            'work_start': '09:00',
            'work_end': '18:00'
        },
        {
            'username': 'sidorova.maria',
            'password': 'password',
            'email': 'sidorova.maria@smileclinic.ru',
            'first_name': 'Мария',
            'last_name': 'Сидорова',
            'specialty': 'Ортодонт',
            'work_start': '10:00',
            'work_end': '19:00'
        },
        {
            'username': 'ivanov.alexey',
            'password': 'password',
            'email': 'ivanov.alexey@smileclinic.ru',
            'first_name': 'Алексей',
            'last_name': 'Иванов',
            'specialty': 'Хирург',
            'work_start': '08:00',
            'work_end': '17:00'
        }
    ]
    
    for d in doctors_data:
        user = User(
            username=d['username'],
            email=d['email'],
            password_hash=generate_password_hash(d['password']),
            role='doctor'
        )
        db.session.add(user)
        db.session.flush()
        
        doctor = Doctor(
            user_id=user.id,
            first_name=d['first_name'],
            last_name=d['last_name'],
            specialty=d['specialty'],
            work_hours_start=datetime.strptime(d['work_start'], '%H:%M').time(),
            work_hours_end=datetime.strptime(d['work_end'], '%H:%M').time()
        )
        db.session.add(doctor)
    
    print("✅ Врачи созданы (3)")
    
    # ========== УСЛУГИ ==========
    services_data = [
        ('Консультация терапевта', 'Первичный осмотр, диагностика и составление плана лечения', 30, 1500.00),
        ('Лечение кариеса', 'Удаление кариозных тканей и пломбирование зуба', 60, 3500.00),
        ('Профессиональная чистка', 'Ультразвуковая чистка, Air Flow, полировка и фторирование', 45, 3000.00),
        ('Удаление зуба', 'Хирургическое удаление зуба любой сложности', 60, 5000.00),
        ('Установка брекетов', 'Консультация ортодонта и установка брекет-системы', 90, 25000.00),
        ('Отбеливание зубов', 'Профессиональное отбеливание системой Zoom', 90, 15000.00)
    ]
    
    for name, desc, duration, price in services_data:
        service = Service(name=name, description=desc, duration=duration, price=price)
        db.session.add(service)
    
    print("✅ Услуги созданы (6)")
    
    # ========== АКЦИИ ==========
    today = date.today()
    promotions_data = [
        {
            'title': 'Скидка 20% на первую консультацию',
            'description': 'Для новых пациентов клиники. Включает полный осмотр и план лечения.',
            'discount_percent': 20,
            'service_id': 1,
            'start_date': today - timedelta(days=5),
            'end_date': today + timedelta(days=25)
        },
        {
            'title': 'Чистка со скидкой 30%',
            'description': 'Комплексная профессиональная чистка зубов.',
            'discount_percent': 30,
            'service_id': 3,
            'start_date': today,
            'end_date': today + timedelta(days=14)
        },
        {
            'title': 'Рассрочка 0% на брекеты',
            'description': 'Установка брекет-системы в беспроцентную рассрочку на 12 месяцев.',
            'discount_percent': 15,
            'service_id': 5,
            'start_date': today - timedelta(days=10),
            'end_date': today + timedelta(days=20)
        },
        {
            'title': 'Приведи друга — скидка 10%',
            'description': 'Приведите друга и получите оба скидку 10% на любую услугу.',
            'discount_percent': 10,
            'service_id': None,
            'start_date': today,
            'end_date': today + timedelta(days=28)
        }
    ]
    
    for p in promotions_data:
        promo = Promotion(
            title=p['title'],
            description=p['description'],
            discount_percent=p['discount_percent'],
            service_id=p['service_id'],
            start_date=p['start_date'],
            end_date=p['end_date'],
            is_active=True
        )
        db.session.add(promo)
    
    print("✅ Акции созданы (4)")
    
    db.session.commit()
    
    print("\n" + "="*50)
    print("🎉 БАЗА ДАННЫХ ЗАПОЛНЕНА!")
    print("="*50)
    print("\n👑 Админ: admin / admin")
    print("👨‍⚕️ Врачи: petrov.ivan / password")
    print("💊 6 услуг")
    print("🎉 4 акции")
    print("="*50)