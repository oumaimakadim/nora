import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from passlib.hash import pbkdf2_sha256

# Database setup
conn = sqlite3.connect('data.db')
c = conn.cursor()

# Ensure necessary columns exist
def ensure_columns_exist():
    c.execute('PRAGMA table_info(form_data)')
    columns = [col[1] for col in c.fetchall()]
    required_columns = ['duration', 'device_type', 'created_by']
    for col in required_columns:
        if col not in columns:
            c.execute(f'ALTER TABLE form_data ADD COLUMN {col} TEXT')
    conn.commit()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)''')
conn.commit()

c.execute('''CREATE TABLE IF NOT EXISTS form_data (
    id INTEGER PRIMARY KEY, 
    name TEXT, 
    satisfaction TEXT, 
    problem TEXT, 
    device_type TEXT, 
    component TEXT, 
    voltage INTEGER, 
    intensity TEXT,
    duration INTEGER,
    created_by TEXT
)''')
conn.commit()

ensure_columns_exist()

# Authentication Functions
def create_account():
    st.subheader("Create New Account")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Create Account"):
        if password == confirm_password:
            hashed_password = pbkdf2_sha256.hash(password)
            try:
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
                st.success("Account created successfully!")
            except sqlite3.IntegrityError:
                st.error("Username already exists. Please choose a different one.")
        else:
            st.error("Passwords do not match.")

def login():
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        if user and pbkdf2_sha256.verify(password, user[2]):  # Check hashed password
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Logged in as {}".format(username))
        else:
            st.error("Incorrect username or password.")

# Main App Logic
def save_data(name, satisfaction, problem, device_type, component, voltage, intensity, duration):
    created_by = st.session_state.username  # Get logged-in username
    c.execute('INSERT INTO form_data (name, satisfaction, problem, device_type, component, voltage, intensity, duration, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
              (name, satisfaction, problem, device_type, component, voltage, intensity, int(duration), created_by))
    conn.commit()

    data = get_data()
    st.write("### Data after insertion")
    st.dataframe(pd.DataFrame(data, columns=["ID", "Name", "Satisfaction", "Problem", "Device Type", "Component", "Voltage", "Intensity", "Duration", "Created By"]))

def get_data():
    c.execute('SELECT * FROM form_data')
    data = c.fetchall()
    return data

def clear_data():
    c.execute('DELETE FROM form_data')
    conn.commit()
    st.success("All data cleared!")

def inject_css():
    st.markdown("""
        <style>
        body {
            background-color: #f0f2f6;
            font-family: 'Arial', sans-serif;
        }
        .container {
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        h2 {
            color: #333;
            margin-bottom: 20px;
        }
        .stButton>button {
            width: 100%;
            padding: 10px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .stButton>button:hover {
            background: #45a049;
        }
        input {
            width: 100%;
            padding: 10px;
            margin: 10px 0 20px 0;
            display: inline-block;
            border: 1px solid #ccc;
            border-radius: 5px;
            box-sizing: border-box;
        }
        </style>
    """, unsafe_allow_html=True)

def form():
    st.markdown('<div class="container"><h2>Fill the Form</h2></div>', unsafe_allow_html=True)
    name = st.text_input("Name")
    satisfaction = st.text_input("Satisfaction")
    problem = st.text_input("Problem")
    device_type = st.selectbox("Device Type", ["disjoncteur", "relais"])

    if device_type == "disjoncteur":
        components = [f"disjoncteur_component_{i}" for i in range(1, 11)]
    else:
        components = [f"relais_component_{i}" for i in range(1, 11)]
    
    component = st.selectbox("Component", components)
    voltage = st.number_input("Voltage")
    intensity = st.text_input("Intensity")
    duration = st.number_input("Duration of the problem (hours)", min_value=0)

    if st.button("Save"):
        save_data(name, satisfaction, problem, device_type, component, voltage, intensity, duration)
        st.success("Data Saved")

def view_data():
    st.markdown('<div class="container"><h2>View Data</h2></div>', unsafe_allow_html=True)
    data = get_data()
    if data:
        df = pd.DataFrame(data, columns=["ID", "Name", "Satisfaction", "Problem", "Device Type", "Component", "Voltage", "Intensity", "Duration", "Created By"])
        st.dataframe(df)

        selected_user = st.selectbox("Filter by User:", ["All"] + list(df['Created By'].unique()))
        if selected_user != "All":
            df = df[df['Created By'] == selected_user]
            st.dataframe(df)
    else:
        st.write("No data available")

def analysis():
    st.markdown('<div class="container"><h2>Analysis and Prediction</h2></div>', unsafe_allow_html=True)
    data = get_data()
    
    if data:
        df = pd.DataFrame(data, columns=["ID", "Name", "Satisfaction", "Problem", "Device Type", "Component", "Voltage", "Intensity", "Duration", "Created By"])

        df['Device Type'] = df['Device Type'].astype(str).str.lower().str.strip()
        df['Component'] = df['Component'].astype(str).str.lower().str.strip()
        
        st.write("### Raw Data")
        st.dataframe(df)
        
        df = df[df['Component'].str.startswith('disjoncteur') | df['Component'].str.startswith('relais')]
        
        df['Duration'] = pd.to_numeric(df['Duration'], errors='coerce')
        
        df = df.dropna(subset=['Duration'])
        
        st.markdown("### Number of problems per component")
        component_counts = df['Component'].value_counts()
        if not component_counts.empty:
            st.bar_chart(component_counts)
        else:
            st.write("No problems per component found.")
        
        st.markdown("### Number of problems per device type")
        device_type_counts = df['Device Type'].value_counts()
        if not device_type_counts.empty:
            st.bar_chart(device_type_counts)
        else:
            st.write("No problems per device type found.")
        
        threshold = 5  # Example threshold
        avg_duration_per_component = df.groupby('Component')['Duration'].mean()
        st.markdown("### Average duration of problems per component")
        if not avg_duration_per_component.empty:
            st.write(avg_duration_per_component)
        
            fig, ax = plt.subplots()
            avg_duration_per_component.plot(kind='bar', ax=ax)
            ax.set_ylabel("Average Duration (hours)")
            st.pyplot(fig)
        
            st.markdown("### Components that should be changed")
            for component, avg_duration in avg_duration_per_component.items():
                if avg_duration > threshold:
                    st.write(f"- {component} (Average duration: {avg_duration} hours)")
        else:
            st.write("No average duration data available.")
    else:
        st.write("No data available for analysis")

def authenticate():
    password = st.sidebar.text_input("Password", type="password")
    if password == "your_secure_password":  # Replace with your actual password
        st.sidebar.success("Logged in!")
        return True
    else:
        st.sidebar.error("Incorrect password!")
        return False

# Main
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    st.sidebar.header("Menu")
    page = st.sidebar.selectbox("Select a page", ["Form", "View Data", "Analysis", "Clear Data", "Logout"])
    
    if page == "Form":
        inject_css()
        form()
    elif page == "View Data":
        inject_css()
        view_data()
    elif page == "Analysis":
        inject_css()
        analysis()
    elif page == "Clear Data":
        clear_data()
    elif page == "Logout":
        st.session_state.logged_in = False
        st.experimental_rerun()
else:
    choice = st.sidebar.selectbox("Select an option", ["Login", "Create Account"])
    if choice == "Login":
        login()
    elif choice == "Create Account":
        create_account()
