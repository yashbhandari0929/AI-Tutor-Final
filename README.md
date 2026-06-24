# 🎓 AI Tutor – Personalized Learning & Interview Preparation Platform

<p align="center">
  <b>AI-Powered Learning Assistant for Students</b><br>
  Learn Smarter • Track Progress • Master Topics • Ace Interviews
</p>

---

## 📌 Overview

AI Tutor is a full-stack AI-powered educational platform that helps students learn efficiently through personalized study plans, intelligent quizzes, document-based learning, analytics, mastery tracking, and AI-driven interview preparation.

The platform combines Retrieval-Augmented Generation (RAG), Large Language Models, adaptive learning techniques, and real-time analytics to create a personalized learning experience.

---

## ✨ Key Features

### 📚 Knowledge Base

* Upload PDFs and study materials
* Automatic document indexing and chunking
* Retrieval-Augmented Generation (RAG)
* Ask questions directly from uploaded documents
* AI-powered contextual responses

### 🤖 AI Chat Tutor

* Interactive conversational learning
* Context-aware answers
* Personalized guidance
* Multi-topic support

### 📝 Smart Quiz Generation

* AI-generated quizzes from any topic
* Multiple difficulty levels
* Instant evaluation
* Correct answers with explanations
* Performance tracking

### 🎯 Topic Mastery Tracking

* Track learning progress across topics
* Mastery score calculation
* Strong and weak topic identification
* Personalized improvement suggestions

### 📈 Learning Analytics Dashboard

* Quiz performance analytics
* Learning accuracy trends
* Progress visualization
* Study streak tracking
* Personalized insights

### 📅 Adaptive Study Plans

* Automatically generated study schedules
* Daily learning tasks
* Weekly milestones
* Focus areas based on weak topics
* Recommendation engine

### 💼 Resume Interview Preparation

* Resume upload and analysis
* AI-generated interview questions
* Answer evaluation and scoring
* Readiness assessment
* Interview performance analytics

### 👤 User Management

* JWT Authentication
* Secure login & registration
* User profiles
* Learning history

---

## 🏗️ System Architecture

```text
Frontend (Next.js + TypeScript)
          │
          ▼
Backend API (FastAPI)
          │
 ┌────────┼────────┐
 ▼        ▼        ▼
SQLite   Gemini   RAG Engine
Database   AI     (Documents)
```

---

## 🛠️ Tech Stack

### Frontend

* Next.js 15
* React
* TypeScript
* Tailwind CSS
* Axios
* Lucide Icons

### Backend

* FastAPI
* Python
* SQLAlchemy
* Pydantic
* JWT Authentication
* Uvicorn

### AI & Machine Learning

* Google Gemini API
* Sentence Transformers
* Vector Embeddings
* Retrieval-Augmented Generation (RAG)

### Database

* SQLite
* SQLAlchemy ORM

---

## 📂 Project Structure

```text
AI-Tutor/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   └── public/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── database/
│   ├── schemas/
│   ├── auth/
│   └── uploads/
│
└── README.md
```

---

## 🚀 Installation

### Clone Repository

```bash
git clone https://github.com/yashbhandari0929/AI-Tutor-Final.git
cd AI-Tutor-Final
```

---

### Backend Setup

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload
```

Backend runs on:

```text
http://localhost:8000
```

---

### Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

Frontend runs on:

```text
http://localhost:3000
```

---

## 🔑 Environment Variables

Create a `.env` file in the backend directory:

```env
GEMINI_API_KEY=your_api_key_here
JWT_SECRET_KEY=your_secret_key_here
```

---

## 📊 Core Modules

| Module          | Description                        |
| --------------- | ---------------------------------- |
| Authentication  | Secure user login and registration |
| Knowledge Base  | PDF & document learning            |
| AI Chat         | Conversational tutoring            |
| Quiz Engine     | AI-generated quizzes               |
| Analytics       | Learning performance tracking      |
| Study Planner   | Adaptive study scheduling          |
| Mastery Tracker | Topic-wise progress measurement    |
| Interview Prep  | Resume-based interview coaching    |

---

## 🎯 Future Enhancements

* Voice-based tutoring
* Multi-language support
* Flashcard generation
* Learning leaderboard
* Collaborative study groups
* Mobile application
* Advanced vector database integration

---

## 👨‍💻 Developer

**Yash Bhandari**

---

## ⭐ Why AI Tutor?

AI Tutor goes beyond traditional learning platforms by combining:

✅ Personalized Learning

✅ AI-Powered Guidance

✅ Real-Time Progress Tracking

✅ Intelligent Study Planning

✅ Resume-Based Interview Preparation

✅ Adaptive Knowledge Assessment

The result is a complete AI learning ecosystem designed to help students learn smarter, faster, and more effectively.

---

<p align="center">
  Built with FastAPI, Next.js, TypeScript, SQLAlchemy, and Gemini AI to deliver a scalable AI-powered learning platform featuring personalized tutoring, adaptive study plans, intelligent document understanding, mastery tracking, and interview preparation.
</p>
