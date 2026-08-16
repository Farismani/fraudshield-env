import re

html_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FraudShieldAI Pay</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Outfit', sans-serif;
    min-height: 100vh;
    display: flex; justify-content: center; align-items: center;
    background: #000;
    overflow: hidden;
    color: #fff;
  }
  
  /* Animated Mesh Gradient Background */
  .bg {
    position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle at 50% 50%, #4f46e5 0%, transparent 40%),
                radial-gradient(circle at 80% 20%, #ec4899 0%, transparent 40%),
                radial-gradient(circle at 20% 80%, #06b6d4 0%, transparent 40%);
    background-size: 100% 100%;
    animation: rotate 20s linear infinite;
    z-index: 0;
    opacity: 0.6;
    filter: blur(80px);
  }
  @keyframes rotate { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

  /* Grid overlay */
  .grid-overlay {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 30px 30px;
    z-index: 1;
  }

  .phone-container {
    position: relative; z-index: 10;
    width: 400px;
    background: rgba(20, 20, 30, 0.6);
    backdrop-filter: blur(30px);
    -webkit-backdrop-filter: blur(30px);
    border-radius: 40px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 30px 60px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.2);
    padding: 32px;
    transform: perspective(1000px) rotateX(2deg) rotateY(0deg);
    transition: transform 0.5s ease, box-shadow 0.5s ease;
  }
  .phone-container:hover {
    transform: perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(-5px);
    box-shadow: 0 40px 80px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.3);
  }
  
  .header { text-align: center; margin-bottom: 30px; }
  .header h1 {
    font-size: 28px; font-weight: 700;
    background: linear-gradient(to right, #fff, #a5b4fc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
  }
  .header p { color: #94a3b8; font-size: 13px; margin-top: 5px; font-weight: 300; letter-spacing: 1px; text-transform: uppercase; }

  .input-group { margin-bottom: 20px; position: relative; }
  .input-group label {
    display: block; font-size: 12px; color: #cbd5e1; margin-bottom: 8px; font-weight: 500;
  }
  .input-group select, .input-group input {
    width: 100%; padding: 14px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    color: #fff; font-size: 16px; font-family: 'Outfit', sans-serif;
    outline: none; transition: all 0.3s ease;
    appearance: none;
  }
  .input-group select option { background: #111; color: #fff; }
  .input-group select:focus, .input-group input:focus {
    background: rgba(255, 255, 255, 0.08);
    border-color: #818cf8;
    box-shadow: 0 0 20px rgba(129, 140, 248, 0.3);
  }
  
  .pay-btn {
    width: 100%; padding: 16px; margin-top: 10px;
    background: linear-gradient(135deg, #6366f1 0%, #ec4899 100%);
    border: none; border-radius: 16px;
    color: #fff; font-size: 18px; font-weight: 600; font-family: 'Outfit', sans-serif;
    cursor: pointer;
    box-shadow: 0 10px 25px rgba(236, 72, 153, 0.4);
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    position: relative; overflow: hidden;
  }
  .pay-btn::after {
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: linear-gradient(to right, rgba(255,255,255,0) 0%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0) 100%);
    transform: rotate(30deg) translateY(-50%);
    transition: 0.5s ease; opacity: 0;
  }
  .pay-btn:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 15px 35px rgba(236, 72, 153, 0.6);
  }
  .pay-btn:hover::after { opacity: 1; left: 100%; transition: 0.8s ease; }
  .pay-btn:disabled { opacity: 0.7; transform: none; cursor: not-allowed; }

  /* Results Modal / Overlay */
  .result-container {
    margin-top: 24px; padding: 20px;
    border-radius: 20px;
    display: none;
    animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    position: relative; overflow: hidden;
  }
  @keyframes slideUp { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }

  .result-container.safe {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    box-shadow: 0 0 30px rgba(16, 185, 129, 0.2);
  }
  .result-container.fraud {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.4);
    box-shadow: 0 0 40px rgba(239, 68, 68, 0.4);
    animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
  }
  @keyframes shake {
    10%, 90% { transform: translate3d(-1px, 0, 0); }
    20%, 80% { transform: translate3d(2px, 0, 0); }
    30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
    40%, 60% { transform: translate3d(4px, 0, 0); }
  }

  .result-header { display: flex; align-items: center; margin-bottom: 16px; }
  .result-icon { font-size: 28px; margin-right: 12px; }
  .result-title { font-size: 18px; font-weight: 600; }
  .safe .result-title { color: #34d399; }
  .fraud .result-title { color: #f87171; text-shadow: 0 0 10px rgba(239, 68, 68, 0.5); }

  .stat-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
  .stat-label { color: #94a3b8; }
  .stat-val { font-weight: 500; }
  
  .explanation {
    margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1);
    font-size: 13px; color: #cbd5e1; line-height: 1.5; font-style: italic;
  }

  /* Custom Spinner */
  .spinner {
    display: inline-block; width: 20px; height: 20px;
    border: 3px solid rgba(255,255,255,0.3); border-radius: 50%;
    border-top-color: #fff; animation: spin 0.8s ease-in-out infinite;
    margin-right: 10px; vertical-align: middle;
  }
</style>
</head>
<body>
<div class="bg"></div>
<div class="grid-overlay"></div>

<div class="phone-container">
  <div class="header">
    <h1>FraudShieldAI Pay</h1>
    <p>Ultra-Secure Payment Simulation</p>
  </div>
  
  <div class="input-group">
    <label>From (Sender)</label>
    <select id="sender">
      <option value="faris">????? Faris (faris@fsaipay)</option>
      <option value="rahul">????? Rahul (rahul@fsaipay)</option>
      <option value="ahmed">?? Ahmed (ahmed@fsaipay)</option>
      <option value="priya">????? Priya (priya@fsaipay)</option>
      <option value="ananya">????? Ananya (ananya@fsaipay)</option>
      <option value="arjun">????? Arjun (arjun@fsaipay)</option>
      <option value="kiran">?? Kiran (kiran@fsaipay)</option>
      <option value="neha">????? Neha (neha@fsaipay)</option>
    </select>
  </div>
  
  <div class="input-group">
    <label>To (Receiver)</label>
    <select id="receiver">
      <option value="rahul">????? Rahul (rahul@fsaipay)</option>
      <option value="faris">????? Faris (faris@fsaipay)</option>
      <option value="ahmed">?? Ahmed (ahmed@fsaipay)</option>
      <option value="priya">????? Priya (priya@fsaipay)</option>
      <option value="ananya">????? Ananya (ananya@fsaipay)</option>
      <option value="arjun">????? Arjun (arjun@fsaipay)</option>
      <option value="kiran">?? Kiran (kiran@fsaipay)</option>
      <option value="neha">????? Neha (neha@fsaipay)</option>
    </select>
  </div>
  
  <div class="input-group">
    <label>Amount (?)</label>
    <input type="number" id="amount" value="500" min="1" max="99999">
  </div>
  
  <button class="pay-btn" id="payBtn" onclick="submitPayment()">Transmit Funds</button>
  
  <div class="result-container" id="result"></div>
</div>

<script>
async function submitPayment(){
  const btn = document.getElementById('payBtn');
  const res = document.getElementById('result');
  const sender = document.getElementById('sender').value;
  const receiver = document.getElementById('receiver').value;
  const amount = parseFloat(document.getElementById('amount').value) || 500;
  
  if(sender === receiver) {
    alert('Sender and receiver must differ'); return;
  }
  
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Authenticating...';
  res.style.display = 'none';
  res.className = 'result-container'; // reset
  
  try {
    const resp = await fetch('/pay', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({sender, receiver, amount})
    });
    const data = await resp.json();
    
    if(!resp.ok) {
      res.classList.add('fraud');
      res.style.display = 'block';
      res.innerHTML = 
        <div class="result-header">
          <div class="result-icon">??</div>
          <div class="result-title">System Error</div>
        </div>
        <div class="explanation"></div>;
      return;
    }
    
    if(data.flagged) {
      res.classList.add('fraud');
      res.innerHTML = 
        <div class="result-header">
          <div class="result-icon">??</div>
          <div class="result-title">TRANSACTION BLOCKED</div>
        </div>
        <div class="stat-row"><span class="stat-label">AI Risk Score</span><span class="stat-val" style="color:#f87171"></span></div>
        <div class="stat-row"><span class="stat-label">TxID</span><span class="stat-val" style="font-family:monospace"></span></div>
        <div class="explanation"><strong>Fraud Indicators:</strong><br></div>
      ;
    } else {
      res.classList.add('safe');
      res.innerHTML = 
        <div class="result-header">
          <div class="result-icon">?</div>
          <div class="result-title">FUNDS SECURED & SENT</div>
        </div>
        <div class="stat-row"><span class="stat-label">Amount</span><span class="stat-val">?</span></div>
        <div class="stat-row"><span class="stat-label">AI Risk Score</span><span class="stat-val" style="color:#34d399"></span></div>
        <div class="stat-row"><span class="stat-label">TxID</span><span class="stat-val" style="font-family:monospace"></span></div>
        <div class="explanation">Transaction cleared by FraudShieldAI.</div>
      ;
    }
    res.style.display = 'block';
  } catch(e) {
    res.classList.add('fraud');
    res.style.display = 'block';
    res.innerHTML = '<div class="result-title">Network Error</div><div class="explanation">' + e.message + '</div>';
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Transmit Funds';
  }
}
</script>
</body>
</html>'''

with open('09_api.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace everything from _UPI_HTML = r""" to the end
new_text = re.sub(r'_UPI_HTML = r\"\"\"<!DOCTYPE html>.*', f'_UPI_HTML = r\"\"\"{html_content}\"\"\"', text, flags=re.DOTALL)

with open('09_api.py', 'w', encoding='utf-8') as f:
    f.write(new_text)

print("Patched 09_api.py successfully")
