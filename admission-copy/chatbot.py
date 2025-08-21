import requests
import json
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId  
from werkzeug.utils import secure_filename 
import re
import os
from flask import Flask, render_template, send_from_directory, request, jsonify
import threading
import webbrowser
import math


import subprocess
import atexit



app = Flask(__name__, template_folder='templates', static_folder='static')

# Database connections - Updated for MongoDB Atlas
MONGO_URI = os.environ.get('MONGO_URI')

if not MONGO_URI:
    raise ValueError("❌ MONGO_URI environment variable is not set.")

print(f"🔍 MONGO_URI: {MONGO_URI}")  # Debug line

try:
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=20000,
        socketTimeoutMS=20000
    )
    # Test the connection
    client.admin.command('ping')
    print("✅ MongoDB Atlas connection successful!")
    
    db_admission_office = client["admission_office"]
    students_collection = db_admission_office["students"]
    
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    import sys
    sys.exit(1)

# Create personal_data.txt if it doesn't exist with the required content
if not os.path.exists("personal_data.txt"):
    with open("personal_data.txt", "w", encoding="utf-8") as f:
        f.write("""🎓 1. General HEC Eligibility Guidelines for BS Admissions
Degree Duration: All BS programs are 4 years long with 124–160 credit hours.

Minimum Qualification: Students must have completed 12 years of education (Intermediate: FSc, ICS, FA, ICom, DAE, etc.).

Minimum Marks: Most universities require at least 50–60% marks in intermediate.

Merit Criteria: Admission is usually based on intermediate marks + university entry test (if applicable).

2. Program-wise Eligibility Based on Intermediate Stream

A) ICS (Intermediate in Computer Science)
Eligible for: BS Computer Science (BSCS), BS IT, BS Data Science, BS AI, BS Software Engineering
Must have studied Mathematics + Computer Science/Physics/Statistics.
Minimum 50% marks. If Math was not studied, deficiency course (6 credit hours) required.

B) FSc Pre-Engineering
Eligible for: BS Engineering (Electrical, Mechanical, Civil, etc.), BSCS, BS IT, BS Data Science
Must have Math, Physics, Chemistry. Minimum 60% marks. ECAT test required for engineering.

C) FSc Pre-Medical
Eligible for: BS Biotechnology, BS Zoology, BS Botany, BS Biochemistry, BS Nutrition, BS Nursing
Must have Biology. Minimum 50–60% marks. BSCS/IT possible only with additional Math or deficiency course.

D) ICom (Intermediate in Commerce)
Eligible for: BBA, BS Accounting & Finance, BS Commerce, BS Economics, BS Banking & Finance
Typically 60% marks. Not eligible for Engineering or BSCS without Math.

E) FA (Intermediate in Arts/Humanities)
Eligible for: BS English, BS Mass Communication, BS IR, BS Psychology, BS Education, BS Sociology, etc.
Entry test or portfolio may be required. Not eligible for technical programs.

F) DAE (Diploma of Associate Engineering)
Eligible for: BS Engineering Technology programs in relevant fields. May grant credit transfer or advanced standing.
Some universities allow BS Engineering admission with additional conditions.

3. Deficiency Courses and Special Cases
Students without Math for BSCS/IT must study a 6-credit Math deficiency course during first year.
Foreign or diploma holders must apply for HEC equivalence via eservices.hec.gov.pk.
Some universities allow switching fields with bridging/deficiency courses.

🎓 NUST University Eligibility Example:
- BS Computer Science: FSc Pre-Engineering or ICS with 60% marks + NUST Entry Test.
- BS Software Engineering: FSc Pre-Engineering or ICS with Math + Entry Test.
- Fee discounts: Above 85% marks in intermediate = up to 30% fee waiver; Above 90% = up to 50% waiver.

🎓 GIKI University Eligibility Example:
- BS Computer Engineering: FSc Pre-Engineering with 60% marks + GIKI Admission Test.
- Scholarships: Top 10% test scorers get merit scholarships covering 25-100% tuition.

🎓 COMSATS University Eligibility Example:
- BSCS: ICS with Math, minimum 50% marks + NTS test.
- BS Electrical Engineering: FSc Pre-Engineering with 60% marks + NTS test.
- Scholarships: Above 80% marks = 20% discount, Above 90% = 40% discount.
""")

# Updated interview questions in specific order
fixed_questions = [
    # Personal Information
    {"question": "What is your full name?", "field": "full_name", "type": "name"},
    {"question": "What is your father's name?", "field": "father_name", "type": "name"},
    {"question": "What is your date of birth?", "field": "dob", "type": "date"},
    {"question": "What is your gender? (Male / Female / Other)", "field": "gender", "type": "gender"},
    {"question": "What is your CNIC or B-Form number?", "field": "cnic", "type": "id"},
    {"question": "What is your email address?", "field": "email", "type": "email"},
    {"question": "What is your mobile number?", "field": "mobile", "type": "phone"},
    {"question": "Which city are you from?", "field": "city", "type": "location"},
    
    # Matriculation (10th Grade) Details
    {"question": "Which education board did you complete your Matric from?", "field": "matric_board", "type": "education"},
    {"question": "What was your group/stream? (Science / Arts / Computer Science)", "field": "matric_stream", "type": "education"},
    {"question": "In which year did you pass Matric?", "field": "matric_year", "type": "year"},
    {"question": "What were the total marks?", "field": "matric_total", "type": "marks"},
    {"question": "How many marks did you obtain?", "field": "matric_obtained", "type": "marks"},
    {"question": "What was the name of your school?", "field": "matric_school", "type": "institution"},
    
    # Intermediate (FA/FSc/ICS/I.Com) Details
    {"question": "Which board did you complete Intermediate from?", "field": "inter_board", "type": "education"},
    {"question": "What was your program? (FSc Pre-Medical / Pre-Engineering / ICS / I.Com / FA)", "field": "inter_program", "type": "education"},
    {"question": "In which year did you complete Intermediate?", "field": "inter_year", "type": "year"},
    {"question": "What were the total marks?", "field": "inter_total", "type": "marks"},
    {"question": "How many marks did you obtain?", "field": "inter_obtained", "type": "marks"},
    {"question": "What was the name of your college?", "field": "inter_college", "type": "institution"},
    
    # BS Program Preference
    {"question": "Which field/program would you like to apply for?", "field": "program_choice", "type": "program"},
    {"question": "Why do you want to choose this program?", "field": "program_reason", "type": "text"},
    {"question": "Do you prefer morning or evening classes?", "field": "class_preference", "type": "preference"},
    {"question": "Are you comfortable attending online classes if required?", "field": "online_comfort", "type": "preference"},
    
    # Aptitude & Interest-Based Questions
    {"question": "Do you enjoy solving logical puzzles or math problems? (Yes / No)", "field": "logical_aptitude", "type": "yesno"},
    {"question": "How familiar are you with computers and technology? (Rate from 1 to 5)", "field": "tech_familiarity", "type": "rating"},
    {"question": "Do you prefer working with numbers or with people? (Numbers / People / Both)", "field": "work_preference", "type": "preference"},
    {"question": "Do you have any prior programming experience? (Yes / No)", "field": "programming_experience", "type": "yesno"},
    {"question": "Do you prefer a theoretical learning environment or practical?", "field": "learning_preference", "type": "preference"},
    
    # Document Upload Confirmation
    {"question": "Are you ready to upload the following documents?\n- Matriculation Result Card\n- Intermediate Result Card\n- CNIC / B-Form\n- Passport-sized Photograph", "field": "documents_ready", "type": "yesno"}
]

