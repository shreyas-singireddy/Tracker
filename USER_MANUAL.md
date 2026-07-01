# FitOS User Manual

## Getting Started

FitOS is an offline AI-powered fitness operating system that runs entirely on your local machine.

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/fitos.git
cd fitos

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize the database
python main.py --init-db

# Launch the app
python run_app.py
```

### System Requirements

- Python 3.11 or later
- SQLite3 (included with Python)
- 4GB RAM minimum
- 500MB disk space

## Features

### Dashboard
Overview of your fitness metrics, recent activity, and quick stats.

### Workouts
- Create workout plans with Push/Pull/Legs splits
- Start, pause, resume, and complete sessions
- Log exercise sets with weight, reps, and RPE

### Nutrition
- Maintain a food database with macro profiles
- Track meals (breakfast, lunch, dinner, snacks)
- View daily macro totals and nutrition summaries

### Habits
- Create habits and track daily/weekly completion
- View consistency streaks
- Log habit entries with notes

### Recovery & Sleep
- Log sleep hours and quality
- Track recovery scores and readiness states
- View recovery trends

### AI Coach
- Rule-based coaching (no ML, no external APIs)
- Query classification and response generation
- Daily insights and recommendations
- Weekly summaries and progress feedback

### Analytics
- Fitness scores with sub-component breakdown
- Weekly and monthly reports
- Progress trends and insights
- Analytics snapshots

### Reports
- Weekly and monthly report generation
- Adherence tracking
- Performance summaries

### Settings
- User registration and profile management
- Body measurements tracking
- Application configuration

## Database

FitOS uses SQLite for all data storage. The database file is created automatically when you first run the application.

Key tables:
- users, user_profiles
- workout_plans, workout_sessions, exercise_logs, exercise_sets
- foods, meals, meal_entries, nutrition_logs
- habits, habit_entries
- sleep_logs, recovery_logs, recovery_profiles
- body_measurements
- goals
- ai_sessions, ai_queries, ai_responses, ai_recommendations
- fitness_scores, weekly_reports, monthly_reports, analytics_snapshots, progress_trends, insight_metrics
