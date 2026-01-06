# Money Transfer forms
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange
from datetime import datetime

class MoneyTransferForm(FlaskForm):
    sender_name = StringField('Sender Name', validators=[DataRequired(), Length(max=200)])
    sender_phone = StringField('Sender Phone (Optional)', validators=[Length(max=20)])
    amount = FloatField('Amount (EGP)', validators=[DataRequired(), NumberRange(min=0)])
    reason = StringField('Transfer Reason', validators=[DataRequired(), Length(max=500)])
    date = DateField('Transfer Date', validators=[DataRequired()], default=datetime.today)
    notes = TextAreaField('Additional Notes', validators=[Length(max=1000)])
    submit = SubmitField('Save Transfer')