def retrieve_relevant_data(user_prompt, data_file="personal_data.txt"):
    """Search personal data file for relevant information"""
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data_lines = f.readlines()

        keywords = user_prompt.lower().split()
        matched_lines = []
        for line in data_lines:
            for kw in keywords:
                if kw in line.lower():
                    matched_lines.append(line.strip())
                    break

        return "\n".join(matched_lines) if matched_lines else "No direct matches found in personal data."

    except FileNotFoundError:
        return "Personal data file not found."

def clean_extracted_text(text):
    """Clean and standardize extracted text"""
    if not text:
        return ""
    text = ' '.join(text.split())
    text = re.sub(r'\b(?:i|am|is|are|was|were|my|the|a|an|from|in|at)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[^a-zA-Z0-9. ]', '', text)
    return text.strip()

def extract_info(answer, question_type):
    """Extract essential information from answers"""
    if not answer:
        return ""
    
    answer = answer.lower().strip()
    
    if question_type == "name":
        name = re.sub(r'^(hi|hello|hey|my name is|i am|name is|im|this is|is)\s*', '', answer)
        return clean_extracted_text(name).title()
    elif question_type == "date":
        date = re.search(r'(\d{2}[/-]\d{2}[/-]\d{4})|(\d{4}[/-]\d{2}[/-]\d{2})', answer)
        return date.group() if date else clean_extracted_text(answer)
    elif question_type == "gender":
        gender = re.search(r'(male|female|other)', answer)
        return gender.group().title() if gender else "Other"
    elif question_type == "id":
        id_num = re.search(r'\d{5}-\d{7}-\d{1}|\d{13}', answer)
        return id_num.group() if id_num else clean_extracted_text(answer)
    elif question_type == "email":
        email = re.search(r'[\w\.-]+@[\w\.-]+', answer)
        return email.group() if email else clean_extracted_text(answer)
    elif question_type == "phone":
        phone = re.search(r'\d{4}-\d{7}', answer)
        return phone.group() if phone else clean_extracted_text(answer)
    elif question_type == "location":
        return clean_extracted_text(answer).title()
    elif question_type == "education":
        return clean_extracted_text(answer).upper()
    elif question_type == "year":
        year = re.search(r'\d{4}', answer)
        return year.group() if year else "N/A"
    elif question_type == "marks":
        marks = re.search(r'(\d+\.?\d*)', answer)
        return marks.group(1) if marks else "N/A"
    elif question_type == "institution":
        return clean_extracted_text(answer).title()
    elif question_type == "program":
        return clean_extracted_text(answer).upper()
    elif question_type == "text":
        return clean_extracted_text(answer)
    elif question_type == "preference":
        return clean_extracted_text(answer).capitalize()
    elif question_type == "yesno":
        yesno = re.search(r'(yes|no)', answer)
        return yesno.group().capitalize() if yesno else "No"
    elif question_type == "rating":
        rating = re.search(r'[1-5]', answer)
        return rating.group() if rating else "3"
    
    return clean_extracted_text(answer)

def determine_field(program_choice, inter_program):
    """Determine student's field category"""
    pc = (program_choice or "").lower()
    ip = (inter_program or "").lower()

    if any(word in pc for word in ["mbbs", "doctor", "medicine", "medical"]) or "pre-medical" in ip:
        return "Medical"
    elif any(word in pc for word in ["cs", "computer", "software", "it", "ai"]) or "ics" in ip or "computer" in ip:
        return "IT"
    elif any(word in pc for word in ["business", "commerce", "bba", "mba"]) or "commerce" in ip:
        return "Business"
    elif any(word in pc for word in ["engineering", "electrical", "mechanical", "civil"]) or "engineering" in ip:
        return "Engineering"
    else:
        return "General"

