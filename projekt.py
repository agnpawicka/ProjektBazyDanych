#!/usr/bin/python

import psycopg2
import json
import sys

conn = None
params = None
cur = None


# Create connection with database
def open_connection(database, login, passwd):
    global params, conn, cur
    try:
        conn = psycopg2.connect(host="localhost", database=database, user=login, password=passwd)
        conn.set_session(autocommit=True)
        cur = conn.cursor()
        if login == "init":
            file = open("tworzenieTabel.sql", 'r')
            sql = " ".join(file.readlines())
            cur.execute(sql)
            print(json.dumps({"status": "OK"}))
        else:
            print(json.dumps({"status": "OK"}))
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)


# Close connection with database
def close_connection():
    cur.close()
    if conn is not None:
        conn.close()


# Check if member with specified id is a leader
def is_leader(id, passwd):
    global cur
    try:
        cur.execute(
            '''SELECT * FROM members WHERE id=%s::numeric AND cryptpwd=crypt(%s::text, cryptpwd) AND leader=%s::boolean;''',
            (id, passwd, True))
        row = cur.fetchone()

        if row is not None:
            return {"status": "OK"}
        return {"status": "there is no leader with given login and password"}
    except(Exception, psycopg2.DatabaseError) as error:
        # print(error)
        return {"status", "SELECT ERROR"}


# Check if member with specified id and password exists, if not insert
def is_member(id, passwd, time):
    global cur
    try:
        cur.execute("select * from members where id = %s::numeric and cryptpwd=crypt(%s::text, cryptpwd);",
                    (id, passwd,))
        row = cur.fetchone()
        if row is not None:
            return {"status": "OK"}
        else:
            # Try to insert new member
            cur.execute(
                '''INSERT INTO members(id, cryptpwd, lastactivity) VALUES(%s::numeric, crypt(%s::text, gen_salt('md5')),
                 timestamp_cast(%s::int));''',
                (id, passwd, time))
            return {"status": "OK"}
    except(Exception, psycopg2.DatabaseError) as error:
        return {"status": "wrong password"}


# Check if member with specified id is still active
def is_active(id, time):
    global cur
    try:
        cur.execute(
            '''SELECT active((SELECT members.lastactivity FROM members WHERE id=%s::numeric), timestamp_cast(%s::int) );''',
            (id, time))
        row = cur.fetchone()
        if row is not None:
            if row[0] is False:
                return {"status": "member is not active"}
            return {"status": "OK"}
        return {"status": "member is not active"}
    except(Exception, psycopg2.DatabaseError) as error:
        return {"status": "unexisting member"}


# Check if action with specified id exists
def is_action(id):
    global cur
    try:
        cur.execute('''SELECT * FROM actions WHERE id=%s::numeric;''', (id,))
        row = cur.fetchone()

        if row is not None:
            return {"status": "OK"}
        return {"status": "action does not exist"}
    except(Exception, psycopg2.DatabaseError) as error:
        # print(error)
        return {"status": "action does not exist"}


# Check if project with specified id exists, if not insert
def is_project(id, time=None, authority=None):
    global cur
    try:
        if authority is not None:
            cur.execute('''SELECT * FROM project WHERE id=%s::numeric AND authority=%s::numeric;''',
                        (id, authority))
            row = cur.fetchone()
            if row is not None:
                return {"status": "OK"}
            else:
                # Try to insert new project
                cur.execute('''INSERT INTO project(id, creationtime, authority) VALUES(%s::numeric, 
                timestamp_cast(%s::int), %s::numeric) ''',
                            (id, time, authority))
                return {"status": "OK"}

        else:
            cur.execute('''SELECT * FROM project WHERE id=%s::numeric;''', (id,))
            row = cur.fetchone()
            if row is not None:
                return {"status": "OK"}
            else:
                return {"status": "wrong authority"}
    except(Exception, psycopg2.DatabaseError) as error:
        return {"status": "wrong authority"}


# Create new leader with id and password
def create_leader(time, passwd, id):
    try:
        cur.execute(
            '''INSERT INTO members(id, cryptpwd, lastactivity, leader) VALUES 
            (%s::numeric, crypt(%s::text, gen_salt('md5')) , timestamp_cast(%s::int), %s);''',
            (id, str(passwd), time, True))
        return {"status": "OK"}
    except(Exception, psycopg2.DatabaseError) as error:
        # print(error)

        return {"status": "wrong id"}


