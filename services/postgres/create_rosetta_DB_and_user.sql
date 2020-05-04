CREATE DATABASE rosetta;
CREATE USER rosetta_master WITH PASSWORD '949fa84a';
ALTER USER rosetta_master CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE rosetta to rosetta_master;
\c rosetta
GRANT CREATE ON SCHEMA PUBLIC TO rosetta_master;
