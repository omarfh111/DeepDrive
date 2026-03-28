# DeepDrive 🚗💨

DeepDrive is an AI-powered automotive platform designed to revolutionize the car-buying and ownership experience. It integrates advanced machine learning models, computer vision, and specialized AI agents to provide personalized advice, vehicle analysis, and seamless transaction management.

## 🌟 Key Features

- **🤖 AI Advisor**: A personalized car-buying assistant that helps users find the perfect vehicle based on their needs and budget.
- **👁️ Computer Vision Analysis**: Integrated with Roboflow and YOLO (Ultralytics) to analyze car dashboard icons and vehicle condition.
- **📅 Test Drive Management**: Streamlined scheduling and tracking of vehicle test drives.
- **💳 Integrated Payments**: Secure payment processing via Stripe for deposits, services, and purchases.
- **📱 Smart Notifications**: Real-time updates via SMS (Twilio) and Email (SMTP) for all user actions.
- **📊 Vehicle Catalog**: Comprehensive management of vehicle listings, features, and pricing.
- **📑 Reviews & Community**: User-generated reviews and social posts to share automotive experiences.
- **📂 AI Agent Orchestration**: Uses CrewAI and LangChain to power complex decision-making and advisory tasks.

## 🛠️ Technology Stack

- **Backend**: Python / Django
- **Database**: SQLite (Development) / PostgreSQL (with pgvector for AI features)
- **AI/ML**: OpenAI GPT-4, CrewAI, LangChain, Groq
- **Computer Vision**: Roboflow, Ultralytics (YOLOv8), Torch, Transformers
- **Infrastructure**: Stripe (Payments), Twilio (SMS), xhtml2pdf (PDF generation)
- **Frontend**: Django Templates, Widget Tweaks, HTML Minifier

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Virtual Environment (pipenv or venv)
- API Keys for OpenAI, Roboflow, Stripe, and Twilio

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/omarfh111/DeepDrive.git
   cd DeepDrive
   ```

2. **Set up the virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file in the root directory and add your API keys:
   ```env
   OPENAI_API_KEY=your_openai_key
   STRIPE_SECRET_KEY=your_stripe_key
   STRIPE_PUBLIC_KEY=your_stripe_public_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   ROBOFLOW_API_KEY=your_roboflow_key
   ```

5. **Database Setup**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run the server**:
   ```bash
   python manage.py runserver
   ```

## 🏗️ Project Structure

- `advisor/`: AI car purchase advisor logic.
- `ai_agent/`: CrewAI and LangChain agent implementations.
- `vehicles/`: Vehicle model and listing management.
- `TestDrive/`: Test drive logistics and tracking.
- `user_app/`: Custom user authentication and profiles.
- `deals/`: Transaction and deal management.
- `static/` & `templates/`: UI components and assets.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
*Developed for the future of automotive technology.*
