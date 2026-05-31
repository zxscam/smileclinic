from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Patient, Doctor, Appointment, Service, Review, Promotion, Message
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dental_clinic.db'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация расширений
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== ЗАГЛУШКИ EMAIL (вывод в консоль) ==========
def print_email(subject, recipients, body):
    """Просто выводит содержимое письма в консоль"""
    print("\n" + "="*60)
    print(f"📧 ПИСЬМО")
    print(f"Кому: {recipients}")
    print(f"Тема: {subject}")
    print(f"Текст: {body[:200]}...")
    print("="*60 + "\n")

def send_welcome_email(user):
    print_email(
        'Добро пожаловать в MedService!',
        [user.email],
        f'Здравствуйте, {user.username}!\n\nСпасибо за регистрацию!\nЛогин: {user.username}\nРоль: {user.role}'
    )

def send_appointment_confirmation(appointment):
    patient = appointment.patient
    user = User.query.get(patient.user_id)
    print_email(
        'Подтверждение записи на приём',
        [user.email],
        f'Запись подтверждена:\nДата: {appointment.appointment_date}\nВремя: {appointment.appointment_time}\nВрач: {appointment.doctor.full_name}\nУслуга: {appointment.service.name}'
    )

def send_appointment_reminder(appointment):
    patient = appointment.patient
    user = User.query.get(patient.user_id)
    print_email(
        'Напоминание о приёме',
        [user.email],
        f'Завтра в {appointment.appointment_time} у вас приём у {appointment.doctor.full_name}'
    )

def send_cancellation_notification(appointment):
    patient = appointment.patient
    user = User.query.get(patient.user_id)
    print_email(
        'Запись отменена',
        [user.email],
        f'Ваша запись на {appointment.appointment_date} отменена.'
    )

# ========== ГЛАВНАЯ СТРАНИЦА ==========
@app.route('/')
def index():
    services = Service.query.all()
    doctors = Doctor.query.all()
    
    top_doctors = []
    for doctor in doctors:
        if doctor.review_count > 0:
            top_doctors.append({
                'doctor': doctor,
                'rating': doctor.average_rating,
                'count': doctor.review_count
            })
    top_doctors.sort(key=lambda x: x['rating'], reverse=True)
    top_doctors = top_doctors[:3]
    
    today = datetime.now().date()
    active_promotions = Promotion.query.filter(
        Promotion.is_active == True,
        Promotion.start_date <= today,
        Promotion.end_date >= today
    ).limit(4).all()
    
    return render_template('index.html', 
                         services=services, 
                         doctors=doctors,
                         top_doctors=top_doctors,
                         active_promotions=active_promotions)

# ========== АУТЕНТИФИКАЦИЯ ==========
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        print(f"DEBUG: session.active_promotion = {session.get('active_promotion', 'нет')}")
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = 'patient'  # Всегда пациент
        
        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Этот email уже используется')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        
        try:
            send_welcome_email(user)
        except Exception as e:
            print(f"Ошибка отправки email: {e}")
        
        flash('Регистрация успешна! Пожалуйста, войдите.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Вы успешно вошли в систему!')
            return redirect(url_for('dashboard'))
        
        flash('Неверное имя пользователя или пароль')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы')
    return redirect(url_for('index'))


# ========== АДМИН: СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ==========
@app.route('/admin/users/add', methods=['POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    
    if User.query.filter_by(username=username).first():
        flash('Пользователь уже существует')
        return redirect(url_for('admin_users'))
    
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()
    
    # Если создали врача — создаём профиль врача
    if role == 'doctor':
        doctor = Doctor(
            user_id=user.id,
            first_name=request.form.get('first_name', ''),
            last_name=request.form.get('last_name', ''),
            specialty=request.form.get('specialty', '')
        )
        db.session.add(doctor)
        db.session.commit()
    
    flash(f'Пользователь {username} создан!')
    return redirect(url_for('admin_users'))

# ========== ЛИЧНЫЕ КАБИНЕТЫ ==========
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_panel'))
    elif current_user.role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    else:
        return redirect(url_for('patient_dashboard'))

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    print(f"DEBUG: patient = {patient}")
    print(f"DEBUG: patient.last_name = {patient.last_name if patient else 'None'}")
    
    if not patient:
        flash('Сначала создайте профиль пациента')
        return redirect(url_for('create_patient_profile'))
    
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.appointment_date.desc()
    ).all()
    print(f"DEBUG: appointments count = {len(appointments)}")
    
    return render_template('dashboard.html', appointments=appointments, patient=patient)

@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    if not doctor:
        flash('Профиль врача не найден')
        return redirect(url_for('create_doctor_profile'))
    
    today = datetime.now().date()
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).filter(
        Appointment.appointment_date >= today
    ).order_by(Appointment.appointment_date.asc()).all()
    
    return render_template('dashboard.html', appointments=appointments, doctor=doctor)

