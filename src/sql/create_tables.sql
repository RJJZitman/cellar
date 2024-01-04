CREATE TABLE IF NOT EXISTS cellar.owners(
     id INT NOT NULL AUTO_INCREMENT,
     name VARCHAR(200),
     username VARCHAR(100) NOT NULL UNIQUE,
     password VARCHAR(100) NOT NULL,
     scopes VARCHAR(100),
     is_admin BOOL NOT NULL DEFAULT 0,
     enabled BOOL NOT NULL DEFAULT 1,
     PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS cellar.storages(
     id INT NOT NULL AUTO_INCREMENT,
     location VARCHAR(200),
     description VARCHAR(2000),
     PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS cellar.ratings(
     id INT NOT NULL AUTO_INCREMENT,
     rater_id INT,
     wine_id INT,
     rating SMALLINT,
     drinking_date DATE,
     comments VARCHAR(2000),
     PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS cellar.wines(
     id INT NOT NULL AUTO_INCREMENT,
     name VARCHAR(200),
     vintage SMALLINT,
     grapes TEXT,
     type VARCHAR(20),
     drink_from DATE,
     drink_before DATE,
     alcohol_col_perc SMALLINT,
     geographic_info TEXT,
     quality_signature VARCHAR(200),
     PRIMARY KEY (id)
);
