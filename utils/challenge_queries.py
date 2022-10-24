CHALLENGE_LIST_QUERY = """
SELECT DISTINCT 
  "challenges"."id", 
  "challenges"."name", 
  "challenges"."photo", 
  "challenges"."updated_at", 
  "challenges"."states", 
  "challenges"."creator_id", 
  "challenges"."parameters", 
  "challenges"."winners_count",
  (select count(*) from challenge_reports 
     where challenge_reports.challenge_id = challenges.id 
       and "state" IN ('A', 'W')
  ) AS "approved_reports_amount", 
  (select string_agg( f, ', ') from (
    select 1 c, 'Вы создатель челленджа' f from challenges c 
      where c.id = challenges.id 
        and c.creator_id = %s and c.organized_by_id <> %s
    union
    select 2, 'Вы организатор челленджа' from challenges c 
      where c.id = challenges.id 
        and c.organized_by_id = %s
    union
    select 2, 'Вы организатор челленджа' from challenge_participants c 
      where c.challenge_id = challenges.id 
        and c.user_participant_id = %s 
        and 'O' = any( c.mode)
    union
    select 4, 'Можно отправить отчёт' from challenges c 
      where c.id = challenges.id 
        and 'C' != all( c.states) 
        --and c.organized_by_id <> %s -- для prod включить!
        and not exists (
            select 1 from challenge_reports c1
              join challenge_participants c2 on c2.id = c1.participant_id
              where c1.challenge_id = challenges.id 
                and c2.user_participant_id = %s) -- проверка на то, что отчет уже отправлялся. если челлендж допускает несколько отчетов, то надо отключить
    union
    select 3, 
      CASE 
        WHEN c.state IN ('S', 'F', 'R') THEN 'Отчёт отправлен' 
        WHEN c.state IN ('A') THEN 'Отчёт подтверждён' 
        WHEN c.state IN ('D') THEN 'Отчёт отклонён' 
        WHEN c.state IN ('W') THEN 'Получено вознаграждение' 
      END
    from challenge_reports c
      where c.challenge_id = challenges.id and c.participant_id in 
        (select id from challenge_participants c1 where c1.challenge_id = challenges.id and c1.user_participant_id = %s)
    order by c
    ) a 
  ) AS "status", 
  (challenges.organized_by_id = %s -- проверка на организатора
     and exists (
       SELECT 1 from challenge_reports c 
         where c.challenge_id = challenges.id AND c."state" IN ('S', 'F', 'R'))) AS "is_new_reports", 
  challenges.start_balance AS "fund",
    EXISTS(select 
            l1.id,  
            l1.user_id, 
            l1.object_id, 
            ct1.model, 
            lk1.code from likes l1 
        join django_content_type ct1 on (l1.content_type_id = ct1.id) 
        join like_kind lk1 on (lk1.id = l1.like_kind_id)
        where ct1.model = 'challenge' and l1.object_id=challenges.id 
        and l1.is_liked=true and lk1.code = 'like' and l1.user_id = %s) as "user_liked",
    (select 
        ls1.like_counter
    from like_statistics ls1
    join django_content_type ct2 on (ls1.content_type_id = ct2.id) 
    join like_kind lk2 on (lk2.id = ls1.like_kind_id)
    where ct2.model = 'challenge' and lk2.code = 'like' and ls1.object_id = challenges.id) as "likes_amount",
    (select
        lcs1.comment_counter
    from like_comment_statistics lcs1
    join django_content_type ct3 on (lcs1.content_type_id = ct3.id)
    where ct3.model = 'challenge' and lcs1.object_id = challenges.id) as "comments_amount"
FROM challenges
ORDER BY 1 DESC
OFFSET %s LIMIT %s
"""

CHALLENGE_ACTIVE_LIST_QUERY = """
SELECT DISTINCT 
  "challenges"."id", 
  "challenges"."name", 
  "challenges"."photo", 
  "challenges"."updated_at", 
  "challenges"."states", 
  "challenges"."creator_id", 
  "challenges"."parameters", 
  "challenges"."winners_count",
  (select count(*) from challenge_reports 
     where challenge_reports.challenge_id = challenges.id 
       and "state" IN ('A', 'W')
  ) AS "approved_reports_amount", 
  (select string_agg( f, ', ') from (
    select 1 c, 'Вы создатель челленджа' f from challenges c 
      where c.id = challenges.id 
        and c.creator_id = %s and c.organized_by_id <> %s
    union
    select 2, 'Вы организатор челленджа' from challenges c 
      where c.id = challenges.id 
        and c.organized_by_id = %s
    union
    select 2, 'Вы организатор челленджа' from challenge_participants c 
      where c.challenge_id = challenges.id 
        and c.user_participant_id = %s 
        and 'O' = any( c.mode)
    union
    select 4, 'Можно отправить отчёт' from challenges c 
      where c.id = challenges.id 
        and 'C' != all( c.states) 
        --and c.organized_by_id <> %s -- для prod включить!
        and not exists (
            select 1 from challenge_reports c1
              join challenge_participants c2 on c2.id = c1.participant_id
              where c1.challenge_id = challenges.id 
                and c2.user_participant_id = %s) -- проверка на то, что отчет уже отправлялся. если челлендж допускает несколько отчетов, то надо отключить
    union
    select 3, 
      CASE 
        WHEN c.state IN ('S', 'F', 'R') THEN 'Отчёт отправлен' 
        WHEN c.state IN ('A') THEN 'Отчёт подтверждён' 
        WHEN c.state IN ('D') THEN 'Отчёт отклонён' 
        WHEN c.state IN ('W') THEN 'Получено вознаграждение' 
      END
    from challenge_reports c
      where c.challenge_id = challenges.id and c.participant_id in 
        (select id from challenge_participants c1 where c1.challenge_id = challenges.id and c1.user_participant_id = %s)
    order by c
    ) a 
  ) AS "status", 
  (challenges.organized_by_id = %s -- проверка на организатора
     and exists (
       SELECT 1 from challenge_reports c 
         where c.challenge_id = challenges.id AND c."state" IN ('S', 'F', 'R'))) AS "is_new_reports", 
  challenges.start_balance AS "fund",
    EXISTS(select 
            l1.id,  
            l1.user_id, 
            l1.object_id, 
            ct1.model, 
            lk1.code from likes l1 
        join django_content_type ct1 on (l1.content_type_id = ct1.id) 
        join like_kind lk1 on (lk1.id = l1.like_kind_id)
        where ct1.model = 'challenge' and l1.object_id=challenges.id 
        and l1.is_liked=true and lk1.code = 'like' and l1.user_id = %s) as "user_liked",
    (select 
        ls1.like_counter
    from like_statistics ls1
    join django_content_type ct2 on (ls1.content_type_id = ct2.id) 
    join like_kind lk2 on (lk2.id = ls1.like_kind_id)
    where ct2.model = 'challenge' and lk2.code = 'like' and ls1.object_id = challenges.id) as "likes_amount",
    (select
        lcs1.comment_counter
    from like_comment_statistics lcs1
    join django_content_type ct3 on (lcs1.content_type_id = ct3.id)
    where ct3.model = 'challenge' and lcs1.object_id = challenges.id) as "comments_amount"
FROM challenges
WHERE NOT ('C'=any("challenges"."states"))
ORDER BY 1 DESC
OFFSET %s LIMIT %s
"""