def ask_ai(prompt, context=None, mode="general"):
    """Call Gemini API with appropriate prompt based on mode"""
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': 'AIzaSyCaDrY8FSdu9M4F1cyBXBJw2YE4udSgYyI'
        }
        
        if mode == "interview":
            if context.get("current_question_index", 0) >= len(fixed_questions):
                return "Thank you for your time. This concludes your admission interview. We will contact you soon."
            
            base_question = fixed_questions[context["current_question_index"]]["question"]
            
            full_prompt = f"""IMPORTANT RULES:
- You are an admission interviewer asking questions to a student.
- You MUST ask about: {base_question}
- REPHRASE this question in a natural, conversational way.
- Ask ONLY ONE question.
- Use student's name if known.
- Reply politely in human interviewer tone.
- DO NOT add any extra text or explanations.

Conversation context:
{context.get("conversation_history", "")}

Please rephrase this question naturally: "{base_question}"
"""
            data = {
                "contents": [{
                    "parts": [{
                        "text": full_prompt
                    }]
                }]
            }
            
        elif mode == "recommendation":
            field = determine_field(context.get("program_choice"), context.get("inter_program"))
            
            full_prompt = f"""You are an expert admission counselor. Suggest only 2-3 programs from this field: {field}.

Student Details:
Name: {context.get("full_name", "Not Provided")}
Matric: {context.get("matric_obtained", "N/A")}/{context.get("matric_total", "N/A")} from {context.get("matric_board", "N/A")}
Intermediate: {context.get("inter_program", "N/A")} - {context.get("inter_obtained", "N/A")}/{context.get("inter_total", "N/A")}
Program Choice: {context.get("program_choice", "Not Provided")}

🔴 STRICT Guidelines:
- Only suggest programs directly related to {field} field.
- Do NOT suggest any program outside {field} field.
- For each program, give a short reason why it suits them based on their education and marks.
- Suggest 2-3 good universities in Pakistan offering each program.
- Output ONLY in this EXACT format:

Program: [Program Name]
Reason: [Short reason]
Universities: [Uni1], [Uni2], [Uni3]

Repeat this block for each suggested program. Do NOT include headings, explanations, or extra text. Strictly follow the format.
"""
            data = {
                "contents": [{
                    "parts": [{
                        "text": full_prompt
                    }]
                }]
            }
            
        else:  # general chat mode
            context_data = retrieve_relevant_data(prompt)
            
            full_prompt = f"""You are an AI university admission assistant.
Use the following personal data context to answer clearly and accurately.

Personal Data Context:
{context_data}

User Question:
{prompt}
"""
            data = {
                "contents": [{
                    "parts": [{
                        "text": full_prompt
                    }]
                }]
            }

        # Make the API request
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        # Parse the response
        response_json = response.json()
        if 'candidates' in response_json and response_json['candidates']:
            return response_json['candidates'][0]['content']['parts'][0]['text']
        return "I didn't get a proper response. Please try again."

    except requests.exceptions.HTTPError as e:
        return f"API Error: {str(e)}"
    except json.JSONDecodeError as e:
        return f"JSON Error: {str(e)}"
    except Exception as e:
        return f"System error: {str(e)}"

# Updated global state for the interview
interview_state = {
    "mode": "menu",
    "student_data": {
        # Personal Information
        "full_name": "",
        "father_name": "",
        "dob": "",
        "gender": "",
        "cnic": "",
        "email": "",
        "mobile": "",
        "city": "",
        
        # Matriculation Details
        "matric_board": "",
        "matric_stream": "",
        "matric_year": "",
        "matric_total": "",
        "matric_obtained": "",
        "matric_school": "",
        
        # Intermediate Details
        "inter_board": "",
        "inter_program": "",
        "inter_year": "",
        "inter_total": "",
        "inter_obtained": "",
        "inter_college": "",
        
        # BS Program Preference
        "program_choice": "",
        "program_reason": "",
        "class_preference": "",
        "online_comfort": "",
        
        # Aptitude & Interest
        "logical_aptitude": "",
        "tech_familiarity": "",
        "work_preference": "",
        "programming_experience": "",
        "learning_preference": "",
        
        # Documents
        "documents_ready": "",
        
        # Metadata
        "interview_date": datetime.now().isoformat()
    },
    "interview_data": [],
    "current_question_index": 0,
    "conversation_history": "",
    "result": None
}

# Route for serving all HTML files
@app.route('/<page>')
def serve_page(page):
    if page.endswith('.html'):
        try:
            return render_template(page)
        except:
            return "Page not found", 404
    return "Page not found", 404

# Updated routes using render_template
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/student')
def student():
    return render_template('student.html')

@app.route('/Subadmin')
def subadmin():
    return render_template('Subadmin.html')

@app.route('/SuperAdmin')
def superadmin():
    return render_template('SuperAdmin.html')

@app.route('/terms-privacy')
def terms_privacy():
    return render_template('terms-privacy.html')

@app.route('/university-dashboard')
def university_dashboard():
    return render_template('university-dashboard.html')

@app.route('/university')
def university():
    return render_template('university.html')

@app.route('/universitylogin')
def university_login():
    return render_template('universitylogin.html')

@app.route('/viewprofile')
def view_profile():
    return render_template('viewprofile.html')

@app.route('/viewuniversityprofile')
def view_university_profile():
    return render_template('viewuniversityprofile.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/adminlogin')
def admin_login():
    return render_template('adminlogin.html')

@app.route('/campus')
def campus():
    return render_template('campus.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/contactus')
def contact_us():
    return render_template('contactus.html')

@app.route('/departments')
def departments():
    return render_template('departments.html')