# ========== ПРОФИЛИ ==========
@app.route('/create-patient-profile', methods=['GET', 'POST'])
@login_required
def create_patient_profile():
    if current_user.role != 'patient':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        patient = Patient(
            user_id=current_user.id,
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            phone=request.form['phone'],
            date_of_birth=datetime.strptime(request.form['dob'], '%Y-%m-%d').date(),
            medical_history=request.form.get('medical_history', '')
        )
        db.session.add(patient)
        db.session.commit()
        flash('Профиль пациента успешно создан!')
        return redirect(url_for('patient_dashboard'))
    
    return render_template('create_profile.html')

@app.route('/create-doctor-profile', methods=['GET', 'POST'])
@login_required
def create_doctor_profile():
    if current_user.role != 'doctor':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        doctor = Doctor(
            user_id=current_user.id,
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            specialty=request.form['specialty'],
            work_hours_start=datetime.strptime(request.form['work_start'], '%H:%M').time(),
            work_hours_end=datetime.strptime(request.form['work_end'], '%H:%M').time()
        )
        db.session.add(doctor)
        db.session.commit()
        flash('Профиль врача успешно создан!')
        return redirect(url_for('doctor_dashboard'))
    
    return render_template('create_doctor_profile.html')

# ========== ЗАПИСЬ НА ПРИЁМ ==========
@app.route('/appointment', methods=['GET', 'POST'])
@login_required
def appointment():
    if current_user.role != 'patient':
        flash('Только пациенты могут записываться на прием')
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Сначала создайте профиль пациента')
        return redirect(url_for('create_patient_profile'))
    
    if request.method == 'POST':
        print("=== НАЧАЛО POST ЗАПИСИ ===")
        print(f"session: {dict(session)}")
        doctor_id = request.form['doctor_id']
        service_id = request.form['service_id']
        appointment_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        appointment_time = datetime.strptime(request.form['time'], '%H:%M').time()
        notes = request.form.get('notes', '')
        
        if appointment_date < datetime.now().date():
            flash('Нельзя записаться на прошедшую дату')
            return redirect(url_for('appointment'))
        
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status='scheduled'
        ).first()
        
        if existing:
            flash('Это время уже занято')
            return redirect(url_for('appointment'))
        
        # Получаем услугу и её цену
        service = Service.query.get(service_id)
        price = service.price
        discount_applied = 0
        promo_title = ''
        
  
         # Применение акции
        discount_applied = 0
        promo_title = ''
        if 'active_promotion' in session:
            promo = Promotion.query.get(session['active_promotion'])
            if promo and promo.is_valid:
                can_apply = True
                
                # Проверка: первая консультация — только для новых пациентов
                if promo.id == 1:
                    any_appointment = Appointment.query.filter_by(
                        patient_id=patient.id
                    ).first()
                    if any_appointment:
                        can_apply = False
                        flash('Акция "Скидка 20% на первую консультацию" только для новых пациентов!')
                
                if can_apply and (promo.service_id is None or promo.service_id == int(service_id)):
                    discount_applied = promo.discount_percent
                    promo_title = promo.title
            
            session.pop('active_promotion')
        
        if discount_applied > 0:
            flash(f'Применена скидка {discount_applied}% по акции "{promo_title}"')
        
        print(f"DEBUG: discount_applied = {discount_applied}")
        
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor_id,
            service_id=service_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            notes=notes,
            status='scheduled',
            discount_applied=discount_applied
        )
        db.session.add(appointment)
        db.session.commit()
        try:
            send_appointment_confirmation(appointment)
        except Exception as e:
            print(f"Ошибка отправки подтверждения: {e}")
        
        if discount_applied > 0:
            flash(f'Запись создана! Применена скидка {discount_applied}% по акции "{promo_title}". Итоговая цена: {price:.0f} ₽')
        else:
            flash('Вы успешно записались на прием!')
        
        return redirect(url_for('patient_dashboard'))
    
    doctors = Doctor.query.all()
    services = Service.query.all()
    
    active_promotion = None
    if 'active_promotion' in session:
        active_promotion = Promotion.query.get(session['active_promotion'])
        if not active_promotion or not active_promotion.is_valid:
            session.pop('active_promotion', None)
            active_promotion = None
    
    return render_template('appointment.html', 
                         doctors=doctors, 
                         services=services, 
                         patient=patient,
                         active_promotion=active_promotion)

