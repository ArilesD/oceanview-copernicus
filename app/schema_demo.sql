CREATE TABLE IF NOT EXISTS variable (
    ID_Variable INT PRIMARY KEY,
    Indicateurs VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS localisation (
    ID_Localisation INT PRIMARY KEY,
    Latitude DOUBLE NOT NULL,
    Longitude DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS mesure (
    ID_Mesure INT PRIMARY KEY,
    ID_Variable INT NOT NULL,
    ID_Localisation INT NOT NULL,
    Jour_Opti DATE NOT NULL,
    Valeur DOUBLE NOT NULL,
    INDEX idx_mesure_variable_jour (ID_Variable, Jour_Opti),
    FOREIGN KEY (ID_Variable) REFERENCES variable (ID_Variable),
    FOREIGN KEY (ID_Localisation) REFERENCES localisation (ID_Localisation)
);

CREATE TABLE IF NOT EXISTS utilisateur (
    ID_Utilisateur INT AUTO_INCREMENT PRIMARY KEY,
    Nom_Utilisateur VARCHAR(80) NOT NULL,
    Email VARCHAR(254) NOT NULL UNIQUE,
    Role VARCHAR(20) NOT NULL DEFAULT 'User',
    Mot_de_Passe VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS historique (
    ID_Log INT AUTO_INCREMENT PRIMARY KEY,
    Action VARCHAR(80) NOT NULL,
    Table_Concernee VARCHAR(80) NOT NULL,
    Detail VARCHAR(255) NOT NULL,
    ID_Utilisateur INT NOT NULL,
    Date_Action DATETIME NOT NULL,
    FOREIGN KEY (ID_Utilisateur) REFERENCES utilisateur (ID_Utilisateur) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS favoris_perso (
    ID_Favori INT AUTO_INCREMENT PRIMARY KEY,
    ID_Utilisateur INT NOT NULL,
    Nom_Zone VARCHAR(40) NOT NULL,
    Indicateur VARCHAR(40) NOT NULL,
    Date_Debut DATE NOT NULL,
    Date_Fin DATE NOT NULL,
    UNIQUE (ID_Utilisateur, Nom_Zone, Indicateur, Date_Debut, Date_Fin),
    FOREIGN KEY (ID_Utilisateur) REFERENCES utilisateur (ID_Utilisateur) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS avis (
    ID_Avis INT AUTO_INCREMENT PRIMARY KEY,
    ID_Utilisateur INT NOT NULL,
    Note INT NOT NULL,
    Message TEXT NOT NULL,
    Date_Avis DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ID_Utilisateur) REFERENCES utilisateur (ID_Utilisateur) ON DELETE CASCADE
);
