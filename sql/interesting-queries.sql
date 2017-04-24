/*
 * This query will return the repository todos/1000 sloc
 * we'll use this as the base for subsequent queries.
 */
SELECT STD((C.regex_lines / C.physical_lines) * 1000) as todo_lines, R.name, R.sample FROM
        repos R
        INNER JOIN commits C ON R.repo_id = C.repo_id
        GROUP BY R.name, R.sample;

/* 
 * This query will prove the hypothesis which states
 * that Scientific repositories will have a higher
 * amount of TODO's per thousand physical lines.
 */ 
SELECT sample, AVG(todo_lines)
    FROM (
        SELECT AVG((C.regex_lines / C.physical_lines) * 1000) as todo_lines, R.name, R.sample FROM
        repos R
        INNER JOIN commits C ON R.repo_id = C.repo_id
        GROUP BY R.name, R.sample
    ) AS T
    GROUP BY sample;

SELECT sample, STD(todo_lines)
    FROM (
        SELECT AVG((C.regex_lines / C.physical_lines) * 1000) as todo_lines, R.name, R.sample FROM
        repos R
        INNER JOIN commits C ON R.repo_id = C.repo_id
        GROUP BY R.name, R.sample
    ) AS T
    GROUP BY sample;

/* 
 * This query will prove the hypothesis which states
 * that Scientific repositories will have a higher
 * amount of TODO's per thousand **source** lines.
 */ 
SELECT sample, name, AVG(todo_lines)
    FROM (
        SELECT AVG((C.regex_lines / C.source_lines) * 1000) as todo_lines, R.name, R.sample FROM
        repos R
        INNER JOIN commits C ON R.repo_id = C.repo_id
        GROUP BY R.name, R.sample
    ) AS T
    GROUP BY sample, name;

/* 
 * This query breaks it down by year.
 */ 
SELECT T.sample, T.commit_year, AVG(todo_lines)
    FROM (
        SELECT AVG((C.regex_lines / C.physical_lines) * 1000) as todo_lines, R.name, R.sample, YEAR(C.commit_date) as commit_year FROM
        repos R
        INNER JOIN commits C ON R.repo_id = C.repo_id
        GROUP BY R.name, R.sample, YEAR(C.commit_date)
    ) AS T
    GROUP BY T.commit_year, T.sample;
/* 
 * This query breaks it down by month and year.
 */ 
SELECT T.commit_year, T.commit_month, T.sample, T.name, AVG(todo_lines)
    FROM (
        SELECT AVG((C.regex_lines / C.physical_lines) * 1000) as todo_lines, R.name, R.sample, YEAR(C.commit_date) as commit_year, MONTH(C.commit_date) as commit_month FROM
        repos R
        INNER JOIN commits C ON R.repo_id = C.repo_id
        GROUP BY R.name, R.sample, YEAR(C.commit_date), MONTH(C.commit_date)
    ) AS T
    GROUP BY T.commit_year, T.commit_month, T.sample, T.name
    ORDER BY commit_year, commit_month, T.sample, T.name;


SELECT T.commit_year, T.commit_month, T.sample, AVG(comment_lines)
    FROM (
        SELECT AVG((C.comment_lines / C.physical_lines) * 1000) as comment_lines, R.name, R.sample, YEAR(C.commit_date) as commit_year, MONTH(C.commit_date) as commit_month FROM
        repos R
        INNER JOIN commits C ON R.repo_id = C.repo_id
        GROUP BY R.name, R.sample, YEAR(C.commit_date), MONTH(C.commit_date)
    ) AS T
    GROUP BY T.commit_year, T.commit_month, T.sample
    ORDER BY commit_year, commit_month, sample;

/*
+---------------------+-------------+------+-----+---------+----------------+
| Field               | Type        | Null | Key | Default | Extra          |
+---------------------+-------------+------+-----+---------+----------------+
| commit_id           | int(11)     | NO   | PRI | NULL    | auto_increment |
| repo_id             | int(11)     | NO   | MUL | NULL    |                |
| commit_hash         | varchar(50) | NO   |     | NULL    |                |
| commit_date         | datetime    | NO   |     | NULL    |                |
| parent_commit_1     | varchar(50) | YES  |     | NULL    |                |
| parent_commit_2     | varchar(50) | YES  |     | NULL    |                |
| physical_lines      | int(11)     | NO   |     | NULL    |                |
| source_lines        | int(11)     | NO   |     | NULL    |                |
| comment_lines       | int(11)     | NO   |     | NULL    |                |
| single_line_comment | int(11)     | NO   |     | NULL    |                |
| block_comment       | int(11)     | NO   |     | NULL    |                |
| mixed_comment       | int(11)     | NO   |     | NULL    |                |
| empty               | int(11)     | NO   |     | NULL    |                |
| todo_lines          | int(11)     | NO   |     | NULL    |                |
| regex_lines         | int(11)     | NO   |     | NULL    |                |
+---------------------+-------------+------+-----+---------+----------------+
*/

CREATE TABLE diffs(
    commit_id INT NOT NULL,
    parent_commit_id INT NOT NULL,
    physical_source INT,
    source_lines INT,
    comment INT,
    single_line_comment INT,
    block_comment INT,
    mixed_comment INT,
    empty INT,
    todo_lines INT,
    regex_lines INT,
    PRIMARY KEY(commit_id, parent_commit_id)
);

INSERT INTO diffs
SELECT C1.commit_id as commit_id, C2.commit_id as parent_commit_id, (C1.physical_lines - C2.physical_lines) as physical_source,
    (C1.source_lines - C2.source_lines) as source_lines,
    (C1.comment_lines - C2.comment_lines) as comment, (C1.single_line_comment - C2.single_line_comment) as single_line_comment,
    (C1.block_comment - C2.block_comment) as block_comment, (C1.mixed_comment - C2.mixed_comment) as mixed_comment, (C1.empty - C2.empty) as empty,
    (C1.todo_lines - C2.todo_lines) as todo_lines, (C1.regex_lines - C2.regex_lines) as regex_lines
     FROM commits C1
    INNER JOIN commits C2 ON C1.commit_hash = C2.parent_commit_1;

/*
Sees which authors are committing satd to github.
*/
SELECT SUM(todo_lines), author, repository FROM
    (
        SELECT (C2.todo_lines - C1.todo_lines) as todo_lines, C2.author as author, R.name as repository FROM commits C1
        INNER JOIN commits C2 ON C1.commit_hash = C2.parent_commit_1
        INNER JOIN repos R ON C1.repo_id = R.repo_id
    ) AS T
    WHERE author IS NOT NULL
    GROUP BY author, repository
    HAVING SUM(todo_lines) <> 0
    ORDER BY SUM(todo_lines) DESC;

SELECT AVG(todo) FROM (
SELECT SUM(todo_lines) as todo, author FROM
    (
        SELECT (C2.todo_lines - C1.todo_lines) as todo_lines, C2.author as author, R.name as repository FROM commits C1
        INNER JOIN commits C2 ON C1.commit_hash = C2.parent_commit_1 AND C1.repo_id = C2.repo_id
        INNER JOIN repos R ON C1.repo_id = R.repo_id
    ) AS T
    WHERE author IS NOT NULL
    GROUP BY author
    ORDER BY SUM(todo_lines) DESC
) AS T

