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
    page_title="DESCASIO - AWS AI Bedrock Agent Demo",
    page_icon="⚡",
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
        padding: 2.5rem 2rem;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 16px 16px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    .main-header .tagline {
        color: #b0b0b0;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        font-weight: 400;
    }
    
    .application-container {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .section-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .section-subtitle {
        font-size: 1rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    
    .upload-section {
        border: 2px dashed #d1d5db;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background: #f9fafb;
        margin: 1.5rem 0;
        transition: all 0.3s ease;
    }
    
    .upload-section:hover {
        border-color: #1a1a1a;
        background: #f3f4f6;
    }
    
    .divider {
        display: flex;
        align-items: center;
        margin: 2rem 0;
        color: #9ca3af;
        font-weight: 500;
    }
    
    .divider::before,
    .divider::after {
        content: '';
        flex: 1;
        height: 1px;
        background: #e5e7eb;
    }
    
    .divider span {
        margin: 0 1rem;
        background: white;
        padding: 0 0.5rem;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .chat-input {
        margin: 1.5rem 0;
    }
    
    .stTextArea > div > div > textarea {
        border: 2px solid #e9ecef;
        border-radius: 12px;
        padding: 1rem;
        font-size: 1rem;
        line-height: 1.5;
        background: white;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #1a1a1a;
        box-shadow: 0 0 0 3px rgba(26,26,26,0.1);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d3436 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2d3436 0%, #636e72 100%);
        transform: translateY(-1px);
    }
    
    .stButton > button:disabled {
        background: #e5e7eb;
        color: #9ca3af;
        transform: none;
    }
    
    .result-container {
        background: white;
        border-radius: 16px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
    }
    
    .decision-approved {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        color: #155724;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-weight: 700;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        border: 2px solid #28a745;
    }
    
    .decision-rejected {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        color: #721c24;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-weight: 700;
        font-size: 1.2rem;
        margin-bottom: 2rem;
        border: 2px solid #dc3545;
    }
    
    .analysis-content {
        background: #f8f9fa;
        border-left: 4px solid #1a1a1a;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1.5rem 0;
        font-size: 1rem;
        line-height: 1.6;
    }
    
    .download-section {
        background: #e3f2fd;
        border: 2px solid #2196f3;
        border-radius: 12px;
        padding: 2rem;
        margin: 2rem 0;
        text-align: center;
    }
    
    .processing-message {
        text-align: center;
        color: #6b7280;
        font-style: italic;
        margin: 2rem 0;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    footer {visibility: hidden;}
    .stApp > header {display: none;}
    
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
if 'last_response' not in st.session_state:
    st.session_state.last_response = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Header
st.markdown('''
<div class="main-header">
    <h1>GITEX Demo Bank</h1>
    <p class="tagline">AI-Powered Loan Processing</p>
</div>
''', unsafe_allow_html=True)

# Get configuration from secrets
try:
    agent_id = st.secrets.get("AGENT_ID", "")
    agent_alias_id = st.secrets.get("AGENT_ALIAS_ID", "TSTALIASID")
    aws_access_key = st.secrets.get("AWS_ACCESS_KEY_ID", "")
    aws_secret_key = st.secrets.get("AWS_SECRET_ACCESS_KEY", "")
    aws_region = st.secrets.get("AWS_REGION", "eu-west-2")
    
    if not agent_id:
        st.error("Configuration Required: Please add your AGENT_ID to Streamlit secrets")
        st.stop()
        
except Exception:
    st.error("Configuration Required: Please add your AWS credentials and AGENT_ID to Streamlit secrets")
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
        st.error(f"AWS Connection Failed: {str(e)}")
        return None

# Main interface
if not st.session_state.processing and not st.session_state.last_response:
    st.markdown('<div class="application-container">', unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">Apply for a Business Loan</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Upload your application or describe your financing needs</div>', unsafe_allow_html=True)
    
    # File upload option
    st.markdown('''
    <div class="upload-section">
        <h4 style="margin-bottom: 0.5rem;">Upload Application Document</h4>
        <p style="color: #6b7280; margin: 0;">PDF format preferred</p>
    </div>
    ''', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose file",
        type=['pdf'],
        label_visibility="collapsed"
    )
    
    # Divider
    st.markdown('<div class="divider"><span>or</span></div>', unsafe_allow_html=True)
    
    # Text input option
    st.markdown("**Describe Your Loan Request**")
    user_message = st.text_area(
        "",
        placeholder="Example: I need $25,000 for restaurant equipment. My business has been operating for 3 years with $8,000 monthly revenue. I have good credit and can provide collateral...",
        height=100,
        label_visibility="collapsed",
        key="loan_request"
    )
    
    # Submit button
    st.markdown("<br>", unsafe_allow_html=True)
    
    if uploaded_file:
        if st.button("Process Application", type="primary", use_container_width=True):
            st.session_state.processing = True
            st.session_state.upload_file = uploaded_file
            st.session_state.text_input = None
            st.rerun()
    elif user_message.strip():
        if st.button("Submit Request", type="primary", use_container_width=True):
            st.session_state.processing = True
            st.session_state.upload_file = None
            st.session_state.text_input = user_message
            st.rerun()
    else:
        st.button("Please provide your loan details", disabled=True, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Processing state
elif st.session_state.processing:
    st.markdown('<div class="processing-message">Processing your loan application...</div>', unsafe_allow_html=True)
    
    # Process the request
    def call_bedrock_agent(message, file_name=None):
        bedrock = get_bedrock_client()
        
        if not bedrock:
            return "Unable to connect to loan processing system. Please try again."
        
        try:
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
            
            response = bedrock.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                enableTrace=False,
                sessionId=st.session_state.session_id,
                inputText=prompt
            )
            
            completion = ""
            for event in response.get("completion", []):
                if 'chunk' in event:
                    chunk = event["chunk"]
                    completion += chunk["bytes"].decode()
            
            return completion if completion else "No response received from the loan processing system."
            
        except Exception as e:
            return f"Processing error: {str(e)}"
    
    # Make the API call
    if hasattr(st.session_state, 'upload_file') and st.session_state.upload_file:
        response = call_bedrock_agent("", st.session_state.upload_file.name)
    else:
        response = call_bedrock_agent(st.session_state.text_input)
    
    # Store results
    st.session_state.last_response = response
    st.session_state.processing = False
    st.rerun()

# Results display
elif st.session_state.last_response:
    # Parse loan data
    def parse_loan_data(response_text):
        try:
            # Extract applicant name
            name_patterns = [
                r'applicant[:\s]+([A-Za-z\s]+)',
                r'name[:\s]+([A-Za-z\s]+)',
                r'borrower[:\s]+([A-Za-z\s]+)'
            ]
            
            applicant_name = "Loan Applicant"
            for pattern in name_patterns:
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    name_candidate = match.group(1).strip()
                    if not any(word in name_candidate.lower() for word in ['report', 'analysis', 'decision', 'loan']):
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
    
    # Generate PDF functions (simplified versions)
    def generate_loan_report(loan_data):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        story.append(Paragraph("GITEX DEMO BANK - LOAN ANALYSIS REPORT", styles['Title']))
        story.append(Spacer(1, 30))
        
        # Summary
        summary_data = [
            ['Applicant:', loan_data['applicant_name']],
            ['Amount:', f"${loan_data['loan_amount']:,}" if loan_data['loan_amount'] > 0 else "Not specified"],
            ['Decision:', loan_data['decision']],
            ['Date:', loan_data['timestamp']]
        ]
        
        if loan_data['decision'] == 'APPROVED' and loan_data['interest_rate'] > 0:
            summary_data.append(['Interest Rate:', f"{loan_data['interest_rate']}% per annum"])
        
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, black),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold')
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Analysis
        story.append(Paragraph("Analysis:", styles['Heading2']))
        story.append(Paragraph(loan_data['full_response'], styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_decision_letter(loan_data):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Header
        story.append(Paragraph("GITEX DEMO BANK", styles['Title']))
        story.append(Spacer(1, 30))
        
        # Content
        story.append(Paragraph(f"Date: {loan_data['timestamp']}", styles['Normal']))
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"Dear {loan_data['applicant_name']},", styles['Normal']))
        story.append(Spacer(1, 20))
        
        if loan_data['decision'] == 'APPROVED':
            content = "We are pleased to inform you that your loan application has been APPROVED."
        else:
            content = "Thank you for your loan application. After careful review, we are unable to approve your request at this time."
        
        story.append(Paragraph(content, styles['Normal']))
        story.append(Spacer(1, 20))
        story.append(Paragraph(loan_data['full_response'], styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    loan_data = parse_loan_data(st.session_state.last_response)
    
    st.markdown('<div class="result-container">', unsafe_allow_html=True)
    
    # Decision header
    if loan_data['decision'] == 'APPROVED':
        st.markdown('<div class="decision-approved">Loan Application Approved</div>', unsafe_allow_html=True)
    elif loan_data['decision'] == 'REJECTED':
        st.markdown('<div class="decision-rejected">Application Not Approved</div>', unsafe_allow_html=True)
    
    # Key details
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Applicant", loan_data['applicant_name'])
    with col2:
        amount_display = f"${loan_data['loan_amount']:,}" if loan_data['loan_amount'] > 0 else "TBD"
        st.metric("Loan Amount", amount_display)
    with col3:
        rate_display = f"{loan_data['interest_rate']}%" if loan_data['interest_rate'] > 0 else "TBD"
        st.metric("Interest Rate", rate_display)
    
    # Analysis
    st.markdown("**Analysis & Decision**")
    st.markdown('<div class="analysis-content">', unsafe_allow_html=True)
    st.write(st.session_state.last_response)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Download section
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.markdown("**Download Your Documents**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            report_pdf = generate_loan_report(loan_data)
            st.download_button(
                label="Download Report",
                data=report_pdf,
                file_name=f"Loan_Report_{loan_data['applicant_name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Report error: {str(e)}")
    
    with col2:
        try:
            letter_pdf = generate_decision_letter(loan_data)
            st.download_button(
                label="Download Letter",
                data=letter_pdf,
                file_name=f"Decision_Letter_{loan_data['applicant_name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Letter error: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # New application button
    if st.button("Process Another Application", use_container_width=True):
        for key in ['last_response', 'processing', 'upload_file', 'text_input']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
