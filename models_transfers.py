# Money Transfer model for tracking incoming transfers
from app import db
from datetime import datetime

class MoneyTransfer(db.Model):
    __tablename__ = 'money_transfer'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_name = db.Column(db.String(200), nullable=False)
    sender_phone = db.Column(db.String(20))
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MoneyTransfer {self.sender_name}: EGP {self.amount}>'