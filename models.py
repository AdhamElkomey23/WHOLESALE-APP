from app import db
from flask_login import UserMixin
from datetime import datetime, timedelta
from sqlalchemy import func
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_admin(self):
        return self.role == 'admin'

class Client(db.Model):
    """Client database for managing customer information"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Client {self.name}>'

class ProductType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    selling_price = db.Column(db.Float, default=0.0)
    cost_price = db.Column(db.Float, default=0.0)
    brand_group = db.Column(db.String(20), nullable=False, default='SHARED')  # 'SHARED' or 'AZIZ'
    available_colors = db.Column(db.Text, default='')  # Comma-separated list of colors
    available_sizes = db.Column(db.Text, default='')  # Comma-separated list of sizes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    color_inventories = db.relationship('ColorSizeInventory', backref='product_type', lazy=True, cascade='all, delete-orphan')
    
    def get_colors_list(self):
        """Get list of available colors"""
        return [color.strip() for color in self.available_colors.split(',') if color.strip()]
    
    def get_sizes_list(self):
        """Get list of available sizes"""
        return [size.strip() for size in self.available_sizes.split(',') if size.strip()]

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_code = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)  # Optional for backward compatibility
    client_name = db.Column(db.String(200), nullable=False)  # Keep for backward compatibility
    phone_number = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    total_pieces = db.Column(db.Integer, nullable=False, default=0)
    is_printed = db.Column(db.Boolean, default=False)
    paid_amount = db.Column(db.Float, default=0.0)
    remaining_amount = db.Column(db.Float, default=0.0)
    brand = db.Column(db.String(50), nullable=False)  # URBRAND or SURVACCI
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    client = db.relationship('Client', backref='orders', lazy=True)
    order_items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    # Legacy properties for backward compatibility
    @property
    def product_type_obj(self):
        if self.order_items:
            return self.order_items[0].product_type
        return None
    
    @staticmethod
    def generate_order_code():
        """Generate unique order code"""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Order.query.filter_by(order_code=code).first():
                return code
    
    @property
    def total_amount(self):
        """Calculate total amount based on order items"""
        return sum(item.total_price for item in self.order_items)
    
    @property
    def profit(self):
        """Calculate profit for this order"""
        return sum(item.profit for item in self.order_items)
    
    @property
    def cost(self):
        """Calculate total cost for this order"""
        return sum(item.total_cost for item in self.order_items)
    
    @property
    def revenue(self):
        """Calculate revenue for this order"""
        return self.total_amount
    
    @property
    def number_of_colors(self):
        """Calculate number of different colors in this order"""
        colors = set()
        for item in self.order_items:
            if item.is_custom_product:
                if item.custom_color_size_matrix:
                    try:
                        matrix = json.loads(item.custom_color_size_matrix)
                        colors.update(matrix.keys())
                    except:
                        pass
                elif item.custom_product_color:
                    colors.add(item.custom_product_color)
            else:
                breakdown = item.get_color_size_breakdown()
                colors.update(breakdown.keys())
        return len(colors)
    
    @property
    def pieces_per_color(self):
        """Calculate average pieces per color"""
        num_colors = self.number_of_colors
        return round(self.total_pieces / num_colors) if num_colors > 0 else 0

class OrderItem(db.Model):
    """Individual product items within an order"""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_type_id = db.Column(db.Integer, db.ForeignKey('product_type.id'), nullable=True)  # Made nullable for custom products
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    color_size_breakdown = db.Column(db.Text, default='{}')  # JSON string storing color/size breakdown
    
    # Custom product fields (when product_type_id is null)
    is_custom_product = db.Column(db.Boolean, default=False)
    custom_product_name = db.Column(db.String(200), nullable=True)
    custom_product_description = db.Column(db.Text, nullable=True)
    custom_product_color = db.Column(db.String(50), nullable=True)
    custom_product_size = db.Column(db.String(20), nullable=True)
    custom_color_size_matrix = db.Column(db.Text, nullable=True)  # JSON string for custom color/size breakdown
    
    # Relationships
    product_type = db.relationship('ProductType', backref='order_items')
    
    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.unit_price
    
    @property
    def total_cost(self):
        """Calculate total cost for this item"""
        if self.is_custom_product:
            # For custom products, assume cost is 50% of selling price (or you can add a custom_cost_price field)
            return self.quantity * (self.unit_price * 0.5)
        return self.quantity * self.product_type.cost_price
    
    @property
    def profit(self):
        """Calculate profit for this item"""
        return self.total_price - self.total_cost
    
    def get_color_size_breakdown(self):
        """Get color/size breakdown as dictionary"""
        try:
            if self.is_custom_product and self.custom_color_size_matrix:
                return json.loads(self.custom_color_size_matrix)
            elif self.color_size_breakdown:
                return json.loads(self.color_size_breakdown)
            return {}
        except:
            return {}
    
    def set_color_size_breakdown(self, breakdown_dict):
        """Set color/size breakdown from dictionary"""
        self.color_size_breakdown = json.dumps(breakdown_dict)
    
    @property
    def product_name(self):
        """Get product name (either from ProductType or custom name)"""
        if self.is_custom_product:
            return self.custom_product_name
        return self.product_type.name if self.product_type else "Unknown Product"
    
    @property
    def product_description(self):
        """Get full product description including color/size"""
        if self.is_custom_product:
            desc = self.custom_product_name
            
            # If we have a color-size matrix, show breakdown
            if self.custom_color_size_matrix:
                try:
                    matrix = json.loads(self.custom_color_size_matrix)
                    if matrix:
                        breakdown_parts = []
                        for color, sizes in matrix.items():
                            size_parts = [f"{size}: {qty}" for size, qty in sizes.items() if qty > 0]
                            if size_parts:
                                breakdown_parts.append(f"{color} ({', '.join(size_parts)})")
                        
                        if breakdown_parts:
                            desc += f" - {' | '.join(breakdown_parts)}"
                except:
                    pass
            else:
                # Fallback to single color/size if no matrix
                if self.custom_product_color:
                    desc += f" - {self.custom_product_color}"
                if self.custom_product_size:
                    desc += f" ({self.custom_product_size})"
            
            if self.custom_product_description:
                desc += f" - {self.custom_product_description}"
            return desc
        else:
            return self.product_type.name if self.product_type else "Unknown Product"

class ColorSizeInventory(db.Model):
    """Detailed inventory tracking by color and size"""
    id = db.Column(db.Integer, primary_key=True)
    product_type_id = db.Column(db.Integer, db.ForeignKey('product_type.id'), nullable=False)
    storage_type = db.Column(db.String(20), nullable=False)  # 'SHARED' or 'AZIZ'
    color = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(20), nullable=True)  # Optional for size tracking
    quantity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (db.UniqueConstraint('product_type_id', 'storage_type', 'color', 'size', name='unique_product_color_size'),)
    
    @staticmethod
    def get_inventory_for_product(product_type_id, storage_type):
        """Get all inventory records for a product"""
        return ColorSizeInventory.query.filter_by(
            product_type_id=product_type_id,
            storage_type=storage_type
        ).all()
    
    @staticmethod
    def update_inventory(product_type_id, storage_type, color, size, quantity_change):
        """Update inventory for specific color/size combination"""
        inventory = ColorSizeInventory.query.filter_by(
            product_type_id=product_type_id,
            storage_type=storage_type,
            color=color,
            size=size
        ).first()
        
        if not inventory:
            inventory = ColorSizeInventory(
                product_type_id=product_type_id,
                storage_type=storage_type,
                color=color,
                size=size,
                quantity=max(0, quantity_change)
            )
            db.session.add(inventory)
        else:
            inventory.quantity = max(0, inventory.quantity + quantity_change)
            inventory.updated_at = datetime.utcnow()
        
        return inventory

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_type_id = db.Column(db.Integer, db.ForeignKey('product_type.id'), nullable=False)
    storage_type = db.Column(db.String(20), nullable=False)  # 'SHARED' or 'AZIZ'
    quantity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite unique constraint to ensure one record per product per storage type
    __table_args__ = (db.UniqueConstraint('product_type_id', 'storage_type', name='unique_product_storage'),)
    
    @staticmethod
    def get_available_stock(product_type_id, brand):
        """Get available stock for a product based on brand"""
        from models import ProductType
        
        # Get the product to check its brand group
        product = ProductType.query.get(product_type_id)
        if not product:
            return 0
        
        # Use the product's assigned brand group for storage type
        storage_type = product.brand_group
        
        inventory = Inventory.query.filter_by(
            product_type_id=product_type_id,
            storage_type=storage_type
        ).first()
        
        return inventory.quantity if inventory else 0
    
    @staticmethod
    def update_stock(product_type_id, brand, quantity_used):
        """Update stock when an order is placed"""
        from models import ProductType
        
        # Get the product to check its brand group
        product = ProductType.query.get(product_type_id)
        if not product:
            return False
        
        # Use the product's assigned brand group for storage type
        storage_type = product.brand_group
            
        inventory = Inventory.query.filter_by(
            product_type_id=product_type_id,
            storage_type=storage_type
        ).first()
        
        if not inventory:
            # Create inventory record if it doesn't exist
            inventory = Inventory(
                product_type_id=product_type_id,
                storage_type=storage_type,
                quantity=0
            )
            db.session.add(inventory)
        
        # Check if enough stock is available
        if inventory.quantity >= quantity_used:
            inventory.quantity -= quantity_used
            inventory.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        else:
            return False
    
    @staticmethod
    def add_stock(product_type_id, storage_type, quantity):
        """Add stock to inventory"""
        inventory = Inventory.query.filter_by(
            product_type_id=product_type_id,
            storage_type=storage_type
        ).first()
        
        if not inventory:
            inventory = Inventory(
                product_type_id=product_type_id,
                storage_type=storage_type,
                quantity=quantity
            )
            db.session.add(inventory)
        else:
            inventory.quantity += quantity
            inventory.updated_at = datetime.utcnow()
        
        db.session.commit()
        return inventory

class StockMovement(db.Model):
    """Track all stock movements for audit purposes"""
    id = db.Column(db.Integer, primary_key=True)
    product_type_id = db.Column(db.Integer, db.ForeignKey('product_type.id'), nullable=False)
    storage_type = db.Column(db.String(20), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # 'ADD', 'REMOVE', 'ORDER'
    quantity = db.Column(db.Integer, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    product_type = db.relationship('ProductType', backref='stock_movements')
    order = db.relationship('Order', backref='stock_movements')
    user = db.relationship('User', backref='stock_movements')

class Expense(db.Model):
    """Track expenses for each brand"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    brand = db.Column(db.String(50), nullable=False)  # URBRAND, SURVACCI, or AZIZ
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    user = db.relationship('User', backref='expenses')

