from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from forms import ProfileForm
from datetime import datetime
import os
import csv

import pandas as pd
from sklearn.neighbors import NearestNeighbors

app = Flask(__name__)

app.config['SECRET_KEY'] = 'change-this-to-a-secure-random-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wellness.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------------
# Dataset Paths
# -----------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DIET_CSV_PATH = os.path.join(BASE_DIR, "Personalized_Diet_Recommendations.csv")
YOGA_CSV_PATH = os.path.join(BASE_DIR, "final_asan1_1.csv")

DISEASE_COL = "Chronic_Disease"
REC_CAL_COL = "Recommended_Calories"
REC_PROT_COL = "Recommended_Protein"
REC_CARBS_COL = "Recommended_Carbs"
REC_FATS_COL = "Recommended_Fats"

YOGA_NAME_COL = "AName"
YOGA_BENEFITS_COL = "Benefits"

DIET_DATA = []
YOGA_DATA = []

# -----------------------------
# Load Diet Dataset
# -----------------------------
try:
    with open(DIET_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        DIET_DATA = list(reader)
        print("Diet dataset loaded:", len(DIET_DATA))
except:
    print("Diet dataset not found")

# -----------------------------
# Convert to DataFrame for AI
# -----------------------------
diet_df = pd.DataFrame(DIET_DATA)

if not diet_df.empty:

    diet_df["BMI"] = pd.to_numeric(diet_df["BMI"], errors="coerce")
    diet_df[REC_CAL_COL] = pd.to_numeric(diet_df[REC_CAL_COL], errors="coerce")
    diet_df[REC_PROT_COL] = pd.to_numeric(diet_df[REC_PROT_COL], errors="coerce")
    diet_df[REC_CARBS_COL] = pd.to_numeric(diet_df[REC_CARBS_COL], errors="coerce")
    diet_df[REC_FATS_COL] = pd.to_numeric(diet_df[REC_FATS_COL], errors="coerce")

    diet_df = diet_df.dropna()

    X = diet_df[["BMI", REC_CAL_COL, REC_PROT_COL, REC_CARBS_COL, REC_FATS_COL]]

    knn_model = NearestNeighbors(n_neighbors=5)
    knn_model.fit(X)

# -----------------------------
# Load Yoga Dataset
# -----------------------------
try:
    with open(YOGA_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row["_benefits_lower"] = (row.get(YOGA_BENEFITS_COL) or "").lower()
            YOGA_DATA.append(row)

        print("Yoga dataset loaded:", len(YOGA_DATA))

except:
    print("Yoga dataset not found")

# -----------------------------
# Database Model
# -----------------------------
class UserProfile(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))

    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)

    activity_level = db.Column(db.String(20))

    diseases = db.Column(db.String(256))
    medications = db.Column(db.String(256))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def bmi(self):

        h = self.height_cm / 100

        if h <= 0:
            return None

        return round(self.weight_kg / (h*h),1)


