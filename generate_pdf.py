from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'FraudShieldAI - Links, Commands & Profiles', 0, 1, 'C')
        self.ln(5)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 6, body)
        self.ln()

pdf = PDF()
pdf.add_page()

pdf.chapter_title('1. Running the API Server')
pdf.chapter_body(
    "To start the FastAPI server, use the virtual environment where all dependencies are installed (.venv_new). Run the following command from the project root:\n\n"
    "Command:\n"
    ".\\.venv_new\\Scripts\\python -m uvicorn 09_api:app --reload\n\n"
    "This will start the server at http://127.0.0.1:8000"
)

pdf.chapter_title('2. Web Interfaces (Open in Browser)')
pdf.chapter_body(
    "Once the server is running, you can access the following web interfaces:\n\n"
    "Spoof UPI Payment App:\n"
    "http://127.0.0.1:8000/\n\n"
    "Bank Analyst Dashboard (with GNN Network Visualization):\n"
    "http://127.0.0.1:8000/console\n\n"
    "API Documentation (Swagger UI):\n"
    "http://127.0.0.1:8000/docs"
)

pdf.chapter_title('3. Simulation Note & Profile Specifications')
pdf.chapter_body(
    "NOTE: This application is an interactive simulation UI. Payment transfers map user profiles to actual precomputed fraud scores sampled from real transactions in the IEEE-CIS Fraud Detection dataset (590,540 real transactions).\n\n"
    "User Profiles:\n"
    "- Faris (faris): Regular Personal Account\n"
    "- Rahul (rahul): Frequent Peer Transfers\n"
    "- Ahmed (ahmed): Retail Merchant Account\n"
    "- Priya (priya): Corporate High-Volume\n"
    "- Ananya (ananya): Freelance / International\n"
    "- Arjun (arjun): New Account (Low Behavioral History)\n"
    "- Kiran (kiran): Whitelisted E-Commerce Entity\n"
    "- Neha (neha): High-Velocity Account"
)

pdf.chapter_title('4. API Endpoints (cURL / Test Commands)')
pdf.chapter_body(
    "You can test the API endpoints directly using PowerShell:\n\n"
    "Health Check:\n"
    "Invoke-WebRequest -Uri \"http://127.0.0.1:8000/health\" | Select-Object Content\n\n"
    "Get Fraud Score by Transaction ID:\n"
    "Invoke-WebRequest -Uri \"http://127.0.0.1:8000/predict_by_id?transaction_id=3012474\" | Select-Object Content\n\n"
    "Simulate a Payment (Sender, Receiver, Amount):\n"
    "Invoke-RestMethod -Method Post -Uri \"http://127.0.0.1:8000/pay\" -Headers @{\"Content-Type\"=\"application/json\"} -Body '{\"sender\":\"faris\",\"receiver\":\"rahul\",\"amount\":100}'"
)

pdf.chapter_title('5. Running the Latency Benchmark')
pdf.chapter_body(
    "To verify the sub-2-second response time requirement, run the latency benchmark script. Ensure the server is running before executing this.\n\n"
    "Command:\n"
    ".\\.venv_new\\Scripts\\python benchmark_latency.py"
)

pdf.output('FraudShieldAI_Links_And_Commands.pdf')
print("Successfully generated FraudShieldAI_Links_And_Commands.pdf")
