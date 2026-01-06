from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SelectMultipleField, IntegerField, FloatField, BooleanField, DateField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError, EqualTo, Optional
from wtforms.widgets import CheckboxInput, ListWidget
from models import ProductType, Client
from datetime import datetime

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class OrderForm(FlaskForm):
    order_code = StringField('Order Code', validators=[Length(max=50)])
    client_id = SelectField('Select Client', coerce=int, validators=[], default=0)
    client_name = StringField('Or Enter New Client Name', validators=[Length(max=200)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    address = TextAreaField('Address', validators=[Length(max=500)])
    date = DateField('Date', validators=[DataRequired()], default=datetime.today)
    is_printed = BooleanField('Printed')
    paid_amount = FloatField('Paid Amount (EGP)', validators=[NumberRange(min=0)], default=0.0)
    remaining_amount = FloatField('Remaining Amount (EGP)', validators=[NumberRange(min=0)], default=0.0)
    brand = SelectField('Brand', choices=[('URBRAND', 'URBRAND'), ('SURVACCI', 'SURVACCI'), ('AZIZ', 'AZIZ')], validators=[DataRequired()])
    notes = TextAreaField('Order Notes', validators=[Length(max=500)])
    # Legacy fields for backward compatibility
    product_type_id = SelectField('Product Type', coerce=int, validators=[], default=0)
    total_pieces = IntegerField('Total Pieces', validators=[NumberRange(min=0)], default=0)
    pieces_per_color = IntegerField('Pieces Per Color', validators=[NumberRange(min=0)], default=0)
    quantity = IntegerField('Quantity', validators=[NumberRange(min=0)], default=0)
    unit_price = FloatField('Unit Price (EGP)', validators=[NumberRange(min=0)], default=0.0)
    selected_colors = SelectMultipleField('Selected Colors', choices=[
        ('Black', 'Black'), ('White', 'White'), ('Green', 'Green'), ('Petrol', 'Petrol'), 
        ('Burgundy', 'Burgundy'), ('Brown', 'Brown'), ('Baby Pink', 'Baby Pink')
    ])
    selected_sizes = SelectMultipleField('Selected Sizes', choices=[
        ('XS', 'Extra Small (XS)'), ('S', 'Small (S)'), ('M', 'Medium (M)'), 
        ('L', 'Large (L)'), ('XL', 'Extra Large (XL)'), ('XXL', '2XL'), 
        ('XXXL', '3XL'), ('XXXXL', '4XL'), ('XXXXXL', '5XL')
    ])
    # Dynamic fields for product quantities will be added via JavaScript
    submit = SubmitField('Save Order')
    
    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        # Load clients for dropdown - handle empty string for coercion
        clients = Client.query.all()
        self.client_id.choices = [(0, 'Select existing client...')] + [(c.id, f"{c.name} - {c.phone_number}") for c in clients]
        # Load products for backward compatibility
        products = ProductType.query.all()
        self.product_type_id.choices = [(0, 'Select product...')] + [(p.id, p.name) for p in products]

class ClientForm(FlaskForm):
    name = StringField('Client Name', validators=[DataRequired(), Length(max=200)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    address = TextAreaField('Address', validators=[Length(max=500)])
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    submit = SubmitField('Save Client')

class ProductTypeForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    selling_price = FloatField('Selling Price (EGP)', validators=[DataRequired(), NumberRange(min=0)])
    brand_group = SelectField('Brand Group', choices=[('SHARED', 'URBRAND/SURVACCI (Shared Storage)'), ('AZIZ', 'AZIZ (Separate Storage)')], validators=[DataRequired()])
    available_colors = SelectMultipleField('Available Colors', choices=[
        ('Black', 'Black'), ('White', 'White'), ('Green', 'Green'), ('Petrol', 'Petrol'), 
        ('Burgundy', 'Burgundy'), ('Brown', 'Brown'), ('Baby Pink', 'Baby Pink')
    ], validators=[DataRequired()])
    available_sizes = SelectMultipleField('Available Sizes', choices=[
        ('XS', 'Extra Small (XS)'), ('S', 'Small (S)'), ('M', 'Medium (M)'), 
        ('L', 'Large (L)'), ('XL', 'Extra Large (XL)'), ('XXL', '2XL'), 
        ('XXXL', '3XL'), ('XXXXL', '4XL'), ('XXXXXL', '5XL')
    ], validators=[DataRequired()])
    submit = SubmitField('Save Product')
    
    def validate_selling_price(self, field):
        # Remove cost_price validation since it's not in this form
        pass

class ColorSizeInventoryForm(FlaskForm):
    product_type_id = SelectField('Product Type', coerce=int, validators=[DataRequired()])
    storage_type = SelectField('Storage Type', choices=[('SHARED', 'URBRAND + SURVACCI (Shared)'), ('AZIZ', 'AZIZ (Independent)')], validators=[DataRequired()])
    submit = SubmitField('Manage Inventory')
    
    def __init__(self, *args, **kwargs):
        super(ColorSizeInventoryForm, self).__init__(*args, **kwargs)
        self.product_type_id.choices = [(pt.id, pt.name) for pt in ProductType.query.all()]

class InventoryForm(FlaskForm):
    product_type_id = SelectField('Product Type', coerce=int, validators=[DataRequired()])
    storage_type = SelectField('Storage Type', choices=[('SHARED', 'URBRAND + SURVACCI (Shared)'), ('AZIZ', 'AZIZ (Independent)')], validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Update Stock')
    
    def __init__(self, *args, **kwargs):
        super(InventoryForm, self).__init__(*args, **kwargs)
        from models import ProductType
        self.product_type_id.choices = [(pt.id, pt.name) for pt in ProductType.query.all()]

class StockAdjustmentForm(FlaskForm):
    adjustment_type = SelectField('Adjustment Type', choices=[('ADD', 'Add Stock'), ('REMOVE', 'Remove Stock')], validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    notes = StringField('Notes', validators=[Length(max=500)])
    submit = SubmitField('Adjust Stock')

class ExpenseForm(FlaskForm):
    name = StringField('Expense Name', validators=[DataRequired(), Length(max=200)])
    amount = FloatField('Amount (EGP)', validators=[DataRequired(), NumberRange(min=0)])
    date = DateField('Date', validators=[DataRequired()], default=datetime.today)
    brand = SelectField('Brand', choices=[('URBRAND', 'URBRAND'), ('SURVACCI', 'SURVACCI'), ('AZIZ', 'AZIZ')], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    submit = SubmitField('Save Expense')

class UserProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[Length(min=6, max=128)])
    confirm_password = PasswordField('Confirm New Password', 
                                   validators=[EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Update Profile')
    
    def __init__(self, original_username, original_email, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email
    
    def validate_username(self, field):
        if field.data != self.original_username:
            from models import User
            user = User.query.filter_by(username=field.data).first()
            if user:
                raise ValidationError('Username already taken. Please choose a different one.')
    
    def validate_email(self, field):
        if field.data != self.original_email:
            from models import User
            user = User.query.filter_by(email=field.data).first()
            if user:
                raise ValidationError('Email already registered. Please choose a different one.')


class WorkerForm(FlaskForm):
    name = StringField('Worker Name', validators=[DataRequired(), Length(max=200)])
    phone_number = StringField('Phone Number', validators=[Length(max=20)])
    daily_salary = FloatField('Daily Salary (EGP)', validators=[DataRequired(), NumberRange(min=0)])
    overtime_rate = FloatField('Overtime Rate (EGP/hour)', validators=[NumberRange(min=0)], default=0.0)
    
    # Department and Brand Assignment
    department = SelectField('Department', choices=[
        ('General', 'General'), 
        ('Print', 'Print (T-Shirt Printing)'), 
        ('Sewing', 'Sewing'),
        ('Cutting', 'Cutting'),
        ('Packaging', 'Packaging'),
        ('Quality Control', 'Quality Control'),
        ('Finishing', 'Finishing')
    ], validators=[DataRequired()])
    assigned_brand = SelectField('Assigned Brand', choices=[
        ('SHARED', 'SHARED (Works for all brands)'),
        ('URBRAND', 'URBRAND Only'),
        ('SURVACCI', 'SURVACCI Only'),
        ('AZIZ', 'AZIZ Only')
    ], validators=[DataRequired()])
    
    # Enhanced Piece-rate payment system with multiple tiers
    piece_rate_enabled = BooleanField('Enable Piece-Rate Payment')
    
    # Tier 1 Configuration
    tier1_threshold = IntegerField('Tier 1 Threshold (pieces)', validators=[NumberRange(min=1)], default=1000)
    tier1_rate = FloatField('Tier 1 Rate (EGP per piece)', validators=[NumberRange(min=0)], default=3.0)
    
    # Tier 2 Configuration
    tier2_threshold = IntegerField('Tier 2 Threshold (pieces)', validators=[NumberRange(min=1)], default=1500)
    tier2_rate = FloatField('Tier 2 Rate (EGP per piece)', validators=[NumberRange(min=0)], default=2.0)
    
    # Tier 3 Configuration
    tier3_threshold = IntegerField('Tier 3 Threshold (pieces)', validators=[NumberRange(min=1)], default=2000)
    tier3_rate = FloatField('Tier 3 Rate (EGP per piece)', validators=[NumberRange(min=0)], default=3.0)
    
    # Tier 4+ Configuration
    tier4_rate = FloatField('Tier 4+ Rate (EGP per piece)', validators=[NumberRange(min=0)], default=3.5)
    
    position = StringField('Position', validators=[Length(max=100)], default='Worker')
    hire_date = DateField('Hire Date', validators=[DataRequired()], default=datetime.today)
    is_active = BooleanField('Active Worker', default=True)
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    submit = SubmitField('Save Worker')


class AttendanceForm(FlaskForm):
    worker_id = SelectField('Worker', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()], default=datetime.today)
    present = BooleanField('Present', default=True)
    check_in_time = TimeField('Check In Time')
    check_out_time = TimeField('Check Out Time')
    overtime_hours = FloatField('Overtime Hours', validators=[NumberRange(min=0)], default=0.0)
    pieces_completed = IntegerField('Pieces Completed', validators=[NumberRange(min=0)], default=0)
    deductions = FloatField('Deductions (EGP)', validators=[NumberRange(min=0)], default=0.0)
    deduction_reason = StringField('Deduction Reason', validators=[Length(max=500)])
    bonus = FloatField('Bonus (EGP)', validators=[NumberRange(min=0)], default=0.0)
    bonus_reason = StringField('Bonus Reason', validators=[Length(max=500)])
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    submit = SubmitField('Save Attendance')
    
    def __init__(self, *args, **kwargs):
        super(AttendanceForm, self).__init__(*args, **kwargs)
        from models import Worker
        self.worker_id.choices = [(w.id, w.name) for w in Worker.query.filter_by(is_active=True).all()]


class AttendanceFilterForm(FlaskForm):
    worker_id = SelectField('Filter by Worker', choices=[], validators=[])
    date_from = DateField('From Date', validators=[])
    date_to = DateField('To Date', validators=[])
    submit = SubmitField('Filter')
    
    def __init__(self, *args, **kwargs):
        super(AttendanceFilterForm, self).__init__(*args, **kwargs)
        from models import Worker
        workers = Worker.query.filter_by(is_active=True).all()
        self.worker_id.choices = [('0', 'All Workers')] + [(str(w.id), w.name) for w in workers]

class MoneyTransferForm(FlaskForm):
    sender_name = StringField('Sender Name', validators=[DataRequired(), Length(max=200)])
    sender_phone = StringField('Sender Phone (Optional)', validators=[Length(max=20)])
    amount = FloatField('Amount (EGP)', validators=[DataRequired(), NumberRange(min=0)])
    reason = StringField('Transfer Reason', validators=[DataRequired(), Length(max=500)])
    date = DateField('Transfer Date', validators=[DataRequired()], default=datetime.today)
    notes = TextAreaField('Additional Notes', validators=[Length(max=1000)])
    submit = SubmitField('Save Transfer')
