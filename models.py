from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='patient')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    patient = db.relationship('Patient', backref='user', uselist=False, lazy=True)
    doctor = db.relationship('Doctor', backref='user', uselist=False, lazy=True)
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Patient(db.Model):
    __tablename__ = 'patients'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    medical_history = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    reviews = db.relationship('Review', backref='patient', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"
    
    def __repr__(self):
        return f'<Patient {self.full_name}>'

class Doctor(db.Model):
    __tablename__ = 'doctors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    specialty = db.Column(db.String(100))
    work_hours_start = db.Column(db.Time, default=datetime.strptime('09:00', '%H:%M').time())
    work_hours_end = db.Column(db.Time, default=datetime.strptime('18:00', '%H:%M').time())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)
    reviews = db.relationship('Review', backref='doctor', lazy=True)
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}"
    
    @property
    def average_rating(self):
        approved_reviews = [r for r in self.reviews if r.is_approved]
        if not approved_reviews:
            return 0
        return round(sum(r.rating for r in approved_reviews) / len(approved_reviews), 1)
    
    @property
    def review_count(self):
        return len([r for r in self.reviews if r.is_approved])
    
    def __repr__(self):
        return f'<Doctor {self.full_name} - {self.specialty}>'

class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)
    price = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointments = db.relationship('Appointment', backref='service', lazy=True)
    promotions = db.relationship('Promotion', backref='service', lazy=True)
    
    def __repr__(self):
        return f'<Service {self.name}>'

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    notes = db.Column(db.Text)
    discount_applied = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    review = db.relationship('Review', backref='appointment', uselist=False, lazy=True)
    messages = db.relationship('Message', backref='appointment', lazy=True)
    
    @property
    def status_display(self):
        statuses = {
            'scheduled': 'Запланирован',
            'completed': 'Выполнен',
            'cancelled': 'Отменён'
        }
        return statuses.get(self.status, self.status)
    
    @property
    def status_color(self):
        colors = {
            'scheduled': '#3498db',
            'completed': '#2ecc71',
            'cancelled': '#e74c3c'
        }
        return colors.get(self.status, '#95a5a6')
    
    def __repr__(self):
        return f'<Appointment {self.appointment_date} {self.appointment_time}>'

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), unique=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=False)
    admin_response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def stars_display(self):
        return '⭐' * self.rating + '☆' * (5 - self.rating)
    
    def __repr__(self):
        return f'<Review {self.rating}★ for Doctor {self.doctor_id}>'

class Promotion(db.Model):
    __tablename__ = 'promotions'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    discount_percent = db.Column(db.Integer, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def is_valid(self):
        today = datetime.now().date()
        return self.is_active and self.start_date <= today <= self.end_date
    
    @property
    def days_left(self):
        if not self.is_valid:
            return 0
        return (self.end_date - datetime.now().date()).days
    
    @property
    def discount_price(self):
        if self.service:
            return round(self.service.price * (1 - self.discount_percent / 100), 2)
        return None
    
    def __repr__(self):
        return f'<Promotion {self.title}>'

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Message from {self.sender_id} to {self.receiver_id}>'