class Worker(db.Model):
    """Track workers/employees"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone_number = db.Column(db.String(20))
    daily_salary = db.Column(db.Float, nullable=False, default=0.0)
    overtime_rate = db.Column(db.Float, default=0.0)  # per hour
    
    # Department and Brand Assignment
    department = db.Column(db.String(100), default='General')  # Print, Sewing, Packaging, etc.
    assigned_brand = db.Column(db.String(50), default='SHARED')  # URBRAND, SURVACCI, AZIZ, or SHARED
    
    # Enhanced Piece-rate payment system with multiple tiers
    piece_rate_enabled = db.Column(db.Boolean, default=False)
    
    # Tier 1: Base pieces (0 to tier1_threshold)
    tier1_threshold = db.Column(db.Integer, default=1000)  # pieces in tier 1
    tier1_rate = db.Column(db.Float, default=3.0)  # rate per piece for tier 1
    
    # Tier 2: Second threshold (tier1_threshold+1 to tier2_threshold)
    tier2_threshold = db.Column(db.Integer, default=1500)  # pieces at end of tier 2
    tier2_rate = db.Column(db.Float, default=2.0)  # rate per piece for tier 2
    
    # Tier 3: Third threshold (tier2_threshold+1 to tier3_threshold)
    tier3_threshold = db.Column(db.Integer, default=2000)  # pieces at end of tier 3
    tier3_rate = db.Column(db.Float, default=3.0)  # rate per piece for tier 3
    
    # Tier 4+: Beyond tier3_threshold
    tier4_rate = db.Column(db.Float, default=3.5)  # rate per piece beyond tier 3
    
    position = db.Column(db.String(100), default='Worker')
    hire_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='workers')
    attendances = db.relationship('WorkerAttendance', backref='worker', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Worker {self.name}>'
    
    def total_salary_for_period(self, start_date, end_date):
        """Calculate total salary for a date range"""
        attendances = WorkerAttendance.query.filter(
            WorkerAttendance.worker_id == self.id,
            WorkerAttendance.date >= start_date,
            WorkerAttendance.date <= end_date
        ).all()
        
        total = 0
        for attendance in attendances:
            total += attendance.calculate_daily_pay()
        
        return total
    
    def days_worked_this_month(self):
        """Count days worked in current month"""
        today = datetime.utcnow().date()
        start_of_month = today.replace(day=1)
        
        return WorkerAttendance.query.filter(
            WorkerAttendance.worker_id == self.id,
            WorkerAttendance.date >= start_of_month,
            WorkerAttendance.date <= today,
            WorkerAttendance.present == True
        ).count()


class WorkerAttendance(db.Model):
    """Daily attendance tracking for workers"""
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    present = db.Column(db.Boolean, default=False)
    check_in_time = db.Column(db.Time)
    check_out_time = db.Column(db.Time)
    overtime_hours = db.Column(db.Float, default=0.0)
    pieces_completed = db.Column(db.Integer, default=0)  # pieces completed that day
    deductions = db.Column(db.Float, default=0.0)
    deduction_reason = db.Column(db.String(500), default='')
    bonus = db.Column(db.Float, default=0.0)
    bonus_reason = db.Column(db.String(500), default='')
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Unique constraint to prevent duplicate entries for same worker on same date
    __table_args__ = (db.UniqueConstraint('worker_id', 'date', name='unique_worker_date'),)
    
    # Relationships
    user = db.relationship('User', backref='worker_attendances')
    
    def __repr__(self):
        return f'<WorkerAttendance {self.worker.name} - {self.date}>'
    
    def calculate_regular_hours(self):
        """Calculate regular working hours (8 hours standard)"""
        if not self.present or not self.check_in_time or not self.check_out_time:
            return 0
        
        # Convert times to datetime objects for calculation
        check_in = datetime.combine(self.date, self.check_in_time)
        check_out = datetime.combine(self.date, self.check_out_time)
        
        # Handle overnight shifts
        if check_out < check_in:
            check_out += timedelta(days=1)
        
        total_hours = (check_out - check_in).total_seconds() / 3600
        regular_hours = min(total_hours, 8)  # Max 8 regular hours
        
        return round(regular_hours, 2)
    
    def calculate_overtime_hours_auto(self):
        """Auto-calculate overtime based on check-in/out times"""
        if not self.present or not self.check_in_time or not self.check_out_time:
            return 0
        
        # Convert times to datetime objects for calculation
        check_in = datetime.combine(self.date, self.check_in_time)
        check_out = datetime.combine(self.date, self.check_out_time)
        
        # Handle overnight shifts
        if check_out < check_in:
            check_out += timedelta(days=1)
        
        total_hours = (check_out - check_in).total_seconds() / 3600
        overtime_hours = max(0, total_hours - 8)  # Overtime after 8 hours
        
        return round(overtime_hours, 2)
    
    def calculate_piece_rate_pay(self):
        """Calculate piece-rate pay based on completed pieces and multi-tier thresholds"""
        if not self.present or not self.worker.piece_rate_enabled or self.pieces_completed <= 0:
            return 0.0
        
        total_piece_pay = 0.0
        pieces_remaining = self.pieces_completed
        
        # Tier 1: 1 to tier1_threshold (e.g., 1-1000 pieces at 3 EGP each)
        if pieces_remaining > 0:
            tier1_pieces = min(pieces_remaining, self.worker.tier1_threshold)
            total_piece_pay += tier1_pieces * self.worker.tier1_rate
            pieces_remaining -= tier1_pieces
        
        # Tier 2: tier1_threshold+1 to tier2_threshold (e.g., 1001-1500 pieces at 2 EGP each)
        if pieces_remaining > 0:
            tier2_pieces = min(pieces_remaining, self.worker.tier2_threshold - self.worker.tier1_threshold)
            total_piece_pay += tier2_pieces * self.worker.tier2_rate
            pieces_remaining -= tier2_pieces
        
        # Tier 3: tier2_threshold+1 to tier3_threshold (e.g., 1501-2000 pieces at 3 EGP each)
        if pieces_remaining > 0:
            tier3_pieces = min(pieces_remaining, self.worker.tier3_threshold - self.worker.tier2_threshold)
            total_piece_pay += tier3_pieces * self.worker.tier3_rate
            pieces_remaining -= tier3_pieces
        
        # Tier 4+: Beyond tier3_threshold (e.g., 2001+ pieces at 3.5 EGP each)
        if pieces_remaining > 0:
            total_piece_pay += pieces_remaining * self.worker.tier4_rate
        
        return round(total_piece_pay, 2)

    def calculate_daily_pay(self):
        """Calculate total daily pay including salary, overtime, piece-rate, deductions, and bonuses"""
        if not self.present:
            return 0
        
        total_pay = 0.0
        
        # Add base daily salary (if not piece-rate only)
        if not self.worker.piece_rate_enabled:
            total_pay += self.worker.daily_salary
        
        # Add piece-rate pay if enabled
        if self.worker.piece_rate_enabled:
            total_pay += self.calculate_piece_rate_pay()
        
        # Add overtime pay
        overtime_pay = self.overtime_hours * self.worker.overtime_rate
        total_pay += overtime_pay
        
        # Add bonuses and subtract deductions
        total_pay += self.bonus - self.deductions
        
        return round(max(0, total_pay), 2)  # Ensure no negative pay


# Add inventory relationships after all models are defined
ProductType.inventory_items = db.relationship('Inventory', backref='product_type_obj', lazy=True)

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