@app.route('/get-available-slots/<int:doctor_id>/<date>')
def get_available_slots(doctor_id, date):
    doctor = Doctor.query.get_or_404(doctor_id)
    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    
    if date_obj.weekday() >= 5:
        return jsonify({'slots': [], 'message': 'Прием не осуществляется в выходные дни'})
    
    if date_obj < datetime.now().date():
        return jsonify({'slots': [], 'message': 'Нельзя записаться на прошедшую дату'})
    
    available_slots = []
    current_time = doctor.work_hours_start
    end_time = doctor.work_hours_end
    
    while current_time < end_time:
        booked = Appointment.query.filter_by(
            doctor_id=doctor_id,
            appointment_date=date_obj,
            appointment_time=current_time,
            status='scheduled'
        ).first()
        
        if not booked:
            available_slots.append({
                'time': current_time.strftime('%H:%M'),
                'display': current_time.strftime('%H:%M')
            })
        
        next_datetime = datetime.combine(date_obj, current_time) + timedelta(minutes=30)
        current_time = next_datetime.time()
    
    return jsonify({'slots': available_slots})

# ========== РАСПИСАНИЕ ==========
@app.route('/schedule')
@login_required
def schedule():
    # Определяем начало недели
    week_offset = request.args.get('week', 0, type=int)
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    
    # Дни недели
    day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    week_days = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        week_days.append({
            'name': day_names[i],
            'date': day_date,
            'is_today': day_date == today,
            'is_weekend': i >= 5
        })
    
    # Временные слоты
    time_slots = []
    hour = 8
    minute = 0
    while hour < 20:
        time_slots.append(f"{hour:02d}:{minute:02d}")
        minute += 30
        if minute == 60:
            hour += 1
            minute = 0
    
        # Получаем данные
    if current_user.role == 'admin':
        doctors = Doctor.query.all()
        all_appointments = Appointment.query.all()  # ВСЕ для статистики
        week_appointments = Appointment.query.filter(
            Appointment.appointment_date.between(week_start, week_end)
        ).all()  # За неделю для сетки
    elif current_user.role == 'doctor':
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        doctors = [doctor] if doctor else []
        if doctor:
            all_appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
            week_appointments = Appointment.query.filter_by(doctor_id=doctor.id).filter(
                Appointment.appointment_date.between(week_start, week_end)
            ).all()
        else:
            all_appointments = []
            week_appointments = []
    else:
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        doctors = Doctor.query.all()
        if patient:
            all_appointments = Appointment.query.filter_by(patient_id=patient.id).all()
            week_appointments = Appointment.query.filter_by(patient_id=patient.id).filter(
                Appointment.appointment_date.between(week_start, week_end)
            ).all()
        else:
            all_appointments = []
            week_appointments = []
    
    # Строим сетку
    schedule_data = {}
    for apt in week_appointments:
        time_key = apt.appointment_time.strftime('%H:%M')
        date_key = apt.appointment_date.strftime('%Y-%m-%d')
        key = f"{date_key}_{time_key}"
        if key not in schedule_data:
            schedule_data[key] = []
        schedule_data[key].append(apt)
    
    return render_template('schedule.html', 
                         schedule_data=schedule_data,
                         week_days=week_days,
                         time_slots=time_slots,
                         doctors=doctors,
                         week_start=week_start,
                         week_end=week_end,
                         week_offset=week_offset,
                         today=today,
                         appointments=all_appointments,
                         week_appointments=week_appointments)
# ========== ПАЦИЕНТЫ ==========
@app.route('/patients')
@login_required
def patients():
    if current_user.role not in ['admin', 'doctor']:
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    patients = Patient.query.all()
    return render_template('patients.html', patients=patients)