# Create new action
def new_action(timestamp, member, passwd, action, project, actype, authority=None):
    global cur
    try:
        message = is_member(member, passwd, timestamp)
        if message["status"] != "OK":
            return message
        else:
            # If member and password are correct
            message = is_active(member, timestamp)
            if message["status"] != "OK":
                return message
            else:
                # If member is active
                message = is_project(project, timestamp, authority)
                if message["status"] != "OK":
                    return message
                else:
                    # If project exists
                    cur.execute(
                        '''INSERT INTO actions(id, memberid, projectid, action, time) VALUES(%s::numeric, %s::numeric, 
                        %s::numeric, %s::action_type_domain, timestamp_cast(%s::int)) ;''',
                        (action, member, project, actype, timestamp))
                    return {"status": "OK"}
    except(Exception, psycopg2.DatabaseError) as error:
        # print(error)

        return {"status": "wrong id"}


# create new vote
def new_vote(timestamp, member, passwd, action, votetype='u'):
    global cur
    try:
        message = is_member(member, passwd, timestamp)
        if message["status"] != "OK":
            return message
        else:
            # If member and password are correct
            message = is_active(member, timestamp)
            if message["status"] != "OK":
                return message
            else:
                # If member is active
                message = is_action(action)
                if message["status"] != "OK":
                    return message
                else:
                    # If action exists
                    cur.execute(
                        '''INSERT INTO votes(actionid, memberid, vote, time) VALUES(%s::numeric, %s::numeric,
                         %s::vote_domain, timestamp_cast(%s::int)) ;''',
                        (action, member, votetype, timestamp))
                    return {"status": "OK"}
    except(Exception, psycopg2.DatabaseError) as error:
        # print(error)
        return {"status": "wrong ids"}


# Run SELECT
def trolls(timestamp):
    global cur
    try:
        cur.execute(
            '''SELECT id::int, upvotes::int, downvotes::int, active(lastactivity, timestamp_cast(%s::int))::boolean FROM members WHERE downvotes>upvotes ORDER BY upvotes-downvotes;''',
            (timestamp,))
        row = cur.fetchall()
        return {"status": "OK", "data": row}
    except(Exception, psycopg2.DatabaseError) as error:
        # print(error)
        return {"status": "error"}


