import streamlit as st
import boto3
import json
import uuid
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
import io

# Configure page
st.set_page_config(
    page_title="GITEX Demo Bank - Loan Processing",
    page_icon="🏦",
    layout="wide"
)

# Professional styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #fafbfc;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d3436 100%);
        padding: 3rem 2rem;
        margin: -1rem -1rem 3rem -1rem;
        border-radius: 0 0 16px 16px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 3rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    .main-header .tagline {
        color: #b0b0b0;
        margin: 1rem 0 0 0;
        font-size: 1.2rem;
        font-weight: 400;
    }
    
    .main-container {
        background: white;
        border-radius: 16px;
        padding: 3rem;
        margin: 2rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
    }
    
    .upload-area {
        border: 3px dashed #d1d5db;
        border-radius: 16px;
        padding: 3rem 2rem;
        text-align: center;
        background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
        transition: all 0.3s ease;
        margin: 2rem 0;
    }
    
    .upload-area:hover {
        border-color: #1a1a1a;
        background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    
    .upload-text {
        font-size: 1.1rem;
        color: #6b7280;
        margin: 1rem 0;
    }
    
    .upload-icon {
        font-size: 3rem;
        color: #9ca3af;
        margin-bottom: 1rem;
    }
    
    .or-divider {
        display: flex;
        align-items: center;
        margin: 3rem 0;
        color: #9ca3af;
        font-weight: 500;
    }
    
    .or-divider::before,
    .or-divider::after {
        content: '';
        flex: 1;
        height: 2px;
        background: linear-gradient(to right, transparent, #e5e7eb, transparent);
    }
    
    .or-divider span {
        margin: 0 2rem;
        background: white;
        padding: 0 1rem;
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .chat-area {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 2rem;
        border: 2px solid #e9ecef;
    }
    
    .stTextArea > div > div > textarea {
        border: 2px solid #e9ecef;
        border-radius: 12px;
        padding: 1.5rem;
        font-size: 1rem;
        line-height: 1.6;
        background: white;
        transition: all 0.2s ease;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #1a1a1a;
        box-shadow: 0 0 0 3px rgba(26,26,26,0.1);
    }
    
    .action-button {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d3436 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 1rem 2.5rem;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(26,26,26,0.2);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d3436 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 1rem 2.5rem;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        width: 100%;
        box-shadow: 0 4px 15px rgba(26,26,26,0.2);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2d3436 0%, #636e72 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(26,26,26,0.3);
    }
    
    .stButton > button:disabled {
        background: #e5e7eb;
        color: #9ca3af;
        transform: none;
        box-shadow: none;
    }
    
    .response-container {
        background: white;
        border-radius: 16px;
        padding: 3rem;
        margin: 2rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
    }
    
    .agent-response {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-left: 5px solid #1a1a1a;
        padding: 2rem;
        border-radius: 12px;
        margin: 2rem 0;
        font-size: 1rem;
        line-height: 1.7;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .status-approved {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        color: #155724;
        padding: 1rem 2rem;
        border-radius: 25px;
        display: inline-block;
        font-weight: 700;
        margin: 1rem 0;
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border: 2px solid #28a745;
        box-shadow: 0 4px 15px rgba(40,167,69,0.2);
    }
    
    .status-rejected {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        color: #721c24;
        padding: 1rem 2rem;
        border-radius: 25px;
        display: inline-block;
        font-weight: 700;
        margin: 1rem 0;
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border: 2px solid #dc3545;
        box-shadow: 0 4px 15px rgba(220,53,69,0.2);
    }
    
    .download-section {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border: 2px solid #2196f3;
        border-radius: 16px;
        padding: 3rem;
        margin: 3rem 0;
        box-shadow: 0 4px 20px rgba(33,150,243,0.15);
    }
    
    .download-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0d47a1;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    .download-subtitle {
        font-size: 1rem;
        color: #1565c0;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    
    .success-message {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 2px solid #28a745;
        color: #155724;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-weight: 600;
        font-size: 1rem;
        box-shadow: 0 4px 15px rgba(40,167,69,0.15);
    }
    
    .processing-indicator {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border: 2px solid #ffc107;
        color: #856404;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 2rem 0;
        text-align: center;
        font-weight: 600;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    
    .footer {
        text-align: center;
        padding: 3rem 0;
        color: #6b7280;
        font-weight: 500;
        border-top: 1px solid #e5e7eb;
        margin-top: 4rem;
    }
    
    .session-info {
        background: #f3f4f6;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        font-size: 0.9rem;
        color: #6b7280;
        margin-top: 2rem;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    footer {visibility: hidden;}
    .stApp > header {display: none;}
    
    /* File uploader styling */
    .stFileUploader > div {
        border: none !important;
        background: none !important;
    }
    
    .stFileUploader label {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'last_response' not in st.session_state:
    st.session_state.last_response = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Header
st.markdown('''
<div class="main-header">
    <h1>GITEX Demo Bank</h1>
    <p class="tagline">AI-Powered Loan Processing Platform</p>
</div>
''', unsafe_allow_html=True)

# Get configuration from secrets (hidden from UI)
try:
    agent_id = st.secrets.get("AGENT_ID", "")
    aws_access_key = st.secrets.get("AWS_ACCESS_KEY_ID", "")
    aws_secret_key = st.secrets.get("AWS_SECRET_ACCESS_KEY", "")
    aws_region = st.secrets.get("AWS_REGION", "eu-west-2")  # Default to London region
    
    if not agent_id:
        st.error("🔧 **Configuration Required**: Please add your AGENT_ID to Streamlit secrets")
        st.stop()
        
except Exception:
    st.error("🔧 **Configuration Required**: Please add your AWS credentials and AGENT_ID to Streamlit secrets")
    st.stop()

# AWS client initialization
@st.cache_resource
def get_bedrock_client():
    try:
        return boto3.client(
            'bedrock-agent-runtime',
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
    except Exception as e:
        st.error(f"❌ **AWS Connection Failed**: {str(e)}")
        return None

# Main interface
st.markdown('<div class="main-container">', unsafe_allow_html=True)

st.markdown("### How would you like to apply for a loan?")

# File upload section
st.markdown('''
<div class="upload-area">
    <div class="upload-icon">📄</div>
    <div style="font-size: 1.3rem; font-weight: 600; color: #374151; margin-bottom: 0.5rem;">
        Upload Completed Application
    </div>
    <div class="upload-text">
        Already have a loan application? Upload your PDF document here
    </div>
</div>
''', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Choose file",
    type=['pdf'],
    label_visibility="collapsed"
)

if uploaded_file:
    st.markdown(f'<div class="success-message">✅ Application received: {uploaded_file.name}</div>', unsafe_allow_html=True)

# OR divider
st.markdown('<div class="or-divider"><span>or</span></div>', unsafe_allow_html=True)

# Chat section
st.markdown('''
<div style="font-size: 1.3rem; font-weight: 600; color: #374151; margin-bottom: 1rem; text-align: center;">
    Describe Your Loan Request
</div>
<div style="font-size: 1rem; color: #6b7280; text-align: center; margin-bottom: 2rem;">
    Tell our AI loan officer about your business and financing needs
</div>
''', unsafe_allow_html=True)

user_message = st.text_area(
    "",
    placeholder="Example: I need a $25,000 loan for restaurant equipment. My business has been operating for 3 years with monthly revenue of $8,000. I have good credit history and can provide collateral...",
    height=120,
    label_visibility="collapsed"
)

# Action buttons
st.markdown("<br>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if uploaded_file and not st.session_state.processing:
        if st.button("🚀 Process Application", type="primary", use_container_width=True):
            st.session_state.processing = True
            st.rerun()
    elif user_message.strip() and not st.session_state.processing:
        if st.button("💬 Submit Loan Request", type="primary", use_container_width=True):
            st.session_state.processing = True
            st.rerun()
    elif st.session_state.processing:
        st.markdown('<div class="processing-indicator">🤖 Processing your request...</div>', unsafe_allow_html=True)
    else:
        st.button("Please upload a file or describe your request", disabled=True, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# Agent interaction function
def call_bedrock_agent(message, file_name=None):
    bedrock = get_bedrock_client()
    
    if not bedrock:
        return "❌ Unable to connect to loan processing system. Please try again."
    
    try:
        # Prepare prompt
        if file_name:
            prompt = f"""Please process this loan application file: {file_name}. 
            
Provide a comprehensive analysis and decision including:
- Applicant name (if available)
- Loan amount requested
- Your recommendation (APPROVED or REJECTED)
- Interest rate (if approved)
- Key decision factors
- Any conditions or requirements

Be professional and thorough in your analysis."""
        else:
            prompt = f"""Loan Request Analysis:

{message}

Please analyze this loan request and provide:
- Your recommendation (APPROVED or REJECTED)
- Suggested loan amount and terms
- Interest rate recommendation
- Key factors in your decision
- Any additional requirements

Be professional and comprehensive in your response."""
        
        # Call Bedrock agent using AWS documentation format
        response = bedrock.invoke_agent(
            agentId=current_agent_id,
            agentAliasId=current_agent_alias_id,
            enableTrace=False,
            sessionId=st.session_state.session_id,
            inputText=prompt
        )
        
        # Extract response text using AWS documentation method
        completion = ""
        for event in response.get("completion", []):
            if 'chunk' in event:
                chunk = event["chunk"]
                completion += chunk["bytes"].decode()
        
        return completion if completion else "No response received from the loan processing system."
        
    except Exception as e:
        return f"❌ Processing error: {str(e)}"

# Parse loan data from agent response
def parse_loan_data(response_text):
    try:
        # Extract applicant name
        name_patterns = [
            r'applicant[:\s]+([A-Za-z\s]+)',
            r'name[:\s]+([A-Za-z\s]+)',
            r'borrower[:\s]+([A-Za-z\s]+)',
            r'client[:\s]+([A-Za-z\s]+)'
        ]
        
        applicant_name = "Loan Applicant"
        for pattern in name_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                name_candidate = match.group(1).strip()
                # Filter out common false positives
                if not any(word in name_candidate.lower() for word in ['report', 'analysis', 'decision', 'loan', 'bank']):
                    applicant_name = name_candidate
                    break
        
        # Extract loan amount
        amount_patterns = [
            r'\$[\s]*([\d,]+)',
            r'([\d,]+)[\s]*dollars?',
            r'amount[:\s]+\$?([\d,]+)'
        ]
        
        loan_amount = 0
        for pattern in amount_patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                try:
                    loan_amount = int(match.group(1).replace(',', ''))
                    break
                except:
                    continue
        
        # Extract decision
        decision = "PENDING"
        if re.search(r'\b(approved?|approve)\b', response_text, re.IGNORECASE):
            decision = "APPROVED"
        elif re.search(r'\b(rejected?|declined?|deny|denied)\b', response_text, re.IGNORECASE):
            decision = "REJECTED"
        
        # Extract interest rate
        rate_match = re.search(r'(\d+\.?\d*)\s*%', response_text)
        interest_rate = float(rate_match.group(1)) if rate_match else 0
        
        return {
            'applicant_name': applicant_name,
            'loan_amount': loan_amount,
            'decision': decision,
            'interest_rate': interest_rate,
            'full_response': response_text,
            'timestamp': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }
        
    except Exception:
        return {
            'applicant_name': "Loan Applicant",
            'loan_amount': 0,
            'decision': "PENDING",
            'interest_rate': 0,
            'full_response': response_text,
            'timestamp': datetime.now().strftime('%B %d, %Y at %I:%M %p')
        }

# Generate professional PDF report
def generate_loan_report(loan_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontSize=24,
        textColor=HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=1,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=HexColor('#1a1a1a'),
        spaceAfter=15,
        fontName='Helvetica-Bold'
    )
    
    # Document header
    story.append(Paragraph("GITEX DEMO BANK", title_style))
    story.append(Paragraph("COMPREHENSIVE LOAN ANALYSIS REPORT", title_style))
    story.append(Spacer(1, 30))
    
    # Executive summary table
    summary_data = [
        ['Report Generated:', loan_data['timestamp']],
        ['Applicant Name:', loan_data['applicant_name']],
        ['Requested Amount:', f"${loan_data['loan_amount']:,}" if loan_data['loan_amount'] > 0 else "Not specified"],
        ['Final Decision:', loan_data['decision']],
        ['Processing System:', 'AI-Powered Multi-Agent Platform']
    ]
    
    if loan_data['decision'] == 'APPROVED' and loan_data['interest_rate'] > 0:
        summary_data.append(['Approved Interest Rate:', f"{loan_data['interest_rate']}% per annum"])
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0,0), (0,-1), HexColor('#1a1a1a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 12),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e5e5e5')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [white, HexColor('#f8f9fa')])
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 40))
    
    # Analysis section
    story.append(Paragraph("DETAILED ANALYSIS & DECISION RATIONALE", header_style))
    
    # Format the response for better readability
    response_text = loan_data['full_response']
    paragraphs = response_text.split('\n\n') if '\n\n' in response_text else [response_text]
    
    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para.strip(), styles['Normal']))
            story.append(Spacer(1, 12))
    
    # Footer
    story.append(Spacer(1, 50))
    story.append(Paragraph(
        "This report is generated by GITEX Demo Bank's AI-powered loan processing system. All decisions are subject to final review and compliance with bank policies and regulations.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=10, textColor=HexColor('#666666'), alignment=1)
    ))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Generate decision letter
def generate_decision_letter(loan_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Header
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=16,
        textColor=HexColor('#1a1a1a'),
        alignment=1,
        fontName='Helvetica-Bold'
    )
    
    story.append(Paragraph("GITEX DEMO BANK", header_style))
    story.append(Paragraph("AI-Powered Loan Processing Division", styles['Normal']))
    story.append(Paragraph("Victoria Island, Lagos, Nigeria", styles['Normal']))
    story.append(Spacer(1, 40))
    
    # Date and address
    story.append(Paragraph(f"Date: {loan_data['timestamp']}", styles['Normal']))
    story.append(Spacer(1, 30))
    
    story.append(Paragraph(f"Dear {loan_data['applicant_name']},", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Letter content based on decision
    if loan_data['decision'] == 'APPROVED':
        subject = "LOAN APPLICATION APPROVED"
        story.append(Paragraph(f"Re: {subject}", ParagraphStyle('Subject', parent=styles['Normal'], fontName='Helvetica-Bold')))
        story.append(Spacer(1, 20))
        
        content = f"""We are pleased to inform you that your loan application has been APPROVED."""
        
        if loan_data['loan_amount'] > 0:
            content += f""" Your approved loan amount is ${loan_data['loan_amount']:,}."""
        
        if loan_data['interest_rate'] > 0:
            content += f""" The approved interest rate is {loan_data['interest_rate']}% per annum."""
        
        content += f"""

Our advanced AI analysis system has completed a comprehensive review of your application and determined that you meet our lending criteria.

Next Steps:
• Our loan officer will contact you within 48 hours
• Please prepare required documentation for final verification
• Loan disbursement will occur upon completion of all paperwork
• You will receive a detailed loan agreement for your review

We appreciate your business and look forward to supporting your financial goals."""
    
    else:
        subject = "LOAN APPLICATION STATUS"
        story.append(Paragraph(f"Re: {subject}", ParagraphStyle('Subject', parent=styles['Normal'], fontName='Helvetica-Bold')))
        story.append(Spacer(1, 20))
        
        content = f"""Thank you for your interest in GITEX Demo Bank and for submitting your loan application.

After careful consideration by our AI-powered analysis system, we regret to inform you that we cannot approve your loan application at this time.

This decision is based on our comprehensive risk assessment and current lending criteria. We encourage you to:

• Review and strengthen your financial position
• Consider reapplying in 6-12 months
• Speak with our business advisory team for guidance
• Explore alternative financing options that may better suit your needs

We value your interest in our services and hope to have the opportunity to serve you in the future as your financial situation continues to develop."""
    
    story.append(Paragraph(content, styles['Normal']))
    story.append(Spacer(1, 40))
    
    # Closing
    story.append(Paragraph("Sincerely,", styles['Normal']))
    story.append(Spacer(1, 30))
    story.append(Paragraph("GITEX DEMO BANK", ParagraphStyle('Signature', parent=styles['Normal'], fontName='Helvetica-Bold')))
    story.append(Paragraph("Automated Loan Processing Division", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Handle processing
if st.session_state.processing:
    # Simulate processing time for better UX
    import time
    time.sleep(2)
    
    # Process the request
    if uploaded_file:
        response = call_bedrock_agent("", uploaded_file.name)
        request_type = f"Application: {uploaded_file.name}"
    else:
        response = call_bedrock_agent(user_message)
        request_type = "Direct Request"
    
    # Store results
    st.session_state.last_response = response
    st.session_state.chat_history.append({
        'type': request_type,
        'response': response,
        'timestamp': datetime.now().strftime('%B %d, %Y at %I:%M %p')
    })
    
    # Reset processing state
    st.session_state.processing = False
    st.rerun()

# Display results
if st.session_state.last_response:
    st.markdown('<div class="response-container">', unsafe_allow_html=True)
    st.markdown("### 🤖 AI Loan Officer Decision")
    
    # Parse loan data
    loan_data = parse_loan_data(st.session_state.last_response)
    
    # Show decision badge
    if loan_data['decision'] == 'APPROVED':
        st.markdown('<div class="status-approved">✅ Loan Approved</div>', unsafe_allow_html=True)
    elif loan_data['decision'] == 'REJECTED':
        st.markdown('<div class="status-rejected">❌ Loan Declined</div>', unsafe_allow_html=True)
    
    # Show agent response
    st.markdown('<div class="agent-response">', unsafe_allow_html=True)
    st.write(st.session_state.last_response)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Generate and offer downloads
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.markdown('<div class="download-title">📄 Professional Documents Generated</div>', unsafe_allow_html=True)
    st.markdown('<div class="download-subtitle">Your personalized loan documents are ready for download</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Generate report PDF
        try:
            report_pdf = generate_loan_report(loan_data)
            st.download_button(
                label="📊 Download Detailed Report",
                data=report_pdf,
                file_name=f"GITEX_Loan_Report_{loan_data['applicant_name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Report generation error: {str(e)}")
    
    with col2:
        # Generate letter PDF
        try:
            letter_pdf = generate_decision_letter(loan_data)
            st.download_button(
                label="📝 Download Decision Letter",
                data=letter_pdf,
                file_name=f"GITEX_Decision_Letter_{loan_data['applicant_name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Letter generation error: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Session info
    st.markdown(f'<div class="session-info">Report generated on {loan_data["timestamp"]} | Session: {st.session_state.session_id[-8:]}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # New application button
    if st.button("🔄 Process Another Application", use_container_width=True):
        st.session_state.last_response = None
        st.session_state.processing = False
        st.rerun()

# Footer
st.markdown('''
<div class="footer">
    <strong>GITEX Demo Bank</strong> | Powered by AWS Bedrock AI Platform<br>
    Secure • Fast • Professional Loan Processing
</div>
''', unsafe_allow_html=True)