@app.route('/patient-history/<int:patient_id>')
@login_required
def patient_history(patient_id):
    if current_user.role not in ['admin', 'doctor']:
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(
        Appointment.appointment_date.desc()
    ).all()
    
    return render_template('patient_history.html', patient=patient, appointments=appointments)

# ========== УПРАВЛЕНИЕ ЗАПИСЯМИ ==========
@app.route('/cancel-appointment/<int:appointment_id>')
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if current_user.role == 'patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient or appointment.patient_id != patient.id:
            flash('Вы не можете отменить эту запись')
            return redirect(url_for('dashboard'))
    
    if appointment.status != 'scheduled':
        flash('Эта запись уже отменена или завершена')
        return redirect(url_for('dashboard'))
    
    appointment.status = 'cancelled'
    db.session.commit()
    
    try:
        send_cancellation_notification(appointment)
    except Exception as e:
        print(f"Ошибка отправки уведомления об отмене: {e}")
    
    flash('Запись успешно отменена')
    return redirect(url_for('dashboard'))

@app.route('/complete-appointment/<int:appointment_id>', methods=['POST'])
@login_required
def complete_appointment(appointment_id):
    if current_user.role not in ['admin', 'doctor']:
        return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
    
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if appointment.status != 'scheduled':
        return jsonify({'success': False, 'error': 'Прием уже отменен или завершен'}), 400
    
    appointment.status = 'completed'
    db.session.commit()
    
    return jsonify({'success': True})

# ========== РЕЙТИНГИ И ОТЗЫВЫ ==========
@app.route('/reviews')
def reviews():
    approved_reviews = Review.query.filter_by(is_approved=True).order_by(
        Review.created_at.desc()
    ).all()
    
    doctors = Doctor.query.all()
    doctors_rating = []
    for doctor in doctors:
        if doctor.review_count > 0:
            doctors_rating.append({
                'doctor': doctor,
                'rating': doctor.average_rating,
                'count': doctor.review_count
            })
    
    doctors_rating.sort(key=lambda x: x['rating'], reverse=True)
    
    return render_template('reviews.html', 
                         reviews=approved_reviews, 
                         doctors_rating=doctors_rating)