CHALLENGE_PK_QUERY = """
SELECT 
  "challenges"."id", 
  "challenges"."name", 
  "challenges"."photo", 
  "challenges"."updated_at", 
  "challenges"."states", 
  "challenges"."creator_id", 
  "challenges"."parameters", 
  "challenges"."winners_count",
  "challenges"."end_at",
  "challenges"."description",
  "p"."first_name" AS "first_name",
  "p"."surname" AS "surname",
  "p"."organization_id" AS "organization_pk",
  "p"."photo" AS "profile_photo",
  "p"."tg_name" AS "tg_name",
  (select count(*) from challenge_reports 
     where challenge_reports.challenge_id = challenges.id 
       and "state" IN ('A', 'W')
  ) AS "approved_reports_amount", 
  (select string_agg( f, ', ') from (
    select 1 c, 'Вы создатель челленджа' f from challenges c 
      where c.id = challenges.id 
        and c.creator_id = %s and c.organized_by_id <> %s
    union
    select 2, 'Вы организатор челленджа' from challenges c 
      where c.id = challenges.id 
        and c.organized_by_id = %s
    union
    select 2, 'Вы организатор челленджа' from challenge_participants c 
      where c.challenge_id = challenges.id 
        and c.user_participant_id = %s 
        and 'O' = any( c.mode)
    union
    select 4, 'Можно отправить отчёт' from challenges c 
      where c.id = challenges.id 
        and 'C' != all( c.states) 
        --and c.organized_by_id <> %s -- для prod включить!
        and not exists (
            select 1 from challenge_reports c1
              join challenge_participants c2 on c2.id = c1.participant_id
              where c1.challenge_id = challenges.id
                and c2.user_participant_id = %s) -- проверка на то, что отчет уже отправлялся. если челлендж допускает несколько отчетов, то надо отключить
    union
    select 3, 
      CASE 
        WHEN c.state IN ('S', 'F', 'R') THEN 'Отчёт отправлен' 
        WHEN c.state IN ('A') THEN 'Отчёт подтверждён' 
        WHEN c.state IN ('D') THEN 'Отчёт отклонён' 
        WHEN c.state IN ('W') THEN 'Получено вознаграждение' 
      END
    from challenge_reports c
      where c.challenge_id = challenges.id and c.participant_id in 
        (select id from challenge_participants c1 where c1.challenge_id = challenges.id and c1.user_participant_id = %s)
    order by c
    ) a 
  ) AS "status", 
  (challenges.organized_by_id = %s -- проверка на организатора
     and exists (
       SELECT 1 from challenge_reports c 
         where c.challenge_id = challenges.id AND c."state" IN ('S', 'F', 'R'))) AS "is_new_reports", 
  challenges.start_balance AS "fund",
    EXISTS(select 
            l1.id,  
            l1.user_id, 
            l1.object_id, 
            ct1.model, 
            lk3.code from likes l1 
        join django_content_type ct1 on (l1.content_type_id = ct1.id) 
        join like_kind lk3 on (lk3.id = l1.like_kind_id)
        where ct1.model = 'challenge' and l1.object_id=challenges.id 
            and l1.is_liked=true and lk3.code = 'like' and l1.user_id = %s) as "user_liked",
    (select 
        ls1.like_counter
    from like_statistics ls1
    join django_content_type ct2 on (ls1.content_type_id = ct2.id) 
    join like_kind lk4 on (lk4.id = ls1.like_kind_id)
    where ct2.model = 'challenge' and lk4.code = 'like' and ls1.object_id = challenges.id) as "likes_amount",
    (select
        lcs1.comment_counter
    from like_comment_statistics lcs1
    join django_content_type ct3 on (lcs1.content_type_id = ct3.id)
    where ct3.model = 'challenge' and lcs1.object_id = challenges.id) as "comments_amount"
FROM challenges
JOIN auth_user au ON (challenges.creator_id = au.id)
JOIN profiles p ON (p.user_id = challenges.creator_id)
WHERE "challenges"."id" = %s
"""
