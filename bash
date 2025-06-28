# Clone the repository
git clone https://github.com/your-username/data-quality-assistant.git
cd data-quality-assistant

# Create project structure
mkdir -p backend frontend/public frontend/src/{components,services}

# Add files to their respective locations

# Initialize Python virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Initialize React app
cd ../frontend
npx create-react-app . --template typescript
npm install axios