@app.route('/faculty')
def faculty():
    return render_template('faculty.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

@app.route('/footer')
def footer():
    return render_template('footer.html')

@app.route('/home')
def home_page():
    return render_template('home.html')

@app.route('/programs')
def programs():
    return render_template('programs.html')

@app.route('/registered-students')
def registered_students():
    return render_template('registered-students.html')

@app.route('/registered-university')
def registered_university():
    return render_template('registered-university.html')

@app.route('/student-profile')
def student_profile():
    return render_template('student-profile.html')

# Static files route (keep this as is)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


def proxy_to_node(path):
    try:
        if request.method == 'GET':
            resp = requests.get(f'http://localhost:3000/api/{path}', params=request.args)
        elif request.method == 'POST':
            resp = requests.post(f'http://localhost:3000/api/{path}', json=request.json)
        elif request.method == 'PUT':
            resp = requests.put(f'http://localhost:3000/api/{path}', json=request.json)
        elif request.method == 'DELETE':
            resp = requests.delete(f'http://localhost:3000/api/{path}')
        
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

# Chatbot routes
@app.route('/get_students', methods=['GET'])
def get_students():
    try:
        page = int(request.args.get('page', 1))
        per_page = 10
        search_query = request.args.get('search', '')
        
        query = {}
        if search_query:
            query['$or'] = [
                {'full_name': {'$regex': search_query, '$options': 'i'}},
                {'email': {'$regex': search_query, '$options': 'i'}},
                {'program_choice': {'$regex': search_query, '$options': 'i'}}
            ]
        
        total_students = students_collection.count_documents(query)
        students = list(students_collection.find(query)
                       .skip((page - 1) * per_page)
                       .limit(per_page))
        
        # Convert ObjectId to string for JSON serialization
        for student in students:
            student['_id'] = str(student['_id'])
        
        return jsonify({
            'success': True,
            'students': students,
            'totalRecords': total_students
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    user_input = request.json['message'].strip()
    response = ""
    
    if interview_state["mode"] == "interview" and interview_state["current_question_index"] < len(fixed_questions):
        # Interview mode - process answer and get next question
        interview_state["interview_data"].append({
            "question": fixed_questions[interview_state["current_question_index"]]["question"],
            "answer": user_input,
            "timestamp": datetime.now().isoformat()
        })
        
        # Extract and store clean data
        current_question = fixed_questions[interview_state["current_question_index"]]
        extracted_value = extract_info(user_input, current_question["type"])
        interview_state["student_data"][current_question["field"]] = extracted_value
        
        # Update conversation history
        interview_state["conversation_history"] += f"\nQ: {current_question['question']}\nA: {user_input}"
        interview_state["current_question_index"] += 1
        
        if interview_state["current_question_index"] >= len(fixed_questions):
            # Interview complete, save to DB
            student_document = {
                **interview_state["student_data"],
                "full_interview": interview_state["interview_data"]
            }
            interview_state["result"] = students_collection.insert_one(student_document)
            response = "✅ Interview completed and saved to database. Would you like program recommendations based on your interview? (yes/no)"
            interview_state["mode"] = "transition"
        else:
            # Get next question
            response = ask_ai("", {
                "current_question_index": interview_state["current_question_index"],
                "conversation_history": interview_state["conversation_history"]
            }, mode="interview")
    
    elif interview_state["mode"] == "transition":
        if user_input.lower() in ['yes', 'y']:
            interview_state["mode"] = "recommendation"
            # Generate recommendations
            recommendations = ask_ai("", interview_state["student_data"], mode="recommendation")
            response = f"🎓 Program Recommendations:\n{recommendations}"
            
            # Save recommendations
            students_collection.update_one(
                {"_id": interview_state["result"].inserted_id},
                {"$set": {"recommendations": recommendations}}
            )
            interview_state["mode"] = "general"
        else:
            response = "You can now ask general questions or type 'menu' to return to main menu."
            interview_state["mode"] = "general"
            
    elif interview_state["mode"] == "recommendation":
        # This mode is handled in the transition phase
        pass
            
    elif interview_state["mode"] == "general":
        if user_input.lower() == 'menu':
            interview_state["mode"] = "menu"
            response = "Main Menu:\n1. Complete admission interview\n2. Get program recommendations (requires completed interview)\n3. Ask general questions\n4. Exit"
        else:
            # General question answering
            response = ask_ai(user_input, mode="general")
    
    else:  # menu mode
        if user_input == "1":
            interview_state["mode"] = "interview"
            interview_state["current_question_index"] = 0
            interview_state["student_data"] = {
                # Personal Information
                "full_name": "",
                "father_name": "",
                "dob": "",
                "gender": "",
                "cnic": "",
                "email": "",
                "mobile": "",
                "city": "",
                
                # Matriculation Details
                "matric_board": "",
                "matric_stream": "",
                "matric_year": "",
                "matric_total": "",
                "matric_obtained": "",
                "matric_school": "",
                
                # Intermediate Details
                "inter_board": "",
                "inter_program": "",
                "inter_year": "",
                "inter_total": "",
                "inter_obtained": "",
                "inter_college": "",
                
                # BS Program Preference
                "program_choice": "",
                "program_reason": "",
                "class_preference": "",
                "online_comfort": "",
                
                # Aptitude & Interest
                "logical_aptitude": "",
                "tech_familiarity": "",
                "work_preference": "",
                "programming_experience": "",
                "learning_preference": "",
                
                # Documents
                "documents_ready": "",
                
                # Metadata
                "interview_date": datetime.now().isoformat()
            }
            interview_state["interview_data"] = []
            interview_state["conversation_history"] = ""
            response = ask_ai("", {
                "current_question_index": interview_state["current_question_index"],
                "conversation_history": interview_state["conversation_history"]
            }, mode="interview")
            
        elif user_input == "2":
            if interview_state["student_data"].get("full_name"):
                interview_state["mode"] = "recommendation"
                recommendations = ask_ai("", interview_state["student_data"], mode="recommendation")
                response = f"🎓 Program Recommendations:\n{recommendations}"
                interview_state["mode"] = "general"
            else:
                response = "Please complete the admission interview first to get personalized recommendations."
                
        elif user_input == "3":
            interview_state["mode"] = "general"
            response = "You can now ask general questions. Type 'menu' to return to main menu."
            
        elif user_input == "4":
            response = "exit"
        else:
            response = "Invalid choice. Please enter 1, 2, 3, or 4."
    
    return jsonify({"response": response})

# University routes
@app.route('/api/universities/register', methods=['POST'])
def register_university():
    try:
        data = request.json
        
        # Connect to universities collection
        universities_collection = db_admission_office["universities"]
        
        # Check if university already exists
        if universities_collection.find_one({"email": data["email"]}):
            return jsonify({"error": "University with this email already exists"}), 400
            
        # Insert new university
        result = universities_collection.insert_one({
            "name": data["name"],
            "contactPerson": data["contactPerson"],
            "email": data["email"],
            "password": data["password"],  # Note: You should hash this in production
            "address": data["address"],
            "website": data.get("website", ""),
            "description": data.get("description", ""),
            "createdAt": datetime.now().isoformat()
        })
        
        return jsonify({
            "success": True,
            "universityId": str(result.inserted_id)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/login', methods=['POST'])
def login_university():
    try:
        data = request.json
        universities_collection = db_admission_office["universities"]
        
        university = universities_collection.find_one({
            "email": data["email"],
            "password": data["password"]  # Again, use hashed passwords in production
        })
        
        if university:
            university['_id'] = str(university['_id'])
            return jsonify({
                "success": True,
                "university": university
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid email or password"
            }), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# University Profile Routes
@app.route('/api/universities/<university_id>', methods=['GET'])
def get_university_profile(university_id):
    try:
        universities_collection = db_admission_office["universities"]
        
        # Convert string ID to MongoDB ObjectId
        from bson import ObjectId
        university = universities_collection.find_one({"_id": ObjectId(university_id)})
        
        if university:
            # Convert ObjectId to string for JSON serialization
            university['_id'] = str(university['_id'])
            return jsonify(university)
        else:
            return jsonify({"error": "University not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/universities', methods=['GET'])
def get_all_universities():
    try:
        page = int(request.args.get('page', 1))
        per_page = 10
        search_query = request.args.get('search', '')
        
        query = {}
        if search_query:
            query['$or'] = [
                {'name': {'$regex': search_query, '$options': 'i'}},
                {'email': {'$regex': search_query, '$options': 'i'}},
                {'contactPerson': {'$regex': search_query, '$options': 'i'}}
            ]
        
        universities_collection = db_admission_office["universities"]
        total_universities = universities_collection.count_documents(query)
        universities = list(universities_collection.find(query)
                          .skip((page - 1) * per_page)
                          .limit(per_page))
        
        # Convert ObjectId to string for JSON serialization
        for university in universities:
            university['_id'] = str(university['_id'])
        
        return jsonify({
            'success': True,
            'universities': universities,
            'totalRecords': total_universities
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/students', methods=['GET'])
def get_all_students():
    try:
        page = int(request.args.get('page', 1))
        per_page = 10
        search_query = request.args.get('search', '')
        
        query = {}
        if search_query:
            query['$or'] = [
                {'full_name': {'$regex': search_query, '$options': 'i'}},
                {'email': {'$regex': search_query, '$options': 'i'}},
                {'program_choice': {'$regex': search_query, '$options': 'i'}}
            ]
        
        total_students = students_collection.count_documents(query)
        students = list(students_collection.find(query)
                       .skip((page - 1) * per_page)
                       .limit(per_page))
        
        # Convert ObjectId to string for JSON serialization
        for student in students:
            student['_id'] = str(student['_id'])
        
        return jsonify({
            'success': True,
            'students': students,
            'totalRecords': total_students
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
# Student Authentication Routes
@app.route('/api/students/signup', methods=['POST'])
def student_signup():
    try:
        data = request.json
        
        # Check if student already exists
        if students_collection.find_one({"email": data["email"]}):
            return jsonify({"error": "Student with this email already exists"}), 400
            
        # Insert new student
        result = students_collection.insert_one({
            "full_name": data["name"],
            "email": data["email"],
            "password": data["password"],  # Note: In production, hash this password
            "created_at": datetime.now().isoformat()
        })
        
        return jsonify({
            "success": True,
            "studentId": str(result.inserted_id)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/students/login', methods=['POST'])
def student_login():
    try:
        data = request.json
        
        student = students_collection.find_one({
            "email": data["email"],
            "password": data["password"]  # Again, use hashed passwords in production
        })
        
        if student:
            student['_id'] = str(student['_id'])
            return jsonify({
                "success": True,
                "studentId": student['_id'],
                "student": student
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid email or password"
            }), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Student Profile Routes
@app.route('/api/students/updateProfile', methods=['POST'])
def update_student_profile():
    try:
        # Get student ID
        student_id = request.form.get('studentId')
        if not student_id:
            return jsonify({"success": False, "message": "Student ID is required"}), 400
        
        # Prepare update data
        update_data = {
            "full_name": request.form.get('fullName'),
            "dob": request.form.get('dob'),
            "gender": request.form.get('gender'),
            "nationality": request.form.get('nationality'),
            "address": request.form.get('address'),
            "contact_number": request.form.get('contactNumber'),
            "applied_university": request.form.get('appliedUniversity'),
            "applied_campus": request.form.get('appliedCampus'),
            "applied_program": request.form.get('appliedProgram'),
            "matric_board": request.form.get('matricBoard'),
            "matric_year": request.form.get('matricYear'),
            "matric_marks": request.form.get('matricMarks'),
            "matric_subjects": request.form.get('matricSubjects', '').split(','),
            "inter_board": request.form.get('interBoard'),
            "inter_year": request.form.get('interYear'),
            "inter_marks": request.form.get('interMarks'),
            "inter_subjects": request.form.get('interSubjects', '').split(','),
            "bachelor_uni": request.form.get('bachelorUni'),
            "bachelor_year": request.form.get('bachelorYear'),
            "bachelor_marks": request.form.get('bachelorMarks'),
            "bachelor_major": request.form.get('bachelorMajor', '').split(','),
            "master_uni": request.form.get('masterUni'),
            "master_year": request.form.get('masterYear'),
            "master_marks": request.form.get('masterMarks'),
            "master_major": request.form.get('masterMajor', '').split(','),
            "updated_at": datetime.now().isoformat()
        }
        
        # Update student profile
        result = students_collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"success": True, "message": "Profile updated successfully"})
        else:
            return jsonify({"success": False, "message": "No changes made to profile"})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/students/uploadFile', methods=['POST'])
def upload_student_file():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "message": "No file uploaded"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "message": "No selected file"}), 400
            
        student_id = request.form.get('studentId')
        file_type = request.form.get('fileType')
        
        if not student_id or not file_type:
            return jsonify({"success": False, "message": "Student ID and file type are required"}), 400
        
        # Create uploads directory if it doesn't exist
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        
        # Save file (in production, you'd want to save to cloud storage)
        filename = f"{student_id}_{file_type}_{secure_filename(file.filename)}"
        file.save(os.path.join('uploads', filename))
        
        # Update student document with file reference
        students_collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": {f"documents.{file_type}": filename}}
        )
        
        return jsonify({"success": True, "message": "File uploaded successfully"})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/api/students/profile/<student_id>', methods=['GET'])
def get_student_profile(student_id):
    try:
        student = students_collection.find_one({"_id": ObjectId(student_id)})
        if not student:
            return jsonify({"success": False, "message": "Student not found"}), 404
            
        # Convert ObjectId and format the response to match frontend expectations
        student['_id'] = str(student['_id'])
        
        # Remove sensitive fields
        if 'password' in student:
            del student['password']
        
        # Format the response to match what viewprofile.html expects
        response_data = {
            "success": True,
            "profile": {
                "fullName": student.get("full_name"),
                "dob": student.get("dob"),
                "gender": student.get("gender"),
                "nationality": student.get("nationality"),
                "address": student.get("address"),
                "contactNumber": student.get("contact_number"),
                "appliedUniversity": student.get("applied_university"),
                "appliedCampus": student.get("applied_campus"),
                "appliedProgram": student.get("applied_program"),
                "matricBoard": student.get("matric_board"),
                "matricYear": student.get("matric_year"),
                "matricMarks": student.get("matric_marks"),
                "matricSubjects": student.get("matric_subjects", []),
                "interBoard": student.get("inter_board"),
                "interYear": student.get("inter_year"),
                "interMarks": student.get("inter_marks"),
                "interSubjects": student.get("inter_subjects", []),
                "bachelorUni": student.get("bachelor_uni"),
                "bachelorYear": student.get("bachelor_year"),
                "bachelorMarks": student.get("bachelor_marks"),
                "bachelorMajor": student.get("bachelor_major", []),
                "masterUni": student.get("master_uni"),
                "masterYear": student.get("master_year"),
                "masterMarks": student.get("master_marks"),
                "masterMajor": student.get("master_major", []),
                "idDocumentPath": student.get("documents", {}).get("idDocument"),
                "matricTranscriptPath": student.get("documents", {}).get("matricTranscript"),
                "interTranscriptPath": student.get("documents", {}).get("interTranscript"),
                "bachelorTranscriptPath": student.get("documents", {}).get("bachelorTranscript"),
                "masterTranscriptPath": student.get("documents", {}).get("masterTranscript")
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
@app.route('/api/registered-students', methods=['GET'])
def get_registered_students():
    try:
        page = int(request.args.get('page', 1))
        per_page = 10
        search_query = request.args.get('search', '')
        
        query = {}
        if search_query:
            query['$or'] = [
                {'full_name': {'$regex': search_query, '$options': 'i'}},
                {'email': {'$regex': search_query, '$options': 'i'}},
                {'applied_program': {'$regex': search_query, '$options': 'i'}},
                {'applied_university': {'$regex': search_query, '$options': 'i'}},
                {'nationality': {'$regex': search_query, '$options': 'i'}}
            ]
        
        # Get total count and paginated results
        total_students = students_collection.count_documents(query)
        students = list(students_collection.find(query)
                       .skip((page - 1) * per_page)
                       .limit(per_page))
        
        # Convert ObjectId to string and format data for frontend
        formatted_students = []
        for student in students:
            student['_id'] = str(student['_id'])
            
            # Format subjects if they exist
            matric_subjects = student.get('matric_subjects', [])
            if isinstance(matric_subjects, list):
                matric_subjects = ', '.join(matric_subjects)
            
            inter_subjects = student.get('inter_subjects', [])
            if isinstance(inter_subjects, list):
                inter_subjects = ', '.join(inter_subjects)
                
            bachelor_major = student.get('bachelor_major', [])
            if isinstance(bachelor_major, list):
                bachelor_major = ', '.join(bachelor_major)
            
            master_major = student.get('master_major', [])
            if isinstance(master_major, list):
                master_major = ', '.join(master_major)
            
            formatted_students.append({
                'fullName': student.get('full_name', 'N/A'),
                'dob': student.get('dob', 'N/A'),
                'nationality': student.get('nationality', 'N/A'),
                'gender': student.get('gender', 'N/A'),
                'address': student.get('address', 'N/A'),
                'contactNumber': student.get('contact_number', 'N/A'),
                'appliedUniversity': student.get('applied_university', 'N/A'),
                'appliedCampus': student.get('applied_campus', 'N/A'),
                'appliedProgram': student.get('applied_program', 'N/A'),
                'matricBoard': student.get('matric_board', 'N/A'),
                'matricYear': student.get('matric_year', 'N/A'),
                'matricMarks': student.get('matric_marks', 'N/A'),
                'matricSubjects': matric_subjects,
                'interBoard': student.get('inter_board', 'N/A'),
                'interYear': student.get('inter_year', 'N/A'),
                'interMarks': student.get('inter_marks', 'N/A'),
                'interSubjects': inter_subjects,
                'bachelorUni': student.get('bachelor_uni', 'N/A'),
                'bachelorYear': student.get('bachelor_year', 'N/A'),
                'bachelorMarks': student.get('bachelor_marks', 'N/A'),
                'bachelorMajor': bachelor_major,
                'masterUni': student.get('master_uni', 'N/A'),
                'masterYear': student.get('master_year', 'N/A'),
                'masterMarks': student.get('master_marks', 'N/A'),
                'masterMajor': master_major,
                'idDocumentPath': student.get('documents', {}).get('idDocument', 'N/A'),
                'matricTranscriptPath': student.get('documents', {}).get('matricTranscript', 'N/A'),
                'interTranscriptPath': student.get('documents', {}).get('interTranscript', 'N/A'),
                'bachelorTranscriptPath': student.get('documents', {}).get('bachelorTranscript', 'N/A'),
                'masterTranscriptPath': student.get('documents', {}).get('masterTranscript', 'N/A')
            })
        
        return jsonify({
            'success': True,
            'students': formatted_students,
            'totalRecords': total_students,
            'currentPage': page,
            'perPage': per_page,
            'totalPages': math.ceil(total_students / per_page)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
# Campus Routes

@app.route('/api/universities/campuses', methods=['POST'])
def add_campus():
    try:
        data = request.json
        university_id = data.get('universityId')
        name = data.get('name')
        address = data.get('address')
        contact = data.get('contact')

        if not all([university_id, name, address, contact]):
            return jsonify({"error": "All fields are required"}), 400

        # Check if university exists
        universities_collection = db_admission_office["universities"]
        if not universities_collection.find_one({"_id": ObjectId(university_id)}):
            return jsonify({"error": "University not found"}), 404

        # Insert new campus
        campuses_collection = db_admission_office["campuses"]
        result = campuses_collection.insert_one({
            "universityId": university_id,
            "name": name,
            "address": address,
            "contact": contact,
            "createdAt": datetime.now().isoformat()
        })

        return jsonify({
            "message": "Campus added successfully",
            "campusId": str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/<university_id>/campuses', methods=['GET'])
def get_university_campuses(university_id):
    try:
        # Check if university exists
        universities_collection = db_admission_office["universities"]
        if not universities_collection.find_one({"_id": ObjectId(university_id)}):
            return jsonify({"error": "University not found"}), 404

        # Get campuses for university
        campuses_collection = db_admission_office["campuses"]
        campuses = list(campuses_collection.find({"universityId": university_id}))

        # Convert ObjectId to string
        for campus in campuses:
            campus["_id"] = str(campus["_id"])

        return jsonify(campuses)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/campuses/<campus_id>', methods=['GET'])
def get_campus(campus_id):
    try:
        campuses_collection = db_admission_office["campuses"]
        campus = campuses_collection.find_one({"_id": ObjectId(campus_id)})

        if not campus:
            return jsonify({"error": "Campus not found"}), 404

        campus["_id"] = str(campus["_id"])
        return jsonify(campus)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/campuses/<campus_id>', methods=['PUT'])
def update_campus(campus_id):
    try:
        data = request.json
        name = data.get('name')
        address = data.get('address')
        contact = data.get('contact')

        if not all([name, address, contact]):
            return jsonify({"error": "All fields are required"}), 400

        campuses_collection = db_admission_office["campuses"]
        result = campuses_collection.update_one(
            {"_id": ObjectId(campus_id)},
            {"$set": {
                "name": name,
                "address": address,
                "contact": contact,
                "updatedAt": datetime.now().isoformat()
            }}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Campus not found"}), 404

        return jsonify({"message": "Campus updated successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/campuses/<campus_id>', methods=['DELETE'])
def delete_campus(campus_id):
    try:
        campuses_collection = db_admission_office["campuses"]
        result = campuses_collection.delete_one({"_id": ObjectId(campus_id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Campus not found"}), 404

        return jsonify({"message": "Campus deleted successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Department Routes

@app.route('/api/universities/departments', methods=['POST'])
def add_department():
    try:
        data = request.json
        university_id = data.get('universityId')
        name = data.get('name')
        campus = data.get('campus')
        description = data.get('description', '')

        if not all([university_id, name, campus]):
            return jsonify({"error": "All required fields must be provided"}), 400

        # Check if university exists
        universities_collection = db_admission_office["universities"]
        if not universities_collection.find_one({"_id": ObjectId(university_id)}):
            return jsonify({"error": "University not found"}), 404

        # Insert new department
        departments_collection = db_admission_office["departments"]
        result = departments_collection.insert_one({
            "universityId": university_id,
            "name": name,
            "campus": campus,
            "description": description,
            "createdAt": datetime.now().isoformat()
        })

        return jsonify({
            "message": "Department added successfully",
            "departmentId": str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/<university_id>/departments', methods=['GET'])
def get_university_departments(university_id):
    try:
        # Check if university exists
        universities_collection = db_admission_office["universities"]
        if not universities_collection.find_one({"_id": ObjectId(university_id)}):
            return jsonify({"error": "University not found"}), 404

        # Get departments for university
        departments_collection = db_admission_office["departments"]
        departments = list(departments_collection.find({"universityId": university_id}))

        # Convert ObjectId to string
        for department in departments:
            department["_id"] = str(department["_id"])

        return jsonify(departments)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/departments/<department_id>', methods=['GET'])
def get_department(department_id):
    try:
        departments_collection = db_admission_office["departments"]
        department = departments_collection.find_one({"_id": ObjectId(department_id)})

        if not department:
            return jsonify({"error": "Department not found"}), 404

        department["_id"] = str(department["_id"])
        return jsonify(department)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/departments/<department_id>', methods=['PUT'])
def update_department(department_id):
    try:
        data = request.json
        name = data.get('name')
        campus = data.get('campus')
        description = data.get('description', '')

        if not all([name, campus]):
            return jsonify({"error": "All required fields must be provided"}), 400

        departments_collection = db_admission_office["departments"]
        result = departments_collection.update_one(
            {"_id": ObjectId(department_id)},
            {"$set": {
                "name": name,
                "campus": campus,
                "description": description,
                "updatedAt": datetime.now().isoformat()
            }}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Department not found"}), 404

        return jsonify({"message": "Department updated successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/departments/<department_id>', methods=['DELETE'])
def delete_department(department_id):
    try:
        departments_collection = db_admission_office["departments"]
        result = departments_collection.delete_one({"_id": ObjectId(department_id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Department not found"}), 404

        return jsonify({"message": "Department deleted successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Program Routes

@app.route('/api/universities/programs', methods=['POST'])
def add_program():
    try:
        data = request.json
        university_id = data.get('universityId')
        title = data.get('title')
        campus = data.get('campus')
        department = data.get('department')
        duration = data.get('duration')
        fees = data.get('fees')
        description = data.get('description', '')

        if not all([university_id, title, campus, department, duration, fees]):
            return jsonify({"error": "All required fields must be provided"}), 400

        # Check if university exists
        universities_collection = db_admission_office["universities"]
        if not universities_collection.find_one({"_id": ObjectId(university_id)}):
            return jsonify({"error": "University not found"}), 404

        # Insert new program
        programs_collection = db_admission_office["programs"]
        result = programs_collection.insert_one({
            "universityId": university_id,
            "title": title,
            "campus": campus,
            "department": department,
            "duration": duration,
            "fees": fees,
            "description": description,
            "createdAt": datetime.now().isoformat()
        })

        return jsonify({
            "message": "Program added successfully",
            "programId": str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/<university_id>/programs', methods=['GET'])
def get_university_programs(university_id):
    try:
        # Check if university exists
        universities_collection = db_admission_office["universities"]
        if not universities_collection.find_one({"_id": ObjectId(university_id)}):
            return jsonify({"error": "University not found"}), 404

        # Get programs for university
        programs_collection = db_admission_office["programs"]
        programs = list(programs_collection.find({"universityId": university_id}))

        # Convert ObjectId to string
        for program in programs:
            program["_id"] = str(program["_id"])

        return jsonify(programs)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/programs/<program_id>', methods=['GET'])
def get_program(program_id):
    try:
        programs_collection = db_admission_office["programs"]
        program = programs_collection.find_one({"_id": ObjectId(program_id)})

        if not program:
            return jsonify({"error": "Program not found"}), 404

        program["_id"] = str(program["_id"])
        return jsonify(program)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/programs/<program_id>', methods=['PUT'])
def update_program(program_id):
    try:
        data = request.json
        title = data.get('title')
        campus = data.get('campus')
        department = data.get('department')
        duration = data.get('duration')
        fees = data.get('fees')
        description = data.get('description', '')

        if not all([title, campus, department, duration, fees]):
            return jsonify({"error": "All required fields must be provided"}), 400

        programs_collection = db_admission_office["programs"]
        result = programs_collection.update_one(
            {"_id": ObjectId(program_id)},
            {"$set": {
                "title": title,
                "campus": campus,
                "department": department,
                "duration": duration,
                "fees": fees,
                "description": description,
                "updatedAt": datetime.now().isoformat()
            }}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Program not found"}), 404

        return jsonify({"message": "Program updated successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/programs/<program_id>', methods=['DELETE'])
def delete_program(program_id):
    try:
        programs_collection = db_admission_office["programs"]
        result = programs_collection.delete_one({"_id": ObjectId(program_id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Program not found"}), 404

        return jsonify({"message": "Program deleted successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# Faculty Routes

@app.route('/api/universities/faculty', methods=['POST'])
def add_faculty():
    try:
        data = request.json
        university_id = data.get('universityId')
        name = data.get('name')
        designation = data.get('designation')
        campus = data.get('campus')
        department = data.get('department')
        email = data.get('email')

        if not all([university_id, name, designation, campus, department, email]):
            return jsonify({"error": "All fields are required"}), 400

        # Check if university exists
        universities_collection = db_admission_office["universities"]
        if not universities_collection.find_one({"_id": ObjectId(university_id)}):
            return jsonify({"error": "University not found"}), 404

        # Insert new faculty member
        faculty_collection = db_admission_office["faculty"]
        result = faculty_collection.insert_one({
            "universityId": university_id,
            "name": name,
            "designation": designation,
            "campus": campus,
            "department": department,
            "email": email,
            "createdAt": datetime.now().isoformat()
        })

        return jsonify({
            "message": "Faculty member added successfully",
            "facultyId": str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/<university_id>/faculty', methods=['GET'])
def get_university_faculty(university_id):
    try:
        # Check if university exists
        universities_collection = db_admission_office["universities"]
        if not universities_collection.find_one({"_id": ObjectId(university_id)}):
            return jsonify({"error": "University not found"}), 404

        # Get faculty for university
        faculty_collection = db_admission_office["faculty"]
        faculty = list(faculty_collection.find({"universityId": university_id}))

        # Convert ObjectId to string
        for member in faculty:
            member["_id"] = str(member["_id"])

        return jsonify(faculty)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/faculty/<faculty_id>', methods=['GET'])
def get_faculty(faculty_id):
    try:
        faculty_collection = db_admission_office["faculty"]
        faculty = faculty_collection.find_one({"_id": ObjectId(faculty_id)})

        if not faculty:
            return jsonify({"error": "Faculty member not found"}), 404

        faculty["_id"] = str(faculty["_id"])
        return jsonify(faculty)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/faculty/<faculty_id>', methods=['PUT'])
def update_faculty(faculty_id):
    try:
        data = request.json
        name = data.get('name')
        designation = data.get('designation')
        campus = data.get('campus')
        department = data.get('department')
        email = data.get('email')

        if not all([name, designation, campus, department, email]):
            return jsonify({"error": "All fields are required"}), 400

        faculty_collection = db_admission_office["faculty"]
        result = faculty_collection.update_one(
            {"_id": ObjectId(faculty_id)},
            {"$set": {
                "name": name,
                "designation": designation,
                "campus": campus,
                "department": department,
                "email": email,
                "updatedAt": datetime.now().isoformat()
            }}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Faculty member not found"}), 404

        return jsonify({"message": "Faculty member updated successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/universities/faculty/<faculty_id>', methods=['DELETE'])
def delete_faculty(faculty_id):
    try:
        faculty_collection = db_admission_office["faculty"]
        result = faculty_collection.delete_one({"_id": ObjectId(faculty_id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Faculty member not found"}), 404

        return jsonify({"message": "Faculty member deleted successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    




def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    # Only open browser in development, not in production
    if os.environ.get('FLASK_ENV') != 'production' and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        threading.Timer(1.25, open_browser).start()
    
    # Use Render's provided port or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
