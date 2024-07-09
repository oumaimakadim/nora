import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px  
from passlib.hash import pbkdf2_sha256
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from streamlit_chat import message
import google.generativeai as palm
import pickle

# Configure Generative AI
API_KEY = 'AIzaSyBuc4pLvEoBKCDPoaUD_BPk7LchMAfvhXg'
palm.configure(api_key=API_KEY)

# Connect to SQLite database
conn = sqlite3.connect('data.db')
c = conn.cursor()

# Ensure necessary columns exist
def ensure_columns_exist():
    c.execute('PRAGMA table_info(form_data)')
    columns = [col[1] for col in c.fetchall()]
    required_columns = ['duration', 'device_type', 'created_by', 'date_panne', 'date_installation', 'duree_utilisation', 'duree_panne']
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
    date_panne TEXT,
    date_installation TEXT,
    duree_utilisation INTEGER,
    duree_panne INTEGER,
    created_by TEXT
)''')
conn.commit()

ensure_columns_exist()

# Authentication Functions
def create_account():
    st.markdown('<div class="container"><h2>Create Account</h2></div>', unsafe_allow_html=True)
    username = st.text_input("Username", key="create_username")
    password = st.text_input("Password", type="password", key="create_password")
    if st.button("Create Account", key="create_button"):
        if username and password:
            hashed_password = pbkdf2_sha256.hash(password)
            try:
                c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
                conn.commit()
                st.success("Account created successfully!")
            except sqlite3.IntegrityError:
                st.error("Username already taken. Please choose another username.")
        else:
            st.error("Please fill out all fields.")

def login():
    st.markdown('<div class="container"><h2>Login</h2></div>', unsafe_allow_html=True)
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", key="login_button"):
        if username and password:
            c.execute('SELECT password FROM users WHERE username = ?', (username,))
            result = c.fetchone()
            if result and pbkdf2_sha256.verify(password, result[0]):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login successful!")
            else:
                st.error("Invalid username or password.")
        else:
            st.error("Please fill out all fields.")

# Form for data entry
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

    date_panne = st.date_input("Date de panne")
    date_installation = st.date_input("Date d'installation du composant")
    duree_utilisation = st.number_input("Durée d'utilisation du composant (jours)", min_value=0)
    duree_panne = st.number_input("Durée de panne (minutes)", min_value=0)

    if st.button("Save"):
        save_data(name, satisfaction, problem, device_type, component, voltage, intensity, duration, date_panne, date_installation, duree_utilisation, duree_panne)
        st.success("Data Saved")

# Function to save data to the database
def save_data(name, satisfaction, problem, device_type, component, voltage, intensity, duration, date_panne, date_installation, duree_utilisation, duree_panne):
    created_by = st.session_state.username
    duration = int(duration)
    duree_utilisation = int(duree_utilisation)
    duree_panne = int(duree_panne)
    
    c.execute('''INSERT INTO form_data
                 (name, satisfaction, problem, device_type, component, voltage, intensity, duration, date_panne, date_installation, duree_utilisation, duree_panne, created_by) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
              (name, satisfaction, problem, device_type, component, voltage, intensity, duration, date_panne, date_installation, duree_utilisation, duree_panne, created_by))
    conn.commit()

# Function to get data from the database
def get_data():
    c.execute('SELECT * FROM form_data')
    return c.fetchall()

# View data
def view_data():
    st.markdown('<div class="container"><h2>View Data</h2></div>', unsafe_allow_html=True)
    data = get_data()
    if data:
        df = pd.DataFrame(data, columns=["ID", "Name", "Satisfaction", "Problem", "Device Type", "Component", "Voltage", "Intensity", "Duration", "Date de Panne", "Date d'Installation", "Durée d'Utilisation", "Durée de Panne", "Created By"])
        st.dataframe(df)

        selected_user = st.selectbox("Filter by User:", ["All"] + list(df['Created By'].unique()))
        if selected_user != "All":
            df = df[df['Created By'] == selected_user]
            st.dataframe(df)
    else:
        st.write("No data available")

# Data analysis
def analysis():
    st.markdown('<div class="container"><h2>Analysis and Prediction</h2></div>', unsafe_allow_html=True)
    data = get_data()
    if data:
        df = pd.DataFrame(data, columns=["ID", "Name", "Satisfaction", "Problem", "Device Type", "Component", "Voltage", "Intensity", "Duration", "Date de Panne", "Date d'Installation", "Durée d'Utilisation", "Durée de Panne", "Created By"])
        
        # Plotting number of problems by user
        st.markdown('<div class="container"><h3>Number of Problems by User</h3></div>', unsafe_allow_html=True)
        fig = px.bar(df, x='Created By', y='Problem', color='Created By', title="Number of Problems by User", labels={'Problem':'Number of Problems'})
        st.plotly_chart(fig)
        
        # Plotting number of breakdowns by component and duration
        st.markdown('<div class="container"><h3>Number of Breakdowns by Component and Duration</h3></div>', unsafe_allow_html=True)
        fig = px.bar(df, x='Component', y='Duration', color='Component', title="Number of Breakdowns by Component and Duration", labels={'Duration':'Duration of Breakdowns (hours)'})
        st.plotly_chart(fig)
        
        # Plotting number of breakdowns by date
        st.markdown('<div class="container"><h3>Number of Breakdowns by Date</h3></div>', unsafe_allow_html=True)
        fig = px.line(df, x='Date de Panne', y='ID', title="Number of Breakdowns by Date", labels={'ID':'Number of Breakdowns'})
        st.plotly_chart(fig)
        
        # Prepare data for prediction
        df['Date d\'Installation'] = pd.to_datetime(df['Date d\'Installation'])
        df['Date de Panne'] = pd.to_datetime(df['Date de Panne'])
        df['days_until_failure'] = (df['Date de Panne'] - df['Date d\'Installation']).dt.days
        X = df[['days_until_failure']]
        y = df['Duration']

        # Splitting data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Building a machine learning model
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('regressor', LogisticRegression())
        ])
        model.fit(X_train, y_train)
        accuracy = model.score(X_test, y_test)

        # Displaying prediction accuracy
        st.markdown(f'<div class="container"><h3>Model Accuracy: {accuracy:.2f}</h3></div>', unsafe_allow_html=True)

    else:
        st.write("No data available for analysis")

# Logout function
def logout():
    st.session_state.logged_in = False
    st.session_state.username = None

# Main function
def main():
    st.markdown('<style>.container { padding: 20px; }</style>', unsafe_allow_html=True)
    st.markdown('<style>body { background-color: #ffffff; }</style>', unsafe_allow_html=True)
    
    st.title("Welcome to the Device Analysis and Prediction Platform")
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        create_account()
        login()
    else:
        st.markdown(f"Logged in as: {st.session_state.username}")
        form()
        view_data()
        analysis()
        logout()

if __name__ == '__main__':
    main()
