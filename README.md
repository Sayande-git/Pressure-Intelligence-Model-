# RR Pressure Intelligence
### Evidence-Led Cricket Analytics & Player Scouting System

**A pressure-based batting and bowling intelligence platform developed for the Rajasthan Royals SupeRR Selector Season 2 challenge.**

[![Python](https://img.shields.io/badge/Python-Backend-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react)](https://react.dev/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Database-47A248?logo=mongodb)](https://www.mongodb.com/)

---

## 1. Project Overview

RR Pressure Intelligence is a cricket analytics and player scouting system designed to evaluate how batters and bowlers perform in high-leverage match situations.

Traditional cricket statistics often focus on aggregate runs, strike rates, wickets and economy rates. However, these metrics do not always capture a player's contribution when match outcomes are most sensitive to individual deliveries.

This project introduces a pressure-based evaluation framework that combines match-state leverage, contextual performance, consistency, statistical reliability and role-based analysis.

The platform transforms ball-by-ball cricket data into structured scouting intelligence to help identify players who demonstrate valuable performance under pressure.

## 2. Key Objectives

- Identify batters who deliver valuable contributions in pressure situations.
- Evaluate bowlers based on their impact in high-leverage deliveries.
- Compare pressure performance against normal-state baselines.
- Measure consistency and statistical reliability.
- Analyse players according to their cricketing roles and match phases.
- Generate evidence-based player rankings and scouting shortlists.
- Present analytical results through an interactive dashboard.

## 3. Core Features

### Batting Pressure Intelligence
- Pressure-based batting performance evaluation.
- Pressure quality and normal baseline comparison.
- Contextual run-value analysis.
- Consistency and reliability assessment.
- Player ranking and shortlist generation.
- Individual player scouting profiles.

### Bowling Pressure Intelligence
- Context-adjusted bowling impact evaluation.
- Runs prevented and wicket-value contribution.
- Pressure economy and dot-ball analysis.
- Powerplay, middle-over and death-over role classification.
- Bowling consistency and sample reliability.
- Individual bowler scouting profiles.

### Statistical Reliability
The system considers multiple dimensions rather than relying exclusively on a single ranking score:

| Metric | Purpose |
|---|---|
| Q – Pressure Quality | Measures contextual performance under pressure |
| Baseline RV | Represents expected contextual performance in normal situations |
| D – Pressure Delta | Difference between pressure quality and normal baseline |
| C – Consistency | Measures repeatability of positive pressure outcomes |
| Sample Size | Indicates the volume of pressure deliveries |
| Bootstrap Evidence | Evaluates ranking stability across resamples |

### Interactive Dashboard
- Executive overview.
- Top 10 batter and bowler rankings.
- Pressure versus normal baseline visualisations.
- Role-based comparisons.
- Individual player rating calculations.
- Statistical evidence and scouting insights.

## 4. How Pressure Is Defined

Pressure is not defined simply by the number of overs remaining, a close score or a high required run rate.

The system uses match-state leverage to identify deliveries where the outcome can significantly influence the batting side's probability of winning.

The pre-delivery match state considers variables such as:

- Current score and wickets.
- Legal balls remaining.
- Target and runs required during a chase.
- Required run rate.
- Innings context.

The model estimates possible outcomes from the same pre-delivery state and uses their win-probability difference to quantify delivery leverage.

The highest-leverage deliveries are used to identify pressure situations.

**Important:** Pressure exposure and pressure performance are different. A player may face many high-pressure deliveries without necessarily performing well in those situations.

## 5. Rating Methodology

The dashboard uses a composite rating based on three standardised performance components:

**Q – Pressure Quality**

Measures the player's contextual performance in pressure situations, adjusted for sample size.

**D – Pressure Delta**

Measures the difference between pressure quality and normal baseline performance.

`D = Q - Baseline RV`

**C – Consistency**

Measures the repeatability of positive pressure contributions using the dashboard's smoothed consistency measure.

The displayed composite rating is:

`Rating = 50 + 10 × [0.50 × Z(Q) + 0.25 × Z(D) + 0.25 × Z(C)]`

Where Z represents standardisation of the respective metrics.

The rating is interpreted alongside sample size, reliability and bootstrap evidence rather than as a standalone measure.

## 6. Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, JavaScript |
| Backend | Python, FastAPI |
| Database | MongoDB |
| Data Processing | Python, Pandas, NumPy |
| Visualisation | Recharts |
| API Communication | REST API |
| Development | VS Code, Git, GitHub |

## 7. System Architecture

The project follows a frontend–backend architecture.

```text
                 CRICKET DATA
                      |
                      v
             DATA PROCESSING
                      |
                      v
          PRESSURE IDENTIFICATION
                      |
                      v
            PERFORMANCE ANALYSIS
                      |
             +--------+--------+
             |                 |
             v                 v
       BATTING MODEL      BOWLING MODEL
             |                 |
             +--------+--------+
                      |
                      v
              RATING ENGINE
                      |
                      v
             MONGODB STORAGE
                      |
                      v
               FASTAPI BACKEND
                      |
                      v
               REACT FRONTEND
                      |
                      v
             SCOUTING DASHBOARD
```

## 8. Project Structure

```text
RR_Pressure_Intelligence/
│
├── backend/
│   ├── datasets/
│   │   └── source_data/
│   ├── outputs/
│   ├── requirements.txt
│   ├── .env.example
│   └── server.py
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── .env.example
│
├── memory/
│
├── RUN_LOCAL.md
└── README.md
```

*Note: This is the documented project structure; adjust individual filenames if your local repository differs.*

## 9. Installation and Local Setup

### Prerequisites

- Python 3.10 or compatible version.
- Node.js and Yarn.
- MongoDB connection.
- Git.

### Step 1 – Clone the Repository

```bash
git clone https://github.com/Sayande-git/Pressure-Intelligence-Model-.git
cd Pressure-Intelligence-Model-
```

### Step 2 – Configure the Backend

```powershell
cd backend

python -m venv venv

.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Create a `.env` file inside the backend directory using `.env.example`.

Configure your own MongoDB connection:

```env
MONGO_URL=your_mongodb_connection_string
DB_NAME=your_database_name
```

Start the backend:

```powershell
uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

Backend API:

`http://127.0.0.1:8000`

API documentation:

`http://127.0.0.1:8000/docs`

### Step 3 – Configure the Frontend

Open a second terminal:

```powershell
cd frontend

yarn install

yarn start
```

Frontend:

`http://localhost:3000`

### Step 4 – Verify the Application

1. Confirm that MongoDB is configured correctly.
2. Start the backend server.
3. Start the React frontend.
4. Open the dashboard in your browser.
5. Verify that the analytical outputs and player rankings load correctly.

For additional setup instructions, refer to `RUN_LOCAL.md`.

## 10. Scouting Interpretation

The rankings are designed to support scouting decisions, not replace professional cricket judgement.

A high rating should be evaluated alongside:

- Pressure sample size.
- Statistical uncertainty.
- Consistency.
- Bootstrap ranking stability.
- Role and phase suitability.
- Squad requirements.
- Player availability and auction eligibility.

A strong middle-over performance should not automatically be interpreted as death-over capability. Each phase requires separate supporting evidence.

## 11. Limitations and Future Scope

### Current Limitations
- Historical pressure performance cannot guarantee future performance.
- Small samples may produce unstable rankings.
- Role classifications require independent validation.
- Injury status, current availability and auction eligibility require external verification.
- Contextual models depend on the quality and coverage of the available dataset.

### Future Enhancements
- Advanced phase-specific scouting models.
- Player matchup analysis against bowling and batting styles.
- Venue-specific performance intelligence.
- Interactive player comparison tools.
- Predictive player suitability models.
- Expanded domestic talent discovery.

## 12. Project Information

**Project:** RR Pressure Intelligence  
**Challenge:** Rajasthan Royals – SupeRR Selector Season 2  
**Domain:** Cricket Analytics | Sports Data Science | Player Scouting

**Developer:** Sayan De  
**Academic Background:** B.Tech – Computer Science and Engineering  
**Institution:** Jain University, Bengaluru  
**Year:** Third Year

### Connect

- **GitHub:** https://github.com/Sayande-git
- **LinkedIn:** https://www.linkedin.com/in/sayan-de-468823322/

---

## Acknowledgement

Developed as an independent cricket analytics and scouting project for the Rajasthan Royals SupeRR Selector Season 2 challenge.

The objective is to demonstrate how ball-by-ball data, match-state leverage and statistical evidence can support more informed cricket scouting decisions.

**Pressure. Performance. Evidence. Intelligence.**
