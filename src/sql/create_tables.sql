CREATE TABLE IF NOT EXISTS `cellar`.`cellar`(
     `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
     `wine_id` INT UNSIGNED,
     `storage_unit` INT UNSIGNED,
     `owner_id` INT UNSIGNED,
     `bottle_size_cl` INT UNSIGNED,
     `quantity` INT UNSIGNED,
     `drink_from` DATE,
     `drink_before` DATE,
     PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS `cellar`.`owners`(
     `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
     `name` VARCHAR(200),
     `username` VARCHAR(100) NOT NULL UNIQUE,
     `password` VARCHAR(100) NOT NULL,
     `scopes` VARCHAR(100),
     `is_admin` BOOL NOT NULL DEFAULT 0,
     `enabled` BOOL NOT NULL DEFAULT 1,
     PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS `cellar`.`storages`(
     `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
     `owner_id` INT UNSIGNED,
     `location` VARCHAR(200),
     `description` VARCHAR(2000),
     unique(`location`, `description`),
     PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS `cellar`.`ratings`(
     `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
     `rater_id` INT UNSIGNED,
     `wine_id` INT UNSIGNED,
     `rating` SMALLINT UNSIGNED,
     `drinking_date` DATE,
     `comments` VARCHAR(2000),
     PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS `cellar`.`wines`(
     `id` INT NOT NULL AUTO_INCREMENT,
     `name` VARCHAR(200),
     `vintage` SMALLINT UNSIGNED,
     `grapes` TEXT,
     `type` VARCHAR(20),
     `drink_from` DATE,
     `drink_before` DATE,
     `alcohol_vol_perc` DECIMAL(3, 1) UNSIGNED,
     `geographic_info` TEXT,
     `quality_signature` VARCHAR(200),
     unique(`name`, `vintage`),
     PRIMARY KEY (id)
);
