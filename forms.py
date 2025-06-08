from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, BooleanField, DateField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError, EqualTo
from wtforms.widgets import CheckboxInput, ListWidget
from models import ProductType
from datetime import datetime

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class OrderForm(FlaskForm):
    client_name = StringField('Client Name', validators=[DataRequired(), Length(max=200)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    date = DateField('Date', validators=[DataRequired()], default=datetime.today)
    product_type_id = SelectField('Product Type', coerce=int, validators=[DataRequired()])
    total_pieces = IntegerField('Total Pieces', validators=[DataRequired(), NumberRange(min=1)])
    selected_colors = SelectField('Colors', choices=[], validators=[DataRequired()])
    pieces_per_color = IntegerField('Pieces per Color', validators=[DataRequired(), NumberRange(min=1)])
    is_printed = BooleanField('Printed')
    paid_amount = FloatField('Paid Amount (EGP)', validators=[NumberRange(min=0)], default=0.0)
    remaining_amount = FloatField('Remaining Amount (EGP)', validators=[NumberRange(min=0)], default=0.0)
    brand = SelectField('Brand', choices=[('URBRAND', 'URBRAND'), ('SURVACCI', 'SURVACCI')], validators=[DataRequired()])
    submit = SubmitField('Save Order')
    
    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        self.product_type_id.choices = [(pt.id, pt.name) for pt in ProductType.query.all()]
    
    def validate_pieces_per_color(self, field):
        if self.total_pieces.data and field.data:
            if (self.total_pieces.data % field.data) != 0:
                raise ValidationError('Total pieces must be divisible by pieces per color.')

class ProductTypeForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    cost_price = FloatField('Cost Price (EGP)', validators=[DataRequired(), NumberRange(min=0)])
    selling_price = FloatField('Selling Price (EGP)', validators=[DataRequired(), NumberRange(min=0)])
    brand_group = SelectField('Brand Group', choices=[('SHARED', 'URBRAND/SURVACCI (Shared Storage)'), ('AZIZ', 'AZIZ (Separate Storage)')], validators=[DataRequired()])
    available_colors = StringField('Available Colors (comma-separated)', validators=[DataRequired()], default='Black,White,Green,Brown,Beige,Navy')
    submit = SubmitField('Save Product')
    
    def validate_selling_price(self, field):
        if self.cost_price.data and field.data < self.cost_price.data:
            raise ValidationError('Selling price should be greater than or equal to cost price')

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
