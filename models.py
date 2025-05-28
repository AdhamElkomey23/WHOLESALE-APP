from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cost_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with orders
    orders = db.relationship('Order', backref='product_type_obj', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(200), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    product_type_id = db.Column(db.Integer, db.ForeignKey('product_type.id'), nullable=False)
    total_pieces = db.Column(db.Integer, nullable=False)
    number_of_colors = db.Column(db.Integer, nullable=False)
    pieces_per_color = db.Column(db.Integer, nullable=False)
    is_printed = db.Column(db.Boolean, default=False)
    paid_amount = db.Column(db.Float, default=0.0)
    remaining_amount = db.Column(db.Float, default=0.0)
    brand = db.Column(db.String(50), nullable=False)  # URBRAND or SURVACCI
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def total_amount(self):
        """Calculate total amount based on pieces and product price"""
        if self.product_type_obj:
            return self.total_pieces * self.product_type_obj.selling_price
        return 0.0
    
    @property
    def profit(self):
        """Calculate profit for this order"""
        if self.product_type_obj:
            cost = self.total_pieces * self.product_type_obj.cost_price
            revenue = self.total_pieces * self.product_type_obj.selling_price
            return revenue - cost
        return 0.0
    
    @property
    def cost(self):
        """Calculate total cost for this order"""
        if self.product_type_obj:
            return self.total_pieces * self.product_type_obj.cost_price
        return 0.0
    
    @property
    def revenue(self):
        """Calculate revenue for this order"""
        if self.product_type_obj:
            return self.total_pieces * self.product_type_obj.selling_price
        return 0.0
