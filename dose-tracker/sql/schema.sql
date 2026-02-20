PRAGMA foreign_keys = ON;

CREATE TABLE patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT
    firstName VARCHAR(20) NOT NULL
    lastName VARCHAR(20) NOT NULL
    regNum INTEGER NOT NULL
    age INTEGER NOT NULL
    height REAL NOT NULL
    weight REAL NOT NULL
    startDate DATETIME NOT NULL
    hospital VARCHAR(20) NOT NULL
    timestamp DATETIME DEFAULT(CURRENT_TIMESTAMP)

    FOREIGN KEY (patient_id) REFERENCES users(patient_id) 
        ON DELETE CASCADE
        ON UPDATE CASCADE
)

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT
    firstName VARCHAR(20) NOT NULL
    lastName VARCHAR(20) NOT NULL
    patient_id INTEGER NOT NULL
)