@app.route('/doctor/<int:doctor_id>/reviews')
def doctor_reviews(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    reviews = Review.query.filter_by(
        doctor_id=doctor_id, 
        is_approved=True
    ).order_by(Review.created_at.desc()).all()
    
    return render_template('doctor_reviews.html', doctor=doctor, reviews=reviews)

@app.route('/add-review/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def add_review(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    
    if current_user.role != 'patient':
        flash('Только пациенты могут оставлять отзывы')
        return redirect(url_for('dashboard'))
    
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient or appointment.patient_id != patient.id:
        flash('Вы не можете оставить отзыв на эту запись')
        return redirect(url_for('dashboard'))
    
    if appointment.status != 'completed':
        flash('Отзыв можно оставить только после завершения приёма')
        return redirect(url_for('dashboard'))
    
    existing_review = Review.query.filter_by(appointment_id=appointment_id).first()
    if existing_review:
        flash('Вы уже оставили отзыв на этот приём')
        return redirect(url_for('patient_dashboard'))
    
    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form.get('comment', '')
        
        if rating < 1 or rating > 5:
            flash('Некорректная оценка')
            return redirect(url_for('add_review', appointment_id=appointment_id))
        
        review = Review(
            patient_id=patient.id,
            doctor_id=appointment.doctor_id,
            appointment_id=appointment_id,
            rating=rating,
            comment=comment,
            is_approved=False
        )
        db.session.add(review)
        db.session.commit()
        
        flash('Спасибо за отзыв! Он появится после проверки модератором.')
        return redirect(url_for('patient_dashboard'))
    
    return render_template('add_review.html', appointment=appointment)

@app.route('/api/doctor-rating/<int:doctor_id>')
def api_doctor_rating(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return jsonify({
        'average_rating': doctor.average_rating,
        'review_count': doctor.review_count,
        'stars': '⭐' * int(doctor.average_rating)
    })

# ========== АКЦИИ И СПЕЦПРЕДЛОЖЕНИЯ ==========
@app.route('/promotions')
def promotions():
    today = datetime.now().date()
    
    active_promotions = Promotion.query.filter(
        Promotion.is_active == True,
        Promotion.start_date <= today,
        Promotion.end_date >= today
    ).order_by(Promotion.created_at.desc()).all()
    
    # Проверяем, является ли пациент новым (если он авторизован)
    is_new_patient = True
    if current_user.is_authenticated and current_user.role == 'patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if patient:
            has_appointments = Appointment.query.filter_by(patient_id=patient.id).first()
            if has_appointments:
                is_new_patient = False
    
    # Убираем акцию "первая консультация" для старых пациентов
    if not is_new_patient:
        active_promotions = [p for p in active_promotions if p.id != 1]
    
    past_promotions = Promotion.query.filter(
        Promotion.end_date < today
    ).order_by(Promotion.end_date.desc()).limit(5).all()
    
    return render_template('promotions.html', 
                         active_promotions=active_promotions,
                         past_promotions=past_promotions,
                         now=datetime.now())

@app.route('/promotion/<int:promotion_id>')
def promotion_detail(promotion_id):
    promotion = Promotion.query.get_or_404(promotion_id)
    return render_template('promotion_detail.html', promotion=promotion)

@app.route('/apply-promotion/<int:promotion_id>')
@login_required
def apply_promotion(promotion_id):
    if current_user.role != 'patient':
        flash('Только пациенты могут использовать акции')
        return redirect(url_for('promotions'))
    
    promotion = Promotion.query.get_or_404(promotion_id)
    
    if not promotion.is_valid:
        flash('Эта акция уже недействительна')
        return redirect(url_for('promotions'))
    
    # Проверка для акции "первая консультация"
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if promotion.id == 1:  # ID акции "Скидка 20% на первую консультацию"
        # Проверяем, есть ли у пациента выполненные приёмы
        completed = Appointment.query.filter_by(
            patient_id=patient.id,
            status='completed'
        ).first()
        if completed:
            flash('Эта акция только для новых пациентов! У вас уже были приёмы.')
            return redirect(url_for('promotions'))
    
    session['active_promotion'] = promotion_id
    flash(f'Акция "{promotion.title}" применена! Скидка {promotion.discount_percent}% будет учтена при записи.')
    return redirect(url_for('appointment'))

# ========== API ==========
@app.route('/api/doctors')
def api_doctors():
    doctors = Doctor.query.all()
    doctors_list = []
    for doctor in doctors:
        doctors_list.append({
            'id': doctor.id,
            'name': doctor.full_name,
            'specialty': doctor.specialty,
            'rating': doctor.average_rating,
            'work_hours': f"{doctor.work_hours_start.strftime('%H:%M')} - {doctor.work_hours_end.strftime('%H:%M')}"
        })
    return jsonify(doctors_list)

@app.route('/api/services')
def api_services():
    services = Service.query.all()
    services_list = []
    for service in services:
        services_list.append({
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'duration': service.duration,
            'price': service.price
        })
    return jsonify(services_list)

@app.route('/api/promotions')
def api_promotions():
    today = datetime.now().date()
    promotions = Promotion.query.filter(
        Promotion.is_active == True,
        Promotion.start_date <= today,
        Promotion.end_date >= today
    ).all()
    
    result = [{
        'id': p.id,
        'title': p.title,
        'description': p.description[:100],
        'discount': p.discount_percent,
        'service': p.service.name if p.service else 'Все услуги',
        'end_date': p.end_date.strftime('%d.%m.%Y')
    } for p in promotions]
    
    return jsonify(result)

# ========== АДМИН-ПАНЕЛЬ ==========
@app.route('/admin')
@login_required
def admin_panel():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    stats = {
        'total_users': User.query.count(),
        'total_patients': Patient.query.count(),
        'total_doctors': Doctor.query.count(),
        'today_appointments': Appointment.query.filter_by(
            appointment_date=datetime.now().date(),
            status='scheduled'
        ).count(),
        'total_reviews': Review.query.count(),
        'pending_reviews': Review.query.filter_by(is_approved=False).count(),
        'active_promotions': Promotion.query.filter(
            Promotion.is_active == True,
            Promotion.start_date <= datetime.now().date(),
            Promotion.end_date >= datetime.now().date()
        ).count()
    }
    
    upcoming_appointments = Appointment.query.filter(
        Appointment.appointment_date >= datetime.now().date(),
        Appointment.status == 'scheduled'
    ).order_by(Appointment.appointment_date.asc()).limit(10).all()
    
    pending_reviews = Review.query.filter_by(is_approved=False).order_by(
        Review.created_at.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats,
                         upcoming_appointments=upcoming_appointments,
                         pending_reviews=pending_reviews)

@app.route('/admin/reviews')
@login_required
def admin_reviews():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    pending = Review.query.filter_by(is_approved=False).order_by(Review.created_at.desc()).all()
    approved = Review.query.filter_by(is_approved=True).order_by(Review.created_at.desc()).all()
    
    return render_template('admin/reviews.html', pending=pending, approved=approved)

@app.route('/admin/approve-review/<int:review_id>')
@login_required
def approve_review(review_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    review = Review.query.get_or_404(review_id)
    review.is_approved = True
    db.session.commit()
    flash('Отзыв одобрен')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/delete-review/<int:review_id>')
@login_required
def delete_review(review_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Отзыв удален')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/respond-review/<int:review_id>', methods=['POST'])
@login_required
def respond_review(review_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    review = Review.query.get_or_404(review_id)
    review.admin_response = request.form['response']
    review.is_approved = True
    db.session.commit()
    flash('Ответ отправлен')
    return redirect(url_for('admin_reviews'))

# ========== ОШИБКИ ==========
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# ========== ЧАТ ==========

@app.route('/chat')
@login_required
def chat_list():
    """Список чатов"""
    if current_user.role == 'patient':
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        if not patient:
            flash('Сначала создайте профиль пациента')
            return redirect(url_for('create_patient_profile'))
        
        # Получаем врачей по записям
        appointments = Appointment.query.filter_by(patient_id=patient.id).all()
        doctor_ids = list(set([a.doctor_id for a in appointments]))
        contacts = Doctor.query.filter(Doctor.id.in_(doctor_ids)).all() if doctor_ids else []
        
    elif current_user.role == 'doctor':
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        if not doctor:
            flash('Профиль врача не найден')
            return redirect(url_for('create_doctor_profile'))
        
        # Получаем пациентов по записям
        appointments = Appointment.query.filter_by(doctor_id=doctor.id).all()
        patient_ids = list(set([a.patient_id for a in appointments]))
        contacts = Patient.query.filter(Patient.id.in_(patient_ids)).all() if patient_ids else []
        
    else:
        contacts = []
    
    return render_template('chat_list.html', contacts=contacts)


@app.route('/chat/<int:contact_id>')
@login_required
def chat(contact_id):
    """Окно чата"""
    
    if current_user.role == 'patient':
        contact_doctor = Doctor.query.get_or_404(contact_id)
        # Получаем user_id врача
        contact_user = User.query.get(contact_doctor.user_id)
        
    elif current_user.role == 'doctor':
        contact_patient = Patient.query.get_or_404(contact_id)
        # Получаем user_id пациента
        contact_user = User.query.get(contact_patient.user_id)
        
    else:
        return redirect(url_for('dashboard'))
    
    # Получаем сообщения
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == contact_user.id)) |
        ((Message.sender_id == contact_user.id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()
    
    # Отмечаем как прочитанные
    unread = Message.query.filter_by(
        receiver_id=current_user.id,
        sender_id=contact_user.id,
        is_read=False
    ).all()
    for msg in unread:
        msg.is_read = True
    
    if unread:
        db.session.commit()
    
    return render_template('chat.html', messages=messages, contact=contact_user)

@app.route('/api/chat/send', methods=['POST'])
@login_required
def send_message():
    """Отправка сообщения"""
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Пустое сообщение'}), 400
    
    message = Message(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'id': message.id,
        'content': message.content,
        'created_at': message.created_at.strftime('%H:%M')
    })


@app.route('/api/chat/new-messages')
@login_required
def check_new_messages():
    """Проверка новых сообщений"""
    last_id = request.args.get('last_id', 0, type=int)
    contact_id = request.args.get('contact_id', 0, type=int)
    
    new_messages = Message.query.filter(
        Message.id > last_id,
        Message.sender_id == contact_id,
        Message.receiver_id == current_user.id
    ).order_by(Message.created_at.asc()).all()
    
    # Отмечаем как прочитанные
    for msg in new_messages:
        msg.is_read = True
    
    if new_messages:
        db.session.commit()
    
    result = [{
        'id': msg.id,
        'content': msg.content,
        'created_at': msg.created_at.strftime('%H:%M')
    } for msg in new_messages]
    
    return jsonify({'messages': result})
@app.route('/doctor/<int:doctor_id>/profile')
def doctor_profile(doctor_id):
    """Профиль врача"""
    doctor = Doctor.query.get_or_404(doctor_id)
    reviews = Review.query.filter_by(
        doctor_id=doctor_id, 
        is_approved=True
    ).order_by(Review.created_at.desc()).all()
    
    return render_template('doctor_profile.html', doctor=doctor, reviews=reviews)

# ========== АДМИН: УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ==========
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/<int:user_id>/delete')
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Нельзя удалить администратора')
        return redirect(url_for('admin_users'))
    
    # Удаляем связанного доктора или пациента
    if user.role == 'doctor':
        doctor = Doctor.query.filter_by(user_id=user.id).first()
        if doctor:
            db.session.delete(doctor)
    elif user.role == 'patient':
        patient = Patient.query.filter_by(user_id=user.id).first()
        if patient:
            db.session.delete(patient)
    
    # Удаляем пользователя
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удалён')
    return redirect(url_for('admin_users'))

# ========== АДМИН: УПРАВЛЕНИЕ ВРАЧАМИ ==========
@app.route('/admin/doctors')
@login_required
def admin_doctors():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    doctors = Doctor.query.all()
    return render_template('admin/doctors.html', doctors=doctors)

@app.route('/admin/doctor/<int:doctor_id>/delete')
@login_required
def admin_delete_doctor(doctor_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Врач удалён')
    return redirect(url_for('admin_doctors'))

# ========== АДМИН: УПРАВЛЕНИЕ УСЛУГАМИ ==========
@app.route('/admin/services')
@login_required
def admin_services():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    services = Service.query.all()
    return render_template('admin/services.html', services=services)

@app.route('/admin/service/add', methods=['POST'])
@login_required
def admin_add_service():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    service = Service(
        name=request.form['name'],
        description=request.form['description'],
        duration=int(request.form['duration']),
        price=float(request.form['price'])
    )
    db.session.add(service)
    db.session.commit()
    flash('Услуга добавлена')
    return redirect(url_for('admin_services'))

@app.route('/admin/service/<int:service_id>/delete')
@login_required
def admin_delete_service(service_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash('Услуга удалена')
    return redirect(url_for('admin_services'))

# ========== АДМИН: ВСЕ ЗАПИСИ ==========
@app.route('/admin/appointments')
@login_required
def admin_appointments():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    appointments = Appointment.query.order_by(Appointment.appointment_date.desc()).limit(50).all()
    return render_template('admin/appointments.html', appointments=appointments)

@app.route('/admin/appointment/<int:appointment_id>/status', methods=['POST'])
@login_required
def admin_change_status(appointment_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = request.form['status']
    db.session.commit()
    flash('Статус изменён')
    return redirect(url_for('admin_appointments'))

# ========== АДМИН: АКЦИИ ==========
@app.route('/admin/promotions')
@login_required
def admin_promotions():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    promotions = Promotion.query.order_by(Promotion.created_at.desc()).all()
    return render_template('admin/promotions.html', promotions=promotions)

@app.route('/admin/promotion/add', methods=['POST'])
@login_required
def admin_add_promotion():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    promotion = Promotion(
        title=request.form['title'],
        description=request.form['description'],
        discount_percent=int(request.form['discount']),
        service_id=request.form.get('service_id') or None,
        start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
        end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date(),
        is_active=True
    )
    db.session.add(promotion)
    db.session.commit()
    flash('Акция добавлена')
    return redirect(url_for('admin_promotions'))

@app.route('/admin/promotion/<int:promotion_id>/toggle')
@login_required
def admin_toggle_promotion(promotion_id):
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    promo = Promotion.query.get_or_404(promotion_id)
    promo.is_active = not promo.is_active
    db.session.commit()
    flash('Статус акции изменён')
    return redirect(url_for('admin_promotions'))
# ========== АДМИН: РЕДАКТИРОВАНИЕ РАСПИСАНИЯ ==========
@app.route('/admin/schedule/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_schedule():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            appointment = Appointment(
                patient_id=int(request.form['patient_id']),
                doctor_id=int(request.form['doctor_id']),
                service_id=int(request.form['service_id']),
                appointment_date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
                appointment_time=datetime.strptime(request.form['time'], '%H:%M').time(),
                notes=request.form.get('notes', ''),
                status='scheduled'
            )
            db.session.add(appointment)
            db.session.commit()
            flash('Запись добавлена!')
        
        elif action == 'edit':
            apt = Appointment.query.get_or_404(int(request.form['appointment_id']))
            apt.doctor_id = int(request.form['doctor_id'])
            apt.service_id = int(request.form['service_id'])
            apt.appointment_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            apt.appointment_time = datetime.strptime(request.form['time'], '%H:%M').time()
            apt.notes = request.form.get('notes', '')
            db.session.commit()
            flash('Запись обновлена!')
        
        elif action == 'delete':
            apt = Appointment.query.get_or_404(int(request.form['appointment_id']))
            db.session.delete(apt)
            db.session.commit()
            flash('Запись удалена!')
        
        return redirect(url_for('admin_edit_schedule'))
    
    # GET - показываем форму
    patients = Patient.query.all()
    doctors = Doctor.query.all()
    services = Service.query.all()
    
    # Ближайшие записи
    appointments = Appointment.query.order_by(
        Appointment.appointment_date.asc()
    ).limit(30).all()
    
    return render_template('admin/edit_schedule.html',
                         patients=patients,
                         doctors=doctors,
                         services=services,
                         appointments=appointments)
# ========== ЗАПУСК ==========
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from werkzeug.security import generate_password_hash
        from datetime import date
        
        # Заполняем только если база пустая
        if not User.query.first():
            print("🔄 Заполнение базы данных...")
            
            # Админ
            db.session.add(User(username='admin', email='admin@smileclinic.ru', 
                              password_hash=generate_password_hash('admin'), role='admin'))
            
            # Врачи
            doctors_data = [
                ('petrov.ivan', 'password', 'petrov.ivan@smileclinic.ru', 'Иван', 'Петров', 'Терапевт', '09:00', '18:00'),
                ('sidorova.maria', 'password', 'sidorova.maria@smileclinic.ru', 'Мария', 'Сидорова', 'Ортодонт', '10:00', '19:00'),
                ('ivanov.alexey', 'password', 'ivanov.alexey@smileclinic.ru', 'Алексей', 'Иванов', 'Хирург', '08:00', '17:00')
            ]
            for uname, pw, em, fn, ln, sp, ws, we in doctors_data:
                u = User(username=uname, email=em, password_hash=generate_password_hash(pw), role='doctor')
                db.session.add(u); db.session.flush()
                db.session.add(Doctor(user_id=u.id, first_name=fn, last_name=ln, specialty=sp,
                                      work_hours_start=datetime.strptime(ws, '%H:%M').time(),
                                      work_hours_end=datetime.strptime(we, '%H:%M').time()))
            print("✅ Врачи (3)")
            
            # Услуги
            for n, d, dur, p in [
                ('Консультация терапевта', 'Первичный осмотр, диагностика и план лечения', 30, 1500),
                ('Лечение кариеса', 'Удаление кариозных тканей и пломбирование', 60, 3500),
                ('Профессиональная чистка', 'Ультразвук, Air Flow, полировка', 45, 3000),
                ('Удаление зуба', 'Хирургическое удаление любой сложности', 60, 5000),
                ('Установка брекетов', 'Консультация ортодонта и установка', 90, 25000),
                ('Отбеливание зубов', 'Профессиональное отбеливание Zoom', 90, 15000)
            ]:
                db.session.add(Service(name=n, description=d, duration=dur, price=p))
            print("✅ Услуги (6)")
            
            # Акции
            t = date.today()
            for ti, desc, dis, sid in [
                ('Приведи друга — скидка 10%', 'Скидка вам и другу на любую услугу.', 10, None),
                ('Рассрочка 0% на брекеты', 'Беспроцентная рассрочка на 12 месяцев.', 15, 5),
                ('Чистка со скидкой 30%', 'Комплексная профессиональная чистка.', 30, 3),
                ('Скидка 20% на первую консультацию', 'Для новых пациентов. Полный осмотр и план лечения.', 20, 1)
                ]:
                db.session.add(Promotion(title=ti, description=desc, discount_percent=dis, service_id=sid,
                                        start_date=t-timedelta(5), end_date=t+timedelta(25), is_active=True))
            print("✅ Акции (4)")
            
            db.session.commit()
            print("\n🎉 БАЗА ЗАПОЛНЕНА!")
            print("👑 admin / admin")
            print("👨‍⚕️ petrov.ivan / password")
    
    app.run(host='0.0.0.0', port=10000)