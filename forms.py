from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional

class ProfileForm(FlaskForm):
    name = StringField('Full name', validators=[DataRequired()])
    age = IntegerField('Age', validators=[DataRequired(), NumberRange(min=1, max=120)])
    gender = SelectField('Gender', choices=[('male','Male'), ('female','Female'), ('other','Other')], validators=[DataRequired()])
    height_cm = FloatField('Height (cm)', validators=[DataRequired(), NumberRange(min=30, max=300)])
    weight_kg = FloatField('Weight (kg)', validators=[DataRequired(), NumberRange(min=2, max=500)])
    activity_level = SelectField('Activity level', choices=[
        ('sedentary','Sedentary (little/no exercise)'),
        ('light','Light (1-3 days/wk)'),
        ('moderate','Moderate (3-5 days/wk)'),
        ('active','Active (6-7 days/wk)')
    ], validators=[DataRequired()])
    diseases = StringField('Chronic conditions (comma-separated e.g. diabetes,hypertension)', validators=[Optional()])
    medications = TextAreaField('Current medications (optional)', validators=[Optional()])
    submit = SubmitField('Save Profile & Generate Plan')
