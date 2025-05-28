from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, BooleanField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError
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
    number_of_colors = IntegerField('Number of Colors', validators=[DataRequired(), NumberRange(min=1)])
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
        if self.total_pieces.data and self.number_of_colors.data:
            if self.total_pieces.data != (field.data * self.number_of_colors.data):
                raise ValidationError('Total pieces must equal pieces per color × number of colors')

class ProductTypeForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=100)])
    cost_price = FloatField('Cost Price (EGP)', validators=[DataRequired(), NumberRange(min=0)])
    selling_price = FloatField('Selling Price (EGP)', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Save Product')
    
    def validate_selling_price(self, field):
        if self.cost_price.data and field.data < self.cost_price.data:
            raise ValidationError('Selling price should be greater than or equal to cost price')