# Run SELECT
def actions(timestamp, member, passwd, actiontype=None, project=None, authority=None):
    global cur

    try:
        message = is_leader(member, passwd)
        if message["status"] != "OK":
            return message
        else:
            # If member is leader and password is correct
            message = is_active(member, timestamp)
            if message["status"] != "OK":
                return message
            else:
                # If member is active
                if actiontype is not None:
                    # If type is specified
                    if project is not None:
                        # If project is specified
                        if authority is not None:
                            # If authority is specified
                            cur.execute(
                                ''' WITH UP AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS ups  
                                FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id)
                                 WHERE votes.vote='u' AND action_type(actions.action)=%s::varchar AND actions.projectid=%s::numeric AND project.authority=%s::numeric
                                  GROUP BY actions.id, actions.action, actions.projectid, project.authority ),
                                   DOWN AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS downs 
                                    FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id) 
                                    WHERE votes.vote='d' AND action_type(actions.action)=%s::varchar AND actions.projectid=%s::numeric AND project.authority=%s::numeric
                                     GROUP BY actions.id, actions.action, actions.projectid, project.authority )
                                      SELECT id, actiontype, pid, pa, ups, downs FROM UP JOIN DOWN USING(id, actiontype, pid, pa) ORDER BY id;''',
                                (actiontype, project, authority, actiontype, project, authority))
                        else:
                            # If only type and project are specified
                            cur.execute(
                                ''' WITH UP AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS ups  
                                FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id)
                                 WHERE votes.vote='u' AND action_type(actions.action)=%s::varchar AND actions.projectid=%s::numeric 
                                  GROUP BY actions.id, actions.action, actions.projectid, project.authority ),
                                   DOWN AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS downs 
                                    FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id) 
                                    WHERE votes.vote='d' AND action_type(actions.action)=%s::varchar AND actions.projectid=%s::numeric 
                                     GROUP BY actions.id, actions.action, actions.projectid, project.authority )
                                      SELECT id, actiontype, pid, pa, ups, downs FROM UP JOIN DOWN USING(id, actiontype, pid, pa) ORDER BY id;''',
                                (actiontype, project, actiontype, project))
                    else:
                        # If only typeis specified
                        cur.execute(
                            ''' WITH UP AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS ups  
                                 FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id)
                                  WHERE votes.vote='u' AND action_type(actions.action)=%s::varchar 
                                   GROUP BY actions.id, actions.action, actions.projectid, project.authority ),
                                    DOWN AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS downs 
                                     FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id) 
                                     WHERE votes.vote='d' AND action_type(actions.action)=%s::varchar 
                                      GROUP BY actions.id, actions.action, actions.projectid, project.authority )
                                       SELECT id, actiontype, pid, pa, ups, downs FROM UP JOIN DOWN USING(id, actiontype, pid, pa) ORDER BY id;''',
                            (actiontype, actiontype))
                else:
                    if project is not None:
                        if authority is not None:
                            # If only authority and project are specified
                            cur.execute(
                                ''' WITH UP AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS ups  
                                FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id)
                                 WHERE votes.vote='u'  AND actions.projectid=%s::numeric AND project.authority=%s::numeric
                                  GROUP BY actions.id, actions.action, actions.projectid, project.authority ),
                                   DOWN AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS downs 
                                    FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id) 
                                    WHERE votes.vote='d'  AND actions.projectid=%s::numeric AND project.authority=%s::numeric
                                     GROUP BY actions.id, actions.action, actions.projectid, project.authority )
                                      SELECT id, actiontype, pid, pa, ups, downs FROM UP JOIN DOWN USING(id, actiontype, pid, pa) ORDER BY id;''',
                                (project, authority, project, authority))
                        else:
                            # If only project is specified
                            cur.execute(
                                ''' WITH UP AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS ups  
                               FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id)
                                WHERE votes.vote='u' AND  actions.projectid=%s::numeric
                                 GROUP BY actions.id, actions.action, actions.projectid, project.authority ),
                                  DOWN AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS downs 
                                   FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id) 
                                   WHERE votes.vote='d' AND actions.projectid=%s::numeric 
                                    GROUP BY actions.id, actions.action, actions.projectid, project.authority )
                                     SELECT id, actiontype, pid, pa, ups, downs FROM UP JOIN DOWN USING(id, actiontype, pid, pa) ORDER BY id;''',
                                (project, project))
                    else:
                        # else
                        cur.execute(
                            ''' WITH UP AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS ups  
                                FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id)
                                 WHERE votes.vote='u' 
                                  GROUP BY actions.id, actions.action, actions.projectid, project.authority ),
                                   DOWN AS (SELECT actions.id AS id, action_type(actions.action) AS actiontype, actions.projectid AS pid, project.authority AS pa, COUNT(*) AS downs 
                                    FROM actions JOIN project ON(actions.projectid=project.id) LEFT JOIN votes ON (votes.actionid=actions.id) 
                                    WHERE votes.vote='d'
                                     GROUP BY actions.id, actions.action, actions.projectid, project.authority )
                                      SELECT id, actiontype, pid, pa, ups, downs FROM UP JOIN DOWN USING(id, actiontype, pid, pa) ORDER BY  id;''')
                row = cur.fetchall()
                return {"status": "OK", "data": row}

    except(Exception, psycopg2.DatabaseError) as error:
        return {"status": "select error"}


# RUN SELECT
def votes(timestamp, member, passwd, action=None, project=None):
    global cur
    try:
        message = is_leader(member, passwd)
        if message["status"] != "OK":
            return message
        else:
            # IF member is a leader and password is correct
            message = is_active(member, timestamp)
            if message["status"] != "OK":
                return message
            else:
               # If member is active
                if project is not None:
                    #If project is specified
                    cur.execute(
                        '''with                       
                                 up as (select id as id, count(vote) as ups from
                                 members m left join (select * from votes v where vote = 'u' and actionid in (select id from actions  where projectid = %s::numeric))subq1 on (m.id = subq1.memberid) group by id),
                                 
                                 down as (select id as id, count(vote) as downs from
                                 members m left join (select * from votes v where vote = 'd' and action_id in (select id from actions where projectid = %s::numeric))subq2 on (m.id = subq2.memberid) group by id)
                         select cast(id as int), ups, downs from up join down using(id) ORDER BY id;''',
                        (project, project))
                    row = cur.fetchall()
                    return {"status": "OK", "data": row}
                elif action is not None:
                    #If action is specified
                    cur.execute('''with                       
                               up as (select id as id, count(vote) as ups from
                               members m left join (select * from votes v where vote = 'u' and actionid in (select id from actions  where id = %s::numeric))subq1 on (m.id = subq1.memberid) group by id),
                               
                               down as (select id as id, count(vote) as downs from
                               members m left join (select * from votes v where vote = 'd' and actionid in (select id from actions where id = %s::numeric))subq2 on (m.id = subq2.memberid) group by id)
                       select cast(id as int), ups, downs from up join down using(id) ORDER BY id;''', (action, action))

                    row = cur.fetchall()
                    return {"status": "OK", "data": row}
                else:
                    cur.execute('''with                       
                               up as (select id as id, count(vote) as ups from
                               members m left join (select * from votes v where vote = 'u' )subq1 on (m.id = subq1.memberid) group by id),
                               
                               down as (select id as id, count(vote) as downs from
                               members m left join (select * from votes v where vote = 'd')subq2 on (m.id = subq2.memberid) group by id)
                       select cast(id as int), ups, downs from up join down using(id) ORDER BY id;''', (action, action))

                row = cur.fetchall()
                return {"status": "OK", "data": row}
    except(Exception, psycopg2.DatabaseError) as error:
        return {"status": "SELECT ERROR"}


