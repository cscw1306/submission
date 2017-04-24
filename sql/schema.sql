CREATE DATABASE IF NOT EXISTS sloc_analyzer;

use sloc_analyzer

CREATE TABLE IF NOT EXISTS repos
(
    repo_id int not null AUTO_INCREMENT,
    name varchar(500),
    sample varchar(100),
    PRIMARY KEY (repo_id)
);

CREATE TABLE IF NOT EXISTS commits
(
    commit_id int not null AUTO_INCREMENT,
    repo_id int not null,
    commit_hash varchar(50) not null,
    commit_date DATETIME not null,
    parent_commit_1 varchar(50),
    parent_commit_2 varchar(50),
    physical_lines int not null,
    source_lines int not null,
    comment_lines int not null,
    single_line_comment int not null,
    block_comment int not null,
    mixed_comment int not null,
    empty int not null,
    todo_lines int not null,
    regex_lines int not null,
    PRIMARY KEY(commit_id),
    FOREIGN KEY(repo_id) REFERENCES repos(repo_id)
);

ALTER TABLE commits
    ADD COLUMN IF NOT EXISTS author VARCHAR(50);