# -----------------------------
# Wellness Plan Generator
# -----------------------------
def generate_wellness_plan(profile):

    bmi = profile.bmi()

    # -------- BMR --------
    if (profile.gender or "").lower() == "male":
        bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5
    else:
        bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age - 161

    activity = {
        "sedentary":1.2,
        "light":1.375,
        "moderate":1.55,
        "active":1.725
    }

    calories = int(bmr * activity.get(profile.activity_level,1.375))

    # -----------------------------
    # AI DIET RECOMMENDATION
    # -----------------------------
    if bmi and not diet_df.empty:

        user_vector = [[bmi, calories, 0, 0, 0]]

        distances, indices = knn_model.kneighbors(user_vector)

        nearest_rows = diet_df.iloc[indices[0]]

        calories = int(nearest_rows[REC_CAL_COL].mean())
        protein = int(nearest_rows[REC_PROT_COL].mean())
        carbs = int(nearest_rows[REC_CARBS_COL].mean())
        fats = int(nearest_rows[REC_FATS_COL].mean())

    else:

        protein = int(profile.weight_kg * 1.2)
        carbs = int(calories * 0.45 / 4)
        fats = int(calories * 0.25 / 9)

    diet_recs = [
        f"AI Recommended Calories: {calories} kcal",
        f"AI Recommended Protein: {protein} g",
        f"AI Recommended Carbohydrates: {carbs} g",
        f"AI Recommended Fats: {fats} g"
    ]

    # -----------------------------
    # SAMPLE MEAL PLAN
    # -----------------------------
    sample_meal_plan = {

        "Breakfast": f"Oats + fruit (~{int(0.25*calories)} kcal)",
        "Lunch": f"Lean protein + vegetables (~{int(0.35*calories)} kcal)",
        "Dinner": f"Vegetables + lean protein (~{int(0.25*calories)} kcal)",
        "Notes": f"Daily target {calories} kcal"

    }

    # -----------------------------
    # EXERCISE
    # -----------------------------
    exercise_recs = [
        "150 minutes aerobic activity weekly"
    ]

    # -----------------------------
    # YOGA RECOMMENDATIONS
    # -----------------------------
    yoga_recs = []

    diseases = [d.strip().lower() for d in (profile.diseases or "").split(",") if d.strip()]

    for dis in diseases:

        poses = []

        for row in YOGA_DATA:

            if dis in row["_benefits_lower"]:

                name = row.get(YOGA_NAME_COL)

                if name and name not in poses:
                    poses.append(name)

            if len(poses) >= 5:
                break

        if poses:
            yoga_recs.append("Yoga poses: " + ", ".join(poses))

    exercise_recs.extend(yoga_recs)

    # -----------------------------
    # WEEKLY PLAN
    # -----------------------------
    schedule = []

    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    for d in days:

        if d in ["Monday","Wednesday","Friday"]:

            acts = [
                {"type":"Cardio","activity":"Brisk walking","duration":30,"time":"07:00"},
                {"type":"Strength","activity":"Resistance training","duration":20,"time":"18:00"}
            ]

        else:

            acts = [
                {"type":"Yoga","activity":"Yoga session","duration":30,"time":"07:00"}
            ]

        schedule.append({"day":d,"activities":acts})
    

    

    return {

    "bmi": bmi,
    "estimated_calories": calories,
    "diet_recommendations": diet_recs,
    "sample_meal_plan": sample_meal_plan,
    "exercise_recommendations": exercise_recs,
    "exercise_schedule": schedule
    }

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():

    profiles = UserProfile.query.order_by(UserProfile.created_at.desc()).limit(6).all()

    return render_template("index.html", profiles=profiles)


@app.route("/profile/new", methods=["GET","POST"])
def new_profile():

    form = ProfileForm()

    if form.validate_on_submit():

        p = UserProfile(

            name=form.name.data,
            age=form.age.data,
            gender=form.gender.data,
            height_cm=form.height_cm.data,
            weight_kg=form.weight_kg.data,
            activity_level=form.activity_level.data,
            diseases=form.diseases.data,
            medications=form.medications.data

        )

        db.session.add(p)
        db.session.commit()

        flash("Profile created!")

        return redirect(url_for("view_plan", profile_id=p.id))

    return render_template("profile_form.html", form=form)


@app.route("/profile/<int:profile_id>/plan")
def view_plan(profile_id):



    p = UserProfile.query.get_or_404(profile_id)

    plan = generate_wellness_plan(p)

    now = datetime.now()

    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    today = day_names[now.weekday()]

    next_activity_msg = None

    for day in plan["exercise_schedule"]:

        if day["day"] == today and day.get("activities"):

            act = day["activities"][0]

            next_activity_msg = (
                f"Today's activity:\n"
                f"Type: {act['type']}\n"
                f"Exercise: {act['activity']}\n"
                f"Time: {act['time']}\n"
                f"Duration: {act['duration']} minutes"
            )

            break

    return render_template(
        "plan.html",
        profile=p,
        plan=plan,
        next_activity_msg=next_activity_msg
    )


@app.cli.command("init-db")
def init_db():

    db.create_all()

    print("Database created")
# -----------------------------
# MODEL EVALUATION (RUN ONCE)
# -----------------------------
from sklearn.metrics import mean_absolute_error
import pandas as pd

if not diet_df.empty:

    y_true = diet_df["Recommended_Calories"]
    y_pred = []

    for i in range(len(diet_df)):
        sample = diet_df.iloc[i]

        # ✅ FIX: use DataFrame instead of list
        user_vec = pd.DataFrame(
            [[
                sample["BMI"],
                sample["Recommended_Calories"],
                sample["Recommended_Protein"],
                sample["Recommended_Carbs"],
                sample["Recommended_Fats"]
            ]],
            columns=[
                "BMI",
                "Recommended_Calories",
                "Recommended_Protein",
                "Recommended_Carbs",
                "Recommended_Fats"
            ]
        )

        _, idx = knn_model.kneighbors(user_vec)

        pred = diet_df.iloc[idx[0]]["Recommended_Calories"].mean()

        y_pred.append(pred)

    mae = mean_absolute_error(y_true, y_pred)

    accuracy = 100 - (mae / y_true.mean()) * 100

    print("Model Accuracy:", round(accuracy, 2), "%")

if __name__ == "__main__":

    print("Starting Wellness Planner server...")
    app.run(debug=True)