--- Moduł pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;

---Tabela ID zawierająca pojedynczą kolumnę zapewniającą unikalność identyfikatorów
CREATE TABLE ID(id numeric PRIMARY KEY);

---Tabela project(id, authority, creationtime)
CREATE TABLE project(id numeric PRIMARY KEY, authority numeric NOT NULL, creationTime timestamp);

---Dodanie więzu klucza obcego pomiędzy authority a tabelą ID
ALTER TABLE project ADD CONSTRAINT foreign_key_authority_id FOREIGN KEY (authority) REFERENCES ID(id) ;

---Dodanie więzu klucza obcego pomiędzy project id a tabelą ID
ALTER TABLE project ADD CONSTRAINT foreign_key_project_id FOREIGN KEY (id) REFERENCES ID(id) ;

---Nowa dziedzina, dopuszczalne wartości to 'p' (protest) oraz 's' (support)
CREATE DOMAIN action_type_domain AS char DEFAULT 'p' CHECK (VALUE IN ('s', 'p')) NOT NULL;

---Tabela actions(id, memberId, projectId, action, time), action to 's' lub 'p'
CREATE TABLE actions(id numeric PRIMARY KEY, memberId numeric, projectId numeric, action action_type_domain, time timestamp);


---Dodanie więzu klucza obcego pomiędzy action id a tabelą ID
ALTER TABLE actions ADD CONSTRAINT foreign_key_actions_id FOREIGN KEY (id) REFERENCES ID(id) ;

---Tabela members(id, password, leader, lastactivity, upvotes, downvotes), ostatnie dwie kolumny dotyczą głosów zliczanych przez funkcję trolls
CREATE TABLE members(id numeric PRIMARY KEY, cryptpwd text, leader bool DEFAULT false, lastActivity timestamp, upvotes int DEFAULT 0, downvotes int DEFAULT 0);


---Dodanie więzu klucza obcego pomiędzy memberid a tabelą ID
ALTER TABLE members ADD CONSTRAINT foreign_key_member_id FOREIGN KEY (id) REFERENCES ID(id) ;


---Dziedzina do głosowania, dopuszczalne wartości 'u' (upvote), 'd' (downvote)
CREATE DOMAIN vote_domain AS char DEFAULT 'd'  CHECK (VALUE IN ('u', 'd')) NOT NULL;

---Tabela votes(actionid,  memberid, vote, time), vote przyjmuje wartości z dziedziny powyżej
CREATE TABLE votes(actionId numeric NOT NULL, memberId numeric NOT NULL, vote vote_domain, time timestamp);

---Więzy klucza głównego tabeli votes (dwie kolumny)
ALTER TABLE  votes ADD PRIMARY KEY (actionId, memberId);


---Dodanie więzu klucza obcego pomiędzy memberid a tabelą members
ALTER TABLE votes ADD CONSTRAINT foreign_key_votes_member FOREIGN KEY (memberid) REFERENCES members(id) ;

---Dodanie więzu klucza obcego pomiędzy  actionid a tabelą actions
ALTER TABLE votes ADD CONSTRAINT foreign_key_votes_action FOREIGN KEY (actionid) REFERENCES actions(id) ;


---Wyzwalac dodający nowe krotki do tabeli ID dla nowych wartości members.id, actions.id, project.id, project.authority
CREATE FUNCTION id_trigger() RETURNS TRIGGER AS $X$ BEGIN
IF NOT EXISTS (SELECT * FROM ID WHERE id=NEW.id) THEN InSERT INTO id VALUES (NEW.id); ELSE RETURN NULL; END IF; RETURN NEW; END $X$ LANGUAGE plpgsql;

---
CREATE TRIGGER  on_insert_to_members BEFORE INSERT ON members FOR EACH ROW EXECUTE PROCEDURE id_trigger();

CREATE TRIGGER  on_insert_to_projects BEFORE INSERT ON project FOR EACH ROW EXECUTE PROCEDURE id_trigger();

CREATE TRIGGER  on_insert_to_actions  BEFORE INSERT ON actions FOR EACH ROW EXECUTE PROCEDURE id_trigger();


---Wyzwalac dodający nowe krotki do tabeli ID dla nowych wartości project.authority
CREATE FUNCTION id_trigger_authority() RETURNS TRIGGER AS $X$ BEGIN 
IF NOT EXISTS (SELECT * FROM ID WHERE id=NEW.authority) THEN INSERT INTO id VALUES (NEW.authority); ELSE RETURN NULL; END IF; RETURN NEW; END $X$ LANGUAGE plpgsql;

CREATE TRIGGER  on_insert_to_authority BEFORE INSERT ON project FOR EACH ROW EXECUTE PROCEDURE id_trigger_authority();


---Wyzwalacz uaktualniający upvotes i downvotes w tabeli members po każdym głosowaniu
 CREATE FUNCTION count_votes() RETURNS TRIGGER AS $X$ DECLARE memid numeric; BEGIN SELECT actions.memberid INTO memid FROM actions WHERE actions.id=NEW.actionid; IF ( NEW.vote='u') THEN UPDATE members SET upvotes=upvotes+1 WHERE id=memid; ELSE UPDATE members SET downvotes=downvotes+1 WHERE id=memid; END IF; RETURN NEW; END $X$ LANGUAGE plpgsql;


CREATE TRIGGER count_votes_trigger AFTER INSERT ON votes FOR EACH ROW EXECUTE PROCEDURE count_votes();

---funkcja uaktualniająca ostatnią aktywność członków partii
CREATE FUNCTION last_activity() RETURNS TRIGGER AS $X$ BEGIN UPDATE members SET lastactivity=NEW.time WHERE id=NEW.memberid; RETURN NEW; END $X$ LANGUAGE plpgsql;

CREATE TRIGGER votes_activity_trigger AFTER INSERT ON votes  FOR EACH ROW EXECUTE PROCEDURE last_activity();


CREATE TRIGGER action_activity_trigger AFTER INSERT ON actions  FOR EACH ROW EXECUTE PROCEDURE last_activity();


---Funkcja sprawdzająca, czy dany członek jest wciąż aktywny
CREATE FUNCTION active(timestamp, timestamp) RETURNS boolean AS $X$  SELECT  DATE_PART('day',$2-$1) < 366  $X$ LANGUAGE SQL;


---Pomocnicza funkcja konwertująca typ akcji na wartości "support" oraz "protest"
CREATE FUNCTION action_type(action_type_domain) RETURNS varchar(7) AS $X$ BEGIN IF ($1='s') THEN RETURN 'support'::varchar(7); ELSE RETURN 'protest'::varchar(7); END IF; END  $X$ LANGUAGE plpgsql;


---Pomocnicza funkcja konwertująca unix timestamp do timestamp without timezone
CREATE FUNCTION timestamp_cast(int) RETURNS timestamp AS $X$
SELECT timestamp 'epoch' + $1 * INTERVAL '1 second'; $X$ LANGUAGE SQL;

---Nowy użytkownik app z nowymi uprawnieniami
CREATE USER app WITH ENCRYPTED PASSWORD 'md596d1b2d8ca22e9afe63b1fc7bb10b9de';
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM app;
GRANT SELECT, UPDATE, INSERT ON ALL TABLES IN SCHEMA public TO app;
GRANT EXECUTE ON FUNCTION crypt(text, text) TO app;
ALTER USER app LOGIN ;


 
 
 
 
 