# Run SELECT
def projects(timestamp, member, passwd, authority=None):
    global cur
    try:
        message = is_leader(member, passwd)
        if message["status"] != "OK":
            return (message)
        else:
            # If member is a leader  and password is correct
            message = is_active(message, timestamp)
            if message["status"] != "OK":
                return message
            else:
                # If member is active
                if authority is not None:
                    # If authority is specified
                    cur.execute(
                        '''select id, authority FROM project WHERE  authority=%s::numeric ORDER BY id;''', (authority,))
                    row = cur.fetchall()
                    return {"status": "OK", "data": row}
                else:
                    cur.execute(
                        '''select id, authority FROM project ORDER BY id;''')
                    row = cur.fetchall()
                    return {"status": "OK", "data": row}
    except(Exception, psycopg2.DatabaseError) as error:
        return {"status": "SELECT ERROR"}


# Convert to variable or None
def taken_args(dictionary, elem):
    if elem in dictionary:
        return int(dictionary[elem])
    return None


# Convert to variable or None
def taken_args_str(dictionary, elem):
    if elem in dictionary:
        return str(dictionary[elem])
    return None


if sys.argv[1] == "--init":
    line = sys.stdin.readline()
    js = json.loads(line)
    if "open" in js:
        if js["open"]["login"] == "init":
            open_connection(js["open"]["database"], js["open"]["login"], js["open"]["password"])
            while True:
                line = sys.stdin.readline()
                js = json.loads(line)
                if "leader" in js:
                    print(json.dumps(create_leader(js["leader"]["timestamp"], js["leader"]["password"], js["leader"]["member"])))
                else:
                    print(json.dumps('{"status": "undefined function"}'))
elif sys.argv[1] == "--app":
    line = sys.stdin.readline()
    opendata = json.loads(line)
    if "open" in opendata:
        if opendata["open"]["login"] == "app":
            open_connection(opendata["open"]["database"], opendata["open"]["login"], opendata["open"]["password"])
            while True:
                line = sys.stdin.readline()
                js = json.loads(line)
                if "support" in js:
                    print(json.dumps(new_action(int(js["support"]["timestamp"]), int(js["support"]["member"]),
                                     str(js["support"]["password"]),
                                     int(js["support"]["action"]), int(js["support"]["project"]), 's',
                                     taken_args(js["support"], "authority"))))
                elif "protest" in js:
                    print(json.dumps(new_action(int(js["protest"]["timestamp"]), int(js["protest"]["member"]),
                                     str(js["protest"]["password"]),
                                     int(js["protest"]["action"]), int(js["protest"]["project"]), 'p',
                                     taken_args(js["protest"], "authority"))))

                elif "upvote" in js:
                    print(json.dumps(new_vote(int(js["upvote"]["timestamp"]), int(js["upvote"]["member"]),
                                   str(js["upvote"]["password"]),
                                   int(js["upvote"]["action"]))))
                elif "downvote" in js:
                    print(json.dumps(new_vote(int(js["downvote"]["timestamp"]), int(js["downvote"]["member"]),
                                   str(js["downvote"]["password"]),
                                   int(js["downvote"]["action"]), 'd')))
                elif "actions" in js:
                    print(json.dumps(actions(int(js["actions"]["timestamp"]), int(js["actions"]["member"]),
                                  str(js["actions"]["password"]),
                                  taken_args_str(js["actions"], "type"), taken_args(js["actions"], "project"),
                                  taken_args(js["actions"], "authority"))))
                elif "projects" in js:
                    print(json.dumps(projects(int(js["projects"]["timestamp"]), int(js["projects"]["member"]),
                                   str(js["projects"]["password"]),
                                   taken_args(js["projects"], "authority"))))
                elif "votes" in js:
                    print(json.dumps(votes(int(js["votes"]["timestamp"]), int(js["votes"]["member"]), str(js["votes"]["password"]),
                                taken_args(js["votes"], "action"), taken_args(js["votes"], "project"))))
                elif "trolls" in js:
                    print(json.dumps(trolls(int(js["trolls"]["timestamp"]))))
                else:
                    print(json.dumps('{"status": "undefined function"}'))
