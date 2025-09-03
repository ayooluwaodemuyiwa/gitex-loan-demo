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
    }
    
    .main-header {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d3436 100%);
        padding: 2rem;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 12px 12px;
        color: white;
        text-align: center;
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        color: #b0b0b0;
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    
    .chat-container {
        background: white;
        border-radius: 12px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border: 1px solid #e5e5e5;
    }
    
    .agent-response {
        background: #f8f9fa;
        border-left: 4px solid #1a1a1a;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    
    .download-section {
        background: linear-gradient(135deg, #e3f2fd 0%, #f0f8ff 100%);
        border: 1px solid #2196f3;
        border-radius: 12px;
        padding: 2rem;
        margin: 2rem 0;
    }
    
    .stButton > button {
        background: #1a1a1a;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: #2d3436;
        transform: translateY(-1px);
    }
    
    .status-approved {
        background: #e8f5e8;
        color: #2e7d32;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    
    .status-rejected {
        background: #ffeaea;
        color: #c62828;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'last_response' not in st.session_state:
    st.session_state.last_response = None

# Header
st.markdown('''
<div class="main-header">
    <h1>GITEX DEMO BANK</h1>
    <p>AI-Powered Loan Processing Platform</p>
</div>
''', unsafe_allow_html=True)

# Configuration section
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

with st.expander("⚙️ System Configuration", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        agent_id = st.text_input(
            "Bedrock Agent ID",
            value=st.secrets.get("AGENT_ID", "YOUR_AGENT_ID_HERE"),
            help="Enter your Bedrock Agent ID"
        )
    
    with col2:
        agent_alias = st.text_input(
            "Agent Alias",
            value="TSTALIASID",
            help="Usually TSTALIASID for test"
        )

st.markdown('</div>', unsafe_allow_html=True)

# AWS client initialization
@st.cache_resource
def get_bedrock_client():
    try:
        return boto3.client(
            'bedrock-agent-runtime',
            region_name='us-east-1',
            aws_access_key_id=st.secrets.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=st.secrets.get("AWS_SECRET_ACCESS_KEY")
        )
    except Exception as e:
        st.error(f"AWS client initialization failed: {str(e)}")
        return None

# Chat interface
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
st.markdown("### Loan Application Processing")

# File upload
uploaded_file = st.file_uploader(
    "Upload Loan Application (PDF)",
    type=['pdf'],
    help="Upload a loan application document"
)

# Chat input
user_message = st.text_area(
    "Or describe your loan request:",
    placeholder="I need a $25,000 loan for restaurant equipment. My business has been operating for 3 years...",
    height=100
)

# Processing buttons
col1, col2 = st.columns(2)

with col1:
    if uploaded_file:
        process_file = st.button("Process Application", type="primary", use_container_width=True)
    else:
        process_file = st.button("Process Application", type="primary", disabled=True, use_container_width=True)

with col2:
    if user_message.strip():
        send_message = st.button("Send Message", use_container_width=True)
    else:
        send_message = st.button("Send Message", disabled=True, use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# Agent interaction function
def call_bedrock_agent(message, file_name=None):
    bedrock = get_bedrock_client()
    
    if not bedrock:
        return "Error: Could not initialize AWS client. Check your credentials."
    
    if agent_id == "YOUR_AGENT_ID_HERE":
        return "Error: Please configure your Bedrock Agent ID in the system configuration."
    
    try:
        # Prepare prompt
        if file_name:
            prompt = f"Please process this loan application file: {file_name}. Provide a comprehensive analysis and decision. Include the applicant name and loan amount clearly in your response."
        else:
            prompt = f"Loan Request: {message}. Please analyze this request and provide a loan decision with reasoning."
        
        # Call Bedrock agent
        response = bedrock.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias,
            sessionId=st.session_state.session_id,
            inputText=prompt
        )
        
        # Extract response text
        response_text = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk_bytes = event['chunk'].get('bytes', b'')
                response_text += chunk_bytes.decode('utf-8')
        
        return response_text if response_text else "No response received from the loan processing agent."
        
    except Exception as e:
        return f"Processing error: {str(e)}"

# Parse loan data from agent response
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
                applicant_name = match.group(1).strip()
                break
        
        # Extract loan amount
        amount_match = re.search(r'\$?([\d,]+)', response_text)
        loan_amount = int(amount_match.group(1).replace(',', '')) if amount_match else 0
        
        # Extract decision
        decision = "PENDING"
        if re.search(r'\b(approved|approve)\b', response_text, re.IGNORECASE):
            decision = "APPROVED"
        elif re.search(r'\b(rejected|declined?|deny|denied)\b', response_text, re.IGNORECASE):
            decision = "REJECTED"
        
        # Extract interest rate (if approved)
        rate_match = re.search(r'(\d+\.?\d*)%', response_text)
        interest_rate = float(rate_match.group(1)) if rate_match else 0
        
        return {
            'applicant_name': applicant_name,
            'loan_amount': loan_amount,
            'decision': decision,
            'interest_rate': interest_rate,
            'full_response': response_text,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception:
        return {
            'applicant_name': "Loan Applicant",
            'loan_amount': 0,
            'decision': "PENDING",
            'interest_rate': 0,
            'full_response': response_text,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# Generate professional PDF report
def generate_loan_report(loan_data):
    buffer = io.BytesIO()
    doc = SimpleDocDocument(buffer, pagesize=A4)
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
    story.append(Paragraph("LOAN DECISION REPORT", title_style))
    story.append(Spacer(1, 30))
    
    # Executive summary table
    summary_data = [
        ['Report Date:', loan_data['timestamp']],
        ['Applicant Name:', loan_data['applicant_name']],
        ['Loan Amount:', f"${loan_data['loan_amount']:,}"],
        ['Decision:', loan_data['decision']],
        ['Processing System:', 'AI Multi-Agent Platform']
    ]
    
    if loan_data['decision'] == 'APPROVED' and loan_data['interest_rate'] > 0:
        summary_data.append(['Interest Rate:', f"{loan_data['interest_rate']}% per annum"])
    
    summary_table = Table(summary_data, colWidths=[2.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0,0), (0,-1), HexColor('#1a1a1a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('GRID', (0,0), (-1,-1), 1, HexColor('#e5e5e5')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [white, HexColor('#f8f9fa')])
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 30))
    
    # Analysis section
    story.append(Paragraph("DETAILED ANALYSIS", header_style))
    
    # Split response into paragraphs for better formatting
    response_paragraphs = loan_data['full_response'].split('\n')
    for para in response_paragraphs:
        if para.strip():
            story.append(Paragraph(para.strip(), styles['Normal']))
            story.append(Spacer(1, 10))
    
    # Footer
    story.append(Spacer(1, 40))
    story.append(Paragraph(
        "This report is generated by GITEX Demo Bank's AI-powered loan processing system. All decisions are subject to final human review and bank policies.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor=HexColor('#666666'))
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
    story.append(Paragraph("GITEX DEMO BANK", styles['Title']))
    story.append(Paragraph("Victoria Island, Lagos, Nigeria", styles['Normal']))
    story.append(Spacer(1, 30))
    
    # Date and address
    story.append(Paragraph(f"Date: {loan_data['timestamp']}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph(f"Dear {loan_data['applicant_name']},", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Letter content based on decision
    if loan_data['decision'] == 'APPROVED':
        content = f"""
        We are pleased to inform you that your loan application has been APPROVED 
        for the amount of ${loan_data['loan_amount']:,}.
        
        Our AI-powered analysis system has completed a comprehensive review of your 
        application and determined that you meet our lending criteria.
        """
        
        if loan_data['interest_rate'] > 0:
            content += f"\n\nYour approved interest rate is {loan_data['interest_rate']}% per annum."
        
        content += """
        
        Next Steps:
        - Our loan officer will contact you within 48 hours
        - Please prepare the required documentation
        - Funds will be disbursed upon completion of paperwork
        
        Thank you for choosing GITEX Demo Bank.
        """
    
    else:
        content = f"""
        Thank you for your interest in GITEX Demo Bank. After careful consideration 
        by our AI-powered analysis system, we regret to inform you that we cannot 
        approve your loan application at this time.
        
        This decision is based on our comprehensive risk assessment and current 
        lending criteria. We encourage you to:
        
        - Review and improve your business financials
        - Consider reapplying in 6-12 months
        - Speak with our business advisory team for guidance
        
        We appreciate your interest and hope to serve you in the future.
        """
    
    story.append(Paragraph(content, styles['Normal']))
    story.append(Spacer(1, 30))
    
    # Closing
    story.append(Paragraph("Sincerely,", styles['Normal']))
    story.append(Spacer(1, 20))
    story.append(Paragraph("GITEX Demo Bank", styles['Normal']))
    story.append(Paragraph("Automated Loan Processing Division", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# Handle file processing
if process_file and uploaded_file:
    with st.spinner("Processing loan application..."):
        response = call_bedrock_agent("", uploaded_file.name)
        st.session_state.last_response = response
        st.session_state.chat_history.append({
            'type': 'file',
            'file_name': uploaded_file.name,
            'response': response,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.rerun()

# Handle message sending
if send_message and user_message.strip():
    with st.spinner("Processing loan request..."):
        response = call_bedrock_agent(user_message)
        st.session_state.last_response = response
        st.session_state.chat_history.append({
            'type': 'message',
            'message': user_message,
            'response': response,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.rerun()

# Display response and generate reports
if st.session_state.last_response:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown("### Loan Processing Results")
    
    # Parse loan data
    loan_data = parse_loan_data(st.session_state.last_response)
    
    # Show decision badge
    if loan_data['decision'] == 'APPROVED':
        st.markdown('<div class="status-approved">LOAN APPROVED</div>', unsafe_allow_html=True)
    elif loan_data['decision'] == 'REJECTED':
        st.markdown('<div class="status-rejected">LOAN DECLINED</div>', unsafe_allow_html=True)
    
    # Show agent response
    st.markdown('<div class="agent-response">', unsafe_allow_html=True)
    st.write(st.session_state.last_response)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Generate and offer downloads
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.markdown("### Generated Documents")
    st.write("Professional loan documents have been automatically generated based on the analysis above.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Generate report PDF
        try:
            report_pdf = generate_loan_report(loan_data)
            st.download_button(
                label="📊 Download Detailed Report",
                data=report_pdf,
                file_name=f"loan_report_{loan_data['applicant_name'].replace(' ', '_')}.pdf",
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
                label=" Download Decision Letter",
                data=letter_pdf,
                file_name=f"decision_letter_{loan_data['applicant_name'].replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Letter generation error: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Chat history
if st.session_state.chat_history:
    with st.expander(" Processing History", expanded=False):
        for entry in reversed(st.session_state.chat_history[-5:]):  # Show last 5
            st.write(f"**{entry['timestamp']}**")
            if entry['type'] == 'file':
                st.write(f"File: {entry['file_name']}")
            else:
                st.write(f"Message: {entry['message']}")
            st.write("Response:", entry['response'][:200] + "..." if len(entry['response']) > 200 else entry['response'])
            st.divider()

# Footer
st.markdown("---")
st.markdown(f"**GITEX Demo Bank** | Session: {st.session_state.session_id[-8:]}")

# Reset session button
if st.button(" New Session"):
    for key in st.session_state.keys():
        del st.session_state[key]
    st.rerun()
